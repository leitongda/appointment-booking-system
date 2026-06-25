"""考勤每日统计 Celery 任务"""
import logging
from datetime import date, timedelta

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db.session import sync_engine
from app.models.attendance import (
    AttendanceRecord,
    AttendanceShift,
    AttendanceStatDaily,
    AttendanceLeaveRequest,
)
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


@celery_app.task(
    name="attendance_daily_stat",
    queue="scheduled",
    max_retries=3,
    default_retry_delay=60,
)
def attendance_daily_stat(target_date_str: str | None = None):
    """统计指定日期的考勤数据

    为每个有打卡记录的员工生成每日统计：
    - 正常/迟到/早退/缺勤状态
    - 工作时长
    - 迟到/早退分钟数
    """
    if target_date_str:
        target_date = date.fromisoformat(target_date_str)
    else:
        target_date = date.today() - timedelta(days=1)  # 默认统计昨天

    logger.info("开始考勤统计: %s", target_date)

    with Session(sync_engine) as db:
        # 获取所有租户
        tenants = db.execute(
            select(Tenant).where(Tenant.status == 1)
        ).scalars().all()

        total_stats = 0
        for tenant in tenants:
            count = _process_tenant_stats(db, tenant.id, target_date)
            total_stats += count

        db.commit()
        logger.info("考勤统计完成: %s, 共处理 %d 条", target_date, total_stats)

    return {"date": str(target_date), "count": total_stats}


def _process_tenant_stats(db: Session, tenant_id: str, target_date: date) -> int:
    """处理单个租户的考勤统计"""
    # 获取该日所有打卡记录
    records = db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.tenant_id == tenant_id,
                AttendanceRecord.check_date == target_date,
            )
        )
    ).scalars().all()

    if not records:
        return 0

    # 获取班次信息
    shift_ids = {r.shift_id for r in records if r.shift_id}
    shifts = {}
    if shift_ids:
        shift_list = db.execute(
            select(AttendanceShift).where(AttendanceShift.id.in_(shift_ids))
        ).scalars().all()
        shifts = {s.id: s for s in shift_list}

    # 获取请假记录
    leave_requests = db.execute(
        select(AttendanceLeaveRequest).where(
            and_(
                AttendanceLeaveRequest.tenant_id == tenant_id,
                AttendanceLeaveRequest.status == "approved",
                AttendanceLeaveRequest.start_date <= target_date,
                AttendanceLeaveRequest.end_date >= target_date,
            )
        )
    ).scalars().all()
    leave_account_ids = {r.account_id for r in leave_requests}

    count = 0
    for record in records:
        # 处理预期记录：如果没有实际打卡，标记为缺勤
        if record.status == "expected" and not record.check_in_time:
            record.status = "absent"
            # 继续生成统计记录

        # 检查是否已有统计记录
        existing = db.execute(
            select(AttendanceStatDaily).where(
                and_(
                    AttendanceStatDaily.account_id == record.account_id,
                    AttendanceStatDaily.date == target_date,
                )
            )
        ).scalar_one_or_none()

        if existing:
            stat = existing
        else:
            stat = AttendanceStatDaily(
                tenant_id=tenant_id,
                account_id=record.account_id,
                date=target_date,
            )

        stat.actual_in = record.check_in_time
        stat.actual_out = record.check_out_time
        stat.late_minutes = record.late_minutes
        stat.early_minutes = record.early_minutes
        stat.work_hours = record.work_hours

        # 判定状态
        if record.account_id in leave_account_ids:
            stat.status = "leave"
        elif record.status == "absent":
            stat.status = "absent"
        elif record.status == "expected":
            # 有实际打卡的预期记录，按正常逻辑判定
            if record.late_minutes > 0:
                stat.status = "late"
            elif record.early_minutes > 0:
                stat.status = "early"
            else:
                stat.status = "normal"
        elif record.late_minutes > 0:
            stat.status = "late"
        elif record.early_minutes > 0:
            stat.status = "early"
        else:
            stat.status = "normal"

        # 设置排班时间
        shift = shifts.get(record.shift_id) if record.shift_id else None
        if shift:
            stat.scheduled_in = shift.start_time
            stat.scheduled_out = shift.end_time
            stat.shift_id = shift.id

        if not existing:
            db.add(stat)
        count += 1

    return count
