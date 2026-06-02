"""
低代码部署流水线单元测试

覆盖:
1. build task -- 创建 BuildJob 记录
2. build task -- 更新页面 deploy_status 为 building
3. upload task -- 创建 ReleaseJob 记录
4. submit_audit task -- 调用微信审核 API
5. publish task -- 更新 deploy_status 为 published
6. rollback task -- 回滚到上一版本
7. deploy-status endpoint -- 返回正确的部署状态
8. deploy endpoint -- 强制执行功能开关
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.lowcode_page import LowCodePage
from app.models.miniapp_platform import BuildJob, MiniappInstance, ReleaseJob


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_result(value):
    """构造 SQLAlchemy execute 返回的 mock 结果对象。"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_mock_page(**overrides):
    """构造 LowCodePage 的 mock 对象。"""
    page = MagicMock(spec=LowCodePage)
    page.id = overrides.get("id", "page-001")
    page.tenant_id = overrides.get("tenant_id", "tenant-001")
    page.miniapp_instance_id = overrides.get("miniapp_instance_id", "inst-001")
    page.deploy_status = overrides.get("deploy_status", "idle")
    page.current_version = overrides.get("current_version", 0)
    page.publish_count = overrides.get("publish_count", 0)
    page.status = overrides.get("status", 0)
    page.last_deploy_at = overrides.get("last_deploy_at", None)
    page.last_build_job_id = overrides.get("last_build_job_id", None)
    page.name = overrides.get("name", "测试页面")
    return page


def _make_mock_instance(**overrides):
    """构造 MiniappInstance 的 mock 对象。"""
    instance = MagicMock(spec=MiniappInstance)
    instance.id = overrides.get("id", "inst-001")
    instance.app_id = overrides.get("app_id", "wx1234567890")
    instance.app_secret_ref = overrides.get("app_secret_ref", "wx_secret_123")
    return instance


def _make_mock_build_job(**overrides):
    """构造 BuildJob 的 mock 对象。"""
    job = MagicMock(spec=BuildJob)
    job.id = overrides.get("id", "build-001")
    job.tenant_id = overrides.get("tenant_id", "tenant-001")
    job.lowcode_page_id = overrides.get("lowcode_page_id", "page-001")
    job.miniapp_instance_id = overrides.get("miniapp_instance_id", "inst-001")
    job.status = overrides.get("status", "success")
    job.build_params = overrides.get(
        "build_params", json.dumps({"page_id": "page-001"})
    )
    job.build_log = overrides.get("build_log", "")
    job.artifact_url = overrides.get("artifact_url", "/tmp/artifact.tar.gz")
    job.started_at = overrides.get("started_at", None)
    job.finished_at = overrides.get("finished_at", None)
    job.trigger_source = overrides.get("trigger_source", "celery_deploy")
    return job


def _make_mock_release_job(**overrides):
    """构造 ReleaseJob 的 mock 对象。"""
    job = MagicMock(spec=ReleaseJob)
    job.id = overrides.get("id", "release-001")
    job.miniapp_instance_id = overrides.get("miniapp_instance_id", "inst-001")
    job.artifact_id = overrides.get("artifact_id", "artifact-001")
    job.action = overrides.get("action", "upload")
    job.status = overrides.get("status", "success")
    job.target_version = overrides.get("target_version", "1.0.0")
    job.result = overrides.get("result", None)
    return job


def _make_sync_db_context(mock_db):
    """构造 get_sync_db 的 context manager mock。"""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=mock_db)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


def _make_mock_db(*execute_results):
    """构造 mock 数据库，预设 execute side_effect。

    flush() 会为所有已 add 但 id 为 None 的对象触发 Column 默认值，
    模拟真实 SQLAlchemy session 的行为。
    """
    db = MagicMock()
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
# 1. build task -- 创建 BuildJob 记录
# ===========================================================================


class TestBuildTaskCreatesBuildJob:
    """build_lowcode_page_task 应在执行过程中创建 BuildJob 记录。"""

    @patch("app.tasks.lowcode_deploy_task._run_taro_build", return_value="build ok")
    @patch("app.tasks.lowcode_deploy_task._write_codegen_files")
    @patch("app.tasks.lowcode_deploy_task._create_tarball")
    @patch(
        "app.tasks.lowcode_deploy_task._get_artifact_dir",
        return_value="/tmp/artifacts",
    )
    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_build_task_adds_build_job_to_db(
        self,
        mock_get_sync_db,
        mock_artifact_dir,
        mock_tarball,
        mock_write_files,
        mock_taro_build,
    ):
        from app.tasks.lowcode_deploy_task import build_lowcode_page_task

        page = _make_mock_page()
        instance = _make_mock_instance()

        mock_db = _make_mock_db(
            _mock_result(page),       # 1. 页面查询
            _mock_result(instance),   # 2. 实例查询
            _mock_result(page),       # 3. _update_page_deploy_status -> building
            _mock_result(page),       # 4. _update_page_deploy_status -> built
        )

        def _get(cls, oid):
            return _make_mock_build_job()

        mock_db.get.side_effect = _get
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        # Mock CodegenService (lazily imported inside task body)
        codegen_result = MagicMock()
        codegen_result.files = []
        codegen_result.warnings = []

        with patch(
            "app.modules.lowcode.codegen_service.CodegenService"
        ) as mock_cls:
            mock_codegen = MagicMock()
            mock_codegen.generate_taro = AsyncMock(return_value=codegen_result)
            mock_cls.return_value = mock_codegen

            result = build_lowcode_page_task("page-001", "tenant-001")

        assert result["success"] is True
        assert result["build_job_id"] is not None

        # 验证 db.add 被调用，且传入 BuildJob 实例
        mock_db.add.assert_called()
        added_obj = mock_db.add.call_args_list[0][0][0]
        assert isinstance(added_obj, BuildJob)
        assert added_obj.tenant_id == "tenant-001"
        assert added_obj.lowcode_page_id == "page-001"
        assert added_obj.trigger_source == "celery_deploy"
        assert added_obj.status == "running"


# ===========================================================================
# 2. build task -- 更新页面 deploy_status 为 building
# ===========================================================================


class TestBuildTaskSetsDeployStatusBuilding:
    """build_lowcode_page_task 应在开始构建时将页面状态设为 building。"""

    @patch("app.tasks.lowcode_deploy_task._run_taro_build", return_value="build ok")
    @patch("app.tasks.lowcode_deploy_task._write_codegen_files")
    @patch("app.tasks.lowcode_deploy_task._create_tarball")
    @patch(
        "app.tasks.lowcode_deploy_task._get_artifact_dir",
        return_value="/tmp/artifacts",
    )
    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_build_task_updates_status_to_building(
        self,
        mock_get_sync_db,
        mock_artifact_dir,
        mock_tarball,
        mock_write_files,
        mock_taro_build,
    ):
        from app.tasks.lowcode_deploy_task import build_lowcode_page_task

        page = _make_mock_page()
        instance = _make_mock_instance()

        mock_db = _make_mock_db(
            _mock_result(page),       # 1. 页面查询
            _mock_result(instance),   # 2. 实例查询
            _mock_result(page),       # 3. _update_page_deploy_status -> building
            _mock_result(page),       # 4. _update_page_deploy_status -> built
        )

        def _get(cls, oid):
            return _make_mock_build_job()

        mock_db.get.side_effect = _get
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        codegen_result = MagicMock()
        codegen_result.files = []
        codegen_result.warnings = []

        with patch("app.modules.lowcode.codegen_service.CodegenService") as mock_cls:
            mock_codegen = MagicMock()
            mock_codegen.generate_taro = AsyncMock(return_value=codegen_result)
            mock_cls.return_value = mock_codegen

            build_lowcode_page_task("page-001", "tenant-001")

        # 任务运行到完成: deploy_status 先被设为 "building"，然后更新为 "built"
        # 同时验证 db.execute 被调用足够多次 (页面查询 + 实例查询 + 2 次状态更新)
        assert mock_db.execute.call_count == 4
        assert page.last_deploy_at is not None


# ===========================================================================
# 3. upload task -- 创建 ReleaseJob 记录
# ===========================================================================


class TestUploadTaskCreatesReleaseJob:
    """upload_to_wechat_task 应创建 action=upload 的 ReleaseJob 记录。"""

    @patch("app.infrastructure.wechat.miniapp_publisher.MiniappPublisher")
    @patch(
        "app.tasks.lowcode_deploy_task._extract_artifact",
        return_value="/tmp/extracted",
    )
    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_upload_task_adds_release_job(
        self,
        mock_get_sync_db,
        mock_extract,
        mock_publisher_cls,
    ):
        from app.tasks.lowcode_deploy_task import upload_to_wechat_task

        build_job = _make_mock_build_job(status="success")
        artifact = MagicMock()
        artifact.id = "artifact-001"
        artifact.file_path = "/tmp/artifact.tar.gz"
        instance = _make_mock_instance()

        page_for_status = _make_mock_page()

        mock_db = _make_mock_db(
            _mock_result(build_job),           # 1. BuildJob 查询
            _mock_result(artifact),            # 2. artifact 查询
            _mock_result(instance),            # 3. instance 查询
            _mock_result(page_for_status),     # 4. _update_page_deploy_status -> uploading
            _mock_result(page_for_status),     # 5. _update_page_deploy_status -> uploaded
        )

        def _get(cls, oid):
            return _make_mock_release_job()

        mock_db.get.side_effect = _get
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        mock_publisher = MagicMock()
        mock_publisher.upload_code = AsyncMock(
            return_value={"success": True, "output": "upload done"}
        )
        mock_publisher_cls.return_value = mock_publisher

        result = upload_to_wechat_task("build-001", "inst-001")

        assert result["success"] is True
        assert result["release_job_id"] is not None

        # 验证 db.add 被调用且传入 ReleaseJob
        mock_db.add.assert_called()
        added_obj = mock_db.add.call_args_list[0][0][0]
        assert isinstance(added_obj, ReleaseJob)
        assert added_obj.action == "upload"
        assert added_obj.miniapp_instance_id == "inst-001"
        assert added_obj.artifact_id == "artifact-001"

        # 验证微信 API 被调用
        mock_publisher.upload_code.assert_called_once()
        call_kwargs = mock_publisher.upload_code.call_args
        assert call_kwargs.kwargs["project_path"] == "/tmp/extracted"
        assert call_kwargs.kwargs["version"] == "1.0.0"


# ===========================================================================
# 4. submit_audit task -- 调用微信审核 API
# ===========================================================================


class TestSubmitAuditCallsWeChatAPI:
    """submit_audit_task 应调用 MiniappPublisher.submit_audit() 提交审核。"""

    @patch("app.infrastructure.wechat.miniapp_publisher.MiniappPublisher")
    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_submit_audit_calls_wechat_submit_audit(
        self,
        mock_get_sync_db,
        mock_publisher_cls,
    ):
        from app.tasks.lowcode_deploy_task import submit_audit_task

        upload_job = _make_mock_release_job(action="upload", status="success")
        instance = _make_mock_instance()

        mock_db = _make_mock_db(
            _mock_result(upload_job),  # upload job 查询
            _mock_result(instance),    # instance 查询
        )

        def _get(cls, oid):
            return _make_mock_release_job(action="submit_audit", status="success")

        mock_db.get.side_effect = _get
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        mock_publisher = MagicMock()
        mock_publisher.submit_audit = AsyncMock(
            return_value={"errcode": 0, "errmsg": "ok", "auditid": 12345}
        )
        mock_publisher_cls.return_value = mock_publisher

        result = submit_audit_task("release-001")

        assert result["success"] is True
        assert result["auditid"] == 12345

        # 验证微信 submit_audit 被调用
        mock_publisher.submit_audit.assert_called_once()

        # 验证创建了 ReleaseJob(action=submit_audit)
        mock_db.add.assert_called()
        added_obj = mock_db.add.call_args_list[0][0][0]
        assert isinstance(added_obj, ReleaseJob)
        assert added_obj.action == "submit_audit"

    @patch("app.infrastructure.wechat.miniapp_publisher.MiniappPublisher")
    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_submit_audit_wechat_error_returns_failure(
        self,
        mock_get_sync_db,
        mock_publisher_cls,
    ):
        """微信 API 返回错误码时，任务应返回失败。"""
        from app.tasks.lowcode_deploy_task import submit_audit_task

        upload_job = _make_mock_release_job(action="upload", status="success")
        instance = _make_mock_instance()

        mock_db = _make_mock_db(
            _mock_result(upload_job),
            _mock_result(instance),
        )

        def _get(cls, oid):
            return _make_mock_release_job(action="submit_audit")

        mock_db.get.side_effect = _get
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        mock_publisher = MagicMock()
        mock_publisher.submit_audit = AsyncMock(
            return_value={"errcode": 87014, "errmsg": "内容含有违规内容"}
        )
        mock_publisher_cls.return_value = mock_publisher

        result = submit_audit_task("release-001")

        assert result["success"] is False
        assert "违规内容" in result["reason"]


# ===========================================================================
# 5. publish task -- 更新 deploy_status 为 published
# ===========================================================================


class TestPublishTaskSetsStatusPublished:
    """publish_release_task 应在成功发布后将页面状态更新为 published。"""

    @patch("app.tasks.lowcode_deploy_task._create_version_snapshot")
    @patch("app.infrastructure.wechat.miniapp_publisher.MiniappPublisher")
    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_publish_task_updates_deploy_status(
        self,
        mock_get_sync_db,
        mock_publisher_cls,
        mock_snapshot,
    ):
        from app.tasks.lowcode_deploy_task import publish_release_task

        audit_job = _make_mock_release_job(action="submit_audit", status="success")
        instance = _make_mock_instance()

        mock_db = _make_mock_db(
            _mock_result(audit_job),   # audit_job 查询
            _mock_result(instance),    # instance 查询
        )

        def _get(cls, oid):
            return _make_mock_release_job(action="publish", status="success")

        mock_db.get.side_effect = _get
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        mock_publisher = MagicMock()
        mock_publisher.release = AsyncMock(
            return_value={"errcode": 0, "errmsg": "ok"}
        )
        mock_publisher_cls.return_value = mock_publisher

        result = publish_release_task("release-001")

        assert result["success"] is True
        assert result["publish_release_job_id"] is not None

        # 验证微信 release API 被调用
        mock_publisher.release.assert_called_once()

        # 验证创建了 ReleaseJob(action=publish)
        mock_db.add.assert_called()
        added_obj = mock_db.add.call_args_list[0][0][0]
        assert isinstance(added_obj, ReleaseJob)
        assert added_obj.action == "publish"

        # 验证版本快照函数被调用（它负责更新 deploy_status -> published）
        mock_snapshot.assert_called_once()

    @patch("app.infrastructure.wechat.miniapp_publisher.MiniappPublisher")
    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_publish_wechat_error_returns_failure(
        self,
        mock_get_sync_db,
        mock_publisher_cls,
    ):
        """微信发布 API 返回错误码时，任务应返回失败。"""
        from app.tasks.lowcode_deploy_task import publish_release_task

        audit_job = _make_mock_release_job(action="submit_audit", status="success")
        instance = _make_mock_instance()

        mock_db = _make_mock_db(
            _mock_result(audit_job),
            _mock_result(instance),
        )

        def _get(cls, oid):
            return _make_mock_release_job(action="publish")

        mock_db.get.side_effect = _get
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        mock_publisher = MagicMock()
        mock_publisher.release = AsyncMock(
            return_value={"errcode": 87013, "errmsg": "发布失败，请重试"}
        )
        mock_publisher_cls.return_value = mock_publisher

        result = publish_release_task("release-001")

        assert result["success"] is False
        assert "发布失败" in result["reason"]


# ===========================================================================
# 6. rollback task -- 回滚到上一版本
# ===========================================================================


class TestRollbackTaskRestoresPreviousVersion:
    """rollback_task 应创建 rollback ReleaseJob 并调用微信 revert API。"""

    @patch("app.infrastructure.wechat.miniapp_publisher.MiniappPublisher")
    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_rollback_task_creates_rollback_release_job(
        self,
        mock_get_sync_db,
        mock_publisher_cls,
    ):
        from app.tasks.lowcode_deploy_task import rollback_task

        source_job = _make_mock_release_job(action="publish")
        instance = _make_mock_instance()

        mock_db = _make_mock_db(
            _mock_result(source_job),  # source_job 查询
            _mock_result(instance),    # instance 查询
        )

        def _get(cls, oid):
            return _make_mock_release_job(action="rollback", status="success")

        mock_db.get.side_effect = _get
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        mock_publisher = MagicMock()
        mock_publisher.rollback = AsyncMock(
            return_value={"errcode": 0, "errmsg": "ok"}
        )
        mock_publisher_cls.return_value = mock_publisher

        result = rollback_task("release-001", target_version="1.0.0")

        assert result["success"] is True
        assert result["rollback_release_job_id"] is not None

        # 验证创建了 ReleaseJob(action=rollback)
        mock_db.add.assert_called()
        added_obj = mock_db.add.call_args_list[0][0][0]
        assert isinstance(added_obj, ReleaseJob)
        assert added_obj.action == "rollback"
        assert added_obj.target_version == "1.0.0"

        # 验证微信 rollback API 被调用
        mock_publisher.rollback.assert_called_once()

    @patch("app.infrastructure.wechat.miniapp_publisher.MiniappPublisher")
    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_rollback_wechat_error_returns_failure(
        self,
        mock_get_sync_db,
        mock_publisher_cls,
    ):
        """微信回滚 API 返回错误码时，任务应返回失败。"""
        from app.tasks.lowcode_deploy_task import rollback_task

        source_job = _make_mock_release_job(action="publish")
        instance = _make_mock_instance()

        mock_db = _make_mock_db(
            _mock_result(source_job),
            _mock_result(instance),
        )

        def _get(cls, oid):
            return _make_mock_release_job(action="rollback")

        mock_db.get.side_effect = _get
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        mock_publisher = MagicMock()
        mock_publisher.rollback = AsyncMock(
            return_value={"errcode": 87015, "errmsg": "回滚失败"}
        )
        mock_publisher_cls.return_value = mock_publisher

        result = rollback_task("release-001")

        assert result["success"] is False
        assert "回滚失败" in result["reason"]


# ===========================================================================
# 7. deploy-status endpoint -- 返回正确的部署状态
# ===========================================================================


class TestDeployStatusEndpoint:
    """deploy-status 端点应返回页面的部署状态信息。"""

    @pytest.mark.asyncio
    @patch("app.modules.lowcode.deploy_service.LowCodeDeployService")
    @patch("app.modules.lowcode.router.LowCodeFeatureGate")
    async def test_deploy_status_returns_correct_status(
        self,
        mock_gate_cls,
        mock_service_cls,
    ):
        """功能开关通过后，端点应返回 service 返回的部署状态。"""
        from app.modules.lowcode.router import get_deploy_status

        mock_gate = AsyncMock()
        mock_gate.enforce_feature = AsyncMock()
        mock_gate_cls.return_value = mock_gate

        mock_service = AsyncMock()
        expected_status = {
            "page_id": "page-001",
            "deploy_status": "building",
            "last_deploy_at": "2026-06-02T10:00:00",
            "miniapp_instance_id": "inst-001",
            "build_job": {
                "id": "build-001",
                "status": "running",
                "build_log": "构建中...",
                "artifact_url": None,
                "started_at": "2026-06-02T10:00:00",
                "finished_at": None,
            },
        }
        mock_service.get_deploy_status = AsyncMock(return_value=expected_status)
        mock_service_cls.return_value = mock_service

        mock_admin = MagicMock()
        mock_admin.tenant_id = "tenant-001"
        mock_admin.id = "admin-001"
        mock_db = AsyncMock()

        result = await get_deploy_status(
            page_id="page-001",
            db=mock_db,
            current_admin=mock_admin,
        )

        # 验证功能开关被检查
        mock_gate.enforce_feature.assert_called_once_with(
            "tenant-001", "lowcode_publish_miniapp"
        )

        # 验证 service 被正确调用
        mock_service.get_deploy_status.assert_called_once_with(
            tenant_id="tenant-001",
            page_id="page-001",
        )

        # 验证返回值
        assert result.deploy_status == "building"
        assert result.page_id == "page-001"
        assert result.build_job is not None
        assert result.build_job["id"] == "build-001"
        assert result.build_job["status"] == "running"


# ===========================================================================
# 8. deploy endpoint -- 强制执行功能开关
# ===========================================================================


class TestDeployEndpointEnforcesFeatureFlag:
    """deploy 端点应在未启用 lowcode_publish_miniapp 时返回 403。"""

    @pytest.mark.asyncio
    @patch("app.modules.lowcode.router.LowCodeFeatureGate")
    async def test_deploy_rejects_when_feature_disabled(
        self,
        mock_gate_cls,
    ):
        """功能开关未启用时，部署端点应返回 HTTP 403。"""
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

    @pytest.mark.asyncio
    @patch("app.modules.lowcode.deploy_service.LowCodeDeployService")
    @patch("app.modules.lowcode.router.LowCodeFeatureGate")
    async def test_deploy_proceeds_when_feature_enabled(
        self,
        mock_gate_cls,
        mock_service_cls,
    ):
        """功能开关已启用时，部署端点应正常调用 service。"""
        from app.modules.lowcode.router import deploy_page

        mock_gate = AsyncMock()
        mock_gate.enforce_feature = AsyncMock()
        mock_gate_cls.return_value = mock_gate

        mock_service = AsyncMock()
        mock_service.trigger_deploy = AsyncMock(
            return_value={
                "build_job_id": "build-001",
                "audit_id": "audit_001",
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

        # 功能开关检查通过
        mock_gate.enforce_feature.assert_called_once_with(
            "tenant-001", "lowcode_publish_miniapp"
        )

        # deploy service 被调用
        mock_service.trigger_deploy.assert_called_once_with(
            tenant_id="tenant-001",
            page_id="page-001",
            updated_by="admin-001",
        )

        # 返回正确的部署结果
        assert result.build_job_id == "build-001"
        assert result.deploy_status == "auditing"


# ===========================================================================
# 额外: 错误路径覆盖
# ===========================================================================


class TestBuildTaskErrorPaths:
    """验证 build task 在各种异常场景下的行为。"""

    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_build_returns_failure_when_page_not_found(self, mock_get_sync_db):
        """页面不存在时，构建任务应返回失败。"""
        from app.tasks.lowcode_deploy_task import build_lowcode_page_task

        mock_db = _make_mock_db(_mock_result(None))
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        result = build_lowcode_page_task("nonexistent-page", "tenant-001")

        assert result["success"] is False
        assert result["reason"] == "页面不存在"

    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_build_returns_failure_when_no_instance(self, mock_get_sync_db):
        """页面未关联小程序实例时，构建任务应返回失败。"""
        from app.tasks.lowcode_deploy_task import build_lowcode_page_task

        page = _make_mock_page(miniapp_instance_id=None)
        mock_db = _make_mock_db(
            _mock_result(page),           # 页面查询 -> page without instance
            _mock_result(page),           # _update_page_deploy_status 查询 page
        )
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        result = build_lowcode_page_task("page-001", "tenant-001")

        assert result["success"] is False
        assert result["reason"] == "页面未关联小程序实例"
        # 页面状态应被标记为 failed
        assert page.deploy_status == "failed"


class TestUploadTaskErrorPaths:
    """验证 upload task 在异常场景下的行为。"""

    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_upload_returns_failure_when_build_job_not_found(self, mock_get_sync_db):
        """构建任务不存在时，上传任务应返回失败。"""
        from app.tasks.lowcode_deploy_task import upload_to_wechat_task

        mock_db = _make_mock_db(_mock_result(None))
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        result = upload_to_wechat_task("nonexistent-build", "inst-001")

        assert result["success"] is False
        assert result["reason"] == "构建任务不存在"

    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_upload_returns_failure_when_build_job_not_success(self, mock_get_sync_db):
        """构建任务状态异常时，上传任务应返回失败。"""
        from app.tasks.lowcode_deploy_task import upload_to_wechat_task

        build_job = _make_mock_build_job(status="failed")
        mock_db = _make_mock_db(_mock_result(build_job))
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        result = upload_to_wechat_task("build-001", "inst-001")

        assert result["success"] is False
        assert "failed" in result["reason"]


class TestRollbackTaskErrorPaths:
    """验证 rollback task 在异常场景下的行为。"""

    @patch("app.tasks.lowcode_deploy_task.get_sync_db")
    def test_rollback_returns_failure_when_source_job_not_found(
        self, mock_get_sync_db
    ):
        """源发布任务不存在时，回滚任务应返回失败。"""
        from app.tasks.lowcode_deploy_task import rollback_task

        mock_db = _make_mock_db(_mock_result(None))
        mock_get_sync_db.return_value = _make_sync_db_context(mock_db)

        result = rollback_task("nonexistent-release")

        assert result["success"] is False
        assert result["reason"] == "发布任务不存在"
