"""积分服务"""
import uuid
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.admin import Admin
from app.models.point_log import PointLog
from app.models.user import Patient, User
from app.utils.audit import set_create_audit


class PointService:
    """积分服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_patient_id(self, patient_id: str) -> User | None:
        """通过患者ID获取用户"""
        result = await self.db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.id == patient_id)
        )
        patient = result.unique().scalar_one_or_none()
        return patient.user if patient else None

    def _tenant_filter(self, stmt):
        """为查询添加租户过滤"""
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return stmt.where(PointLog.tenant_id == tenant_id)
        return stmt

    async def get_point_logs(
        self,
        patient_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int, int]:
        """获取积分流水

        Returns:
            Tuple[List[dict], int, int]: (流水列表, 总数, 当前积分)
        """
        # 获取用户
        user = await self.get_user_by_patient_id(patient_id)
        if not user:
            return [], 0, 0

        # 查询积分流水
        query = self._tenant_filter(select(PointLog).where(PointLog.user_id == user.id))

        count_query = self._tenant_filter(select(func.count(PointLog.id)).where(PointLog.user_id == user.id))
        total = await self.db.scalar(count_query)

        query = query.order_by(PointLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        log_data = []
        for log in logs:
            # 获取操作人名称
            operator_name = None
            if log.operator_id:
                admin = await self.db.get(Admin, log.operator_id)
                if admin:
                    operator_name = admin.name or admin.username

            log_data.append({
                'id': log.id,
                'userId': log.user_id,
                'changeAmount': log.change_amount,
                'balance': log.balance,
                'type': log.type,
                'remark': log.remark,
                'operatorId': log.operator_id,
                'operatorName': operator_name,
                'createdAt': log.created_at.isoformat() if log.created_at else None,
            })

        return log_data, total or 0, user.points or 0

    async def adjust_points(
        self,
        patient_id: str,
        amount: int,
        remark: str,
        operator_id: str | None = None,
        log_type: int = 4,  # 默认为手动调整
    ) -> dict | None:
        """调整积分

        Args:
            patient_id: 患者ID
            amount: 调整数量（正数增加，负数减少）
            remark: 备注
            operator_id: 操作人ID
            log_type: 类型 1消费 2充值 3赠送 4手动调整

        Returns:
            调整后的积分信息
        """
        # 获取用户
        user = await self.get_user_by_patient_id(patient_id)
        if not user:
            return None

        # 计算新余额
        current_points = user.points or 0
        new_balance = current_points + amount

        # 不允许负积分
        if new_balance < 0:
            return None

        # 更新用户积分
        user.points = new_balance

        # 创建积分流水记录
        point_log = PointLog(
            id=str(uuid.uuid4()),
            tenant_id=get_current_tenant_id(),
            user_id=user.id,
            change_amount=amount,
            balance=new_balance,
            type=log_type,
            remark=remark,
            operator_id=operator_id,
        )
        set_create_audit(point_log, operator_id)
        self.db.add(point_log)

        await self.db.commit()
        await self.db.refresh(point_log)

        # 获取操作人名称
        operator_name = None
        if operator_id:
            admin = await self.db.get(Admin, operator_id)
            if admin:
                operator_name = admin.name or admin.username

        return {
            'id': point_log.id,
            'userId': user.id,
            'changeAmount': point_log.change_amount,
            'balance': point_log.balance,
            'type': point_log.type,
            'remark': point_log.remark,
            'operatorId': point_log.operator_id,
            'operatorName': operator_name,
            'createdAt': point_log.created_at.isoformat() if point_log.created_at else None,
            'currentPoints': new_balance,
        }

    async def get_point_summary(self, patient_id: str) -> dict:
        """获取积分汇总"""
        user = await self.get_user_by_patient_id(patient_id)
        if not user:
            return {
                'currentPoints': 0,
                'totalEarned': 0,
                'totalSpent': 0,
            }

        # 获取累计获得积分
        total_earned = await self.db.scalar(
            select(func.coalesce(func.sum(PointLog.change_amount), 0))
            .where(and_(
                PointLog.user_id == user.id,
                PointLog.change_amount > 0
            ))
        )

        # 获取累计消费积分
        total_spent = await self.db.scalar(
            select(func.coalesce(func.sum(func.abs(PointLog.change_amount)), 0))
            .where(and_(
                PointLog.user_id == user.id,
                PointLog.change_amount < 0
            ))
        )

        return {
            'currentPoints': user.points or 0,
            'totalEarned': total_earned or 0,
            'totalSpent': total_spent or 0,
        }

    async def get_all_logs(
        self,
        keyword: str | None = None,
        log_type: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取全局积分流水（跨用户）"""
        query = self._tenant_filter(select(PointLog))
        count_query = self._tenant_filter(select(func.count(PointLog.id)))

        # 用户关键词过滤（通过子查询匹配 User 表）
        if keyword:
            user_subq = (
                select(User.id)
                .where(or_(User.nickname.contains(keyword), User.phone.contains(keyword)))
            )
            user_result = await self.db.execute(user_subq)
            user_ids = [row[0] for row in user_result.all()]
            if user_ids:
                query = query.where(PointLog.user_id.in_(user_ids))
                count_query = count_query.where(PointLog.user_id.in_(user_ids))
            else:
                return [], 0

        if log_type is not None:
            query = query.where(PointLog.type == log_type)
            count_query = count_query.where(PointLog.type == log_type)

        if start_date:
            start = datetime.fromisoformat(start_date)
            query = query.where(PointLog.created_at >= start)
            count_query = count_query.where(PointLog.created_at >= start)

        if end_date:
            end = datetime.fromisoformat(end_date + "T23:59:59")
            query = query.where(PointLog.created_at <= end)
            count_query = count_query.where(PointLog.created_at <= end)

        total = await self.db.scalar(count_query)

        query = query.order_by(PointLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        # 批量获取用户信息和操作人信息
        user_ids = list({log.user_id for log in logs if log.user_id})
        operator_ids = list({log.operator_id for log in logs if log.operator_id})

        users_map = {}
        if user_ids:
            users_result = await self.db.execute(
                select(User).where(User.id.in_(user_ids))
            )
            for u in users_result.scalars().all():
                users_map[u.id] = u

        admins_map = {}
        if operator_ids:
            admins_result = await self.db.execute(
                select(Admin).where(Admin.id.in_(operator_ids))
            )
            for a in admins_result.scalars().all():
                admins_map[a.id] = a

        log_data = []
        for log in logs:
            user = users_map.get(log.user_id)
            operator = admins_map.get(log.operator_id) if log.operator_id else None
            log_data.append({
                'id': log.id,
                'userId': log.user_id,
                'userName': user.nickname if user else None,
                'userPhone': user.phone if user else None,
                'changeAmount': log.change_amount,
                'balance': log.balance,
                'type': log.type,
                'remark': log.remark,
                'operatorId': log.operator_id,
                'operatorName': (operator.name or operator.username) if operator else None,
                'createdAt': log.created_at.isoformat() if log.created_at else None,
            })

        return log_data, total or 0

    async def get_user_ranking(
        self,
        keyword: str | None = None,
        sort_by: str = "points",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取用户积分排行"""
        query = select(User)
        count_query = select(func.count(User.id))

        tenant_id = get_current_tenant_id()
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
            count_query = count_query.where(User.tenant_id == tenant_id)

        if keyword:
            cond = or_(User.nickname.contains(keyword), User.phone.contains(keyword))
            query = query.where(cond)
            count_query = count_query.where(cond)

        total = await self.db.scalar(count_query)

        # 排序
        order_col = User.points if sort_by == "points" else User.points
        if sort_order == "asc":
            query = query.order_by(order_col.asc())
        else:
            query = query.order_by(order_col.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        users = result.scalars().all()

        user_data = []
        for u in users:
            user_data.append({
                'id': u.id,
                'nickname': u.nickname,
                'phone': u.phone,
                'points': u.points or 0,
                'status': u.status,
                'createdAt': u.created_at.isoformat() if u.created_at else None,
            })

        return user_data, total or 0

    async def adjust_points_by_user_id(
        self,
        user_id: str,
        amount: int,
        remark: str,
        operator_id: str | None = None,
    ) -> dict | None:
        """直接通过 user_id 调整积分"""
        user = await self.db.get(User, user_id)
        if not user:
            return None

        current_points = user.points or 0
        new_balance = current_points + amount

        if new_balance < 0:
            return None

        user.points = new_balance

        point_log = PointLog(
            id=str(uuid.uuid4()),
            tenant_id=get_current_tenant_id(),
            user_id=user.id,
            change_amount=amount,
            balance=new_balance,
            type=4,
            remark=remark,
            operator_id=operator_id,
        )
        set_create_audit(point_log, operator_id)
        self.db.add(point_log)

        await self.db.commit()
        await self.db.refresh(point_log)

        operator_name = None
        if operator_id:
            admin = await self.db.get(Admin, operator_id)
            if admin:
                operator_name = admin.name or admin.username

        return {
            'id': point_log.id,
            'userId': user.id,
            'changeAmount': point_log.change_amount,
            'balance': point_log.balance,
            'type': point_log.type,
            'remark': point_log.remark,
            'operatorId': point_log.operator_id,
            'operatorName': operator_name,
            'createdAt': point_log.created_at.isoformat() if point_log.created_at else None,
            'currentPoints': new_balance,
        }
