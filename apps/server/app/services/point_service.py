"""积分服务"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
import uuid

from app.models.user import User, Patient
from app.models.point_log import PointLog
from app.models.admin import Admin


class PointService:
    """积分服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_patient_id(self, patient_id: str) -> Optional[User]:
        """通过患者ID获取用户"""
        result = await self.db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.id == patient_id)
        )
        patient = result.unique().scalar_one_or_none()
        return patient.user if patient else None

    async def get_point_logs(
        self,
        patient_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int, int]:
        """获取积分流水
        
        Returns:
            Tuple[List[dict], int, int]: (流水列表, 总数, 当前积分)
        """
        # 获取用户
        user = await self.get_user_by_patient_id(patient_id)
        if not user:
            return [], 0, 0
        
        # 查询积分流水
        query = select(PointLog).where(PointLog.user_id == user.id)
        
        count_query = select(func.count(PointLog.id)).where(PointLog.user_id == user.id)
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
        operator_id: Optional[str] = None,
        log_type: int = 4,  # 默认为手动调整
    ) -> Optional[dict]:
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
            user_id=user.id,
            change_amount=amount,
            balance=new_balance,
            type=log_type,
            remark=remark,
            operator_id=operator_id,
        )
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
