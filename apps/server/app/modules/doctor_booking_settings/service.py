import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.doctor import Doctor
from app.models.doctor_booking_setting import DoctorBookingSetting
from app.models.store import Store
from app.schemas.doctor_booking_setting import (
    DoctorBookingSettingCreate,
    DoctorBookingSettingQuery,
    DoctorBookingSettingUpdate,
)
from app.utils.audit import set_create_audit, set_update_audit


class DoctorBookingSettingService:
    """医生预约设置服务

    Args:
        db: 数据库会话
        tenant_id: 管理员账号租户锚点（R1-13）。查询/写入以锚点强过滤；
            未传入时才回退请求上下文（兼容内部调用）。
    """

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    def _tenant_id(self) -> str | None:
        """账号锚点优先，未提供时回退请求上下文。"""
        if self.tenant_id is not None:
            return self.tenant_id
        return get_current_tenant_id()

    async def get_by_id(self, setting_id: str) -> DoctorBookingSetting | None:
        """根据ID获取设置"""
        stmt = select(DoctorBookingSetting).where(
            DoctorBookingSetting.id == setting_id
        )
        tenant_id = self._tenant_id()
        if tenant_id:
            stmt = stmt.where(DoctorBookingSetting.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_store_and_doctor(
        self,
        store_id: str,
        doctor_id: str
    ) -> DoctorBookingSetting | None:
        """根据门店ID和医生ID获取设置"""
        stmt = select(DoctorBookingSetting).where(
            and_(
                DoctorBookingSetting.store_id == store_id,
                DoctorBookingSetting.doctor_id == doctor_id
            )
        )
        tenant_id = self._tenant_id()
        if tenant_id:
            stmt = stmt.where(DoctorBookingSetting.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_effective_for_store_and_doctor(
        self,
        store_id: str,
        doctor_id: str,
    ) -> DoctorBookingSetting | None:
        stmt = (
            select(DoctorBookingSetting)
            .where(
                and_(
                    DoctorBookingSetting.store_id == store_id,
                    DoctorBookingSetting.doctor_id == doctor_id,
                    DoctorBookingSetting.status == 1,
                )
            )
        )
        tenant_id = self._tenant_id()
        if tenant_id:
            stmt = stmt.where(DoctorBookingSetting.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list(
        self,
        query: DoctorBookingSettingQuery
    ) -> tuple[list[dict], int]:
        """获取设置列表（包含门店名和医生名）"""
        stmt = (
            select(
                DoctorBookingSetting,
                Store.name.label('store_name'),
                Doctor.name.label('doctor_name')
            )
            .join(Store, DoctorBookingSetting.store_id == Store.id)
            .join(Doctor, DoctorBookingSetting.doctor_id == Doctor.id)
        )

        count_stmt = select(func.count(DoctorBookingSetting.id))

        tenant_id = self._tenant_id()
        if tenant_id:
            stmt = stmt.where(DoctorBookingSetting.tenant_id == tenant_id)
            count_stmt = count_stmt.where(DoctorBookingSetting.tenant_id == tenant_id)

        if query.store_id:
            stmt = stmt.where(DoctorBookingSetting.store_id == query.store_id)
            count_stmt = count_stmt.where(DoctorBookingSetting.store_id == query.store_id)

        if query.doctor_id:
            stmt = stmt.where(DoctorBookingSetting.doctor_id == query.doctor_id)
            count_stmt = count_stmt.where(DoctorBookingSetting.doctor_id == query.doctor_id)

        if query.status is not None:
            stmt = stmt.where(DoctorBookingSetting.status == query.status)
            count_stmt = count_stmt.where(DoctorBookingSetting.status == query.status)

        stmt = stmt.order_by(DoctorBookingSetting.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        items = []
        for row in result.all():
            setting = row[0]
            items.append({
                'id': setting.id,
                'store_id': setting.store_id,
                'store_name': row[1],
                'doctor_id': setting.doctor_id,
                'doctor_name': row[2],
                'booking_start_offset': setting.booking_start_offset,
                'booking_range_days': setting.booking_range_days,
                'release_time': setting.release_time,
                'status': setting.status,
                'created_at': setting.created_at,
                'updated_at': setting.updated_at,
            })

        total = count_result.scalar() or 0
        return items, total

    async def create(self, data: DoctorBookingSettingCreate, operator_id: str | None = None) -> DoctorBookingSetting:
        """创建设置"""
        existing = await self.get_by_store_and_doctor(data.store_id, data.doctor_id)
        if existing:
            raise ValueError("该门店已存在此医生的预约设置")

        store_result = await self.db.execute(
            select(Store).where(Store.id == data.store_id)
        )
        store = store_result.scalar_one_or_none()
        if not store:
            raise ValueError("门店不存在")
        tenant_id = self._tenant_id()
        if tenant_id and store.tenant_id != tenant_id:
            raise ValueError("门店不存在或无权限访问")

        doctor_result = await self.db.execute(
            select(Doctor).where(Doctor.id == data.doctor_id, Doctor.deleted_at.is_(None))
        )
        doctor = doctor_result.scalar_one_or_none()
        if not doctor:
            raise ValueError("医生不存在")
        if doctor.store_id != data.store_id:
            raise ValueError("所选医生不属于当前门店")

        setting = DoctorBookingSetting(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            **data.model_dump()
        )
        set_create_audit(setting, operator_id)
        self.db.add(setting)
        await self.db.commit()
        await self.db.refresh(setting)
        return setting

    async def update(
        self,
        setting_id: str,
        data: DoctorBookingSettingUpdate,
        operator_id: str | None = None
    ) -> DoctorBookingSetting | None:
        """更新设置"""
        setting = await self.get_by_id(setting_id)
        if not setting:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(setting, field, value)

        set_update_audit(setting, operator_id)
        await self.db.commit()
        await self.db.refresh(setting)
        return setting

    async def delete(self, setting_id: str) -> bool:
        """删除设置"""
        setting = await self.get_by_id(setting_id)
        if not setting:
            return False

        await self.db.delete(setting)
        await self.db.commit()
        return True

    async def get_existing_doctor_ids(self, store_id: str) -> list[str]:
        """获取指定门店已配置的医生ID列表"""
        stmt = (
            select(DoctorBookingSetting.doctor_id)
            .where(DoctorBookingSetting.store_id == store_id)
        )
        tenant_id = self._tenant_id()
        if tenant_id:
            stmt = stmt.where(DoctorBookingSetting.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def update_status(
        self,
        setting_id: str,
        status: int,
        operator_id: str | None = None
    ) -> DoctorBookingSetting | None:
        """更新设置状态"""
        setting = await self.get_by_id(setting_id)
        if not setting:
            return None

        setting.status = status
        set_update_audit(setting, operator_id)
        await self.db.commit()
        await self.db.refresh(setting)
        return setting
