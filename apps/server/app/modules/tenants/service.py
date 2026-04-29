"""租户管理服务"""
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, Tuple, List
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid

from fastapi import HTTPException, status

from app.core.config import settings
from app.models.tenant import Tenant, TenantSubscription, TenantUsageLog, TenantNotification, SubscriptionPlan
from app.models.store import Store
from app.models.admin import Admin, Role
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.appointment import Appointment
from app.models.schedule_template import ScheduleTemplate
from app.models.doctor_booking_setting import DoctorBookingSetting
from app.models.booking_notice import BookingNotice
from app.models.email_template import EmailTemplate
from app.models.message import MessageTemplate
from app.models.rest_day import RestDay
from app.models.blacklist import Blacklist
from app.models.store_visit_type_config import StoreVisitTypeConfig
from app.models.store_email_recipient import StoreEmailRecipient
from app.models.consultation_fee import ConsultationFeeTemplate
from app.models.rule_set import RuleSet, RuleWindow, RuleBookingPolicy, RuleCheckinPolicy, RuleCapacityPolicy, RuleSetShiftType
from app.modules.tenants.schemas import (
    TenantCreate, TenantUpdate, TenantQuery,
    SubscriptionPlanCreate, SubscriptionPlanUpdate,
    TenantSubscriptionCreate
)


class SubscriptionPlanService:
    """订阅计划服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, plan_id: str) -> Optional[SubscriptionPlan]:
        """获取订阅计划"""
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, plan_code: str) -> Optional[SubscriptionPlan]:
        """通过编码获取订阅计划"""
        result = await self.db.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.plan_code == plan_code)
        )
        return result.scalar_one_or_none()

    async def get_list(self, status: Optional[int] = None) -> List[SubscriptionPlan]:
        """获取订阅计划列表"""
        query = select(SubscriptionPlan).order_by(SubscriptionPlan.sort_order, SubscriptionPlan.created_at)
        if status is not None:
            query = query.where(SubscriptionPlan.status == status)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_default_plan(self) -> Optional[SubscriptionPlan]:
        """获取默认订阅计划"""
        result = await self.db.execute(
            select(SubscriptionPlan).where(
                and_(
                    SubscriptionPlan.is_default == True,
                    SubscriptionPlan.status == 1
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: SubscriptionPlanCreate) -> SubscriptionPlan:
        """创建订阅计划"""
        # 检查编码是否已存在
        existing = await self.get_by_code(data.plan_code)
        if existing:
            raise ValueError(f"计划编码 '{data.plan_code}' 已存在")

        plan = SubscriptionPlan(**data.model_dump())
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def update(self, plan_id: str, data: SubscriptionPlanUpdate) -> Optional[SubscriptionPlan]:
        """更新订阅计划"""
        plan = await self.get_by_id(plan_id)
        if not plan:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(plan, key, value)

        await self.db.commit()
        await self.db.refresh(plan)
        return plan

    async def delete(self, plan_id: str) -> bool:
        """删除订阅计划"""
        plan = await self.get_by_id(plan_id)
        if not plan:
            return False

        # 检查是否有租户使用此计划
        result = await self.db.execute(
            select(func.count(Tenant.id)).where(Tenant.subscription_plan_id == plan_id)
        )
        count = result.scalar()
        if count > 0:
            raise ValueError(f"有 {count} 个租户正在使用此计划，无法删除")

        await self.db.delete(plan)
        await self.db.commit()
        return True


class TenantService:
    """租户服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tenant_id: str) -> Optional[Tenant]:
        """获取租户"""
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.subscription_plan))
            .where(Tenant.id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, tenant_code: str) -> Optional[Tenant]:
        """通过编码获取租户"""
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.subscription_plan))
            .where(Tenant.tenant_code == tenant_code)
        )
        return result.scalar_one_or_none()

    async def get_list(self, query: TenantQuery, include_deleted: bool = False) -> Tuple[List[Tenant], int]:
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
            import json as _json
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

    async def create(self, data: TenantCreate, created_by: Optional[str] = None) -> Tenant:
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

        tenant = Tenant(
            tenant_code=data.tenant_code,
            name=data.name,
            status=3 if data.is_trial else 1,  # 试用租户状态为3
            subscription_plan_id=data.subscription_plan_id,
            subscription_start_at=now,
            subscription_end_at=end_at,
            billing_cycle=data.billing_cycle,
            max_stores=data.max_stores,
            max_admins=data.max_admins,
            max_doctors=data.max_doctors,
            max_appointments_per_month=data.max_appointments_per_month,
            features=data.features,
            branding_config=data.branding_config,
            contact_name=data.contact_name,
            contact_phone=data.contact_phone,
            contact_email=data.contact_email,
            address=data.address,
            custom_domain=data.custom_domain,
            subdomain=data.subdomain,
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
        from app.utils.audit import set_create_audit

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

    async def update(self, tenant_id: str, data: TenantUpdate, updated_by: Optional[str] = None) -> Optional[Tenant]:
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

    async def update_status(self, tenant_id: str, new_status: int, actor_id: Optional[str] = None) -> Optional[Tenant]:
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

    async def suspend(self, tenant_id: str) -> Optional[Tenant]:
        """暂停租户"""
        return await self.update_status(tenant_id, 0)

    async def activate(self, tenant_id: str) -> Optional[Tenant]:
        """激活租户"""
        return await self.update_status(tenant_id, 1)

    async def mark_overdue(self, tenant_id: str) -> Optional[Tenant]:
        """标记租户为欠费"""
        return await self.update_status(tenant_id, 2)

    async def delete(self, tenant_id: str, deleted_by: Optional[str] = None) -> bool:
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

    async def restore(self, tenant_id: str, restored_by: Optional[str] = None) -> Optional[Tenant]:
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

    async def get_store_counts_batch(self, tenant_ids: List[str]) -> dict:
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

    async def get_admin_counts_batch(self, tenant_ids: List[str]) -> dict:
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

    async def check_code_exists(self, tenant_code: str, exclude_id: Optional[str] = None) -> bool:
        """检查租户编码是否已存在"""
        query = select(func.count(Tenant.id)).where(Tenant.tenant_code == tenant_code)
        if exclude_id:
            query = query.where(Tenant.id != exclude_id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def register_tenant(self, data) -> dict:
        """租户自助注册（创建试用租户 + 管理员账号）"""
        from app.core.security import get_password_hash
        from app.models.admin import Admin as AdminModel, Role

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

    async def precheck_migration(
        self,
        target_tenant_id: str,
        source_tenant_id: str,
        entity_types: Optional[List[str]] = None,
    ) -> dict:
        """迁移前预检：检查配额、数据量"""
        from app.modules.tenants.schemas import PrecheckQuotaItem

        target = await self.get_by_id(target_tenant_id)
        if not target:
            raise ValueError("目标租户不存在")
        source = await self.get_by_id(source_tenant_id)
        if not source:
            raise ValueError("源租户不存在")
        if target_tenant_id == source_tenant_id:
            raise ValueError("源租户和目标租户不能相同")

        warnings = []
        quota_checks = []
        entity_counts = {}

        count_models = {
            "stores": (Store, Store.tenant_id),
            "departments": (Department, Department.tenant_id),
            "doctors": (Doctor, Doctor.tenant_id),
            "schedule_templates": (ScheduleTemplate, ScheduleTemplate.tenant_id),
            "booking_notices": (BookingNotice, BookingNotice.tenant_id),
            "email_templates": (EmailTemplate, EmailTemplate.tenant_id),
            "message_templates": (MessageTemplate, MessageTemplate.tenant_id),
            "rest_days": (RestDay, RestDay.tenant_id),
            "blacklists": (Blacklist, Blacklist.tenant_id),
            "rule_sets": (RuleSet, RuleSet.tenant_id),
        }

        if entity_types:
            count_models = {k: v for k, v in count_models.items() if k in entity_types}

        for name, (model, filter_col) in count_models.items():
            result = await self.db.execute(
                select(func.count(model.id)).where(filter_col == source_tenant_id)
            )
            entity_counts[name] = result.scalar() or 0

        if "stores" in entity_counts:
            src = entity_counts["stores"]
            cur = await self.get_store_count(target_tenant_id)
            mx = target.get_effective_max_stores()
            quota_checks.append(PrecheckQuotaItem(
                resource_name="门店", current_count=cur, max_count=mx,
                source_count=src, would_exceed=cur + src > mx,
            ))

        if "doctors" in entity_counts:
            src = entity_counts["doctors"]
            cur = await self.get_doctor_count(target_tenant_id)
            mx = target.get_effective_max_doctors()
            quota_checks.append(PrecheckQuotaItem(
                resource_name="医生", current_count=cur, max_count=mx,
                source_count=src, would_exceed=cur + src > mx,
            ))

        if target.status == 3:
            warnings.append("目标租户处于试用期，功能可能受限")
        if source.status == 0:
            warnings.append("源租户已被禁用，数据可能不完整")

        can_migrate = not any(q.would_exceed for q in quota_checks)
        estimated_ms = sum(entity_counts.values()) * 15

        return {
            "can_migrate": can_migrate,
            "warnings": warnings,
            "quota_checks": quota_checks,
            "entity_counts": entity_counts,
            "estimated_duration_ms": estimated_ms,
        }

    async def migrate_data(
        self,
        target_tenant_id: str,
        source_tenant_id: str,
        preserve_ids: bool = False,
        entity_types: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> dict:
        """跨租户数据迁移

        将源租户的配置类数据复制到目标租户。
        支持按 entity_types 过滤，None 表示迁移全部支持的类型。

        Args:
            target_tenant_id: 目标租户ID
            source_tenant_id: 源租户ID
            preserve_ids: 是否保留原始ID（默认生成新ID）
            entity_types: 要迁移的实体类型列表，None表示全部
            created_by: 操作人ID

        Returns:
            {"copied": {...}, "failures": [...], "duration_ms": int}
        """
        import time
        from sqlalchemy.orm import class_mapper

        start_time = time.time()

        # 验证目标租户和源租户
        target_tenant = await self.get_by_id(target_tenant_id)
        if not target_tenant:
            raise ValueError("目标租户不存在")

        source_tenant = await self.get_by_id(source_tenant_id)
        if not source_tenant:
            raise ValueError("源租户不存在")

        if target_tenant_id == source_tenant_id:
            raise ValueError("源租户和目标租户不能相同")

        # 定义所有支持的实体类型及其配置
        # 顺序很重要：有外键依赖的放在后面
        all_entity_configs = [
            {
                "name": "stores",
                "model": Store,
                "filter_col": Store.tenant_id,
                "quota_field": "max_stores",
                "quota_name": "门店",
            },
            {
                "name": "departments",
                "model": Department,
                "filter_col": Department.tenant_id,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "doctors",
                "model": Doctor,
                "filter_col": Doctor.tenant_id,
                "quota_field": "max_doctors",
                "quota_name": "医生",
                "depends_on": {"stores": "store_id", "departments": "department_id"},
            },
            {
                "name": "schedule_templates",
                "model": ScheduleTemplate,
                "filter_col": ScheduleTemplate.tenant_id,
                "depends_on": {"stores": "store_id", "departments": "department_id", "doctors": "doctor_id"},
            },
            {
                "name": "doctor_booking_settings",
                "model": DoctorBookingSetting,
                "filter_col": None,  # 通过 store -> doctor 关联
                "depends_on": {"stores": "store_id", "doctors": "doctor_id"},
            },
            {
                "name": "booking_notices",
                "model": BookingNotice,
                "filter_col": BookingNotice.tenant_id,
            },
            {
                "name": "email_templates",
                "model": EmailTemplate,
                "filter_col": EmailTemplate.tenant_id,
            },
            {
                "name": "message_templates",
                "model": MessageTemplate,
                "filter_col": MessageTemplate.tenant_id,
            },
            {
                "name": "rest_days",
                "model": RestDay,
                "filter_col": RestDay.tenant_id,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "blacklists",
                "model": Blacklist,
                "filter_col": Blacklist.tenant_id,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "store_visit_type_configs",
                "model": StoreVisitTypeConfig,
                "filter_col": None,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "store_email_recipients",
                "model": StoreEmailRecipient,
                "filter_col": None,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "consultation_fee_templates",
                "model": ConsultationFeeTemplate,
                "filter_col": None,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "rule_sets",
                "model": RuleSet,
                "filter_col": RuleSet.tenant_id,
                "depends_on": {"stores": "store_id", "departments": "department_id", "doctors": "doctor_id"},
                "has_nested": True,
            },
        ]

        # 过滤要迁移的实体类型
        if entity_types:
            entity_configs = [c for c in all_entity_configs if c["name"] in entity_types]
            # 检查无效的实体类型
            valid_names = {c["name"] for c in all_entity_configs}
            invalid = set(entity_types) - valid_names
            if invalid:
                raise ValueError(f"不支持的实体类型: {', '.join(invalid)}")
        else:
            entity_configs = all_entity_configs

        # 配额预检查（仅对配置了 quota_field 的类型）
        for config in entity_configs:
            quota_field = config.get("quota_field")
            if not quota_field:
                continue

            quota_name = config.get("quota_name", quota_field)
            model = config["model"]
            filter_col = config.get("filter_col")

            # 获取源租户该类型数量
            if filter_col is not None:
                source_count_result = await self.db.execute(
                    select(func.count(model.id)).where(filter_col == source_tenant_id)
                )
            else:
                # 通过 store 关联查询
                if model == DoctorBookingSetting:
                    source_count_result = await self.db.execute(
                        select(func.count(DoctorBookingSetting.id))
                        .join(Store, DoctorBookingSetting.store_id == Store.id)
                        .where(Store.tenant_id == source_tenant_id)
                    )
                elif model == StoreVisitTypeConfig:
                    source_count_result = await self.db.execute(
                        select(func.count(StoreVisitTypeConfig.id))
                        .join(Store, StoreVisitTypeConfig.store_id == Store.id)
                        .where(Store.tenant_id == source_tenant_id)
                    )
                elif model == StoreEmailRecipient:
                    source_count_result = await self.db.execute(
                        select(func.count(StoreEmailRecipient.id))
                        .join(Store, StoreEmailRecipient.store_id == Store.id)
                        .where(Store.tenant_id == source_tenant_id)
                    )
                elif model == ConsultationFeeTemplate:
                    source_count_result = await self.db.execute(
                        select(func.count(ConsultationFeeTemplate.id))
                        .join(Store, ConsultationFeeTemplate.store_id == Store.id)
                        .where(Store.tenant_id == source_tenant_id)
                    )
                else:
                    continue

            source_count = source_count_result.scalar() or 0
            if source_count == 0:
                continue

            # 获取目标租户当前数量
            if quota_field == "max_stores":
                target_current = await self.get_store_count(target_tenant_id)
                target_max = target_tenant.get_effective_max_stores()
            elif quota_field == "max_doctors":
                target_current = await self.get_doctor_count(target_tenant_id)
                target_max = target_tenant.get_effective_max_doctors()
            else:
                continue

            if target_current + source_count > target_max:
                raise ValueError(
                    f"{quota_name}配额不足: 目标租户当前 {target_current}，"
                    f"需迁移 {source_count}，上限 {target_max}"
                )

        # 执行迁移
        copied_counts: dict = {}
        failures: List[dict] = []
        id_mappings: dict = {}  # {entity_name: {old_id: new_id}}

        now = datetime.utcnow()

        def _get_new_id(old_id: str) -> str:
            return old_id if preserve_ids else str(uuid.uuid4())

        def _copy_model_instance(instance, model_class, tenant_id_override: Optional[str] = None,
                                  id_override: Optional[str] = None,
                                  field_overrides: Optional[dict] = None):
            """复制 SQLAlchemy 模型实例，排除主键和审计字段"""
            mapper = class_mapper(model_class)
            new_data = {}

            for col in mapper.columns:
                col_name = col.name
                # 跳过主键（如果重新生成）
                if col.primary_key and id_override is None and not preserve_ids:
                    continue
                # 跳过审计字段
                if col_name in ("created_at", "updated_at", "created_by", "updated_by", "deleted_at", "deleted_by"):
                    continue

                val = getattr(instance, col_name, None)

                # 替换 tenant_id
                if col_name == "tenant_id" and tenant_id_override is not None:
                    new_data[col_name] = tenant_id_override
                # 替换主键
                elif col.primary_key and id_override is not None:
                    new_data[col_name] = id_override
                # 字段覆盖
                elif field_overrides and col_name in field_overrides:
                    new_data[col_name] = field_overrides[col_name]
                else:
                    new_data[col_name] = val

            # 设置审计字段
            new_data["created_at"] = now
            new_data["updated_at"] = now
            if created_by:
                new_data["created_by"] = created_by
                new_data["updated_by"] = created_by

            return model_class(**new_data)

        for config in entity_configs:
            entity_name = config["name"]
            model = config["model"]
            filter_col = config.get("filter_col")
            depends_on = config.get("depends_on", {})
            has_nested = config.get("has_nested", False)

            try:
                # 查询源数据
                if filter_col is not None:
                    result = await self.db.execute(
                        select(model).where(filter_col == source_tenant_id)
                    )
                else:
                    # 通过 store 关联查询
                    if model == DoctorBookingSetting:
                        result = await self.db.execute(
                            select(DoctorBookingSetting)
                            .join(Store, DoctorBookingSetting.store_id == Store.id)
                            .where(Store.tenant_id == source_tenant_id)
                        )
                    elif model == StoreVisitTypeConfig:
                        result = await self.db.execute(
                            select(StoreVisitTypeConfig)
                            .join(Store, StoreVisitTypeConfig.store_id == Store.id)
                            .where(Store.tenant_id == source_tenant_id)
                        )
                    elif model == StoreEmailRecipient:
                        result = await self.db.execute(
                            select(StoreEmailRecipient)
                            .join(Store, StoreEmailRecipient.store_id == Store.id)
                            .where(Store.tenant_id == source_tenant_id)
                        )
                    elif model == ConsultationFeeTemplate:
                        result = await self.db.execute(
                            select(ConsultationFeeTemplate)
                            .join(Store, ConsultationFeeTemplate.store_id == Store.id)
                            .where(Store.tenant_id == source_tenant_id)
                        )
                    else:
                        result = await self.db.execute(select(model).where(False))

                source_items = list(result.scalars().all())
                if not source_items:
                    copied_counts[entity_name] = 0
                    continue

                # 构建ID映射
                id_mappings[entity_name] = {}
                for item in source_items:
                    old_id = item.id
                    new_id = _get_new_id(old_id)
                    id_mappings[entity_name][old_id] = new_id

                copied = 0
                for item in source_items:
                    new_id = id_mappings[entity_name][item.id]

                    # 构建字段覆盖
                    overrides = {"tenant_id": target_tenant_id}

                    # 处理外键依赖映射
                    for dep_name, fk_col in depends_on.items():
                        if dep_name in id_mappings:
                            old_fk = getattr(item, fk_col, None)
                            if old_fk and old_fk in id_mappings[dep_name]:
                                overrides[fk_col] = id_mappings[dep_name][old_fk]

                    new_instance = _copy_model_instance(
                        item, model,
                        tenant_id_override=target_tenant_id,
                        id_override=new_id,
                        field_overrides=overrides,
                    )
                    self.db.add(new_instance)
                    copied += 1

                await self.db.flush()
                copied_counts[entity_name] = copied

                # 处理 RuleSet 的嵌套关系
                if has_nested and entity_name == "rule_sets" and copied > 0:
                    total_windows = 0
                    for item in source_items:
                        old_rule_set_id = item.id
                        new_rule_set_id = id_mappings["rule_sets"][old_rule_set_id]

                        # 复制 windows
                        windows_result = await self.db.execute(
                            select(RuleWindow).where(RuleWindow.rule_set_id == old_rule_set_id)
                        )
                        windows = list(windows_result.scalars().all())
                        for w in windows:
                            new_w = _copy_model_instance(
                                w, RuleWindow,
                                field_overrides={"rule_set_id": new_rule_set_id, "tenant_id": target_tenant_id},
                            )
                            self.db.add(new_w)
                        total_windows += len(windows)

                        # 复制 booking_policy
                        if item.booking_policy:
                            new_bp = _copy_model_instance(
                                item.booking_policy, RuleBookingPolicy,
                                field_overrides={"rule_set_id": new_rule_set_id},
                            )
                            self.db.add(new_bp)

                        # 复制 checkin_policy
                        if item.checkin_policy:
                            new_cp = _copy_model_instance(
                                item.checkin_policy, RuleCheckinPolicy,
                                field_overrides={"rule_set_id": new_rule_set_id},
                            )
                            self.db.add(new_cp)

                        # 复制 capacity_policy
                        if item.capacity_policy:
                            new_cap = _copy_model_instance(
                                item.capacity_policy, RuleCapacityPolicy,
                                field_overrides={"rule_set_id": new_rule_set_id},
                            )
                            self.db.add(new_cap)

                        # 复制 shift_types 关联（多对多）
                        if item.shift_types:
                            for st in item.shift_types:
                                # ShiftType 是全局的（code unique），不需要复制
                                # 只需要建立关联
                                new_assoc = RuleSetShiftType(
                                    rule_set_id=new_rule_set_id,
                                    shift_type_id=st.id,
                                )
                                self.db.add(new_assoc)

                    await self.db.flush()
                    if total_windows > 0:
                        copied_counts["rule_set_windows"] = total_windows

            except Exception as exc:
                failures.append({
                    "entity": entity_name,
                    "error": str(exc),
                })
                # 继续处理下一个实体类型
                continue

        await self.db.commit()

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "copied": copied_counts,
            "failures": failures,
            "duration_ms": duration_ms,
        }


class TenantSubscriptionService:
    """租户订阅服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _check_downgrade_quota(
        self,
        tenant_id: str,
        old_plan: SubscriptionPlan,
        new_plan: SubscriptionPlan,
    ) -> None:
        """降级配额检查：当新计划某项配额低于旧计划时，校验当前实际使用量。

        如果任一资源超出新计划配额，抛出 HTTPException 并附上详细信息。
        """
        # 定义需要检查的配额维度：(字段名, 显示名, 获取实际使用量的协程)
        tenant_svc = TenantService(self.db)

        quota_dimensions = [
            (
                "max_stores",
                "门店",
                old_plan.max_stores,
                new_plan.max_stores,
                tenant_svc.get_store_count(tenant_id),
            ),
            (
                "max_admins",
                "管理员",
                old_plan.max_admins,
                new_plan.max_admins,
                tenant_svc.get_admin_count(tenant_id),
            ),
            (
                "max_doctors",
                "医生",
                old_plan.max_doctors,
                new_plan.max_doctors,
                tenant_svc.get_doctor_count(tenant_id),
            ),
            (
                "max_appointments_per_month",
                "月预约",
                old_plan.max_appointments_per_month,
                new_plan.max_appointments_per_month,
                self._get_month_appointment_count(tenant_id),
            ),
        ]

        violations: list[str] = []
        for field_name, display_name, old_limit, new_limit, coro in quota_dimensions:
            # 只在降级场景检查：新配额严格小于旧配额
            if new_limit >= old_limit:
                continue
            current_usage = await coro
            if current_usage > new_limit:
                violations.append(
                    f"{display_name}：当前 {current_usage}，新计划上限 {new_limit}，超出 {current_usage - new_limit}"
                )

        if violations:
            detail = "降级失败，以下资源超出新计划配额：" + "；".join(violations)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            )

    async def _get_month_appointment_count(self, tenant_id: str) -> int:
        """获取租户本月预约数"""
        today = date.today()
        month_start = today.replace(day=1)

        result = await self.db.execute(
            select(func.count(Appointment.id)).where(
                and_(
                    Appointment.tenant_id == tenant_id,
                    Appointment.created_at >= month_start,
                )
            )
        )
        return result.scalar() or 0

    async def create_subscription(
        self,
        tenant_id: str,
        data: TenantSubscriptionCreate,
        created_by: Optional[str] = None
    ) -> TenantSubscription:
        """创建租户订阅"""
        # 获取租户（加载关联的 subscription_plan）
        result = await self.db.execute(
            select(Tenant)
            .options(selectinload(Tenant.subscription_plan))
            .where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("租户不存在")

        # 获取新计划
        new_plan = await self.db.get(SubscriptionPlan, data.plan_id)
        if not new_plan:
            raise ValueError("订阅计划不存在")

        # 降级配额检查：如果租户当前已有订阅计划，且新计划配额更低，则校验实际使用量
        old_plan = tenant.subscription_plan
        if old_plan is not None and old_plan.id != new_plan.id:
            await self._check_downgrade_quota(tenant_id, old_plan, new_plan)

        # 记录旧的订阅信息用于审计
        old_plan_id = old_plan.id if old_plan else None
        old_end_at = str(tenant.subscription_end_at) if tenant.subscription_end_at else None

        # 计算时间范围
        start_at = data.start_at or datetime.utcnow()
        if data.billing_cycle == "yearly":
            end_at = start_at + timedelta(days=365)
            amount = new_plan.price_yearly
        else:
            end_at = start_at + timedelta(days=30)
            amount = new_plan.price_monthly

        # 创建订阅记录
        subscription = TenantSubscription(
            tenant_id=tenant_id,
            plan_id=new_plan.id,
            plan_code=new_plan.plan_code,
            plan_name=new_plan.name,
            billing_cycle=data.billing_cycle,
            start_at=start_at,
            end_at=end_at,
            amount=amount,
            final_amount=amount,
            auto_renew=data.auto_renew,
            created_by=created_by,
        )

        self.db.add(subscription)

        # 更新租户的订阅信息
        tenant.subscription_plan_id = new_plan.id
        tenant.subscription_start_at = start_at
        tenant.subscription_end_at = end_at
        tenant.billing_cycle = data.billing_cycle
        if tenant.status == 2:  # 如果是欠费状态，激活
            tenant.status = 1

        # 审计追踪：订阅变更
        from app.modules.tenants.audit_tracker import AuditTracker
        tracker = AuditTracker(self.db)
        await tracker.track_subscription_change(
            tenant_id=tenant_id,
            old_plan_id=old_plan_id,
            new_plan_id=new_plan.id,
            old_end_at=old_end_at,
            new_end_at=str(end_at),
            actor_id=created_by,
        )

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def get_tenant_subscriptions(
        self,
        tenant_id: str,
        limit: int = 10
    ) -> List[TenantSubscription]:
        """获取租户的订阅记录"""
        result = await self.db.execute(
            select(TenantSubscription)
            .where(TenantSubscription.tenant_id == tenant_id)
            .order_by(TenantSubscription.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class TenantUsageService:
    """租户用量统计服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_usage_summary(self, tenant_id: str) -> dict:
        """获取租户用量汇总"""
        stmt = select(Tenant).where(Tenant.id == tenant_id).options(selectinload(Tenant.subscription_plan))
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise ValueError("租户不存在")

        # 获取配额
        max_stores = tenant.get_effective_max_stores()
        max_admins = tenant.get_effective_max_admins()
        max_doctors = tenant.get_effective_max_doctors()
        max_appointments = tenant.get_effective_max_appointments()

        # 获取当前使用量
        store_count = await self._get_store_count(tenant_id)
        admin_count = await self._get_admin_count(tenant_id)
        doctor_count = await self._get_doctor_count(tenant_id)
        month_appointments = await self._get_month_appointment_count(tenant_id)
        storage_mb = await self._get_storage_usage(tenant_id)

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "max_stores": max_stores,
            "max_admins": max_admins,
            "max_doctors": max_doctors,
            "max_appointments_per_month": max_appointments,
            "current_store_count": store_count,
            "current_admin_count": admin_count,
            "current_doctor_count": doctor_count,
            "current_month_appointments": month_appointments,
            "current_storage_mb": storage_mb,
            "store_usage_rate": round(store_count / max_stores * 100, 2) if max_stores > 0 else 0,
            "admin_usage_rate": round(admin_count / max_admins * 100, 2) if max_admins > 0 else 0,
            "doctor_usage_rate": round(doctor_count / max_doctors * 100, 2) if max_doctors > 0 else 0,
            "appointment_usage_rate": round(month_appointments / max_appointments * 100, 2) if max_appointments > 0 else 0,
        }

    async def get_usage_logs(
        self,
        tenant_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 30
    ) -> List[TenantUsageLog]:
        """获取租户用量日志"""
        query = select(TenantUsageLog).where(TenantUsageLog.tenant_id == tenant_id)

        if start_date:
            query = query.where(TenantUsageLog.usage_date >= start_date)
        if end_date:
            query = query.where(TenantUsageLog.usage_date <= end_date)

        query = query.order_by(TenantUsageLog.usage_date.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def record_daily_usage(self, tenant_id: str, usage_date: Optional[date] = None) -> TenantUsageLog:
        """记录每日用量（定时任务调用）"""
        usage_date = usage_date or date.today()

        # 检查是否已存在
        result = await self.db.execute(
            select(TenantUsageLog).where(
                and_(
                    TenantUsageLog.tenant_id == tenant_id,
                    TenantUsageLog.usage_date == usage_date
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # 更新现有记录
            log = existing
        else:
            # 创建新记录
            log = TenantUsageLog(
                tenant_id=tenant_id,
                usage_date=usage_date
            )
            self.db.add(log)

        # 统计数据
        log.appointment_count = await self._get_day_appointment_count(tenant_id, usage_date)
        log.new_user_count = await self._get_day_new_user_count(tenant_id, usage_date)
        log.active_doctor_count = await self._get_doctor_count(tenant_id)

        await self.db.commit()
        await self.db.refresh(log)

        return log

    async def _get_store_count(self, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Store.id)).where(Store.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def _get_admin_count(self, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Admin.id)).where(Admin.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def _get_doctor_count(self, tenant_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Doctor.id))
            .join(Store, Doctor.store_id == Store.id)
            .where(Store.tenant_id == tenant_id)
        )
        return result.scalar() or 0

    async def _get_month_appointment_count(self, tenant_id: str) -> int:
        """获取本月预约数"""
        today = date.today()
        month_start = today.replace(day=1)

        result = await self.db.execute(
            select(func.count(Appointment.id))
            .where(
                and_(
                    Appointment.tenant_id == tenant_id,
                    Appointment.created_at >= month_start
                )
            )
        )
        return result.scalar() or 0

    async def _get_day_appointment_count(self, tenant_id: str, usage_date: date) -> int:
        """获取当日预约数"""
        day_start = datetime.combine(usage_date, datetime.min.time())
        day_end = datetime.combine(usage_date, datetime.max.time())

        result = await self.db.execute(
            select(func.count(Appointment.id))
            .where(
                and_(
                    Appointment.tenant_id == tenant_id,
                    Appointment.created_at >= day_start,
                    Appointment.created_at <= day_end
                )
            )
        )
        return result.scalar() or 0

    async def _get_day_new_user_count(self, tenant_id: str, usage_date: date) -> int:
        """获取当日新用户数"""
        from app.models.user import User, Patient

        day_start = datetime.combine(usage_date, datetime.min.time())
        day_end = datetime.combine(usage_date, datetime.max.time())

        # 通过患者首次就诊门店统计
        result = await self.db.execute(
            select(func.count(Patient.id))
            .join(Store, Patient.first_visit_store_id == Store.id)
            .where(
                and_(
                    Store.tenant_id == tenant_id,
                    Patient.created_at >= day_start,
                    Patient.created_at <= day_end
                )
            )
        )
        return result.scalar() or 0

    async def get_usage_trends(
        self,
        tenant_id: str,
        period_type: str = "week",
        periods: int = 8,
    ) -> dict:
        """获取租户用量趋势

        Args:
            tenant_id: 租户ID
            period_type: 周期类型 week/month
            periods: 返回几个周期

        Returns:
            包含趋势数据和环比变化率的字典
        """
        from app.modules.tenants.schemas import UsageTrendItem

        today = date.today()
        trends = []

        for i in range(periods - 1, -1, -1):
            if period_type == "month":
                # 计算月份起止
                target_month = today.month - i
                target_year = today.year
                while target_month <= 0:
                    target_month += 12
                    target_year -= 1
                period_start = date(target_year, target_month, 1)
                # 下月首日减一天
                if target_month == 12:
                    period_end = date(target_year + 1, 1, 1) - timedelta(days=1)
                else:
                    period_end = date(target_year, target_month + 1, 1) - timedelta(days=1)
                period_label = f"{target_year}-{target_month:02d}"
            else:
                # 计算周起止（周一开始）
                week_start = today - timedelta(days=today.weekday() + i * 7)
                period_start = week_start
                period_end = week_start + timedelta(days=6)
                period_label = f"{week_start.year}-W{week_start.isocalendar()[1]:02d}"

            # 聚合该周期内的用量日志
            stmt = select(
                func.coalesce(func.sum(TenantUsageLog.appointment_count), 0),
                func.coalesce(func.sum(TenantUsageLog.new_user_count), 0),
                func.coalesce(func.sum(TenantUsageLog.active_user_count), 0),
                func.coalesce(func.sum(TenantUsageLog.sms_sent_count), 0),
                func.coalesce(func.sum(TenantUsageLog.push_sent_count), 0),
                func.coalesce(func.max(TenantUsageLog.storage_used_mb), Decimal("0")),
            ).where(
                and_(
                    TenantUsageLog.tenant_id == tenant_id,
                    TenantUsageLog.usage_date >= period_start,
                    TenantUsageLog.usage_date <= period_end,
                )
            )
            result = await self.db.execute(stmt)
            row = result.one()

            trends.append(UsageTrendItem(
                period=period_label,
                appointment_count=row[0] or 0,
                new_user_count=row[1] or 0,
                active_user_count=row[2] or 0,
                sms_sent_count=row[3] or 0,
                push_sent_count=row[4] or 0,
                storage_used_mb=row[5] or Decimal("0"),
            ))

        # 计算环比变化率（最后两个周期）
        current = trends[-1] if trends else None
        previous = trends[-2] if len(trends) >= 2 else None

        def _change_rate(current_val, previous_val):
            if previous_val and previous_val > 0:
                return round((current_val - previous_val) / previous_val * 100, 2)
            return None

        return {
            "tenant_id": tenant_id,
            "period_type": period_type,
            "current_period": current,
            "previous_period": previous,
            "trends": trends,
            "appointment_change_rate": _change_rate(current.appointment_count, previous.appointment_count) if current and previous else None,
            "new_user_change_rate": _change_rate(current.new_user_count, previous.new_user_count) if current and previous else None,
            "active_user_change_rate": _change_rate(current.active_user_count, previous.active_user_count) if current and previous else None,
        }

    async def _get_storage_usage(self, tenant_id: str) -> Decimal:
        """获取存储使用量（MB）"""
        if settings.STORAGE_TYPE.lower() != "local":
            return Decimal("0")

        tenant_upload_dir = Path(settings.LOCAL_UPLOAD_DIR) / "tenants" / tenant_id
        if not tenant_upload_dir.exists():
            return Decimal("0")

        total_bytes = 0
        for path in tenant_upload_dir.rglob("*"):
            if path.is_file():
                total_bytes += path.stat().st_size

        megabyte = Decimal(1024 * 1024)
        return (Decimal(total_bytes) / megabyte).quantize(Decimal("0.0001"))


class TenantNotificationService:
    """租户通知服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_notifications(
        self,
        tenant_id: str,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[TenantNotification], int, int]:
        """获取通知列表，返回 (items, unread_count, total)"""
        base = select(TenantNotification).where(TenantNotification.tenant_id == tenant_id)
        count_base = select(func.count(TenantNotification.id)).where(TenantNotification.tenant_id == tenant_id)

        if unread_only:
            base = base.where(TenantNotification.is_read == False)  # noqa: E712
            count_base = count_base.where(TenantNotification.is_read == False)  # noqa: E712

        # 未读数（始终基于全部）
        unread_result = await self.db.execute(
            select(func.count(TenantNotification.id)).where(
                TenantNotification.tenant_id == tenant_id,
                TenantNotification.is_read == False,  # noqa: E712
            )
        )
        unread_count = unread_result.scalar() or 0

        # 总数
        total_result = await self.db.execute(count_base)
        total = total_result.scalar() or 0

        # 分页
        query = base.order_by(TenantNotification.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, unread_count, total

    async def mark_read(self, tenant_id: str, notification_id: str) -> bool:
        """标记单条已读"""
        result = await self.db.execute(
            select(TenantNotification).where(
                TenantNotification.id == notification_id,
                TenantNotification.tenant_id == tenant_id,
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return False
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def mark_all_read(self, tenant_id: str) -> int:
        """标记全部已读，返回影响行数"""
        result = await self.db.execute(
            select(TenantNotification).where(
                TenantNotification.tenant_id == tenant_id,
                TenantNotification.is_read == False,  # noqa: E712
            )
        )
        notifications = list(result.scalars().all())
        now = datetime.utcnow()
        for n in notifications:
            n.is_read = True
            n.read_at = now
        await self.db.commit()
        return len(notifications)
