from datetime import datetime, timedelta

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.appointment import Appointment
from app.models.store_visit_type_config import StoreVisitTypeConfig
from app.schemas.store_visit_type_config import StoreVisitTypeConfigCreate, StoreVisitTypeConfigUpdate
from app.utils.audit import set_create_audit, set_update_audit


class VisitTypeService:
    """复诊规则配置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, config_id: str) -> StoreVisitTypeConfig | None:
        """根据ID获取配置"""
        result = await self.db.execute(
            select(StoreVisitTypeConfig)
            .options(joinedload(StoreVisitTypeConfig.store))
            .where(StoreVisitTypeConfig.id == config_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_store_id(self, store_id: str) -> StoreVisitTypeConfig | None:
        """根据门店ID获取配置"""
        result = await self.db.execute(
            select(StoreVisitTypeConfig)
            .options(joinedload(StoreVisitTypeConfig.store))
            .where(StoreVisitTypeConfig.store_id == store_id)
        )
        return result.unique().scalar_one_or_none()

    async def create(self, data: StoreVisitTypeConfigCreate, operator_id: str | None = None) -> StoreVisitTypeConfig:
        """创建配置"""
        config = StoreVisitTypeConfig(
            store_id=data.store_id,
            time_limit=data.time_limit,
            time_unit=data.time_unit.value,
            scope=data.scope.value,
            status=data.status
        )
        set_create_audit(config, operator_id)
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update(self, config_id: str, data: StoreVisitTypeConfigUpdate, operator_id: str | None = None) -> StoreVisitTypeConfig | None:
        """更新配置"""
        config = await self.get_by_id(config_id)
        if not config:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(value, 'value'):  # Enum
                setattr(config, key, value.value)
            else:
                setattr(config, key, value)

        set_update_audit(config, operator_id)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def create_or_update(self, store_id: str, data: StoreVisitTypeConfigUpdate, operator_id: str | None = None) -> StoreVisitTypeConfig:
        """创建或更新门店配置"""
        config = await self.get_by_store_id(store_id)

        if config:
            # 更新现有配置
            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(value, 'value'):  # Enum
                    setattr(config, key, value.value)
                else:
                    setattr(config, key, value)
            set_update_audit(config, operator_id)
        else:
            # 创建新配置
            config = StoreVisitTypeConfig(
                store_id=store_id,
                time_limit=data.time_limit or 30,
                time_unit=data.time_unit.value if data.time_unit else "days",
                scope=data.scope.value if data.scope else "same_doctor",
                status=data.status if data.status is not None else 1
            )
            set_create_audit(config, operator_id)
            self.db.add(config)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete(self, config_id: str) -> bool:
        """删除配置"""
        config = await self.get_by_id(config_id)
        if not config:
            return False

        await self.db.delete(config)
        await self.db.commit()
        return True

    async def is_follow_up_visit(
        self,
        patient_id: str,
        store_id: str,
        doctor_id: str,
        department_id: str,
        check_time: datetime | None = None
    ) -> bool:
        """
        判断是否为复诊

        根据门店配置的复诊规则判断：
        1. 获取门店的复诊规则配置
        2. 根据配置的时间限制和范围查询历史预约
        3. 如果在时间限制内有符合范围条件的已完成预约，则为复诊
        """
        if check_time is None:
            check_time = datetime.now()

        # 获取门店配置
        config = await self.get_by_store_id(store_id)

        # 如果没有配置或配置禁用，默认按初诊处理
        if not config or config.status != 1:
            return False

        # 计算时间范围
        if config.time_unit == "hours":
            start_time = check_time - timedelta(hours=config.time_limit)
        else:
            start_time = check_time - timedelta(days=config.time_limit)

        # 构建查询条件
        conditions = [
            Appointment.patient_id == patient_id,
            Appointment.status == 5,  # 已完成
            Appointment.complete_time >= start_time,
            Appointment.complete_time < check_time,
        ]

        # 根据范围配置添加条件
        if config.scope == "same_doctor":
            # 同一医生
            conditions.append(Appointment.doctor_id == doctor_id)
        elif config.scope == "same_department":
            # 同一科室 - 需要通过排班获取科室
            # 获取该科室下所有医生的预约
            from app.models.doctor import Doctor
            doctor_result = await self.db.execute(
                select(Doctor.id).where(Doctor.department_id == department_id, Doctor.deleted_at.is_(None))
            )
            doctor_ids = [row[0] for row in doctor_result.fetchall()]
            if doctor_ids:
                conditions.append(Appointment.doctor_id.in_(doctor_ids))
            else:
                return False
        elif config.scope == "same_store":
            # 同一门店 - 查询该门店下所有医生的预约
            from app.models.doctor import Doctor
            doctor_result = await self.db.execute(
                select(Doctor.id).where(Doctor.store_id == store_id, Doctor.deleted_at.is_(None))
            )
            doctor_ids = [row[0] for row in doctor_result.fetchall()]
            if doctor_ids:
                conditions.append(Appointment.doctor_id.in_(doctor_ids))
            else:
                return False

        # 查询历史预约
        result = await self.db.execute(
            select(Appointment.id).where(and_(*conditions)).limit(1)
        )

        return result.scalar_one_or_none() is not None
