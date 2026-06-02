"""
低代码部署服务 (LowCodeDeployService) 单元测试

覆盖公开方法:
- trigger_deploy: 部署触发
- get_deploy_status: 状态查询
- rollback_deploy: 回滚部署
- handle_audit_callback: 审核回调

覆盖错误路径:
- 页面不存在
- 页面未关联小程序实例
- 状态转换非法 (含并发部署保护)
- 功能关闭拦截 (router 层)
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.lowcode_page import LowCodePage
from app.models.miniapp_platform import BuildJob, ReleaseJob
from app.modules.lowcode.deploy_service import (
    DEPLOY_STATUS_AUDITING,
    DEPLOY_STATUS_BUILDING,
    DEPLOY_STATUS_BUILT,
    DEPLOY_STATUS_FAILED,
    DEPLOY_STATUS_IDLE,
    DEPLOY_STATUS_PUBLISHED,
    DEPLOY_STATUS_UPLOADED,
    DeployError,
    LowCodeDeployService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_result(value):
    """构造 SQLAlchemy execute 返回的 mock 结果对象。"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _mock_scalars_result(values):
    """构造 SQLAlchemy execute 返回的 scalars 结果对象。"""
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


def _make_page(**overrides):
    """构造 LowCodePage mock 对象。"""
    page = MagicMock(spec=LowCodePage)
    page.id = overrides.get("id", "page-001")
    page.tenant_id = overrides.get("tenant_id", "tenant-001")
    page.miniapp_instance_id = overrides.get("miniapp_instance_id", "inst-001")
    page.deploy_status = overrides.get("deploy_status", DEPLOY_STATUS_IDLE)
    page.current_version = overrides.get("current_version", 0)
    page.publish_count = overrides.get("publish_count", 0)
    page.status = overrides.get("status", 0)
    page.last_deploy_at = overrides.get("last_deploy_at", None)
    page.last_build_job_id = overrides.get("last_build_job_id", None)
    page.name = overrides.get("name", "测试页面")
    return page


def _make_build_job(**overrides):
    """构造 BuildJob mock 对象。"""
    job = MagicMock(spec=BuildJob)
    job.id = overrides.get("id", "build-001")
    job.tenant_id = overrides.get("tenant_id", "tenant-001")
    job.lowcode_page_id = overrides.get("lowcode_page_id", "page-001")
    job.miniapp_instance_id = overrides.get("miniapp_instance_id", "inst-001")
    job.status = overrides.get("status", "pending")
    job.build_params = overrides.get("build_params", "{}")
    job.build_log = overrides.get("build_log", None)
    job.artifact_url = overrides.get("artifact_url", None)
    job.started_at = overrides.get("started_at", None)
    job.finished_at = overrides.get("finished_at", None)
    job.trigger_source = overrides.get("trigger_source", "lowcode_deploy")
    return job


def _make_release_job(**overrides):
    """构造 ReleaseJob mock 对象。"""
    job = MagicMock(spec=ReleaseJob)
    job.id = overrides.get("id", "release-001")
    job.miniapp_instance_id = overrides.get("miniapp_instance_id", "inst-001")
    job.artifact_id = overrides.get("artifact_id", None)
    job.action = overrides.get("action", "upload")
    job.status = overrides.get("status", "pending")
    job.target_version = overrides.get("target_version", None)
    job.result = overrides.get("result", None)
    return job


def _make_mock_db(*execute_results):
    """构造 mock AsyncSession，预设 execute side_effect。

    flush() 会为所有已 add 但 id 为 None 的对象触发 Column 默认值，
    模拟真实 SQLAlchemy session 的行为。
    """
    db = AsyncMock()
    db.execute.side_effect = list(execute_results)

    def _flush_with_defaults():
        """模拟 flush：为 pending 对象的 id 列触发默认值。"""
        import uuid as _uuid

        for call_args in db.add.call_args_list:
            obj = call_args[0][0]
            if hasattr(obj, "id") and obj.id is None:
                obj.id = str(_uuid.uuid4())

    db.flush.side_effect = _flush_with_defaults
    return db


# ===========================================================================
# 1. test_start_deploy -- 测试部署触发
# ===========================================================================


class TestStartDeploy:
    """trigger_deploy 应完成完整的 codegen -> build -> upload -> audit 流水线。"""

    @pytest.mark.asyncio
    async def test_trigger_deploy_success(self):
        """正常部署流程: 页面存在且已关联小程序实例，应走完 4 个阶段。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_IDLE)
        build_job = _make_build_job(id="build-001")

        # execute 调用顺序:
        # 1. _load_page -> select(LowCodePage)
        # 2. _create_build_job -> commit+refresh
        # 3. _update_deploy_status -> building: commit+refresh
        # 4. _update_deploy_status -> built: commit+refresh
        # 5. _update_deploy_status -> uploading: commit+refresh
        # 6. _update_deploy_status -> uploaded: commit+refresh
        # 7. _update_deploy_status -> auditing: commit+refresh
        db = _make_mock_db(
            _mock_result(page),        # 1. _load_page
            _mock_result(page),        # 2. refresh after _create_build_job
            _mock_result(page),        # 3. refresh: building
            _mock_result(page),        # 4. refresh: built
            _mock_result(page),        # 5. refresh: uploading
            _mock_result(page),        # 6. refresh: uploaded
            _mock_result(page),        # 7. refresh: auditing
        )

        service = LowCodeDeployService(db)

        result = await service.trigger_deploy(
            tenant_id="tenant-001",
            page_id="page-001",
            updated_by="admin-001",
        )

        # 验证返回结构
        assert result["deploy_status"] == DEPLOY_STATUS_AUDITING
        assert "build_job_id" in result
        assert "audit_id" in result
        assert "artifact_url" in result
        assert result["audit_id"] == "audit_page-001"

        # 验证 BuildJob 被添加到 session
        db.add.assert_called()
        added_obj = db.add.call_args_list[0][0][0]
        assert isinstance(added_obj, BuildJob)
        assert added_obj.tenant_id == "tenant-001"
        assert added_obj.lowcode_page_id == "page-001"

        # 验证 commit 被多次调用
        assert db.commit.await_count >= 6

    @pytest.mark.asyncio
    async def test_trigger_deploy_records_build_job_status(self):
        """部署成功后，BuildJob 应标记为 completed 并记录 artifact_url。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_IDLE)

        db = _make_mock_db(
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
        )

        service = LowCodeDeployService(db)
        await service.trigger_deploy(
            tenant_id="tenant-001",
            page_id="page-001",
        )

        # BuildJob 被添加到 db
        added = db.add.call_args_list[0][0][0]
        assert isinstance(added, BuildJob)
        # 部署完成后 BuildJob 的 status 应为 completed
        assert added.status == "completed"
        assert added.artifact_url is not None
        assert added.finished_at is not None


# ===========================================================================
# 2. test_get_deploy_status -- 测试状态查询
# ===========================================================================


class TestGetDeployStatus:
    """get_deploy_status 应返回页面的部署状态和最近构建任务信息。"""

    @pytest.mark.asyncio
    async def test_get_deploy_status_idle(self):
        """页面处于 idle 状态且无历史构建任务时，应返回默认状态。"""
        page = _make_page(
            deploy_status=DEPLOY_STATUS_IDLE,
            last_build_job_id=None,
            last_deploy_at=None,
        )

        db = _make_mock_db(_mock_result(page))
        service = LowCodeDeployService(db)

        result = await service.get_deploy_status(
            tenant_id="tenant-001",
            page_id="page-001",
        )

        assert result["page_id"] == "page-001"
        assert result["deploy_status"] == DEPLOY_STATUS_IDLE
        assert result["last_deploy_at"] is None
        assert result["miniapp_instance_id"] == "inst-001"
        assert result["build_job"] is None

    @pytest.mark.asyncio
    async def test_get_deploy_status_with_build_job(self):
        """页面有最近构建任务时，应返回构建任务详情。"""
        now = datetime.now(timezone.utc)
        build_job = _make_build_job(
            id="build-001",
            status="success",
            build_log="构建完成",
            artifact_url="artifact://build/build-001",
            started_at=now,
            finished_at=now,
        )
        page = _make_page(
            deploy_status=DEPLOY_STATUS_BUILT,
            last_build_job_id="build-001",
            last_deploy_at=now,
        )

        db = _make_mock_db(
            _mock_result(page),       # _load_page
            _mock_result(build_job),  # 查询 BuildJob
        )
        service = LowCodeDeployService(db)

        result = await service.get_deploy_status(
            tenant_id="tenant-001",
            page_id="page-001",
        )

        assert result["deploy_status"] == DEPLOY_STATUS_BUILT
        assert result["last_deploy_at"] is not None
        assert result["build_job"] is not None
        assert result["build_job"]["id"] == "build-001"
        assert result["build_job"]["status"] == "success"
        assert result["build_job"]["artifact_url"] == "artifact://build/build-001"
        assert result["build_job"]["build_log"] == "构建完成"

    @pytest.mark.asyncio
    async def test_get_deploy_status_build_job_not_found(self):
        """last_build_job_id 指向的 BuildJob 已被清理时，build_job 应为 None。"""
        page = _make_page(
            deploy_status=DEPLOY_STATUS_PUBLISHED,
            last_build_job_id="build-deleted",
        )

        db = _make_mock_db(
            _mock_result(page),
            _mock_result(None),  # BuildJob 不存在
        )
        service = LowCodeDeployService(db)

        result = await service.get_deploy_status(
            tenant_id="tenant-001",
            page_id="page-001",
        )

        assert result["deploy_status"] == DEPLOY_STATUS_PUBLISHED
        assert result["build_job"] is None

    @pytest.mark.asyncio
    async def test_get_deploy_status_defaults_to_idle(self):
        """deploy_status 为 None 时应默认返回 idle。"""
        page = _make_page(deploy_status=None, last_build_job_id=None)

        db = _make_mock_db(_mock_result(page))
        service = LowCodeDeployService(db)

        result = await service.get_deploy_status(
            tenant_id="tenant-001",
            page_id="page-001",
        )

        assert result["deploy_status"] == DEPLOY_STATUS_IDLE


# ===========================================================================
# 3. test_cancel_deploy -- 测试部署取消
# ===========================================================================


class TestCancelDeploy:
    """部署服务不提供 cancel 方法。

    尝试通过非法状态转换实现 "取消" 应抛出 DeployError。
    """

    @pytest.mark.asyncio
    async def test_cancel_deploy_no_such_operation(self):
        """从 building 状态尝试回滚（非法转换），应抛出 DeployError。

        deploy_service 无 cancel 方法，此测试验证状态机拒绝
        building -> 任何非 built/failed 的转换。
        """
        page = _make_page(deploy_status=DEPLOY_STATUS_BUILDING)

        db = _make_mock_db(_mock_result(page))
        service = LowCodeDeployService(db)

        # 从 building 状态尝试回滚到 published 不被允许
        with pytest.raises(DeployError, match="不允许回滚"):
            await service.rollback_deploy(
                tenant_id="tenant-001",
                page_id="page-001",
            )

    @pytest.mark.asyncio
    async def test_rollback_deploy_from_building_rejected(self):
        """building 状态不允许回滚 (只允许 published/auditing/failed)。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_BUILDING)

        db = _make_mock_db(_mock_result(page))
        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="不允许回滚"):
            await service.rollback_deploy(
                tenant_id="tenant-001",
                page_id="page-001",
            )

    @pytest.mark.asyncio
    async def test_rollback_deploy_from_idle_rejected(self):
        """idle 状态不允许回滚。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_IDLE)

        db = _make_mock_db(_mock_result(page))
        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="不允许回滚"):
            await service.rollback_deploy(
                tenant_id="tenant-001",
                page_id="page-001",
            )


# ===========================================================================
# 4. test_deploy_with_feature_disabled -- 测试功能关闭时的拦截
# ===========================================================================


class TestDeployWithFeatureDisabled:
    """router 层通过 LowCodeFeatureGate 拦截未启用 lowcode_publish_miniapp 的租户。"""

    @pytest.mark.asyncio
    @patch("app.modules.lowcode.router.LowCodeFeatureGate")
    async def test_deploy_rejected_when_feature_disabled(self, mock_gate_cls):
        """功能开关未启用时，deploy 端点应返回 HTTP 403。"""
        from fastapi import HTTPException

        from app.modules.lowcode.router import deploy_page

        mock_gate = AsyncMock()
        mock_gate.enforce_feature = AsyncMock(
            side_effect=HTTPException(
                status_code=403,
                detail="当前订阅计划不支持此功能: lowcode_publish_miniapp",
            )
        )
        mock_gate_cls.return_value = mock_gate

        mock_admin = MagicMock()
        mock_admin.tenant_id = "tenant-001"
        mock_admin.id = "admin-001"
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await deploy_page(
                page_id="page-001",
                db=mock_db,
                current_admin=mock_admin,
            )

        assert exc_info.value.status_code == 403
        assert "lowcode_publish_miniapp" in exc_info.value.detail

        # 验证功能开关被检查
        mock_gate.enforce_feature.assert_called_once_with(
            "tenant-001", "lowcode_publish_miniapp"
        )

    @pytest.mark.asyncio
    @patch("app.modules.lowcode.router.LowCodeFeatureGate")
    async def test_get_deploy_status_rejected_when_feature_disabled(
        self, mock_gate_cls
    ):
        """功能开关未启用时，deploy-status 端点也应返回 HTTP 403。"""
        from fastapi import HTTPException

        from app.modules.lowcode.router import get_deploy_status

        mock_gate = AsyncMock()
        mock_gate.enforce_feature = AsyncMock(
            side_effect=HTTPException(
                status_code=403,
                detail="当前订阅计划不支持此功能: lowcode_publish_miniapp",
            )
        )
        mock_gate_cls.return_value = mock_gate

        mock_admin = MagicMock()
        mock_admin.tenant_id = "tenant-001"
        mock_admin.id = "admin-001"
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_deploy_status(
                page_id="page-001",
                db=mock_db,
                current_admin=mock_admin,
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    @patch("app.modules.lowcode.router.LowCodeFeatureGate")
    @patch("app.modules.lowcode.deploy_service.LowCodeDeployService")
    async def test_deploy_proceeds_when_feature_enabled(
        self, mock_service_cls, mock_gate_cls
    ):
        """功能开关已启用时，deploy 端点应正常调用 service。"""
        from app.modules.lowcode.router import deploy_page

        mock_gate = AsyncMock()
        mock_gate.enforce_feature = AsyncMock()
        mock_gate_cls.return_value = mock_gate

        mock_service = AsyncMock()
        mock_service.trigger_deploy = AsyncMock(
            return_value={
                "build_job_id": "build-001",
                "audit_id": "audit_page-001",
                "deploy_status": "auditing",
                "artifact_url": "artifact://build/build-001",
            }
        )
        mock_service_cls.return_value = mock_service

        mock_admin = MagicMock()
        mock_admin.tenant_id = "tenant-001"
        mock_admin.id = "admin-001"
        mock_db = AsyncMock()

        result = await deploy_page(
            page_id="page-001",
            db=mock_db,
            current_admin=mock_admin,
        )

        # 功能开关通过
        mock_gate.enforce_feature.assert_called_once_with(
            "tenant-001", "lowcode_publish_miniapp"
        )
        # service 被调用
        mock_service.trigger_deploy.assert_called_once_with(
            tenant_id="tenant-001",
            page_id="page-001",
            updated_by="admin-001",
        )
        # 返回正确的结果
        assert result.build_job_id == "build-001"
        assert result.deploy_status == "auditing"


# ===========================================================================
# 5. test_deploy_page_not_found -- 测试页面不存在
# ===========================================================================


class TestDeployPageNotFound:
    """页面不存在时，deploy 相关操作应抛出明确异常。"""

    @pytest.mark.asyncio
    async def test_trigger_deploy_page_not_found(self):
        """trigger_deploy 找不到页面时应抛出 DeployError。"""
        db = _make_mock_db(_mock_result(None))
        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="页面不存在"):
            await service.trigger_deploy(
                tenant_id="tenant-001",
                page_id="nonexistent-page",
            )

    @pytest.mark.asyncio
    async def test_get_deploy_status_page_not_found(self):
        """get_deploy_status 找不到页面时应抛出 DeployError。"""
        db = _make_mock_db(_mock_result(None))
        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="页面不存在"):
            await service.get_deploy_status(
                tenant_id="tenant-001",
                page_id="nonexistent-page",
            )

    @pytest.mark.asyncio
    async def test_rollback_deploy_page_not_found(self):
        """rollback_deploy 找不到页面时应抛出 DeployError。"""
        db = _make_mock_db(_mock_result(None))
        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="页面不存在"):
            await service.rollback_deploy(
                tenant_id="tenant-001",
                page_id="nonexistent-page",
            )

    @pytest.mark.asyncio
    async def test_trigger_deploy_no_miniapp_instance(self):
        """页面未关联小程序实例时，trigger_deploy 应抛出 DeployError。"""
        page = _make_page(miniapp_instance_id=None)

        db = _make_mock_db(_mock_result(page))
        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="未关联小程序实例"):
            await service.trigger_deploy(
                tenant_id="tenant-001",
                page_id="page-001",
            )

    @pytest.mark.asyncio
    async def test_audit_callback_page_not_found(self):
        """handle_audit_callback 中 audit_id 对应的页面不存在时应抛出异常。"""
        db = _make_mock_db(_mock_result(None))
        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="找不到关联页面"):
            await service.handle_audit_callback(
                callback_data={"auditid": "audit_nonexistent", "status": 0}
            )


# ===========================================================================
# 6. test_concurrent_deploy_guard -- 测试并发部署保护
# ===========================================================================


class TestConcurrentDeployGuard:
    """并发部署保护: 页面正在构建时不允许再次触发部署。"""

    @pytest.mark.asyncio
    async def test_concurrent_deploy_rejected_when_building(self):
        """页面处于 building 状态时，再次 trigger_deploy 应因非法状态转换而失败。

        状态机: building -> building 不被允许 (只允许 building -> built/failed)。
        _update_deploy_status 会抛出 DeployError。
        """
        page = _make_page(deploy_status=DEPLOY_STATUS_BUILDING)

        # execute 调用:
        # 1. _load_page -> 返回 building 状态的页面
        # 2. _create_build_job -> commit+refresh
        # 3. _update_deploy_status -> 检查 building -> building 非法
        db = _make_mock_db(
            _mock_result(page),       # 1. _load_page
            _mock_result(page),       # 2. refresh after _create_build_job
        )

        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="不允许从 'building' 转换到 'building'"):
            await service.trigger_deploy(
                tenant_id="tenant-001",
                page_id="page-001",
            )

    @pytest.mark.asyncio
    async def test_concurrent_deploy_rejected_when_uploading(self):
        """页面处于 uploading 状态时，不允许再次部署。"""
        page = _make_page(deploy_status="uploading")

        db = _make_mock_db(
            _mock_result(page),
            _mock_result(page),
        )

        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="不允许从 'uploading' 转换到 'building'"):
            await service.trigger_deploy(
                tenant_id="tenant-001",
                page_id="page-001",
            )

    @pytest.mark.asyncio
    async def test_concurrent_deploy_rejected_when_auditing(self):
        """页面处于 auditing 状态时，不允许再次部署。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_AUDITING)

        db = _make_mock_db(
            _mock_result(page),
            _mock_result(page),
        )

        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="不允许从 'auditing' 转换到 'building'"):
            await service.trigger_deploy(
                tenant_id="tenant-001",
                page_id="page-001",
            )

    @pytest.mark.asyncio
    async def test_deploy_allowed_from_idle(self):
        """idle 状态允许部署 (idle -> building 是合法转换)。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_IDLE)

        db = _make_mock_db(
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
        )

        service = LowCodeDeployService(db)

        result = await service.trigger_deploy(
            tenant_id="tenant-001",
            page_id="page-001",
        )

        assert result["deploy_status"] == DEPLOY_STATUS_AUDITING

    @pytest.mark.asyncio
    async def test_deploy_allowed_from_failed(self):
        """failed 状态允许重新部署 (failed -> building 是合法转换)。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_FAILED)

        db = _make_mock_db(
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
        )

        service = LowCodeDeployService(db)

        result = await service.trigger_deploy(
            tenant_id="tenant-001",
            page_id="page-001",
        )

        assert result["deploy_status"] == DEPLOY_STATUS_AUDITING

    @pytest.mark.asyncio
    async def test_deploy_allowed_from_published(self):
        """published 状态允许重新构建 (published -> building 是合法转换)。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_PUBLISHED)

        db = _make_mock_db(
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
            _mock_result(page),
        )

        service = LowCodeDeployService(db)

        result = await service.trigger_deploy(
            tenant_id="tenant-001",
            page_id="page-001",
        )

        assert result["deploy_status"] == DEPLOY_STATUS_AUDITING


# ===========================================================================
# 7. 部署失败路径覆盖
# ===========================================================================


class TestDeployFailurePaths:
    """验证部署流水线在异常时正确标记失败状态。"""

    @pytest.mark.asyncio
    async def test_trigger_deploy_failure_marks_status_failed(self):
        """部署阶段抛出异常时，deploy_status 应被标记为 failed。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_IDLE)

        db = _make_mock_db(
            _mock_result(page),       # _load_page
            _mock_result(page),       # refresh after _create_build_job
            _mock_result(page),       # refresh: building
        )

        service = LowCodeDeployService(db)

        # 让 codegen 阶段失败
        with patch.object(service, "_stage_codegen", side_effect=RuntimeError("codegen 失败")):
            with pytest.raises(DeployError, match="部署失败"):
                await service.trigger_deploy(
                    tenant_id="tenant-001",
                    page_id="page-001",
                )

        # 验证页面状态被更新为 failed
        assert page.deploy_status == DEPLOY_STATUS_FAILED
        assert page.last_deploy_at is not None


# ===========================================================================
# 8. 审核回调测试
# ===========================================================================


class TestHandleAuditCallback:
    """handle_audit_callback 应根据微信回调结果更新部署状态。"""

    @pytest.mark.asyncio
    async def test_audit_callback_passed(self):
        """审核通过 (status=0) 时，页面应变为 published。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_AUDITING, status=0)

        db = _make_mock_db(_mock_result(page))
        service = LowCodeDeployService(db)

        result = await service.handle_audit_callback(
            callback_data={"auditid": "audit_page-001", "status": 0, "reason": ""}
        )

        assert result["page_id"] == "page-001"
        assert result["deploy_status"] == DEPLOY_STATUS_PUBLISHED
        assert result["audit_status"] == "passed"
        assert page.status == 1  # 标记为已发布

    @pytest.mark.asyncio
    async def test_audit_callback_failed(self):
        """审核失败 (status != 0) 时，页面应变为 failed。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_AUDITING, status=0)

        db = _make_mock_db(_mock_result(page))
        service = LowCodeDeployService(db)

        result = await service.handle_audit_callback(
            callback_data={
                "auditid": "audit_page-001",
                "status": 1,
                "reason": "内容含有违规信息",
            }
        )

        assert result["deploy_status"] == DEPLOY_STATUS_FAILED
        assert result["audit_status"] == "failed"
        assert result["reason"] == "内容含有违规信息"

    @pytest.mark.asyncio
    async def test_audit_callback_missing_auditid(self):
        """回调缺少 auditid 字段时应抛出 DeployError。"""
        db = _make_mock_db()
        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="缺少 auditid"):
            await service.handle_audit_callback(
                callback_data={"status": 0}
            )

    @pytest.mark.asyncio
    async def test_audit_callback_invalid_auditid_format(self):
        """audit_id 格式无效时应抛出 DeployError。"""
        db = _make_mock_db()
        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="无效的 audit_id 格式"):
            await service.handle_audit_callback(
                callback_data={"auditid": "invalid_format", "status": 0}
            )


# ===========================================================================
# 9. rollback_deploy 测试
# ===========================================================================


class TestRollbackDeploy:
    """rollback_deploy 应回滚到上一个已发布版本。"""

    @pytest.mark.asyncio
    async def test_rollback_deploy_success(self):
        """从 published 状态回滚，应创建 rollback ReleaseJob。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_PUBLISHED)

        # 两个已完成的 BuildJob: jobs[0]=当前版本, jobs[1]=上一版本
        job_current = _make_build_job(
            id="build-current", artifact_url="artifact://build/current"
        )
        job_previous = _make_build_job(
            id="build-previous", artifact_url="artifact://build/previous"
        )

        db = _make_mock_db(
            _mock_result(page),                              # 1. _load_page
            _mock_scalars_result([job_current, job_previous]),  # 2. 查询历史 BuildJob
            _mock_result(page),                              # 3. refresh
        )

        service = LowCodeDeployService(db)

        result = await service.rollback_deploy(
            tenant_id="tenant-001",
            page_id="page-001",
            updated_by="admin-001",
        )

        assert result["page_id"] == "page-001"
        assert result["rollback_to_version"] == "artifact://build/previous"
        assert result["deploy_status"] == DEPLOY_STATUS_UPLOADED
        assert "release_job_id" in result

        # 验证 ReleaseJob 被创建
        added = db.add.call_args_list[0][0][0]
        assert isinstance(added, ReleaseJob)
        assert added.action == "rollback"

    @pytest.mark.asyncio
    async def test_rollback_deploy_insufficient_history(self):
        """没有足够的历史版本时应抛出 DeployError。"""
        page = _make_page(deploy_status=DEPLOY_STATUS_PUBLISHED)

        # 只有一个 BuildJob (不够回滚)
        job_current = _make_build_job(id="build-current")

        db = _make_mock_db(
            _mock_result(page),
            _mock_scalars_result([job_current]),
        )

        service = LowCodeDeployService(db)

        with pytest.raises(DeployError, match="没有可回滚的历史版本"):
            await service.rollback_deploy(
                tenant_id="tenant-001",
                page_id="page-001",
            )
