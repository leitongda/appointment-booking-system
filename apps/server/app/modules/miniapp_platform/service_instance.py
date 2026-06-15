"""小程序实例、模板、构建、发布服务"""
import logging

logger = logging.getLogger(__name__)

import json
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.miniapp_platform import (
    AppTemplate,
    BuildJob,
    MiniappInstance,
    PaymentProfile,
    ReleaseArtifact,
    ReleaseJob,
    TemplateVersion,
)
from app.modules.miniapp_platform.schemas import MiniappInstanceCreate, MiniappInstanceQuery, MiniappInstanceUpdate
from app.schemas.miniapp_template import BuildJobCreate, ReleaseJobCreate


class MiniappInstanceService:
    """小程序实例服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, instance_id: str) -> MiniappInstance | None:
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

    async def get_by_code(self, code: str, tenant_id: str) -> MiniappInstance | None:
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
        tenant_id: str | None = None,
        query: MiniappInstanceQuery | None = None
    ) -> tuple[list[MiniappInstance], int]:
        """获取实例列表"""
        from sqlalchemy import or_

        if query is None:
            query = MiniappInstanceQuery()

        base_query = select(MiniappInstance)
        conditions = []

        if tenant_id:
            conditions.append(MiniappInstance.tenant_id == tenant_id)
        else:
            current_tenant_id = get_current_tenant_id()
            if current_tenant_id:
                conditions.append(MiniappInstance.tenant_id == current_tenant_id)

        if query.keyword:
            keyword_pattern = f"%{query.keyword}%"
            conditions.append(
                or_(
                    MiniappInstance.name.ilike(keyword_pattern),
                    MiniappInstance.code.ilike(keyword_pattern),
                    MiniappInstance.app_id.ilike(keyword_pattern),
                )
            )

        if query.status is not None:
            conditions.append(MiniappInstance.status == query.status)

        if query.template_id:
            conditions.append(MiniappInstance.template_id == query.template_id)

        if conditions:
            base_query = base_query.where(and_(*conditions))

        count_query = select(func.count(MiniappInstance.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        offset = (query.page - 1) * query.page_size
        base_query = base_query.order_by(MiniappInstance.created_at.desc()).offset(offset).limit(query.page_size)

        result = await self.db.execute(base_query)
        instances = list(result.scalars().all())

        return instances, total

    async def check_code_exists(
        self,
        code: str,
        tenant_id: str,
        exclude_id: str | None = None
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
        exclude_id: str | None = None
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
        operator_id: str | None = None
    ) -> MiniappInstance:
        """创建小程序实例"""
        from app.models.miniapp_platform import AppTemplate, TemplateVersion
        from app.models.store import Store

        if data.code:
            existing = await self.check_code_exists(data.code, tenant_id)
            if existing:
                raise ValueError(f"实例编码 '{data.code}' 已存在")

        existing = await self.check_app_id_exists(data.app_id, tenant_id)
        if existing:
            raise ValueError(f"AppID '{data.app_id}' 已存在")

        if data.template_id:
            template = await self.db.get(AppTemplate, data.template_id)
            if not template:
                raise ValueError("模板不存在")

        if data.template_version_id:
            version = await self.db.get(TemplateVersion, data.template_version_id)
            if not version:
                raise ValueError("模板版本不存在")

        if data.default_store_id:
            store = await self.db.get(Store, data.default_store_id)
            if not store:
                raise ValueError("默认门店不存在")
            if store.tenant_id != tenant_id:
                raise ValueError("默认门店不属于当前租户")

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
        operator_id: str | None = None
    ) -> MiniappInstance | None:
        """更新小程序实例"""
        from app.models.miniapp_platform import AppTemplate, TemplateVersion
        from app.models.store import Store

        instance = await self.get_by_id(instance_id)
        if not instance:
            return None

        if data.code and data.code != instance.code:
            existing = await self.check_code_exists(data.code, instance.tenant_id, exclude_id=instance_id)
            if existing:
                raise ValueError(f"实例编码 '{data.code}' 已存在")

        if data.app_id and data.app_id != instance.app_id:
            existing = await self.check_app_id_exists(data.app_id, instance.tenant_id, exclude_id=instance_id)
            if existing:
                raise ValueError(f"AppID '{data.app_id}' 已存在")

        if data.template_id and data.template_id != instance.template_id:
            template = await self.db.get(AppTemplate, data.template_id)
            if not template:
                raise ValueError("模板不存在")

        if data.template_version_id and data.template_version_id != instance.template_version_id:
            version = await self.db.get(TemplateVersion, data.template_version_id)
            if not version:
                raise ValueError("模板版本不存在")

        if data.default_store_id and data.default_store_id != instance.default_store_id:
            store = await self.db.get(Store, data.default_store_id)
            if not store:
                raise ValueError("默认门店不存在")
            if store.tenant_id != instance.tenant_id:
                raise ValueError("默认门店不属于当前租户")

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

        instance.status = 2
        await self.db.commit()

        return True

    async def update_status(self, instance_id: str, new_status: int) -> MiniappInstance | None:
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


class AppTemplateService:
    """模板管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, template_id: str) -> AppTemplate | None:
        """获取模板详情"""
        result = await self.db.execute(
            select(AppTemplate).where(AppTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> AppTemplate | None:
        """按编码获取模板"""
        result = await self.db.execute(
            select(AppTemplate).where(AppTemplate.code == code)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        category: str | None = None,
        status: int | None = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[list[AppTemplate], int]:
        """获取模板列表"""
        conditions = []

        if category:
            conditions.append(AppTemplate.category == category)

        if status is not None:
            conditions.append(AppTemplate.status == status)

        base_query = select(AppTemplate)
        if conditions:
            base_query = base_query.where(and_(*conditions))

        count_query = select(func.count(AppTemplate.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        base_query = base_query.order_by(AppTemplate.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(base_query)
        templates = list(result.scalars().all())

        return templates, total

    async def create(
        self,
        name: str,
        code: str,
        description: str | None,
        category: str,
        default_config: dict[str, Any] | None,
        operator_id: str | None = None
    ) -> AppTemplate:
        """创建模板"""
        existing = await self.get_by_code(code)
        if existing:
            raise ValueError(f"模板编码 '{code}' 已存在")

        template = AppTemplate(
            name=name,
            code=code,
            description=description,
            category=category,
            default_config=json.dumps(default_config) if default_config else None,
            status=1,
            created_by=operator_id,
        )

        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)

        return template

    async def update(
        self,
        template_id: str,
        name: str | None = None,
        description: str | None = None,
        default_config: dict[str, Any] | None = None,
        status: int | None = None,
        operator_id: str | None = None
    ) -> AppTemplate | None:
        """更新模板"""
        template = await self.get_by_id(template_id)
        if not template:
            return None

        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if default_config is not None:
            template.default_config = json.dumps(default_config)
        if status is not None:
            template.status = status

        template.updated_by = operator_id
        await self.db.commit()
        await self.db.refresh(template)

        return template

    async def get_versions(
        self,
        template_id: str,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[list[TemplateVersion], int]:
        """获取模板版本列表"""
        count_query = select(func.count(TemplateVersion.id)).where(
            TemplateVersion.template_id == template_id
        )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        base_query = select(TemplateVersion).where(
            TemplateVersion.template_id == template_id
        ).order_by(
            TemplateVersion.created_at.desc()
        ).offset(skip).limit(limit)

        result = await self.db.execute(base_query)
        versions = list(result.scalars().all())

        return versions, total

    async def create_version(
        self,
        template_id: str,
        version: str,
        source_ref: str | None = None,
        schema_version: str | None = None,
        changelog: str | None = None,
        operator_id: str | None = None
    ) -> TemplateVersion:
        """创建模板版本"""
        existing_query = select(TemplateVersion).where(
            and_(
                TemplateVersion.template_id == template_id,
                TemplateVersion.version == version
            )
        )
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise ValueError(f"模板版本 '{version}' 已存在")

        template_version = TemplateVersion(
            template_id=template_id,
            version=version,
            source_ref=source_ref,
            schema_version=schema_version,
            changelog=changelog,
            status=1,
            created_by=operator_id,
        )

        self.db.add(template_version)
        await self.db.commit()
        await self.db.refresh(template_version)

        return template_version


class BuildJobService:
    """构建任务服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, job_id: str) -> BuildJob | None:
        """获取构建任务详情"""
        result = await self.db.execute(
            select(BuildJob)
            .options(
                selectinload(BuildJob.miniapp_instance),
                selectinload(BuildJob.template_version),
            )
            .where(BuildJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        tenant_id: str,
        instance_id: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[list[BuildJob], int]:
        """获取构建任务列表"""
        conditions = [BuildJob.tenant_id == tenant_id]

        if instance_id:
            conditions.append(BuildJob.miniapp_instance_id == instance_id)

        if status:
            conditions.append(BuildJob.status == status)

        base_query = select(BuildJob).options(
            selectinload(BuildJob.miniapp_instance),
            selectinload(BuildJob.template_version),
        )
        if conditions:
            base_query = base_query.where(and_(*conditions))

        count_query = select(func.count(BuildJob.id)).where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        base_query = base_query.order_by(BuildJob.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(base_query)
        jobs = list(result.scalars().all())

        return jobs, total

    async def create(
        self,
        tenant_id: str,
        data: BuildJobCreate,
        operator_id: str | None = None
    ) -> BuildJob:
        """创建构建任务"""
        instance = await self.db.execute(
            select(MiniappInstance).where(
                and_(
                    MiniappInstance.id == data.miniapp_instance_id,
                    MiniappInstance.tenant_id == tenant_id
                )
            )
        )
        instance_obj = instance.scalar_one_or_none()
        if not instance_obj:
            raise ValueError("小程序实例不存在或不属于当前租户")

        if data.template_version_id:
            version = await self.db.get(TemplateVersion, data.template_version_id)
            if not version:
                raise ValueError("模板版本不存在")

        job = BuildJob(
            tenant_id=tenant_id,
            miniapp_instance_id=data.miniapp_instance_id,
            template_version_id=data.template_version_id,
            trigger_source=data.trigger_source,
            build_params=json.dumps(data.build_params) if data.build_params else None,
            status="pending",
            created_by=operator_id,
        )

        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        return job

    async def update_status(
        self,
        job_id: str,
        status: str,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        **kwargs
    ) -> BuildJob | None:
        """更新构建任务状态"""
        job = await self.get_by_id(job_id)
        if not job:
            return None

        job.status = status
        if started_at:
            job.started_at = started_at
        if finished_at:
            job.finished_at = finished_at

        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)

        await self.db.commit()
        await self.db.refresh(job)

        return job


class ReleaseJobService:
    """发布任务服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, job_id: str) -> ReleaseJob | None:
        """获取发布任务详情"""
        result = await self.db.execute(
            select(ReleaseJob)
            .options(
                selectinload(ReleaseJob.miniapp_instance),
                selectinload(ReleaseJob.artifact),
            )
            .where(ReleaseJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        tenant_id: str,
        instance_id: str | None = None,
        action: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[list[ReleaseJob], int]:
        """获取发布任务列表"""
        conditions = []

        if instance_id:
            conditions.append(ReleaseJob.miniapp_instance_id == instance_id)

        if action:
            conditions.append(ReleaseJob.action == action)

        if status:
            conditions.append(ReleaseJob.status == status)

        base_query = select(ReleaseJob).options(
            selectinload(ReleaseJob.miniapp_instance),
            selectinload(ReleaseJob.artifact),
        )
        if conditions:
            base_query = base_query.where(and_(*conditions))

        count_query = select(func.count(ReleaseJob.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        base_query = base_query.order_by(ReleaseJob.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(base_query)
        jobs = list(result.scalars().all())

        return jobs, total

    async def create(
        self,
        tenant_id: str,
        data: ReleaseJobCreate,
        operator_id: str | None = None
    ) -> ReleaseJob:
        """创建发布任务"""
        instance = await self.db.execute(
            select(MiniappInstance).where(
                and_(
                    MiniappInstance.id == data.miniapp_instance_id,
                    MiniappInstance.tenant_id == tenant_id
                )
            )
        )
        instance_obj = instance.scalar_one_or_none()
        if not instance_obj:
            raise ValueError("小程序实例不存在或不属于当前租户")

        if data.artifact_id:
            artifact = await self.db.get(ReleaseArtifact, data.artifact_id)
            if not artifact:
                raise ValueError("发布制品不存在")

        job = ReleaseJob(
            miniapp_instance_id=data.miniapp_instance_id,
            artifact_id=data.artifact_id,
            action=data.action,
            target_version=data.target_version,
            status="pending",
            created_by=operator_id,
        )

        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        return job

    async def update_status(
        self,
        job_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        **kwargs
    ) -> ReleaseJob | None:
        """更新发布任务状态"""
        job = await self.get_by_id(job_id)
        if not job:
            return None

        job.status = status
        if result is not None:
            job.result = json.dumps(result)

        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)

        await self.db.commit()
        await self.db.refresh(job)

        return job
