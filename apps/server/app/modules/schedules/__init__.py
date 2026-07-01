"""Schedules domain module."""
from app.modules.approval_flows.callback_registry import callback_registry
from app.modules.schedules.callbacks_extra_quota import handle_extra_quota_approval

# 业务侧自注册审批回调（依赖倒置：引擎不再反向 import 业务包）。
callback_registry.register("extra_quota", handle_extra_quota_approval)
