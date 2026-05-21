from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date
import uuid
import json

from app.models.rest_day import RestDay
from app.models.doctor import Doctor
from app.models.store import Store
from app.schemas.rest_day import RestDayCreate
from app.utils.audit import set_create_audit, set_update_audit
from app.middleware.tenant_context import get_current_tenant_id
from app.modules.schedules.service_query import _invalidate_rest_days_cache


class RestDayService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, rest_day_id: str) -> Optional[RestDay]:
        stmt = (
            select(RestDay)
            .options(selectinload(RestDay.store))
            .where(RestDay.id == rest_day_id)
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(RestDay.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[RestDay], int]:
        query = select(RestDay).options(selectinload(RestDay.store))
        count_query = select(func.count(RestDay.id))

        conditions = []
        tenant_id = get_current_tenant_id()
        if tenant_id:
            conditions.append(RestDay.tenant_id == tenant_id)

        if store_id:
            conditions.append(RestDay.store_id == store_id)
        if start_date:
            conditions.append(RestDay.end_date >= start_date)
        if end_date:
            conditions.append(RestDay.start_date <= end_date)
        if status is not None:
            conditions.append(RestDay.status == status)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        query = query.order_by(RestDay.start_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        rest_days = list(result.scalars().all())

        # 如果指定了doctor_id，需要过滤
        if doctor_id:
            filtered = []
            for rd in rest_days:
                if rd.doctor_ids is None:
                    # NULL表示门店所有医生
                    filtered.append(rd)
                else:
                    try:
                        doctor_ids_list = json.loads(rd.doctor_ids)
                        if doctor_id in doctor_ids_list:
                            filtered.append(rd)
                    except:
                        pass
            rest_days = filtered

        count_result = await self.db.execute(count_query)

        return rest_days, count_result.scalar() or 0

    async def create(self, data: RestDayCreate, operator_id: Optional[str] = None) -> RestDay:
        """创建休息日"""
        tenant_id = get_current_tenant_id()
        rest_day = RestDay(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            store_id=data.store_id,
            doctor_ids=json.dumps(data.doctor_ids) if data.doctor_ids else None,
            reason=data.reason,
            start_date=data.start_date,
            end_date=data.end_date,
            status=1
        )
        set_create_audit(rest_day, operator_id)
        self.db.add(rest_day)
        await self.db.commit()
        _invalidate_rest_days_cache(tenant_id)
        await self.db.refresh(rest_day)
        return rest_day

    async def delete(self, rest_day_id: str) -> bool:
        """删除休息日"""
        rest_day = await self.get_by_id(rest_day_id)
        if not rest_day:
            return False

        await self.db.delete(rest_day)
        await self.db.commit()
        _invalidate_rest_days_cache(get_current_tenant_id())
        return True

    async def cancel(self, rest_day_id: str, operator_id: Optional[str] = None) -> Optional[RestDay]:
        """取消休息日"""
        rest_day = await self.get_by_id(rest_day_id)
        if not rest_day:
            return None

        rest_day.status = 0
        set_update_audit(rest_day, operator_id)
        await self.db.commit()
        _invalidate_rest_days_cache(get_current_tenant_id())
        await self.db.refresh(rest_day)
        return rest_day

    async def check_rest_day(
        self,
        store_id: str,
        doctor_id: str,
        check_date: date
    ) -> Optional[RestDay]:
        """检查指定日期是否为休息日"""
        stmt = select(RestDay).where(
            and_(
                RestDay.store_id == store_id,
                RestDay.status == 1,
                RestDay.start_date <= check_date,
                RestDay.end_date >= check_date
            )
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(RestDay.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        rest_days = result.scalars().all()

        for rd in rest_days:
            if rd.doctor_ids is None:
                # NULL表示门店所有医生
                return rd
            else:
                try:
                    doctor_ids_list = json.loads(rd.doctor_ids)
                    if doctor_id in doctor_ids_list:
                        return rd
                except (json.JSONDecodeError, TypeError):
                    # 解析失败时跳过该记录
                    pass

        return None

    async def get_doctor_names(self, doctor_ids: List[str]) -> List[str]:
        """获取医生姓名列表"""
        if not doctor_ids:
            return []

        result = await self.db.execute(
            select(Doctor).where(Doctor.id.in_(doctor_ids), Doctor.deleted_at.is_(None))
        )
        doctors = result.scalars().all()
        return [d.name for d in doctors]

    async def get_doctor_names_batch(self, doctor_ids_list: List[List[str]]) -> dict:
        """批量获取医生姓名

        Args:
            doctor_ids_list: 医生ID列表的列表

        Returns:
            {tuple(sorted_doctor_ids): [doctor_names]} 的字典
        """
        if not doctor_ids_list:
            return {}

        # 收集所有唯一的 doctor_id
        all_doctor_ids = set()
        for ids in doctor_ids_list:
            if ids:
                all_doctor_ids.update(ids)

        if not all_doctor_ids:
            # 所有列表都为空
            return {tuple(): []}

        # 批量查询所有医生
        result = await self.db.execute(
            select(Doctor).where(Doctor.id.in_(all_doctor_ids), Doctor.deleted_at.is_(None))
        )
        doctors = result.scalars().all()
        doctor_map = {d.id: d.name for d in doctors}

        # 为每个输入列表构建结果
        batch_result = {}
        for ids in doctor_ids_list:
            key = tuple(sorted(ids)) if ids else tuple()
            names = [doctor_map.get(did) for did in ids if did in doctor_map]
            batch_result[key] = names

        return batch_result
