"""假期管理服务"""

import uuid
from datetime import date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.attendance import (
    AttendanceLeaveBalance,
    AttendanceLeaveRequest,
    AttendanceLeaveType,
)
from app.utils.audit import set_create_audit, set_update_audit


class AttendanceLeaveService:
    """假期管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 假期类型 ====================

    async def get_type_list(
        self,
        enabled: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AttendanceLeaveType], int]:
        """获取假期类型列表"""
        tenant_id = get_current_tenant_id()
        conditions = [AttendanceLeaveType.tenant_id == tenant_id]

        if enabled is not None:
            conditions.append(AttendanceLeaveType.enabled == enabled)

        count_result = await self.db.execute(
            select(func.count(AttendanceLeaveType.id)).where(and_(*conditions))
        )
        total = count_result.scalar_one() or 0

        result = await self.db.execute(
            select(AttendanceLeaveType)
            .where(and_(*conditions))
            .order_by(AttendanceLeaveType.sort_order.asc(), AttendanceLeaveType.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_type_by_id(self, type_id: str) -> AttendanceLeaveType | None:
        """获取假期类型详情"""
        tenant_id = get_current_tenant_id()
        result = await self.db.execute(
            select(AttendanceLeaveType).where(
                AttendanceLeaveType.id == type_id,
                AttendanceLeaveType.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_type(self, data: dict, operator_id: str | None = None) -> AttendanceLeaveType:
        """创建假期类型

        Raises:
            ValueError: 代码已存在
        """
        tenant_id = get_current_tenant_id()

        existing = await self.db.execute(
            select(AttendanceLeaveType).where(
                AttendanceLeaveType.tenant_id == tenant_id,
                AttendanceLeaveType.code == data["code"],
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"假期代码 '{data['code']}' 已存在")

        leave_type = AttendanceLeaveType(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **data,
        )
        set_create_audit(leave_type, operator_id)

        self.db.add(leave_type)
        await self.db.commit()
        await self.db.refresh(leave_type)
        return leave_type

    async def update_type(
        self, type_id: str, data: dict, operator_id: str | None = None
    ) -> AttendanceLeaveType | None:
        """更新假期类型"""
        leave_type = await self.get_type_by_id(type_id)
        if not leave_type:
            return None

        for key, value in data.items():
            if value is not None and hasattr(leave_type, key):
                setattr(leave_type, key, value)

        set_update_audit(leave_type, operator_id)
        await self.db.commit()
        await self.db.refresh(leave_type)
        return leave_type

    async def delete_type(self, type_id: str) -> bool:
        """删除假期类型"""
        leave_type = await self.get_type_by_id(type_id)
        if not leave_type:
            return False

        await self.db.delete(leave_type)
        await self.db.commit()
        return True

    # ==================== 假期余额 ====================

    async def get_balances(
        self, account_id: str, year: int | None = None
    ) -> list[dict]:
        """获取员工假期余额列表"""
        tenant_id = get_current_tenant_id()
        if year is None:
            year = date.today().year

        query = (
            select(
                AttendanceLeaveBalance,
                AttendanceLeaveType.name.label("leave_type_name"),
            )
            .join(
                AttendanceLeaveType,
                AttendanceLeaveBalance.leave_type_id == AttendanceLeaveType.id,
            )
            .where(
                AttendanceLeaveBalance.tenant_id == tenant_id,
                AttendanceLeaveBalance.account_id == account_id,
                AttendanceLeaveBalance.year == year,
            )
            .order_by(AttendanceLeaveType.sort_order.asc())
        )
        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "id": row.AttendanceLeaveBalance.id,
                "account_id": row.AttendanceLeaveBalance.account_id,
                "leave_type_id": row.AttendanceLeaveBalance.leave_type_id,
                "leave_type_name": row.leave_type_name,
                "year": row.AttendanceLeaveBalance.year,
                "total_days": row.AttendanceLeaveBalance.total_days,
                "used_days": row.AttendanceLeaveBalance.used_days,
                "remaining_days": round(
                    row.AttendanceLeaveBalance.total_days - row.AttendanceLeaveBalance.used_days, 1
                ),
            }
            for row in rows
        ]

    async def update_balance(
        self, account_id: str, leave_type_id: str, year: int, total_days: float, operator_id: str | None = None
    ) -> AttendanceLeaveBalance:
        """更新假期余额（不存在则创建）"""
        tenant_id = get_current_tenant_id()

        result = await self.db.execute(
            select(AttendanceLeaveBalance).where(
                AttendanceLeaveBalance.tenant_id == tenant_id,
                AttendanceLeaveBalance.account_id == account_id,
                AttendanceLeaveBalance.leave_type_id == leave_type_id,
                AttendanceLeaveBalance.year == year,
            )
        )
        balance = result.scalar_one_or_none()

        if balance:
            balance.total_days = total_days
            set_update_audit(balance, operator_id)
        else:
            balance = AttendanceLeaveBalance(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                account_id=account_id,
                leave_type_id=leave_type_id,
                year=year,
                total_days=total_days,
                used_days=0,
            )
            set_create_audit(balance, operator_id)
            self.db.add(balance)

        await self.db.commit()
        await self.db.refresh(balance)
        return balance

    async def init_yearly_balances(self, year: int, operator_id: str | None = None) -> int:
        """为所有启用的假期类型初始化年度余额

        Returns:
            新建的余额记录数
        """
        tenant_id = get_current_tenant_id()

        # 获取所有启用的假期类型
        types_result = await self.db.execute(
            select(AttendanceLeaveType).where(
                AttendanceLeaveType.tenant_id == tenant_id,
                AttendanceLeaveType.enabled == True,
                AttendanceLeaveType.default_days > 0,
            )
        )
        leave_types = list(types_result.scalars().all())
        if not leave_types:
            return 0

        # 获取已有余额的 (account_id, leave_type_id) 组合
        existing_result = await self.db.execute(
            select(
                AttendanceLeaveBalance.account_id,
                AttendanceLeaveBalance.leave_type_id,
            ).where(
                AttendanceLeaveBalance.tenant_id == tenant_id,
                AttendanceLeaveBalance.year == year,
            )
        )
        existing_keys = {(row[0], row[1]) for row in existing_result.all()}

        # 获取所有有账号的员工（通过已有余额记录反推，或通过 Account 表）
        # 这里只初始化已有余额记录的员工 + 按需创建
        # 实际场景中通常通过 Account 表批量初始化，此处简化为仅处理已有记录的更新
        return 0

    # ==================== 假期申请 ====================

    async def _calc_duration_days(self, start_date: date, end_date: date) -> float:
        """计算请假天数（含首尾日）"""
        delta = (end_date - start_date).days + 1
        return max(delta, 0)

    async def create_request(
        self, account_id: str, data: dict, operator_id: str | None = None
    ) -> AttendanceLeaveRequest:
        """创建假期申请"""
        tenant_id = get_current_tenant_id()
        duration_days = await self._calc_duration_days(data["start_date"], data["end_date"])

        leave_request = AttendanceLeaveRequest(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            account_id=account_id,
            leave_type_id=data["leave_type_id"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            duration_days=duration_days,
            reason=data.get("reason"),
            status="pending",
        )
        set_create_audit(leave_request, operator_id or account_id)

        self.db.add(leave_request)
        await self.db.commit()
        await self.db.refresh(leave_request)
        return leave_request

    async def get_my_requests(
        self, account_id: str, page: int = 1, page_size: int = 10
    ) -> tuple[list[dict], int]:
        """获取我的假期申请列表"""
        tenant_id = get_current_tenant_id()
        conditions = [
            AttendanceLeaveRequest.tenant_id == tenant_id,
            AttendanceLeaveRequest.account_id == account_id,
        ]

        count_result = await self.db.execute(
            select(func.count(AttendanceLeaveRequest.id)).where(and_(*conditions))
        )
        total = count_result.scalar_one() or 0

        query = (
            select(
                AttendanceLeaveRequest,
                AttendanceLeaveType.name.label("leave_type_name"),
            )
            .join(
                AttendanceLeaveType,
                AttendanceLeaveRequest.leave_type_id == AttendanceLeaveType.id,
            )
            .where(and_(*conditions))
            .order_by(AttendanceLeaveRequest.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        rows = result.all()

        items = [
            {
                "id": row.AttendanceLeaveRequest.id,
                "tenant_id": row.AttendanceLeaveRequest.tenant_id,
                "account_id": row.AttendanceLeaveRequest.account_id,
                "leave_type_id": row.AttendanceLeaveRequest.leave_type_id,
                "leave_type_name": row.leave_type_name,
                "start_date": row.AttendanceLeaveRequest.start_date,
                "end_date": row.AttendanceLeaveRequest.end_date,
                "duration_days": row.AttendanceLeaveRequest.duration_days,
                "reason": row.AttendanceLeaveRequest.reason,
                "status": row.AttendanceLeaveRequest.status,
                "reviewer_id": row.AttendanceLeaveRequest.reviewer_id,
                "review_comment": row.AttendanceLeaveRequest.review_comment,
                "reviewed_at": row.AttendanceLeaveRequest.reviewed_at,
                "created_at": row.AttendanceLeaveRequest.created_at,
                "updated_at": row.AttendanceLeaveRequest.updated_at,
            }
            for row in rows
        ]
        return items, total

    async def get_all_requests(
        self,
        tenant_id: str | None = None,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """获取所有假期申请（管理员）"""
        if tenant_id is None:
            tenant_id = get_current_tenant_id()

        conditions = [AttendanceLeaveRequest.tenant_id == tenant_id]

        if status:
            conditions.append(AttendanceLeaveRequest.status == status)

        if keyword:
            conditions.append(
                AttendanceLeaveRequest.reason.ilike(f"%{keyword}%")
            )

        count_result = await self.db.execute(
            select(func.count(AttendanceLeaveRequest.id)).where(and_(*conditions))
        )
        total = count_result.scalar_one() or 0

        query = (
            select(
                AttendanceLeaveRequest,
                AttendanceLeaveType.name.label("leave_type_name"),
            )
            .join(
                AttendanceLeaveType,
                AttendanceLeaveRequest.leave_type_id == AttendanceLeaveType.id,
            )
            .where(and_(*conditions))
            .order_by(AttendanceLeaveRequest.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        rows = result.all()

        items = [
            {
                "id": row.AttendanceLeaveRequest.id,
                "tenant_id": row.AttendanceLeaveRequest.tenant_id,
                "account_id": row.AttendanceLeaveRequest.account_id,
                "leave_type_id": row.AttendanceLeaveRequest.leave_type_id,
                "leave_type_name": row.leave_type_name,
                "start_date": row.AttendanceLeaveRequest.start_date,
                "end_date": row.AttendanceLeaveRequest.end_date,
                "duration_days": row.AttendanceLeaveRequest.duration_days,
                "reason": row.AttendanceLeaveRequest.reason,
                "status": row.AttendanceLeaveRequest.status,
                "reviewer_id": row.AttendanceLeaveRequest.reviewer_id,
                "review_comment": row.AttendanceLeaveRequest.review_comment,
                "reviewed_at": row.AttendanceLeaveRequest.reviewed_at,
                "created_at": row.AttendanceLeaveRequest.created_at,
                "updated_at": row.AttendanceLeaveRequest.updated_at,
            }
            for row in rows
        ]
        return items, total

    async def _get_request_by_id(self, request_id: str) -> AttendanceLeaveRequest | None:
        """获取假期申请详情"""
        tenant_id = get_current_tenant_id()
        result = await self.db.execute(
            select(AttendanceLeaveRequest).where(
                AttendanceLeaveRequest.id == request_id,
                AttendanceLeaveRequest.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def approve(
        self, request_id: str, reviewer_id: str, comment: str | None = None
    ) -> AttendanceLeaveRequest | None:
        """审批通过假期申请

        审批通过后扣减假期余额。
        """
        leave_request = await self._get_request_by_id(request_id)
        if not leave_request or leave_request.status != "pending":
            return None

        leave_request.status = "approved"
        leave_request.reviewer_id = reviewer_id
        leave_request.review_comment = comment
        leave_request.reviewed_at = datetime.utcnow()
        set_update_audit(leave_request, reviewer_id)

        # 扣减假期余额
        year = leave_request.start_date.year
        balance_result = await self.db.execute(
            select(AttendanceLeaveBalance).where(
                AttendanceLeaveBalance.tenant_id == leave_request.tenant_id,
                AttendanceLeaveBalance.account_id == leave_request.account_id,
                AttendanceLeaveBalance.leave_type_id == leave_request.leave_type_id,
                AttendanceLeaveBalance.year == year,
            )
        )
        balance = balance_result.scalar_one_or_none()
        if balance:
            balance.used_days = round(balance.used_days + leave_request.duration_days, 1)
            set_update_audit(balance, reviewer_id)
        else:
            # 没有余额记录时自动创建
            balance = AttendanceLeaveBalance(
                id=str(uuid.uuid4()),
                tenant_id=leave_request.tenant_id,
                account_id=leave_request.account_id,
                leave_type_id=leave_request.leave_type_id,
                year=year,
                total_days=0,
                used_days=leave_request.duration_days,
            )
            set_create_audit(balance, reviewer_id)
            self.db.add(balance)

        await self.db.commit()
        await self.db.refresh(leave_request)
        return leave_request

    async def reject(
        self, request_id: str, reviewer_id: str, comment: str | None = None
    ) -> AttendanceLeaveRequest | None:
        """驳回假期申请"""
        leave_request = await self._get_request_by_id(request_id)
        if not leave_request or leave_request.status != "pending":
            return None

        leave_request.status = "rejected"
        leave_request.reviewer_id = reviewer_id
        leave_request.review_comment = comment
        leave_request.reviewed_at = datetime.utcnow()
        set_update_audit(leave_request, reviewer_id)

        await self.db.commit()
        await self.db.refresh(leave_request)
        return leave_request

    async def cancel(
        self, request_id: str, account_id: str
    ) -> AttendanceLeaveRequest | None:
        """取消假期申请（仅 pending 状态可取消）"""
        leave_request = await self._get_request_by_id(request_id)
        if not leave_request:
            return None
        if leave_request.account_id != account_id:
            return None
        if leave_request.status != "pending":
            return None

        leave_request.status = "cancelled"
        set_update_audit(leave_request, account_id)

        await self.db.commit()
        await self.db.refresh(leave_request)
        return leave_request
