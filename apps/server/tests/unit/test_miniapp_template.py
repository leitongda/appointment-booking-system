"""
小程序模板 CRUD API 端到端测试

测试模板列表、获取单个模板、404处理、构建任务和发布任务的完整流程
"""
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy import select

from app.models.miniapp_platform import (
    AppTemplate, TemplateVersion, MiniappInstance, BuildJob, ReleaseJob, ReleaseArtifact
)
from app.models.tenant import Tenant, SubscriptionPlan
from app.models.store import Store


@pytest.mark.asyncio
async def test_get_templates_list(db_session, test_tenant):
    """测试获取模板列表 - 应返回 5 套模板"""
    # 创建 5 套模板
    templates = [
        AppTemplate(
            id=str(uuid4()),
            name="现代综合医疗",
            code="modern-general",
            description="通用型医院模板",
            status=1,
            created_at=datetime.now(),
        ),
        AppTemplate(
            id=str(uuid4()),
            name="长辈友好中医康养",
            code="elderly-tcm",
            description="面向55岁以上长辈用户",
            status=1,
            created_at=datetime.now(),
        ),
        AppTemplate(
            id=str(uuid4()),
            name="高端专科门诊",
            code="premium-specialty",
            description="面向口腔、医美、私立专科",
            status=1,
            created_at=datetime.now(),
        ),
        AppTemplate(
            id=str(uuid4()),
            name="亲子儿科",
            code="family-pediatrics",
            description="面向儿童医院、儿科门诊",
            status=1,
            created_at=datetime.now(),
        ),
        AppTemplate(
            id=str(uuid4()),
            name="女性健康",
            code="womens-health",
            description="面向妇科、产康、女性体检",
            status=1,
            created_at=datetime.now(),
        ),
    ]
    db_session.add_all(templates)
    await db_session.commit()

    # 测试 API
    from app.modules.miniapp_platform.service import AppTemplateService

    service = AppTemplateService(db_session)
    result_templates, total = await service.get_list()

    assert total == 5, f"Expected 5 templates, got {total}"
    assert len(result_templates) == 5
    assert all(isinstance(t, AppTemplate) for t in result_templates)

    # 验证模板编码
    codes = [t.code for t in result_templates]
    expected_codes = {
        "modern-general", "elderly-tcm", "premium-specialty",
        "family-pediatrics", "womens-health"
    }
    assert set(codes) == expected_codes


@pytest.mark.asyncio
async def test_get_template_by_code(db_session):
    """测试按编码获取单个模板"""
    template = AppTemplate(
        id=str(uuid4()),
        name="现代综合医疗",
        code="modern-general",
        description="通用型医院模板",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(template)
    await db_session.commit()

    from app.modules.miniapp_platform.service import AppTemplateService

    service = AppTemplateService(db_session)
    result = await service.get_by_code("modern-general")

    assert result is not None
    assert result.code == "modern-general"
    assert result.name == "现代综合医疗"


@pytest.mark.asyncio
async def test_get_template_by_code_not_found(db_session):
    """测试获取不存在的模板返回 404"""
    from app.modules.miniapp_platform.service import AppTemplateService

    service = AppTemplateService(db_session)
    result = await service.get_by_code("non-existent-template")

    assert result is None


@pytest.mark.asyncio
async def test_create_build_job(db_session, test_tenant, test_store):
    """测试创建构建任务"""
    # 创建模板和版本
    template = AppTemplate(
        id=str(uuid4()),
        name="现代综合医疗",
        code="modern-general",
        description="通用型医院模板",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(template)
    await db_session.flush()

    version = TemplateVersion(
        id=str(uuid4()),
        template_id=template.id,
        version="1.0.0",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(version)
    await db_session.flush()

    # 创建小程序实例
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=test_store.id,
        name="测试实例",
        code="test-instance",
        app_id="wx-test-app-id",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(instance)
    await db_session.commit()

    # 测试创建构建任务
    from app.modules.miniapp_platform.service import BuildJobService
    from app.schemas.miniapp_template import BuildJobCreate

    service = BuildJobService(db_session)
    job_data = BuildJobCreate(
        miniapp_instance_id=instance.id,
        template_version_id=version.id,
        trigger_source="manual",
        build_params={"env": "production"}
    )

    job = await service.create(
        tenant_id=test_tenant.id,
        data=job_data,
        operator_id=str(uuid4())
    )

    assert job is not None
    assert job.miniapp_instance_id == instance.id
    assert job.template_version_id == version.id
    assert job.trigger_source == "manual"
    assert job.status == "pending"


@pytest.mark.asyncio
async def test_get_build_jobs_list(db_session, test_tenant, test_store):
    """测试获取构建任务列表"""
    # 创建必要的关联数据
    template = AppTemplate(
        id=str(uuid4()),
        name="现代综合医疗",
        code="modern-general",
        description="通用型医院模板",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(template)
    await db_session.flush()

    version = TemplateVersion(
        id=str(uuid4()),
        template_id=template.id,
        version="1.0.0",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(version)
    await db_session.flush()

    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=test_store.id,
        name="测试实例",
        code="test-instance",
        app_id="wx-test-app-id",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(instance)
    await db_session.flush()

    # 创建多个构建任务
    jobs = [
        BuildJob(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            miniapp_instance_id=instance.id,
            template_version_id=version.id,
            trigger_source="manual",
            status="pending",
            created_at=datetime.now(),
        ),
        BuildJob(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            miniapp_instance_id=instance.id,
            template_version_id=version.id,
            trigger_source="api",
            status="running",
            started_at=datetime.now(),
            created_at=datetime.now(),
        ),
        BuildJob(
            id=str(uuid4()),
            tenant_id=test_tenant.id,
            miniapp_instance_id=instance.id,
            template_version_id=version.id,
            trigger_source="scheduled",
            status="completed",
            started_at=datetime.now(),
            finished_at=datetime.now(),
            created_at=datetime.now(),
        ),
    ]
    db_session.add_all(jobs)
    await db_session.commit()

    # 测试获取列表
    from app.modules.miniapp_platform.service import BuildJobService

    service = BuildJobService(db_session)
    result_jobs, total = await service.get_list(
        tenant_id=test_tenant.id,
        skip=0,
        limit=10
    )

    assert total == 3
    assert len(result_jobs) == 3

    # 验证状态分布
    statuses = {j.status for j in result_jobs}
    assert statuses == {"pending", "running", "completed"}


@pytest.mark.asyncio
async def test_create_release_job(db_session, test_tenant, test_store):
    """测试创建发布任务"""
    # 创建必要的关联数据
    template = AppTemplate(
        id=str(uuid4()),
        name="现代综合医疗",
        code="modern-general",
        description="通用型医院模板",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(template)
    await db_session.flush()

    version = TemplateVersion(
        id=str(uuid4()),
        template_id=template.id,
        version="1.0.0",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(version)
    await db_session.flush()

    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=test_store.id,
        name="测试实例",
        code="test-instance",
        app_id="wx-test-app-id",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(instance)
    await db_session.flush()

    # 创建构建产物
    build_job = BuildJob(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        miniapp_instance_id=instance.id,
        template_version_id=version.id,
        status="completed",
        created_at=datetime.now(),
    )
    db_session.add(build_job)
    await db_session.flush()

    artifact = ReleaseArtifact(
        id=str(uuid4()),
        build_job_id=build_job.id,
        file_path="/uploads/test-app-v1.0.0.zip",
        checksum="abc123def456",
        created_at=datetime.now(),
    )
    db_session.add(artifact)
    await db_session.commit()

    # 测试创建发布任务
    from app.modules.miniapp_platform.service import ReleaseJobService
    from app.schemas.miniapp_template import ReleaseJobCreate

    service = ReleaseJobService(db_session)
    job_data = ReleaseJobCreate(
        miniapp_instance_id=instance.id,
        artifact_id=artifact.id,
        action="upload",
        target_version="1.0.0"
    )

    job = await service.create(
        tenant_id=test_tenant.id,
        data=job_data,
        operator_id=str(uuid4())
    )

    assert job is not None
    assert job.miniapp_instance_id == instance.id
    assert job.artifact_id == artifact.id
    assert job.action == "upload"
    assert job.target_version == "1.0.0"
    assert job.status == "pending"


@pytest.mark.asyncio
async def test_get_release_jobs_list(db_session, test_tenant, test_store):
    """测试获取发布任务列表"""
    # 创建必要的关联数据
    template = AppTemplate(
        id=str(uuid4()),
        name="现代综合医疗",
        code="modern-general",
        description="通用型医院模板",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(template)
    await db_session.flush()

    version = TemplateVersion(
        id=str(uuid4()),
        template_id=template.id,
        version="1.0.0",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(version)
    await db_session.flush()

    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=test_store.id,
        name="测试实例",
        code="test-instance",
        app_id="wx-test-app-id",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(instance)
    await db_session.flush()

    build_job = BuildJob(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        miniapp_instance_id=instance.id,
        template_version_id=version.id,
        status="completed",
        created_at=datetime.now(),
    )
    db_session.add(build_job)
    await db_session.flush()

    artifact = ReleaseArtifact(
        id=str(uuid4()),
        build_job_id=build_job.id,
        file_path="/uploads/test-app-v1.0.0.zip",
        checksum="abc123def456",
        created_at=datetime.now(),
    )
    db_session.add(artifact)
    await db_session.flush()

    # 创建多个发布任务
    import json
    jobs = [
        ReleaseJob(
            id=str(uuid4()),
            miniapp_instance_id=instance.id,
            artifact_id=artifact.id,
            action="upload",
            target_version="1.0.0",
            status="pending",
            created_at=datetime.now(),
        ),
        ReleaseJob(
            id=str(uuid4()),
            miniapp_instance_id=instance.id,
            artifact_id=artifact.id,
            action="submit_audit",
            target_version="1.0.0",
            status="completed",
            result=json.dumps({"auditId": "12345"}),
            created_at=datetime.now(),
        ),
        ReleaseJob(
            id=str(uuid4()),
            miniapp_instance_id=instance.id,
            artifact_id=artifact.id,
            action="publish",
            target_version="1.0.0",
            status="running",
            created_at=datetime.now(),
        ),
    ]
    db_session.add_all(jobs)
    await db_session.commit()

    # 测试获取列表
    from app.modules.miniapp_platform.service import ReleaseJobService

    service = ReleaseJobService(db_session)
    result_jobs, total = await service.get_list(
        tenant_id=None,  # 不过滤租户
        skip=0,
        limit=10
    )

    assert total == 3
    assert len(result_jobs) == 3

    # 验证动作类型
    actions = {j.action for j in result_jobs}
    assert actions == {"upload", "submit_audit", "publish"}


@pytest.mark.asyncio
async def test_template_version_crud(db_session):
    """测试模板版本 CRUD"""
    # 创建模板
    template = AppTemplate(
        id=str(uuid4()),
        name="现代综合医疗",
        code="modern-general",
        description="通用型医院模板",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(template)
    await db_session.commit()

    # 测试创建版本
    from app.modules.miniapp_platform.service import AppTemplateService

    service = AppTemplateService(db_session)
    version = await service.create_version(
        template_id=template.id,
        version="1.0.0",
        source_ref="git://templates/modern-general.git#v1.0.0",
        schema_version="1.0.0",
        changelog="初始版本"
    )

    assert version is not None
    assert version.template_id == template.id
    assert version.version == "1.0.0"
    assert version.source_ref == "git://templates/modern-general.git#v1.0.0"
    assert version.schema_version == "1.0.0"
    assert version.changelog == "初始版本"

    # 测试获取版本列表
    versions, total = await service.get_versions(template_id=template.id)
    assert total == 1
    assert len(versions) == 1
    assert versions[0].version == "1.0.0"


@pytest.mark.asyncio
async def test_build_job_status_update(db_session, test_tenant, test_store):
    """测试构建任务状态更新"""
    from app.modules.miniapp_platform.service import BuildJobService

    # 创建必要数据
    template = AppTemplate(
        id=str(uuid4()),
        name="现代综合医疗",
        code="modern-general",
        description="通用型医院模板",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(template)
    await db_session.flush()

    version = TemplateVersion(
        id=str(uuid4()),
        template_id=template.id,
        version="1.0.0",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(version)
    await db_session.flush()

    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=test_store.id,
        name="测试实例",
        code="test-instance",
        app_id="wx-test-app-id",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(instance)
    await db_session.flush()

    job = BuildJob(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        miniapp_instance_id=instance.id,
        template_version_id=version.id,
        trigger_source="manual",
        status="pending",
        created_at=datetime.now(),
    )
    db_session.add(job)
    await db_session.commit()

    # 测试状态更新
    service = BuildJobService(db_session)
    now = datetime.now()

    updated_job = await service.update_status(
        job_id=job.id,
        status="running",
        started_at=now
    )

    assert updated_job is not None
    assert updated_job.status == "running"
    assert updated_job.started_at is not None

    # 测试完成状态
    completed_job = await service.update_status(
        job_id=job.id,
        status="completed",
        finished_at=datetime.now()
    )

    assert completed_job is not None
    assert completed_job.status == "completed"
    assert completed_job.finished_at is not None


@pytest.mark.asyncio
async def test_release_job_action_validation(db_session, test_tenant, test_store):
    """测试发布任务动作验证"""
    from app.schemas.miniapp_template import ReleaseJobCreate
    import pytest

    # 测试有效动作
    valid_actions = ["upload", "submit_audit", "publish", "rollback"]
    for action in valid_actions:
        job_data = ReleaseJobCreate(
            miniapp_instance_id=str(uuid4()),
            action=action
        )
        assert job_data.action == action

    # 测试无效动作
    with pytest.raises(ValueError, match="动作必须是"):
        ReleaseJobCreate(
            miniapp_instance_id=str(uuid4()),
            action="invalid_action"
        )


@pytest.mark.asyncio
async def test_template_with_default_config(db_session):
    """测试带默认配置的模板"""
    import json

    default_config = {
        "navSchema": {
            "tabs": [
                {"pagePath": "/pages/index/index", "text": "首页", "iconKey": "home"},
            ],
            "height": 100
        },
        "designTokens": {
            "primary": "#3D6CA8",
            "bodyFontSize": 30
        }
    }

    template = AppTemplate(
        id=str(uuid4()),
        name="现代综合医疗",
        code="modern-general",
        description="通用型医院模板",
        default_config=json.dumps(default_config),
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(template)
    await db_session.commit()

    from app.modules.miniapp_platform.service import AppTemplateService

    service = AppTemplateService(db_session)
    result = await service.get_by_id(template.id)

    assert result is not None
    assert result.default_config is not None
    config = json.loads(result.default_config)
    assert config["navSchema"]["height"] == 100
    assert config["designTokens"]["primary"] == "#3D6CA8"


@pytest.mark.asyncio
async def test_template_list_filter_by_status(db_session):
    """测试按状态过滤模板"""
    # 创建不同状态的模板
    templates = [
        AppTemplate(
            id=str(uuid4()),
            name="现代综合医疗",
            code="modern-general",
            description="通用型医院模板",
            status=1,
            created_at=datetime.now(),
        ),
        AppTemplate(
            id=str(uuid4()),
            name="长辈友好中医康养",
            code="elderly-tcm",
            description="面向55岁以上长辈用户",
            status=1,
            created_at=datetime.now(),
        ),
        AppTemplate(
            id=str(uuid4()),
            name="高端专科门诊",
            code="premium-specialty",
            description="面向口腔、医美、私立专科",
            status=0,
            created_at=datetime.now(),
        ),
    ]
    db_session.add_all(templates)
    await db_session.commit()

    from app.modules.miniapp_platform.service import AppTemplateService

    service = AppTemplateService(db_session)

    # 测试按状态过滤
    enabled_templates, enabled_total = await service.get_list(status=1)
    assert enabled_total == 2

    disabled_templates, disabled_total = await service.get_list(status=0)
    assert disabled_total == 1
    assert disabled_templates[0].code == "premium-specialty"

    # 测试获取全部
    all_templates, all_total = await service.get_list()
    assert all_total == 3


@pytest.mark.asyncio
async def test_miniapp_instance_crud(db_session, test_tenant, test_store):
    """测试小程序实例 CRUD"""
    from app.modules.miniapp_platform.service import MiniappInstanceService
    from app.modules.miniapp_platform.schemas import MiniappInstanceCreate

    # 创建模板
    template = AppTemplate(
        id=str(uuid4()),
        name="现代综合医疗",
        code="modern-general",
        description="通用型医院模板",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(template)
    await db_session.flush()

    version = TemplateVersion(
        id=str(uuid4()),
        template_id=template.id,
        version="1.0.0",
        status=1,
        created_at=datetime.now(),
    )
    db_session.add(version)
    await db_session.commit()

    # 测试创建实例
    service = MiniappInstanceService(db_session)
    import json
    instance_data = MiniappInstanceCreate(
        code="test-instance",
        name="测试实例",
        app_id="wx-test-app-id",
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=test_store.id,
        app_config=json.dumps({"theme": "light"})
    )

    instance = await service.create(
        data=instance_data,
        tenant_id=test_tenant.id,
        operator_id=str(uuid4())
    )

    assert instance is not None
    assert instance.code == "test-instance"
    assert instance.name == "测试实例"
    assert instance.app_id == "wx-test-app-id"
    assert instance.tenant_id == test_tenant.id
    assert instance.template_id == template.id

    # 测试按编码获取实例
    fetched = await service.get_by_code("test-instance", test_tenant.id)
    assert fetched is not None
    assert fetched.code == "test-instance"
