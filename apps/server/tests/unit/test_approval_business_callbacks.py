"""业务回调拆环后的单测。

覆盖:
1. 引擎包 import 后不泄漏业务模块到 sys.modules（循环依赖拆解的硬保证）。
2. leave_requests/callbacks.py 与 schedules/callbacks_extra_quota.py 的分支逻辑:
   - on_approved 触发业务状态推进（leave_request 还会调 _handle_approved_request）
   - on_rejected / on_cancelled 仅改状态字段
   - 不存在的业务记录或非 pending 状态提前 return
"""
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.leave_request import RequestStatus
from app.modules.approval_flows.callback_registry import callback_registry

_SERVER_ROOT = Path(__file__).resolve().parent.parent.parent

# ============================================================
# 1. 引擎包零业务依赖（拆环硬保证）
# ============================================================

@pytest.mark.unit
class TestApprovalFlowsPackagePurity:
    """import 引擎包不应拉起任何业务 service 模块。"""

    def test_import_approval_flows_does_not_load_business_services(self):
        """在干净子进程中 import 引擎包，断言不拉起业务模块。

        用子进程是为了排除同一 pytest session 中其他测试先 import 业务模块带来的
        sys.modules 污染，保证断言的是"引擎包自身的导入副作用"。
        """
        import subprocess
        import sys as _sys

        code = (
            "import importlib, sys; "
            "importlib.import_module('app.modules.approval_flows'); "
            "assert 'app.modules.leave_requests.service' not in sys.modules, 'leave_requests leaked'; "
            "assert 'app.modules.schedules' not in sys.modules, 'schedules leaked'; "
            "print('PURE_OK')"
        )
        result = subprocess.run(
            [_sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=str(_SERVER_ROOT),
        )
        assert result.returncode == 0, (
            f"引擎包 import 泄漏了业务模块:\nSTDOUT={result.stdout}\nSTDERR={result.stderr}"
        )
        assert "PURE_OK" in result.stdout

    def test_engine_has_no_business_service_import(self):
        """静态断言：引擎包源码不再 import 业务 service（grep 等价检查）。"""
        import os

        import app.modules.approval_flows as af

        pkg_dir = os.path.dirname(af.__file__)
        offenders = []
        for name in os.listdir(pkg_dir):
            if not name.endswith(".py"):
                continue
            path = os.path.join(pkg_dir, name)
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            for needle in (
                "from app.modules.leave_requests",
                "from app.modules.schedules",
                "import app.modules.leave_requests",
                "import app.modules.schedules",
            ):
                if needle in src:
                    offenders.append(f"{name}: {needle}")
        assert not offenders, f"引擎包仍残留业务 import: {offenders}"


# ============================================================
# 2. leave_requests 回调分支
# ============================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestLeaveRequestCallbackBranches:
    """leave_requests/callbacks.py 分支单测。"""

    def _make_instance(self, business_id="lr-1", applicant_id="doc-1"):
        instance = MagicMock()
        instance.id = "inst-1"
        instance.business_id = business_id
        instance.applicant_id = applicant_id
        instance.updated_by = None
        return instance

    def _make_request(self, status=RequestStatus.PENDING.value):
        request = MagicMock()
        request.status = status
        return request

    async def test_on_approved_triggers_handle_approved_request(self):
        """on_approved 设置 APPROVED 状态并调用 LeaveRequestService._handle_approved_request。"""
        from app.modules.leave_requests.callbacks import handle_leave_request_approval

        db = MagicMock()
        request = self._make_request()
        db.get = AsyncMock(return_value=request)

        instance = self._make_instance()
        # last_action_record 返回 None → 走 instance.applicant_id 分支
        with patch(
            "app.modules.leave_requests.callbacks.last_action_record",
            AsyncMock(return_value=None),
        ) as mock_rec, patch(
            "app.modules.leave_requests.callbacks.LeaveRequestService"
        ) as MockSvc:
            mock_svc_inst = MagicMock()
            mock_svc_inst._handle_approved_request = AsyncMock()
            MockSvc.return_value = mock_svc_inst

            await handle_leave_request_approval("on_approved", instance, db)

        mock_rec.assert_awaited_once_with(db, instance.id)
        assert request.status == RequestStatus.APPROVED.value
        assert request.reviewer_id == instance.applicant_id  # record=None 走 applicant_id
        assert request.reviewed_at is not None
        MockSvc.assert_called_once_with(db)
        mock_svc_inst._handle_approved_request.assert_awaited_once_with(request)

    async def test_on_rejected_sets_status_without_handling(self):
        """on_rejected 仅改状态，不调用 _handle_approved_request。"""
        from app.modules.leave_requests.callbacks import handle_leave_request_approval

        db = MagicMock()
        request = self._make_request()
        db.get = AsyncMock(return_value=request)
        instance = self._make_instance()

        record = MagicMock()
        record.approver_id = "rev-1"
        record.comment = "不同意"
        with patch(
            "app.modules.leave_requests.callbacks.last_action_record",
            AsyncMock(return_value=record),
        ), patch(
            "app.modules.leave_requests.callbacks.LeaveRequestService"
        ) as MockSvc:
            mock_svc_inst = MagicMock()
            mock_svc_inst._handle_approved_request = AsyncMock()
            MockSvc.return_value = mock_svc_inst

            await handle_leave_request_approval("on_rejected", instance, db)

        assert request.status == RequestStatus.REJECTED.value
        assert request.reviewer_id == "rev-1"
        assert request.review_comment == "不同意"
        MockSvc.assert_not_called()

    async def test_on_cancelled_sets_cancelled_status(self):
        from app.modules.leave_requests.callbacks import handle_leave_request_approval

        db = MagicMock()
        request = self._make_request()
        db.get = AsyncMock(return_value=request)
        instance = self._make_instance()

        with patch(
            "app.modules.leave_requests.callbacks.last_action_record",
            AsyncMock(return_value=None),
        ), patch(
            "app.modules.leave_requests.callbacks.LeaveRequestService"
        ) as MockSvc:
            await handle_leave_request_approval("on_cancelled", instance, db)

        assert request.status == RequestStatus.CANCELLED.value
        MockSvc.assert_not_called()

    async def test_request_not_found_is_noop(self):
        """db.get 返回 None 时静默返回，不抛异常。"""
        from app.modules.leave_requests.callbacks import handle_leave_request_approval

        db = MagicMock()
        db.get = AsyncMock(return_value=None)
        instance = self._make_instance()

        # 不应触发 last_action_record（提前 return）
        with patch(
            "app.modules.leave_requests.callbacks.last_action_record",
            AsyncMock(),
        ) as mock_rec:
            result = await handle_leave_request_approval("on_approved", instance, db)

        assert result is None
        mock_rec.assert_not_called()

    async def test_non_pending_request_is_noop(self):
        """已是 APPROVED 的申请不重复处理。"""
        from app.modules.leave_requests.callbacks import handle_leave_request_approval

        db = MagicMock()
        request = self._make_request(status=RequestStatus.APPROVED.value)
        db.get = AsyncMock(return_value=request)
        instance = self._make_instance()

        with patch(
            "app.modules.leave_requests.callbacks.last_action_record",
            AsyncMock(),
        ) as mock_rec:
            await handle_leave_request_approval("on_approved", instance, db)

        mock_rec.assert_not_called()
        # 状态未被回调改动（保持 APPROVED）
        assert request.status == RequestStatus.APPROVED.value


# ============================================================
# 3. extra_quota 回调分支
# ============================================================

@pytest.mark.unit
@pytest.mark.asyncio
class TestExtraQuotaCallbackBranches:
    """schedules/callbacks_extra_quota.py 分支单测。"""

    def _make_instance(self, business_id="eq-1", applicant_id="u-1"):
        instance = MagicMock()
        instance.id = "inst-eq-1"
        instance.business_id = business_id
        instance.applicant_id = applicant_id
        instance.updated_by = None
        return instance

    def _make_request(self, approval_status="pending", schedule_id="sch-1", quantity=3):
        request = MagicMock()
        request.approval_status = approval_status
        request.schedule_id = schedule_id
        request.quantity = quantity
        return request

    async def test_on_approved_updates_schedule_quota(self):
        from app.modules.schedules.callbacks_extra_quota import handle_extra_quota_approval

        db = MagicMock()
        request = self._make_request(quantity=3)
        db.get = AsyncMock(side_effect=[request, "schedule_obj"])  # 1st: request, 2nd: schedule
        instance = self._make_instance()

        schedule = MagicMock()
        schedule.extra_quota = 7
        db.get = AsyncMock(side_effect=[request, schedule])

        with patch(
            "app.modules.schedules.callbacks_extra_quota.last_action_record",
            AsyncMock(return_value=None),
        ):
            await handle_extra_quota_approval("on_approved", instance, db)

        assert request.approval_status == "approved"
        assert request.approver_id == instance.applicant_id  # record=None 走 applicant_id
        assert request.approved_at is not None
        # 排班号源累加
        assert schedule.extra_quota == 10  # 7 + 3
        schedule.sync_total_slots.assert_called_once()

    async def test_on_approved_with_record_uses_approver_id(self):
        from app.modules.schedules.callbacks_extra_quota import handle_extra_quota_approval

        db = MagicMock()
        request = self._make_request()
        schedule = MagicMock()
        schedule.extra_quota = 0
        db.get = AsyncMock(side_effect=[request, schedule])
        instance = self._make_instance()

        record = MagicMock()
        record.approver_id = "rev-9"
        record.comment = "同意加号"
        with patch(
            "app.modules.schedules.callbacks_extra_quota.last_action_record",
            AsyncMock(return_value=record),
        ):
            await handle_extra_quota_approval("on_approved", instance, db)

        assert request.approver_id == "rev-9"
        assert request.approval_remark == "同意加号"

    async def test_on_rejected_sets_status(self):
        from app.modules.schedules.callbacks_extra_quota import handle_extra_quota_approval

        db = MagicMock()
        request = self._make_request()
        db.get = AsyncMock(return_value=request)
        instance = self._make_instance()

        with patch(
            "app.modules.schedules.callbacks_extra_quota.last_action_record",
            AsyncMock(return_value=None),
        ):
            await handle_extra_quota_approval("on_rejected", instance, db)

        assert request.approval_status == "rejected"

    async def test_on_cancelled_sets_status(self):
        from app.modules.schedules.callbacks_extra_quota import handle_extra_quota_approval

        db = MagicMock()
        request = self._make_request()
        db.get = AsyncMock(return_value=request)
        instance = self._make_instance()

        with patch(
            "app.modules.schedules.callbacks_extra_quota.last_action_record",
            AsyncMock(return_value=None),
        ):
            await handle_extra_quota_approval("on_cancelled", instance, db)

        assert request.approval_status == "cancelled"

    async def test_non_pending_request_is_noop(self):
        from app.modules.schedules.callbacks_extra_quota import handle_extra_quota_approval

        db = MagicMock()
        request = self._make_request(approval_status="approved")
        db.get = AsyncMock(return_value=request)
        instance = self._make_instance()

        with patch(
            "app.modules.schedules.callbacks_extra_quota.last_action_record",
            AsyncMock(),
        ) as mock_rec:
            await handle_extra_quota_approval("on_approved", instance, db)

        mock_rec.assert_not_called()
        assert request.approval_status == "approved"

    async def test_request_not_found_is_noop(self):
        from app.modules.schedules.callbacks_extra_quota import handle_extra_quota_approval

        db = MagicMock()
        db.get = AsyncMock(return_value=None)
        instance = self._make_instance()

        with patch(
            "app.modules.schedules.callbacks_extra_quota.last_action_record",
            AsyncMock(),
        ) as mock_rec:
            result = await handle_extra_quota_approval("on_approved", instance, db)

        assert result is None
        mock_rec.assert_not_called()


# ============================================================
# 4. 自注册集成（单例 registry）
# ============================================================

@pytest.mark.unit
class TestBusinessSelfRegistration:
    """业务模块 import 后回调应自动注册到全局 registry。"""

    def test_leave_request_registered_after_module_import(self):
        import importlib

        importlib.import_module("app.modules.leave_requests")
        assert "leave_request" in callback_registry._handlers

    def test_extra_quota_registered_after_module_import(self):
        import importlib

        importlib.import_module("app.modules.schedules")
        assert "extra_quota" in callback_registry._handlers
