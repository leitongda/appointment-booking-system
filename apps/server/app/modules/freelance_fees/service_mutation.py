"""兼职费用 — 写入服务"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.freelance import (
    FreelanceInteraction,
    Freelancer,
    FreelanceSettlement,
    FreelanceSettlementItem,
    FreelanceTask,
)
from app.modules.freelance_fees.schemas import (
    FreelanceInteractionCreate,
    FreelancerCreate,
    FreelancerUpdate,
    FreelanceTaskCreate,
    FreelanceTaskUpdate,
)
from app.utils.audit import set_create_audit, set_update_audit


def _next_workday(dt: datetime, holidays: set | None = None) -> datetime:
    """计算下一个工作日（跳过周末和节假日）

    Args:
        dt: 起始日期
        holidays: 节假日日期集合（date 对象），可选
    """
    if holidays is None:
        holidays = set()
    while dt.weekday() >= 5 or dt.date() in holidays:
        dt += timedelta(days=1)
    return dt


async def _get_holidays(db: AsyncSession, tenant_id: str | None) -> set:
    """查询租户的节假日集合"""

    from sqlalchemy import and_, select

    from app.models.schedule_holiday import ScheduleHoliday

    stmt = select(ScheduleHoliday.holiday_date).where(
        and_(
            ScheduleHoliday.status == 1,
            ScheduleHoliday.allow_schedule == False,  # 法定节假日（非调休上班日）
        )
    )
    if tenant_id:
        stmt = stmt.where(
            (ScheduleHoliday.tenant_id == tenant_id) | (ScheduleHoliday.tenant_id.is_(None))
        )
    result = await db.execute(stmt)
    return set(result.scalars().all())


def _calculate_planned_dates(published_at: datetime, holidays: set | None = None) -> dict:
    """计算理论结算日"""
    return {
        "planned_base_settle_at": _next_workday(published_at + timedelta(days=1), holidays),
        "planned_bonus_settle_at": _next_workday(published_at + timedelta(days=7), holidays),
        "planned_likes_settle_at": _next_workday(published_at + timedelta(days=22), holidays),
    }


class FreelanceMutationMixin:
    """兼职费用写入"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- 兼职人员 ----------

    async def create_freelancer(self, data: FreelancerCreate, operator_id: str | None = None) -> Freelancer:
        tenant_id = get_current_tenant_id()
        freelancer = Freelancer(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            access_token=uuid.uuid4().hex,
            **data.model_dump(exclude_unset=True),
        )
        set_create_audit(freelancer, operator_id)
        self.db.add(freelancer)
        await self.db.commit()
        await self.db.refresh(freelancer)
        return freelancer

    async def update_freelancer(self, freelancer_id: str, data: FreelancerUpdate, operator_id: str | None = None) -> Freelancer | None:
        from app.modules.freelance_fees.service_query import FreelanceQueryMixin
        query_svc = FreelanceQueryMixin(self.db)
        freelancer = await query_svc.get_freelancer_by_id(freelancer_id)
        if not freelancer:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(freelancer, key, value)
        set_update_audit(freelancer, operator_id)

        await self.db.commit()
        await self.db.refresh(freelancer)
        return freelancer

    async def delete_freelancer(self, freelancer_id: str) -> bool:
        from app.modules.freelance_fees.service_query import FreelanceQueryMixin
        query_svc = FreelanceQueryMixin(self.db)
        freelancer = await query_svc.get_freelancer_by_id(freelancer_id)
        if not freelancer:
            return False
        freelancer.status = 0
        await self.db.commit()
        return True

    # ---------- 发布任务 ----------

    async def create_task(self, data: FreelanceTaskCreate, operator_id: str | None = None) -> FreelanceTask:
        tenant_id = get_current_tenant_id()

        # 计算理论结算日（含节假日顺延）
        published_at = data.published_at or datetime.utcnow()
        holidays = await _get_holidays(self.db, tenant_id)
        planned_dates = _calculate_planned_dates(published_at, holidays)

        task = FreelanceTask(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            store_id=data.store_id,
            freelancer_id=data.freelancer_id,
            title=data.title,
            content_url=data.content_url,
            published_at=published_at,
            status="published" if data.published_at else "pending",
            base_amount=Decimal("5"),
            remark=data.remark,
            **planned_dates,
        )
        set_create_audit(task, operator_id)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def update_task(self, task_id: str, data: FreelanceTaskUpdate, operator_id: str | None = None) -> FreelanceTask | None:
        from app.modules.freelance_fees.service_query import FreelanceQueryMixin
        query_svc = FreelanceQueryMixin(self.db)
        task = await query_svc.get_task_by_id(task_id)
        if not task:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # 如果更新了点赞数，自动计算点赞奖励
        if "likes_count" in update_data:
            task.likes_bonus_amount = Decimal("10") if update_data["likes_count"] >= 50 else Decimal("0")

        for key, value in update_data.items():
            setattr(task, key, value)
        set_update_audit(task, operator_id)

        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def add_interaction(self, data: FreelanceInteractionCreate, operator_id: str | None = None) -> FreelanceInteraction | None:
        from app.modules.freelance_fees.service_query import FreelanceQueryMixin
        query_svc = FreelanceQueryMixin(self.db)
        task = await query_svc.get_task_by_id(data.task_id)
        if not task:
            return None

        tenant_id = get_current_tenant_id()
        interaction = FreelanceInteraction(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            task_id=data.task_id,
            interaction_type=data.interaction_type,
            content=data.content,
            amount=Decimal("0.5"),
            interacted_at=data.interacted_at or datetime.utcnow(),
        )
        set_create_audit(interaction, operator_id)
        self.db.add(interaction)

        # 更新任务的评论数（仅评论计入，私信不计入）
        if data.interaction_type == "comment":
            task.comments_count = (task.comments_count or 0) + 1

        await self.db.commit()
        await self.db.refresh(interaction)
        return interaction

    # ---------- 结算 ----------

    async def generate_settlement(
        self,
        freelancer_id: str,
        store_id: str | None = None,
        operator_id: str | None = None,
    ) -> FreelanceSettlement | None:
        """为指定兼职人员生成结算单"""
        from app.modules.freelance_fees.service_query import FreelanceQueryMixin
        query_svc = FreelanceQueryMixin(self.db)

        tenant_id = get_current_tenant_id()
        freelancer = await query_svc.get_freelancer_by_id(freelancer_id)
        if not freelancer:
            return None

        now = datetime.utcnow()

        # 检查是否已有待确认的结算单（防止重复生成，使用行锁防并发）
        from sqlalchemy import and_, select
        existing_stmt = select(FreelanceSettlement.id).where(
            and_(
                FreelanceSettlement.freelancer_id == freelancer_id,
                FreelanceSettlement.status == "pending",
            )
        ).with_for_update()
        if tenant_id:
            existing_stmt = existing_stmt.where(FreelanceSettlement.tenant_id == tenant_id)
        existing = (await self.db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            return None  # 已有待确认结算单，不允许重复生成

        # 查找已结算过的任务 ID（排除已确认/已支付的结算单中的任务）
        settled_task_ids = set()
        settled_items_stmt = (
            select(FreelanceSettlementItem.task_id)
            .join(FreelanceSettlement, FreelanceSettlementItem.settlement_id == FreelanceSettlement.id)
            .where(
                FreelanceSettlement.freelancer_id == freelancer_id,
                FreelanceSettlement.status.in_(["confirmed", "paid"]),
                FreelanceSettlementItem.task_id.isnot(None),
            )
        )
        settled_task_ids = set(
            (await self.db.execute(settled_items_stmt)).scalars().all()
        )

        # 查找所有已发布但未结算的任务
        task_stmt = select(FreelanceTask).where(
            and_(
                FreelanceTask.freelancer_id == freelancer_id,
                FreelanceTask.status.in_(["published", "indexed"]),
                FreelanceTask.id.notin_(settled_task_ids) if settled_task_ids else True,
            )
        )
        if tenant_id:
            task_stmt = task_stmt.where(FreelanceTask.tenant_id == tenant_id)
        tasks = (await self.db.execute(task_stmt)).scalars().all()

        if not tasks:
            return None

        # 计算各项金额
        base_total = Decimal("0")
        bonus_total = Decimal("0")
        likes_bonus_total = Decimal("0")
        interaction_total = Decimal("0")
        items = []

        for task in tasks:
            # 基础金额（次日结算）
            if task.planned_base_settle_at and task.planned_base_settle_at <= now:
                base_total += task.base_amount or Decimal("5")
                items.append(FreelanceSettlementItem(
                    id=str(uuid.uuid4()),
                    item_type="base",
                    task_id=task.id,
                    description=f"发布笔记: {task.title}",
                    amount=task.base_amount or Decimal("5"),
                    created_at=now,
                ))

            # 补贴金额（第 7 天结算）
            if task.planned_bonus_settle_at and task.planned_bonus_settle_at <= now and task.bonus_amount and task.bonus_amount > 0:
                bonus_total += task.bonus_amount
                items.append(FreelanceSettlementItem(
                    id=str(uuid.uuid4()),
                    item_type="bonus",
                    task_id=task.id,
                    description=f"一周补贴: {task.title}",
                    amount=task.bonus_amount,
                    created_at=now,
                ))

            # 点赞奖励（第 22 天结算）
            if task.planned_likes_settle_at and task.planned_likes_settle_at <= now and task.likes_bonus_amount and task.likes_bonus_amount > 0:
                likes_bonus_total += task.likes_bonus_amount
                items.append(FreelanceSettlementItem(
                    id=str(uuid.uuid4()),
                    item_type="likes_bonus",
                    task_id=task.id,
                    description=f"点赞奖励: {task.title} ({task.likes_count}赞)",
                    amount=task.likes_bonus_amount,
                    created_at=now,
                ))

            # 互动金额（第 7 天结算）
            if task.planned_bonus_settle_at and task.planned_bonus_settle_at <= now:
                interactions = await query_svc.get_interactions_by_task(task.id)
                for interaction in interactions:
                    interaction_total += interaction.amount or Decimal("0.5")
                    items.append(FreelanceSettlementItem(
                        id=str(uuid.uuid4()),
                        item_type="interaction",
                        task_id=task.id,
                        interaction_id=interaction.id,
                        description=f"互动({interaction.interaction_type}): {task.title}",
                        amount=interaction.amount or Decimal("0.5"),
                        created_at=now,
                    ))

        if not items:
            return None

        total_amount = base_total + bonus_total + likes_bonus_total + interaction_total

        # 生成结算单号（含随机段，避免同租户同秒同兼职重复）
        settlement_no = f"FS{now.strftime('%Y%m%d%H%M%S')}{freelancer_id[:2]}{uuid.uuid4().hex[:4].upper()}"

        settlement = FreelanceSettlement(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            store_id=store_id or freelancer.store_id,
            freelancer_id=freelancer_id,
            settlement_no=settlement_no,
            period_start=tasks[0].published_at,
            period_end=now,
            base_total=base_total,
            bonus_total=bonus_total,
            likes_bonus_total=likes_bonus_total,
            interaction_total=interaction_total,
            total_amount=total_amount,
            actual_amount=total_amount,  # tax 默认 0
            status="pending",
        )
        set_create_audit(settlement, operator_id)
        self.db.add(settlement)
        await self.db.flush()

        # 添加明细
        for item in items:
            item.settlement_id = settlement.id
            self.db.add(item)

        await self.db.commit()
        await self.db.refresh(settlement)
        return settlement

    async def _notify_settlement_event(self, settlement: FreelanceSettlement, event_type: str, operator_id: str | None = None):
        """发送结算通知"""
        try:
            from app.middleware.tenant_context import get_current_tenant_id
            from app.modules.unified_message.schemas import NotificationEvent
            from app.modules.unified_message.service import UnifiedMessageService

            tenant_id = get_current_tenant_id()
            if not tenant_id:
                return

            # 查找兼职人员信息
            from app.modules.freelance_fees.service_query import FreelanceQueryMixin
            query_svc = FreelanceQueryMixin(self.db)
            freelancer = await query_svc.get_freelancer_by_id(settlement.freelancer_id)

            event_titles = {
                "confirmed": "结算单已确认",
                "rejected": "结算单已驳回",
                "paid": "结算单已支付",
            }

            title = event_titles.get(event_type, "结算通知")
            content = f"结算单 {settlement.settlement_no}，金额 ¥{float(settlement.actual_amount):.2f}"
            if event_type == "rejected" and settlement.reject_reason:
                content += f"，原因：{settlement.reject_reason}"

            # 通知管理员（通过站内信）
            if operator_id:
                service = UnifiedMessageService(self.db)
                event = NotificationEvent(
                    tenant_id=tenant_id,
                    store_id=settlement.store_id,
                    recipient_id=operator_id,
                    recipient_type="admin",
                    recipient_phone=freelancer.phone if freelancer else None,
                    template_code=f"freelance_settlement_{event_type}",
                    variables={
                        "settlement_no": settlement.settlement_no,
                        "amount": str(float(settlement.actual_amount)),
                        "freelancer_name": freelancer.name if freelancer else "",
                    },
                    message_type="system",
                    related_id=settlement.id,
                    title=title,
                    content=content,
                )
                await service.send(event)
        except Exception as e:
            # 通知失败不影响业务
            import logging
            logging.getLogger(__name__).warning(f"发送结算通知失败: {e}")

    async def confirm_settlement(self, settlement_id: str, operator_id: str | None = None, remark: str | None = None) -> FreelanceSettlement | None:
        from app.modules.freelance_fees.service_query import FreelanceQueryMixin
        query_svc = FreelanceQueryMixin(self.db)
        settlement = await query_svc.get_settlement_by_id(settlement_id)
        if not settlement or settlement.status != "pending":
            return None

        settlement.status = "confirmed"
        settlement.confirmed_at = datetime.utcnow()
        settlement.confirmed_by = operator_id
        if remark:
            settlement.remark = remark
        set_update_audit(settlement, operator_id)

        await self.db.commit()
        await self.db.refresh(settlement)

        # 发送通知
        await self._notify_settlement_event(settlement, "confirmed", operator_id)
        return settlement

    async def reject_settlement(self, settlement_id: str, operator_id: str | None = None, reject_reason: str = "") -> FreelanceSettlement | None:
        from app.modules.freelance_fees.service_query import FreelanceQueryMixin
        query_svc = FreelanceQueryMixin(self.db)
        settlement = await query_svc.get_settlement_by_id(settlement_id)
        if not settlement or settlement.status != "pending":
            return None

        settlement.status = "cancelled"
        settlement.reject_reason = reject_reason
        set_update_audit(settlement, operator_id)

        await self.db.commit()
        await self.db.refresh(settlement)

        # 发送通知
        await self._notify_settlement_event(settlement, "rejected", operator_id)
        return settlement

    async def mark_settlement_paid(self, settlement_id: str, operator_id: str | None = None) -> FreelanceSettlement | None:
        from app.modules.freelance_fees.service_query import FreelanceQueryMixin
        query_svc = FreelanceQueryMixin(self.db)
        settlement = await query_svc.get_settlement_by_id(settlement_id)
        if not settlement or settlement.status != "confirmed":
            return None

        settlement.status = "paid"
        settlement.paid_at = datetime.utcnow()
        set_update_audit(settlement, operator_id)

        await self.db.commit()
        await self.db.refresh(settlement)

        # 发送通知
        await self._notify_settlement_event(settlement, "paid", operator_id)
        return settlement
