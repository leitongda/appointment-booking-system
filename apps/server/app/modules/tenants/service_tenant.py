"""租户服务"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin import Admin, Role
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.lowcode_page import LowCodePage
from app.models.miniapp_platform import MiniappInstance
from app.models.store import Store
from app.models.tenant import SubscriptionPlan, Tenant
from app.modules.tenants.schemas import (
    TenantCreate,
    TenantQuery,
    TenantSelfUpdateRequest,
    TenantUpdate,
)


class TenantService:
    """租户服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tenant_id: str) -> Tenant | None:
        """获取租户"""
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.subscription_plan))
            .where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, tenant_code: str) -> Tenant | None:
        """通过编码获取租户"""
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.subscription_plan))
            .where(Tenant.tenant_code == tenant_code)
        )
        return result.scalar_one_or_none()

    async def get_list(self, query: TenantQuery, include_deleted: bool = False) -> tuple[list[Tenant], int]:
        """获取租户列表

        Args:
            query: 查询条件
            include_deleted: 是否包含已软删除的租户

        Returns:
            (租户列表, 总数)
        """
        base_query = select(Tenant).options(selectinload(Tenant.subscription_plan))

        # 默认过滤已软删除的租户
        if not include_deleted:
            base_query = base_query.where(Tenant.deleted_at.is_(None))

        # 条件过滤
        conditions = []
        if query.keyword:
            keyword = f"%{query.keyword}%"
            conditions.append(
                or_(
                    Tenant.name.ilike(keyword),
                    Tenant.tenant_code.ilike(keyword),
                    Tenant.contact_name.ilike(keyword),
                    Tenant.contact_phone.ilike(keyword),
                )
            )
        if query.status is not None:
            conditions.append(Tenant.status == query.status)
        if query.subscription_plan_id:
            conditions.append(Tenant.subscription_plan_id == query.subscription_plan_id)
        if query.tags:
            tag_list = [t.strip() for t in query.tags.split(",") if t.strip()]
            if tag_list:
                tag_conditions = []
                for tag in tag_list:
                    tag_conditions.append(Tenant.tags.contains(f'"{tag}"'))
                conditions.append(or_(*tag_conditions))

        if conditions:
            base_query = base_query.where(and_(*conditions))

        # 统计总数
        count_query = select(func.count(Tenant.id))
        if not include_deleted:
            count_query = count_query.where(Tenant.deleted_at.is_(None))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 分页
        offset = (query.page - 1) * query.page_size
        base_query = base_query.order_by(Tenant.created_at.desc()).offset(offset).limit(query.page_size)

        result = await self.db.execute(base_query)
        tenants = list(result.scalars().all())

        return tenants, total

    # TenantCreate 中需要单独计算、不从 data 直接映射的字段
    _CREATE_COMPUTED_FIELDS = {"is_trial"}

    async def create(self, data: TenantCreate, created_by: str | None = None) -> Tenant:
        """创建租户"""
        # 检查编码是否已存在
        existing = await self.get_by_code(data.tenant_code)
        if existing:
            raise ValueError(f"租户标识 '{data.tenant_code}' 已存在")

        # 获取订阅计划
        plan = None
        if data.subscription_plan_id:
            plan = await self.db.get(SubscriptionPlan, data.subscription_plan_id)
            if not plan:
                raise ValueError("订阅计划不存在")

        # 计算订阅时间
        now = datetime.utcnow()
        if data.billing_cycle == "yearly":
            end_at = now + timedelta(days=365)
        else:
            end_at = now + timedelta(days=30)

        # 通用字段映射：排除 is_trial（计算字段），其余全部从 schema 映射
        create_data = data.model_dump(exclude=self._CREATE_COMPUTED_FIELDS, exclude_unset=True)

        tenant = Tenant(
            **create_data,
            status=3 if data.is_trial else 1,
            subscription_start_at=now,
            subscription_end_at=end_at,
            created_by=created_by,
        )

        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)

        # 初始化租户默认数据
        await self._init_tenant_defaults(tenant)

        # 重新加载关联
        await self.db.refresh(tenant, ["subscription_plan"])

        return tenant

    async def _init_tenant_defaults(self, tenant: Tenant) -> None:
        """初始化租户默认数据：门店、科室、角色"""

        now = datetime.utcnow()

        # 1. 创建默认门店
        default_store = Store(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            name=f"{tenant.name}总店",
            code="MAIN",
            status=1,
            sort_order=0,
            created_at=now,
            updated_at=now,
        )
        self.db.add(default_store)
        await self.db.flush()

        # 2. 创建默认科室
        default_department = Department(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            store_id=default_store.id,
            name="全科",
            description="默认科室",
            status=1,
            sort_order=0,
            created_at=now,
            updated_at=now,
        )
        self.db.add(default_department)
        await self.db.flush()

        # 3. 创建默认管理员角色
        default_role = Role(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            name="管理员",
            code="admin",
            description="租户默认管理员，拥有全部权限",
            status=1,
            permissions='["*"]',  # 全部权限
            created_at=now,
            updated_at=now,
        )
        self.db.add(default_role)
        await self.db.flush()

        await self.db.commit()

    async def update(self, tenant_id: str, data: TenantUpdate | TenantSelfUpdateRequest, updated_by: str | None = None) -> Tenant | None:
        """更新租户"""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        old_status = tenant.status

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(tenant, key, value)

        tenant.updated_by = updated_by
        await self.db.commit()
        await self.db.refresh(tenant)

        # 审计追踪
        from app.modules.tenants.audit_tracker import AuditTracker
        tracker = AuditTracker(self.db)
        await tracker.track_update(
            tenant, tenant_id=tenant.id,
            resource_type="tenant", resource_id=tenant.id,
            actor_id=updated_by, actor_type="admin",
        )
        if tenant.status != old_status:
            await tracker.track_status_change(
                tenant_id=tenant.id,
                resource_type="tenant", resource_id=tenant.id,
                old_status=old_status, new_status=tenant.status,
                actor_id=updated_by, actor_type="admin",
            )

        return tenant

    async def update_status(self, tenant_id: str, new_status: int, actor_id: str | None = None) -> Tenant | None:
        """更新租户状态"""
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return None

        old_status = tenant.status
        tenant.status = new_status
        await self.db.commit()
        await self.db.refresh(tenant)

        # 审计追踪
        from app.modules.tenants.audit_tracker import AuditTracker
        tracker = AuditTracker(self.db)
        await tracker.track_status_change(
            tenant_id=tenant_id,
            resource_type="tenant", resource_id=tenant_id,
            old_status=old_status, new_status=new_status,
            actor_id=actor_id,
        )

        return tenant

    async def suspend(self, tenant_id: str) -> Tenant | None:
        """暂停租户"""
        return await self.update_status(tenant_id, 0)

    async def activate(self, tenant_id: str) -> Tenant | None:
        """激活租户"""
        return await self.update_status(tenant_id, 1)

    async def mark_overdue(self, tenant_id: str) -> Tenant | None:
        """标记租户为欠费"""
        return await self.update_status(tenant_id, 2)

    async def delete(self, tenant_id: str, deleted_by: str | None = None) -> bool:
        """删除租户（软删除）

        软删除策略：
        - 设置 deleted_at 和 deleted_by 字段
        - 设置 status 为 0（禁用）
        - 保留所有关联数据 90 天后才能物理删除
        - 删除后租户无法登录和访问

        Args:
            tenant_id: 租户ID
            deleted_by: 操作人ID

        Returns:
            是否删除成功
        """
        tenant = await self.get_by_id(tenant_id)
        if not tenant:
            return False

        # 检查是否已经软删除
        if tenant.deleted_at is not None:
            raise ValueError("租户已被删除")

        # 软删除
        tenant.deleted_at = datetime.utcnow()
        tenant.deleted_by = deleted_by
        tenant.status = 0  # 禁用
        await self.db.commit()
        return True

    async def restore(self, tenant_id: str, restored_by: str | None = None) -> Tenant | None:
        """恢复已软删除的租户

        Args:
            tenant_id: 租户ID
            restored_by: 操作人ID

        Returns:
            恢复的租户对象
        """
        result = await self.db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        # 检查是否已软删除
        if tenant.deleted_at is None:
            raise ValueError("租户未被删除，无需恢复")

        # 恢复
        tenant.deleted_at = None
        tenant.deleted_by = None
        tenant.status = 1  # 正常
        tenant.updated_by = restored_by
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def get_store_count(self, tenant_id: str) -> int:
        """获取租户的门店数量"""
        result = await self.db.execute(
            select(func.count(Store.id)).where(Store.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def get_admin_count(self, tenant_id: str) -> int:
        """获取租户的管理员数量"""
        result = await self.db.execute(
            select(func.count(Admin.id)).where(Admin.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def get_store_counts_batch(self, tenant_ids: list[str]) -> dict:
        """批量获取租户的门店数量

        Args:
            tenant_ids: 租户ID列表

        Returns:
            {tenant_id: count} 的字典
        """
        if not tenant_ids:
            return {}

        result = await self.db.execute(
            select(Store.tenant_id, func.count(Store.id).label("count"))
            .where(Store.tenant_id.in_(tenant_ids))
            .group_by(Store.tenant_id)
        )
        return {row.tenant_id: row.count for row in result.all()}

    async def get_admin_counts_batch(self, tenant_ids: list[str]) -> dict:
        """批量获取租户的管理员数量

        Args:
            tenant_ids: 租户ID列表

        Returns:
            {tenant_id: count} 的字典
        """
        if not tenant_ids:
            return {}

        result = await self.db.execute(
            select(Admin.tenant_id, func.count(Admin.id).label("count"))
            .where(Admin.tenant_id.in_(tenant_ids))
            .group_by(Admin.tenant_id)
        )
        return {row.tenant_id: row.count for row in result.all()}

    async def get_doctor_count(self, tenant_id: str) -> int:
        """获取租户的医生数量"""
        # 通过门店关联获取医生数
        result = await self.db.execute(
            select(func.count(Doctor.id))
            .join(Store, Doctor.store_id == Store.id)
            .where(Store.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def get_lowcode_page_count(self, tenant_id: str) -> int:
        """获取租户的低代码页面数量"""
        result = await self.db.execute(
            select(func.count(LowCodePage.id))
            .where(LowCodePage.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def get_miniapp_instance_count(self, tenant_id: str) -> int:
        """获取租户的小程序实例数量"""
        result = await self.db.execute(
            select(func.count(MiniappInstance.id))
            .where(MiniappInstance.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def check_code_exists(self, tenant_code: str, exclude_id: str | None = None) -> bool:
        """检查租户编码是否已存在"""
        query = select(func.count(Tenant.id)).where(Tenant.tenant_code == tenant_code)
        if exclude_id:
            query = query.where(Tenant.id != exclude_id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def register_tenant(self, data) -> dict:
        """租户自助注册（创建试用租户 + 管理员账号）"""
        from app.core.security import get_password_hash
        from app.models.admin import Admin as AdminModel
        from app.models.admin import Role
        from app.modules.tenants.service_plan import SubscriptionPlanService

        existing = await self.get_by_code(data.tenant_code)
        if existing:
            raise ValueError(f"租户标识 '{data.tenant_code}' 已被占用")

        plan_svc = SubscriptionPlanService(self.db)
        default_plan = await plan_svc.get_default_plan()

        now = datetime.utcnow()
        end_at = now + timedelta(days=14)

        tenant = Tenant(
            tenant_code=data.tenant_code,
            name=data.name,
            status=3,  # 试用
            subscription_plan_id=default_plan.id if default_plan else None,
            subscription_start_at=now,
            subscription_end_at=end_at,
            billing_cycle="monthly",
            contact_name=data.contact_name,
            contact_phone=data.contact_phone,
            contact_email=data.contact_email,
            created_at=now,
            updated_at=now,
        )
        self.db.add(tenant)
        await self.db.flush()

        await self._init_tenant_defaults(tenant)

        result = await self.db.execute(
            select(Role).where(Role.tenant_id == tenant.id, Role.code == "admin")
        )
        admin_role = result.scalar_one_or_none()

        admin = AdminModel(
            id=str(uuid.uuid4()),
            tenant_id=tenant.id,
            username=data.admin_username,
            password_hash=get_password_hash(data.admin_password),
            name=data.contact_name,
            phone=data.contact_phone,
            role_id=admin_role.id if admin_role else None,
            status=1,
            is_super_admin=False,
            created_at=now,
            updated_at=now,
        )
        self.db.add(admin)
        await self.db.commit()

        return {
            "tenant_id": tenant.id,
            "tenant_code": tenant.tenant_code,
            "name": tenant.name,
            "admin_id": admin.id,
        }
