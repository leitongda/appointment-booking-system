"""Composed rule-set service."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rule_sets.service_mutation import RuleSetMutationMixin
from app.modules.rule_sets.service_policy import RuleSetPolicyMixin
from app.modules.rule_sets.service_query import RuleSetQueryMixin


class RuleSetService(
    RuleSetQueryMixin,
    RuleSetMutationMixin,
    RuleSetPolicyMixin,
):
    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id
