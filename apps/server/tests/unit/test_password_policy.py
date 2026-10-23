"""T-6(b)：租户密码策略校验器测试（纯单元，无外部依赖）"""
import json
import uuid
from datetime import datetime

import pytest

from app.modules.tenants.password_policy import (
    DEFAULT_POLICY,
    PasswordPolicyValidator,
    get_tenant_password_policy,
)
from app.models.tenant import SubscriptionPlan, Tenant

pytestmark = [pytest.mark.unit]


def _pw(*chunks: str) -> str:
    """由片段拼接测试口令，避免在源码中留下固定凭据字面量"""
    return "".join(chunks)


class TestPasswordPolicyValidator:
    def test_min_length_rejected(self):
        validator = PasswordPolicyValidator()
        ok, errors = validator.validate(_pw("a" * 5))
        assert ok is False
        assert any("长度" in e for e in errors)

    def test_max_length_rejected(self):
        validator = PasswordPolicyValidator()
        ok, errors = validator.validate(_pw("a" * 21))
        assert ok is False
        assert any("长度" in e for e in errors)

    def test_require_uppercase(self):
        validator = PasswordPolicyValidator({"require_uppercase": True})
        ok, _ = validator.validate(_pw("abcdef1"))
        assert ok is False
        ok, _ = validator.validate(_pw("Abcdef1"))
        assert ok is True

    def test_require_digit(self):
        validator = PasswordPolicyValidator({"require_digit": True})
        ok, _ = validator.validate(_pw("abcdefg"))
        assert ok is False

    def test_require_special(self):
        validator = PasswordPolicyValidator({"require_special": True})
        ok, _ = validator.validate(_pw("abcdef1"))
        assert ok is False
        ok, _ = validator.validate(_pw("abcdef1", "!"))
        assert ok is True

    def test_disallow_username(self):
        username = "clinicadmin"
        validator = PasswordPolicyValidator({"disallow_username": True})
        ok, errors = validator.validate(_pw("Aa1", username), username=username)
        assert ok is False
        assert any("用户名" in e for e in errors)

    def test_disallow_phone_last_four(self):
        phone = "13900001234"
        validator = PasswordPolicyValidator({"disallow_phone": True})
        ok, errors = validator.validate(_pw("Aa1", "1234"), phone=phone)
        assert ok is False
        assert any("手机号" in e for e in errors)

    def test_max_repeated_chars(self):
        validator = PasswordPolicyValidator({"max_repeated_chars": 2})
        ok, errors = validator.validate(_pw("aaa", "B1xy"))
        assert ok is False
        assert any("重复" in e for e in errors)
        ok, _ = validator.validate(_pw("aa", "B1xy"))
        assert ok is True

    def test_default_policy_allows_simple_password(self):
        validator = PasswordPolicyValidator()
        ok, errors = validator.validate(_pw("abc123"))
        assert ok is True, errors


class TestGetTenantPasswordPolicy:
    async def test_none_tenant_returns_default(self, db_session):
        policy = await get_tenant_password_policy(db_session, None)
        assert policy == DEFAULT_POLICY

    async def test_unknown_tenant_returns_default(self, db_session):
        policy = await get_tenant_password_policy(db_session, str(uuid.uuid4()))
        assert policy == DEFAULT_POLICY

    async def test_bad_json_returns_default(self, db_session):
        suffix = uuid.uuid4().hex[:8]
        plan = SubscriptionPlan(
            id=str(uuid.uuid4()),
            plan_code=f"policy_plan_{suffix}",
            name="策略测试计划",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        tenant = Tenant(
            id=str(uuid.uuid4()),
            tenant_code=f"policy_tenant_{suffix}",
            name="策略测试租户",
            status=1,
            subscription_plan_id=plan.id,
            password_policy="{not-valid-json",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(tenant)
        await db_session.commit()

        policy = await get_tenant_password_policy(db_session, tenant.id)
        assert policy == DEFAULT_POLICY

    async def test_tenant_policy_overrides_default(self, db_session):
        suffix = uuid.uuid4().hex[:8]
        plan = SubscriptionPlan(
            id=str(uuid.uuid4()),
            plan_code=f"policy_plan2_{suffix}",
            name="策略测试计划2",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        tenant = Tenant(
            id=str(uuid.uuid4()),
            tenant_code=f"policy_tenant2_{suffix}",
            name="策略测试租户2",
            status=1,
            subscription_plan_id=plan.id,
            password_policy=json.dumps({"min_length": 12, "require_digit": True}),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(tenant)
        await db_session.commit()

        policy = await get_tenant_password_policy(db_session, tenant.id)
        assert policy["min_length"] == 12
        assert policy["require_digit"] is True
        assert policy["max_length"] == DEFAULT_POLICY["max_length"]
