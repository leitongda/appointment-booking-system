"""小程序平台管理服务"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.orm import selectinload
from typing import Optional, Tuple, List
from datetime import datetime

from app.models.miniapp_platform import Company, PaymentProfile, MiniappInstance
from app.modules.miniapp_platform.schemas import (
    CompanyCreate, CompanyUpdate,
    PaymentProfileCreate, PaymentProfileUpdate, PaymentProfileQuery,
    MiniappInstanceCreate, MiniappInstanceUpdate, MiniappInstanceQuery,
)
from app.common.tenant_filter import add_tenant_filter
from app.middleware.tenant_context import get_current_tenant_id


class CompanyService:
    """公司/结算主体服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, company_id: str) -> Optional[Company]:
        """获取公司详情"""
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str, tenant_id: str) -> Optional[Company]:
        """按编码获取公司"""
        result = await self.db.execute(
            select(Company).where(
                and_(
                    Company.code == code,
                    Company.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        tenant_id: Optional[str] = None,
        keyword: Optional[str] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[Company], int]:
        """获取公司列表"""
        # 构建查询
        base_query = select(Company)
        conditions = []

        # 租户过滤
        if tenant_id:
            conditions.append(Company.tenant_id == tenant_id)
        else:
            # 如果没有指定租户，从上下文获取
            current_tenant_id = get_current_tenant_id()
            if current_tenant_id:
                conditions.append(Company.tenant_id == current_tenant_id)

        # 关键词搜索
        if keyword:
            keyword_pattern = f"%{keyword}%"
            conditions.append(
                or_(
                    Company.name.ilike(keyword_pattern),
                    Company.code.ilike(keyword_pattern),
                    Company.contact_name.ilike(keyword_pattern),
                    Company.contact_phone.ilike(keyword_pattern),
                )
            )

        # 状态过滤
        if status is not None:
            conditions.append(Company.status == status)

        if conditions:
            base_query = base_query.where(and_(*conditions))

        # 统计总数
        count_query = select(func.count(Company.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 分页
        offset = (page - 1) * page_size
        base_query = base_query.order_by(Company.created_at.desc()).offset(offset).limit(page_size)

        result = await self.db.execute(base_query)
        companies = list(result.scalars().all())

        return companies, total

    async def check_code_exists(
        self,
        code: str,
        tenant_id: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """检查编码是否已存在"""
        query = select(func.count(Company.id)).where(
            and_(
                Company.code == code,
                Company.tenant_id == tenant_id
            )
        )
        if exclude_id:
            query = query.where(Company.id != exclude_id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def create(
        self,
        data: CompanyCreate,
        tenant_id: str,
        operator_id: Optional[str] = None
    ) -> Company:
        """创建公司"""
        # 检查编码唯一性
        if data.code:
            existing = await self.check_code_exists(data.code, tenant_id)
            if existing:
                raise ValueError(f"公司编码 '{data.code}' 已存在")

        company = Company(
            tenant_id=tenant_id,
            name=data.name,
            code=data.code,
            unified_social_credit_code=data.unified_social_credit_code,
            contact_name=data.contact_name,
            contact_phone=data.contact_phone,
            status=1,
            created_by=operator_id,
        )

        self.db.add(company)
        await self.db.commit()
        await self.db.refresh(company)

        return company

    async def update(
        self,
        company_id: str,
        data: CompanyUpdate,
        operator_id: Optional[str] = None
    ) -> Optional[Company]:
        """更新公司"""
        company = await self.get_by_id(company_id)
        if not company:
            return None

        # 检查编码唯一性
        if data.code and data.code != company.code:
            existing = await self.check_code_exists(data.code, company.tenant_id, exclude_id=company_id)
            if existing:
                raise ValueError(f"公司编码 '{data.code}' 已存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(company, key, value)

        company.updated_by = operator_id
        await self.db.commit()
        await self.db.refresh(company)

        return company

    async def delete(self, company_id: str) -> bool:
        """删除公司"""
        company = await self.get_by_id(company_id)
        if not company:
            return False

        # 检查是否被支付配置引用
        result = await self.db.execute(
            select(func.count(PaymentProfile.id)).where(PaymentProfile.company_id == company_id)
        )
        count = result.scalar()
        if count > 0:
            raise ValueError(f"该公司已被 {count} 个支付配置引用，无法删除")

        await self.db.delete(company)
        await self.db.commit()

        return True


class PaymentProfileService:
    """支付配置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, profile_id: str) -> Optional[PaymentProfile]:
        """获取支付配置详情"""
        result = await self.db.execute(
            select(PaymentProfile)
            .options(selectinload(PaymentProfile.company))
            .where(PaymentProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str, tenant_id: str) -> Optional[PaymentProfile]:
        """按编码获取支付配置"""
        result = await self.db.execute(
            select(PaymentProfile).where(
                and_(
                    PaymentProfile.code == code,
                    PaymentProfile.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        tenant_id: Optional[str] = None,
        query: Optional[PaymentProfileQuery] = None
    ) -> Tuple[List[PaymentProfile], int]:
        """获取支付配置列表"""
        if query is None:
            query = PaymentProfileQuery()

        # 构建查询
        base_query = select(PaymentProfile).options(selectinload(PaymentProfile.company))
        conditions = []

        # 租户过滤
        if tenant_id:
            conditions.append(PaymentProfile.tenant_id == tenant_id)
        else:
            # 如果没有指定租户，从上下文获取
            current_tenant_id = get_current_tenant_id()
            if current_tenant_id:
                conditions.append(PaymentProfile.tenant_id == current_tenant_id)

        # 关键词搜索
        if query.keyword:
            keyword_pattern = f"%{query.keyword}%"
            conditions.append(
                or_(
                    PaymentProfile.name.ilike(keyword_pattern),
                    PaymentProfile.code.ilike(keyword_pattern),
                    PaymentProfile.app_id.ilike(keyword_pattern),
                )
            )

        # 状态过滤
        if query.status is not None:
            conditions.append(PaymentProfile.status == query.status)

        # 公司过滤
        if query.company_id:
            conditions.append(PaymentProfile.company_id == query.company_id)

        if conditions:
            base_query = base_query.where(and_(*conditions))

        # 统计总数
        count_query = select(func.count(PaymentProfile.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 分页
        offset = (query.page - 1) * query.page_size
        base_query = base_query.order_by(
            PaymentProfile.is_default.desc(),
            PaymentProfile.created_at.desc()
        ).offset(offset).limit(query.page_size)

        result = await self.db.execute(base_query)
        profiles = list(result.scalars().all())

        return profiles, total

    async def check_code_exists(
        self,
        code: str,
        tenant_id: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """检查编码是否已存在"""
        query = select(func.count(PaymentProfile.id)).where(
            and_(
                PaymentProfile.code == code,
                PaymentProfile.tenant_id == tenant_id
            )
        )
        if exclude_id:
            query = query.where(PaymentProfile.id != exclude_id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def create(
        self,
        data: PaymentProfileCreate,
        tenant_id: str,
        operator_id: Optional[str] = None
    ) -> PaymentProfile:
        """创建支付配置"""
        # 检查编码唯一性
        if data.code:
            existing = await self.check_code_exists(data.code, tenant_id)
            if existing:
                raise ValueError(f"支付配置编码 '{data.code}' 已存在")

        # 如果设置为默认，取消其他默认配置
        if data.is_default:
            await self._clear_other_defaults(tenant_id)

        # 验证公司是否属于同一租户
        if data.company_id:
            company = await self.db.get(Company, data.company_id)
            if not company:
                raise ValueError("公司不存在")
            if company.tenant_id != tenant_id:
                raise ValueError("公司不属于当前租户")

        profile = PaymentProfile(
            tenant_id=tenant_id,
            name=data.name,
            code=data.code,
            mode=data.mode,
            app_id=data.app_id,
            mch_id=data.mch_id,
            sub_mchid=data.sub_mchid,
            notify_url=data.notify_url,
            refund_notify_url=data.refund_notify_url,
            api_v3_key_ref=data.api_v3_key_ref,
            cert_serial_no=data.cert_serial_no,
            private_key_ref=data.private_key_ref,
            company_id=data.company_id,
            is_default=data.is_default if hasattr(data, 'is_default') else False,
            status=1,
            created_by=operator_id,
        )

        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)

        return profile

    async def update(
        self,
        profile_id: str,
        data: PaymentProfileUpdate,
        operator_id: Optional[str] = None
    ) -> Optional[PaymentProfile]:
        """更新支付配置"""
        profile = await self.get_by_id(profile_id)
        if not profile:
            return None

        # 检查编码唯一性
        if data.code and data.code != profile.code:
            existing = await self.check_code_exists(data.code, profile.tenant_id, exclude_id=profile_id)
            if existing:
                raise ValueError(f"支付配置编码 '{data.code}' 已存在")

        # 如果设置为默认，取消其他默认配置
        if data.is_default is True and not profile.is_default:
            await self._clear_other_defaults(profile.tenant_id, exclude_id=profile_id)

        # 验证公司是否属于同一租户
        if data.company_id and data.company_id != profile.company_id:
            company = await self.db.get(Company, data.company_id)
            if not company:
                raise ValueError("公司不存在")
            if company.tenant_id != profile.tenant_id:
                raise ValueError("公司不属于当前租户")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)

        profile.updated_by = operator_id
        await self.db.commit()
        await self.db.refresh(profile)

        return profile

    async def delete(self, profile_id: str) -> bool:
        """删除支付配置"""
        profile = await self.get_by_id(profile_id)
        if not profile:
            return False

        # 检查是否被路由引用
        from app.models.miniapp_platform import PaymentRoute
        result = await self.db.execute(
            select(func.count(PaymentRoute.id)).where(PaymentRoute.payment_profile_id == profile_id)
        )
        count = result.scalar()
        if count > 0:
            raise ValueError(f"该支付配置已被 {count} 个路由规则引用，无法删除")

        await self.db.delete(profile)
        await self.db.commit()

        return True

    async def set_default(self, profile_id: str, tenant_id: str) -> Optional[PaymentProfile]:
        """设置为默认支付配置"""
        profile = await self.get_by_id(profile_id)
        if not profile:
            return None

        # 验证租户
        if profile.tenant_id != tenant_id:
            raise ValueError("支付配置不属于当前租户")

        # 取消其他默认配置
        await self._clear_other_defaults(tenant_id, exclude_id=profile_id)

        # 设置为默认
        profile.is_default = True
        await self.db.commit()
        await self.db.refresh(profile)

        return profile

    async def _clear_other_defaults(
        self,
        tenant_id: str,
        exclude_id: Optional[str] = None
    ) -> None:
        """取消其他默认配置"""
        query = update(PaymentProfile).where(
            and_(
                PaymentProfile.tenant_id == tenant_id,
                PaymentProfile.is_default == True
            )
        ).values(is_default=False)

        if exclude_id:
            query = query.where(PaymentProfile.id != exclude_id)

        await self.db.execute(query)
        await self.db.commit()


class MiniappInstanceService:
    """小程序实例服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, instance_id: str) -> Optional[MiniappInstance]:
        """获取实例详情"""
        result = await self.db.execute(
            select(MiniappInstance)
            .options(
                selectinload(MiniappInstance.template),
                selectinload(MiniappInstance.template_version),
                selectinload(MiniappInstance.default_store),
                selectinload(MiniappInstance.default_payment_profile).selectinload(PaymentProfile.company),
            )
            .where(MiniappInstance.id == instance_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str, tenant_id: str) -> Optional[MiniappInstance]:
        """按编码获取实例"""
        result = await self.db.execute(
            select(MiniappInstance).where(
                and_(
                    MiniappInstance.code == code,
                    MiniappInstance.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        tenant_id: Optional[str] = None,
        query: Optional[MiniappInstanceQuery] = None
    ) -> Tuple[List[MiniappInstance], int]:
        """获取实例列表"""
        if query is None:
            query = MiniappInstanceQuery()

        # 构建查询
        base_query = select(MiniappInstance)
        conditions = []

        # 租户过滤
        if tenant_id:
            conditions.append(MiniappInstance.tenant_id == tenant_id)
        else:
            # 如果没有指定租户，从上下文获取
            current_tenant_id = get_current_tenant_id()
            if current_tenant_id:
                conditions.append(MiniappInstance.tenant_id == current_tenant_id)

        # 关键词搜索
        if query.keyword:
            keyword_pattern = f"%{query.keyword}%"
            conditions.append(
                or_(
                    MiniappInstance.name.ilike(keyword_pattern),
                    MiniappInstance.code.ilike(keyword_pattern),
                    MiniappInstance.app_id.ilike(keyword_pattern),
                )
            )

        # 状态过滤
        if query.status is not None:
            conditions.append(MiniappInstance.status == query.status)

        # 模板过滤
        if query.template_id:
            conditions.append(MiniappInstance.template_id == query.template_id)

        if conditions:
            base_query = base_query.where(and_(*conditions))

        # 统计总数
        count_query = select(func.count(MiniappInstance.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # 分页
        offset = (query.page - 1) * query.page_size
        base_query = base_query.order_by(MiniappInstance.created_at.desc()).offset(offset).limit(query.page_size)

        result = await self.db.execute(base_query)
        instances = list(result.scalars().all())

        return instances, total

    async def check_code_exists(
        self,
        code: str,
        tenant_id: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """检查编码是否已存在"""
        query = select(func.count(MiniappInstance.id)).where(
            and_(
                MiniappInstance.code == code,
                MiniappInstance.tenant_id == tenant_id
            )
        )
        if exclude_id:
            query = query.where(MiniappInstance.id != exclude_id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def check_app_id_exists(
        self,
        app_id: str,
        tenant_id: str,
        exclude_id: Optional[str] = None
    ) -> bool:
        """检查 AppID 是否已存在"""
        query = select(func.count(MiniappInstance.id)).where(
            and_(
                MiniappInstance.app_id == app_id,
                MiniappInstance.tenant_id == tenant_id
            )
        )
        if exclude_id:
            query = query.where(MiniappInstance.id != exclude_id)
        result = await self.db.execute(query)
        return (result.scalar() or 0) > 0

    async def create(
        self,
        data: MiniappInstanceCreate,
        tenant_id: str,
        operator_id: Optional[str] = None
    ) -> MiniappInstance:
        """创建小程序实例"""
        from app.models.miniapp_platform import AppTemplate, TemplateVersion
        from app.models.store import Store

        # 检查编码唯一性
        if data.code:
            existing = await self.check_code_exists(data.code, tenant_id)
            if existing:
                raise ValueError(f"实例编码 '{data.code}' 已存在")

        # 检查 AppID 唯一性
        existing = await self.check_app_id_exists(data.app_id, tenant_id)
        if existing:
            raise ValueError(f"AppID '{data.app_id}' 已存在")

        # 验证模板是否存在
        if data.template_id:
            template = await self.db.get(AppTemplate, data.template_id)
            if not template:
                raise ValueError("模板不存在")

        # 验证模板版本是否存在
        if data.template_version_id:
            version = await self.db.get(TemplateVersion, data.template_version_id)
            if not version:
                raise ValueError("模板版本不存在")

        # 验证门店是否属于同一租户
        if data.default_store_id:
            store = await self.db.get(Store, data.default_store_id)
            if not store:
                raise ValueError("默认门店不存在")
            if store.tenant_id != tenant_id:
                raise ValueError("默认门店不属于当前租户")

        # 验证支付配置是否属于同一租户
        if data.default_payment_profile_id:
            profile = await self.db.get(PaymentProfile, data.default_payment_profile_id)
            if not profile:
                raise ValueError("默认支付配置不存在")
            if profile.tenant_id != tenant_id:
                raise ValueError("默认支付配置不属于当前租户")

        instance = MiniappInstance(
            tenant_id=tenant_id,
            code=data.code,
            name=data.name,
            app_id=data.app_id,
            app_secret_ref=data.app_secret_ref,
            upload_private_key_ref=data.upload_private_key_ref,
            template_id=data.template_id,
            template_version_id=data.template_version_id,
            default_store_id=data.default_store_id,
            default_payment_profile_id=data.default_payment_profile_id,
            app_config=data.app_config,
            status=1,
            created_by=operator_id,
        )

        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)

        return instance

    async def update(
        self,
        instance_id: str,
        data: MiniappInstanceUpdate,
        operator_id: Optional[str] = None
    ) -> Optional[MiniappInstance]:
        """更新小程序实例"""
        from app.models.miniapp_platform import AppTemplate, TemplateVersion
        from app.models.store import Store

        instance = await self.get_by_id(instance_id)
        if not instance:
            return None

        # 检查编码唯一性
        if data.code and data.code != instance.code:
            existing = await self.check_code_exists(data.code, instance.tenant_id, exclude_id=instance_id)
            if existing:
                raise ValueError(f"实例编码 '{data.code}' 已存在")

        # 检查 AppID 唯一性
        if data.app_id and data.app_id != instance.app_id:
            existing = await self.check_app_id_exists(data.app_id, instance.tenant_id, exclude_id=instance_id)
            if existing:
                raise ValueError(f"AppID '{data.app_id}' 已存在")

        # 验证模板是否存在
        if data.template_id and data.template_id != instance.template_id:
            template = await self.db.get(AppTemplate, data.template_id)
            if not template:
                raise ValueError("模板不存在")

        # 验证模板版本是否存在
        if data.template_version_id and data.template_version_id != instance.template_version_id:
            version = await self.db.get(TemplateVersion, data.template_version_id)
            if not version:
                raise ValueError("模板版本不存在")

        # 验证门店是否属于同一租户
        if data.default_store_id and data.default_store_id != instance.default_store_id:
            store = await self.db.get(Store, data.default_store_id)
            if not store:
                raise ValueError("默认门店不存在")
            if store.tenant_id != instance.tenant_id:
                raise ValueError("默认门店不属于当前租户")

        # 验证支付配置是否属于同一租户
        if data.default_payment_profile_id and data.default_payment_profile_id != instance.default_payment_profile_id:
            profile = await self.db.get(PaymentProfile, data.default_payment_profile_id)
            if not profile:
                raise ValueError("默认支付配置不存在")
            if profile.tenant_id != instance.tenant_id:
                raise ValueError("默认支付配置不属于当前租户")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(instance, key, value)

        instance.updated_by = operator_id
        await self.db.commit()
        await self.db.refresh(instance)

        return instance

    async def delete(self, instance_id: str) -> bool:
        """删除小程序实例（软删除/归档）"""
        instance = await self.get_by_id(instance_id)
        if not instance:
            return False

        # 归档而不是真正删除
        instance.status = 2  # 归档状态
        await self.db.commit()

        return True

    async def update_status(self, instance_id: str, new_status: int) -> Optional[MiniappInstance]:
        """更新实例状态"""
        instance = await self.get_by_id(instance_id)
        if not instance:
            return None

        if new_status not in [0, 1, 2]:
            raise ValueError("状态值必须是 0(禁用)、1(启用) 或 2(归档)")

        instance.status = new_status
        await self.db.commit()
        await self.db.refresh(instance)

        return instance
