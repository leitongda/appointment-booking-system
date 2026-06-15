"""门店经营指标预聚合定时任务

平台经营看台的数据底座。每日凌晨聚合前一天数据，并补算近 N 天
（应对预约状态延迟变更：签到/完成/爽约在就诊后才发生）。

口径：
- stat_date = Schedule.schedule_date（就诊日）
- 门店归属 = Schedule.store_id（Appointment 无 store_id）
- 计数与营收均排除软删除医生（与 RevenueService 一致）
- 营收/已到院状态集合统一引用 constants.VISITED_STATUSES / REVENUE_STATUSES（含历史 3）
- 复诊判断：该患者在同门店此前（schedule_date < D，严格小于、不含当天）已有 status>=2 就诊记录
  （批量近似，与 VisitTypeService.is_follow_up_visit 基本一致；同一天多次就诊不互判复诊，
   这是聚合层有意的性能取舍——逐条精确判断会退回 RevenueService 的 N 次查询）
- 日期边界用 date.today()（服务器本地日，Celery 配置 timezone=Asia/Shanghai）
"""
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, case, delete, func, select

from app.celery_app import celery_app
from app.constants.appointment import CANCELLED_STATUSES, REVENUE_STATUSES, VISITED_STATUSES
from app.db.session import get_sync_db
from app.models.appointment import Appointment
from app.models.consultation_fee import ConsultationFeeType, DoctorConsultationFee
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.store_metric import StoreDailyMetric

logger = logging.getLogger(__name__)

# 语义集合统一引用 constants，避免硬编码漂移（详见 constants/appointment.py）
_VISIT_STATUSES = list(VISITED_STATUSES)
_REVENUE_STATUSES = list(REVENUE_STATUSES)
_CANCEL_STATUSES = list(CANCELLED_STATUSES)


def _aggregate_one_day(db, target_date: date) -> int:
    """聚合单日所有门店指标，返回写入/更新的门店记录数。幂等（先删后插）。"""
    # ========== 1. 计数聚合（一条 SQL） ==========
    count_rows = db.execute(
        select(
            Schedule.store_id,
            Store.tenant_id,
            func.count(Appointment.id).label("appointment_count"),
            func.sum(case((Appointment.status.in_(_VISIT_STATUSES), 1), else_=0)).label("visit_count"),
            func.sum(case((Appointment.status == 5, 1), else_=0)).label("completed_count"),
            func.sum(case((Appointment.status == 8, 1), else_=0)).label("no_show_count"),
            func.sum(case((Appointment.status.in_(_CANCEL_STATUSES), 1), else_=0)).label("cancelled_count"),
        )
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Store, Schedule.store_id == Store.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(and_(
            Schedule.schedule_date == target_date,
            Doctor.deleted_at.is_(None),
        ))
        .group_by(Schedule.store_id, Store.tenant_id)
    ).all()

    if not count_rows:
        # 当天无任何预约：清理可能存在的旧快照
        db.execute(
            delete(StoreDailyMetric).where(StoreDailyMetric.stat_date == target_date)
        )
        return 0

    store_ids = [r.store_id for r in count_rows]
    tenant_by_store = {r.store_id: r.tenant_id for r in count_rows}
    counts_by_store = {
        r.store_id: {
            "appointment_count": int(r.appointment_count or 0),
            "visit_count": int(r.visit_count or 0),
            "completed_count": int(r.completed_count or 0),
            "no_show_count": int(r.no_show_count or 0),
            "cancelled_count": int(r.cancelled_count or 0),
        }
        for r in count_rows
    }

    # ========== 2. 历史就诊集合（用于复诊 & 新患者判断） ==========
    # 当天涉及的患者
    today_rows = db.execute(
        select(Appointment.patient_id, Schedule.store_id)
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(and_(
            Schedule.schedule_date == target_date,
            Appointment.status.in_(_VISIT_STATUSES),
            Doctor.deleted_at.is_(None),
        ))
    ).all()
    today_patients = {r.patient_id for r in today_rows}

    # 这些患者在更早日期（< target_date）已就诊过的 (patient, store)
    earlier_set = set()
    if today_patients:
        earlier_rows = db.execute(
            select(Appointment.patient_id, Schedule.store_id)
            .select_from(Appointment)
            .join(Schedule, Appointment.schedule_id == Schedule.id)
            .join(Doctor, Schedule.doctor_id == Doctor.id)
            .where(and_(
                Schedule.schedule_date < target_date,
                Appointment.status.in_(_VISIT_STATUSES),
                Doctor.deleted_at.is_(None),
                Appointment.patient_id.in_(today_patients),
            ))
        ).all()
        earlier_set = {(r.patient_id, r.store_id) for r in earlier_rows}

    # 新患者数：当天首次到该门店（此前无就诊记录），同一患者同店只计一次
    new_patient_by_store = defaultdict(int)
    seen_today = set()
    for patient_id, store_id in today_rows:
        key = (patient_id, store_id)
        if key in seen_today:
            continue
        seen_today.add(key)
        if key not in earlier_set:
            new_patient_by_store[store_id] += 1

    # ========== 3. 营收批量计算 ==========
    revenue_by_store = defaultdict(lambda: Decimal("0"))

    # 当天产生营收的预约明细
    rev_rows = db.execute(
        select(Appointment.patient_id, Appointment.doctor_id, Schedule.store_id, Schedule.appointment_type)
        .select_from(Appointment)
        .join(Schedule, Appointment.schedule_id == Schedule.id)
        .join(Doctor, Schedule.doctor_id == Doctor.id)
        .where(and_(
            Schedule.schedule_date == target_date,
            Appointment.status.in_(_REVENUE_STATUSES),
            Doctor.deleted_at.is_(None),
        ))
    ).all()

    if rev_rows:
        # fee_type: code -> id
        fee_type_map = {
            ft.code: ft.id
            for ft in db.execute(
                select(ConsultationFeeType).where(ConsultationFeeType.status == 1)
            ).scalars()
        }
        # doctor_fee: (doctor_id, fee_type_id) -> (initial_fee, follow_up_fee)
        involved_doctor_ids = {r.doctor_id for r in rev_rows}
        doctor_fee_map = {}
        if involved_doctor_ids:
            for df in db.execute(
                select(DoctorConsultationFee).where(
                    and_(
                        DoctorConsultationFee.status == 1,
                        DoctorConsultationFee.doctor_id.in_(involved_doctor_ids),
                    )
                )
            ).scalars():
                doctor_fee_map[(df.doctor_id, df.fee_type_id)] = (df.initial_fee, df.follow_up_fee)

        for r in rev_rows:
            ft_id = fee_type_map.get(r.appointment_type or "normal")
            if not ft_id:
                continue
            fees = doctor_fee_map.get((r.doctor_id, ft_id))
            if not fees:
                continue
            is_follow_up = (r.patient_id, r.store_id) in earlier_set
            fee = fees[1] if is_follow_up else fees[0]  # follow_up_fee / initial_fee
            revenue_by_store[r.store_id] += (fee or Decimal("0"))

    # ========== 4. 幂等写入（先删后插） ==========
    db.execute(
        delete(StoreDailyMetric).where(
            and_(
                StoreDailyMetric.stat_date == target_date,
                StoreDailyMetric.store_id.in_(store_ids),
            )
        )
    )

    now = datetime.utcnow()
    objects = []
    for store_id in store_ids:
        c = counts_by_store[store_id]
        objects.append(StoreDailyMetric(
            tenant_id=tenant_by_store.get(store_id),
            store_id=store_id,
            stat_date=target_date,
            appointment_count=c["appointment_count"],
            visit_count=c["visit_count"],
            completed_count=c["completed_count"],
            no_show_count=c["no_show_count"],
            cancelled_count=c["cancelled_count"],
            new_patient_count=new_patient_by_store.get(store_id, 0),
            revenue=revenue_by_store.get(store_id, Decimal("0")),
            created_at=now,
            updated_at=now,
        ))
    db.add_all(objects)
    return len(objects)


@celery_app.task(
    name="app.tasks.store_metric_task.aggregate_store_daily_metrics",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def aggregate_store_daily_metrics(stat_date: str = None, backfill_days: int = 3):
    """聚合门店每日经营指标。

    Args:
        stat_date: 指定单日（YYYY-MM-DD）；不传则聚合昨天 + 补算近 backfill_days 天
        backfill_days: 不传 stat_date 时，向前补算的天数（含昨天）
    """
    logger.info("[定时任务] 开始聚合门店经营指标 stat_date=%s backfill_days=%s", stat_date, backfill_days)

    if stat_date:
        dates = [date.fromisoformat(stat_date)]
    else:
        yesterday = date.today() - timedelta(days=1)
        dates = [yesterday - timedelta(days=i) for i in range(backfill_days)]

    total = 0
    with get_sync_db() as db:
        for d in dates:
            try:
                n = _aggregate_one_day(db, d)
                total += n
                logger.info("[定时任务] 门店经营指标聚合 %s: %d 条门店记录", d.isoformat(), n)
            except Exception as e:
                logger.exception("[定时任务] 门店经营指标聚合失败 %s: %s", d.isoformat(), e)
                raise

    logger.info("[定时任务] 门店经营指标聚合完成，共 %d 条记录", total)
    return {"days": len(dates), "records": total}
