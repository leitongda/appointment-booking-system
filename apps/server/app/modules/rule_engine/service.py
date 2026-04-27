"""Composed rule engine service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rule_engine.policies import RuleEnginePolicyMixin
from app.modules.rule_engine.time_windows import RuleEngineTimeWindowMixin
from app.modules.rule_engine.validation import RuleEngineValidationMixin


class RuleEngineService(
    RuleEngineTimeWindowMixin,
    RuleEnginePolicyMixin,
    RuleEngineValidationMixin,
):
    """Rule engine facade composed from smaller mixins."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # 初始化 TimeWindowMixin 中的缓存属性
        RuleEngineTimeWindowMixin.__init__(self)
