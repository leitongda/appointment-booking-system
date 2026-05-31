"""
兼职费用结算扫描任务。
- 每天下午 5 点扫描待结算的兼职任务
- 自动生成结算单
- 支持多租户隔离
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, and_

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.models.freelance import Freelancer, FreelanceTask, FreelanceInteraction, FreelanceSettlement, FreelanceSettlementItem
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


def _next_workday(dt: datetime, holidays: set = None) -> datetime:
    """计算下一个工作日（跳过周末和节假日）"""
    if holidays is None:
        holidays = set()
    while dt.weekday() >= 5 or dt.date() in holidays:
        dt += timedelta(days=1)
    return dt


def _get_holidays_sync(db, tenant_id: str) -> set:
    """同步查询租户的节假日集合"""
    from app.models.schedule_holiday import ScheduleHoliday
    result = db.execute(
        select(ScheduleHoliday.holiday_date).where(
            and_(
                ScheduleHoliday.status == 1,
                ScheduleHoliday.allow_schedule == False,
                (ScheduleHoliday.tenant_id == tenant_id) | (ScheduleHoliday.tenant_id.is_(None)),
            )
        )
    )
    return set(result.scalars().all())


def _generate_settlement_no(freelancer_id: str) -> str:
    """生成结算单号"""
    now = datetime.now()
    return f"FS{now.strftime('%Y%m%d%H%M%S')}{freelancer_id[:6]}"


def _process_tenant_settlements(db, tenant_id: str) -> int:
    """处理单个租户的待结算任务"""
    now = datetime.utcnow()
    generated_count = 0

    # 查找所有有待结算任务的兼职人员
    freelancer_ids = db.execute(
        select(FreelanceTask.freelancer_id).where(
            and_(
                FreelanceTask.tenant_id == tenant_id,
                FreelanceTask.status.in_(["published", "indexed"]),
            )
        ).distinct()
    ).scalars().all()

    for freelancer_id in freelancer_ids:
        try:
            # 检查是否已有待确认的结算单
            existing = db.execute(
                select(FreelanceSettlement.id).where(
                    and_(
                        FreelanceSettlement.freelancer_id == freelancer_id,
                        FreelanceSettlement.status == "pending",
                    )
                )
            ).scalar_one_or_none()

            if existing:
                continue  # 已有待确认结算单，跳过

            # 排除已结算过的任务
            settled_task_ids = set(
                db.execute(
                    select(FreelanceSettlementItem.task_id)
                    .join(FreelanceSettlement, FreelanceSettlementItem.settlement_id == FreelanceSettlement.id)
                    .where(
                        FreelanceSettlement.freelancer_id == freelancer_id,
                        FreelanceSettlement.status.in_(["confirmed", "paid"]),
                        FreelanceSettlementItem.task_id.isnot(None),
                    )
                ).scalars().all()
            )

            # 查找可结算的任务
            task_query = and_(
                FreelanceTask.freelancer_id == freelancer_id,
                FreelanceTask.tenant_id == tenant_id,
                FreelanceTask.status.in_(["published", "indexed"]),
            )
            if settled_task_ids:
                task_query = and_(task_query, FreelanceTask.id.notin_(settled_task_ids))

            tasks = db.execute(
                select(FreelanceTask).where(task_query)
            ).scalars().all()

            if not tasks:
                continue

            # 检查是否有任何可结算的金额
            base_total = Decimal("0")
            bonus_total = Decimal("0")
            likes_bonus_total = Decimal("0")
            interaction_total = Decimal("0")
            items = []

            for task in tasks:
                # 基础金额（次日结算）
                if task.planned_base_settle_at and task.planned_base_settle_at <= now:
                    base_total += Decimal(str(task.base_amount or 5))
                    items.append({
                        "item_type": "base",
                        "task_id": task.id,
                        "description": f"发布笔记: {task.title}",
                        "amount": Decimal(str(task.base_amount or 5)),
                    })

                # 补贴金额（第 7 天结算）
                if task.planned_bonus_settle_at and task.planned_bonus_settle_at <= now and task.bonus_amount and Decimal(str(task.bonus_amount)) > 0:
                    bonus_total += Decimal(str(task.bonus_amount))
                    items.append({
                        "item_type": "bonus",
                        "task_id": task.id,
                        "description": f"一周补贴: {task.title}",
                        "amount": Decimal(str(task.bonus_amount)),
                    })

                # 点赞奖励（第 22 天结算）
                if task.planned_likes_settle_at and task.planned_likes_settle_at <= now and task.likes_bonus_amount and Decimal(str(task.likes_bonus_amount)) > 0:
                    likes_bonus_total += Decimal(str(task.likes_bonus_amount))
                    items.append({
                        "item_type": "likes_bonus",
                        "task_id": task.id,
                        "description": f"点赞奖励: {task.title} ({task.likes_count}赞)",
                        "amount": Decimal(str(task.likes_bonus_amount)),
                    })

                # 互动金额（第 7 天结算）
                if task.planned_bonus_settle_at and task.planned_bonus_settle_at <= now:
                    interactions = db.execute(
                        select(FreelanceInteraction).where(FreelanceInteraction.task_id == task.id)
                    ).scalars().all()
                    for interaction in interactions:
                        interaction_total += Decimal(str(interaction.amount or 0.5))
                        items.append({
                            "item_type": "interaction",
                            "task_id": task.id,
                            "interaction_id": interaction.id,
                            "description": f"互动({interaction.interaction_type}): {task.title}",
                            "amount": Decimal(str(interaction.amount or 0.5)),
                        })

            if not items:
                continue

            total_amount = base_total + bonus_total + likes_bonus_total + interaction_total

            # 获取兼职人员信息
            freelancer = db.execute(
                select(Freelancer).where(Freelancer.id == freelancer_id)
            ).scalar_one_or_none()

            # 创建结算单
            settlement = FreelanceSettlement(
                tenant_id=tenant_id,
                store_id=freelancer.store_id if freelancer else None,
                freelancer_id=freelancer_id,
                settlement_no=_generate_settlement_no(freelancer_id),
                period_start=tasks[0].published_at,
                period_end=now,
                base_total=base_total,
                bonus_total=bonus_total,
                likes_bonus_total=likes_bonus_total,
                interaction_total=interaction_total,
                total_amount=total_amount,
                actual_amount=total_amount,
                status="pending",
            )
            db.add(settlement)
            db.flush()

            # 添加明细
            for item_data in items:
                item = FreelanceSettlementItem(
                    settlement_id=settlement.id,
                    **item_data,
                    created_at=now,
                )
                db.add(item)

            generated_count += 1
            logger.info(f"为兼职人员 {freelancer_id} 生成结算单 {settlement.settlement_no}，金额 {total_amount}")

        except Exception as e:
            logger.error(f"处理兼职人员 {freelancer_id} 结算失败: {e}")
            continue

    db.commit()
    return generated_count


@celery_app.task(
    name="freelance.generate_settlements",
    queue="scheduled",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=540,
)
def generate_freelance_settlements(self):
    """
    每天下午 5 点扫描待结算的兼职任务，自动生成结算单。
    周末不执行结算。
    """
    # 周末跳过（5=周六, 6=周日）
    if datetime.utcnow().weekday() >= 5:
        logger.info("今天是周末，跳过兼职结算扫描")
        return

    logger.info("开始扫描待结算兼职任务...")

    try:
        db_gen = get_sync_db()
        db = next(db_gen)
        try:
            tenants = db.execute(
                select(Tenant.id).where(Tenant.status == 1)
            ).scalars().all()

            total_generated = 0

            for tenant_id in tenants:
                try:
                    set_tenant_context(tenant_id)
                    count = _process_tenant_settlements(db, tenant_id)
                    total_generated += count
                except Exception as e:
                    logger.error(f"租户 {tenant_id} 兼职结算扫描失败: {e}")
                finally:
                    clear_tenant_context()

            logger.info(f"兼职结算扫描完成，共生成 {total_generated} 个结算单")

        finally:
            db_gen.close()

    except Exception as e:
        logger.error(f"兼职结算扫描任务失败: {e}")
        raise
