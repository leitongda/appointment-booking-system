"""TenantFeatures Pydantic schema 校验测试"""
import json
import pytest
from pydantic import ValidationError

from app.modules.tenants.schemas import (
    TenantFeatures,
    _validate_features_json,
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    TenantCreate,
    TenantUpdate,
)


# ==================== _validate_features_json 单元测试 ====================


class TestValidateFeaturesJson:
    """features JSON 校验函数测试"""

    def test_none_returns_none(self):
        assert _validate_features_json(None) is None

    def test_empty_string_returns_none(self):
        assert _validate_features_json("  ") is None

    def test_empty_json_object_returns_none(self):
        """空 JSON 对象是合法的（所有功能默认关闭）"""
        result = _validate_features_json("{}")
        assert result == "{}"

    def test_valid_features(self):
        result = _validate_features_json('{"basic_appointment": true}')
        parsed = json.loads(result)
        assert parsed["basic_appointment"] is True

    def test_sorted_keys(self):
        """返回的 JSON key 应排序，保证幂等"""
        result = _validate_features_json('{"wechat_integration": true, "basic_appointment": false}')
        parsed = json.loads(result)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_extra_fields_preserved(self):
        """额外字段应被保留（extra='allow'）"""
        result = _validate_features_json('{"basic_appointment": true, "future_feature": true}')
        parsed = json.loads(result)
        assert parsed["future_feature"] is True

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="不是合法的 JSON"):
            _validate_features_json("not json at all")

    def test_non_dict_json_raises(self):
        with pytest.raises(ValueError, match="必须是一个 JSON 对象"):
            _validate_features_json("[1, 2, 3]")

    def test_non_bool_value_raises(self):
        with pytest.raises(ValueError, match="布尔类型"):
            _validate_features_json('{"basic_appointment": "yes"}')

    def test_numeric_value_raises(self):
        with pytest.raises(ValueError, match="布尔类型"):
            _validate_features_json('{"basic_appointment": 1}')

    def test_null_value_raises(self):
        with pytest.raises(ValueError):
            _validate_features_json('{"basic_appointment": null}')


# ==================== TenantFeatures 模型测试 ====================


class TestTenantFeaturesModel:
    """TenantFeatures Pydantic model 测试"""

    def test_defaults(self):
        tf = TenantFeatures()
        assert tf.basic_appointment is False
        assert tf.wechat_integration is False
        assert tf.sso is False

    def test_explicit_values(self):
        tf = TenantFeatures(basic_appointment=True, sso=True)
        assert tf.basic_appointment is True
        assert tf.sso is True
        assert tf.basic_schedule is False

    def test_extra_fields_allowed(self):
        tf = TenantFeatures(basic_appointment=True, new_feature_x=True)
        dumped = tf.model_dump()
        assert dumped["new_feature_x"] is True

    def test_all_known_features(self):
        """确保所有 init_subscription_plans.py 中使用到的 key 都已定义"""
        all_keys = [
            "basic_appointment", "basic_schedule", "basic_statistics",
            "advanced_statistics", "wechat_integration", "sms_notification",
            "export_data", "api_access", "custom_branding", "priority_support",
            "sso", "online_payment",
        ]
        tf = TenantFeatures()
        for key in all_keys:
            assert hasattr(tf, key), f"TenantFeatures 缺少字段: {key}"


# ==================== SubscriptionPlanCreate 校验测试 ====================


class TestSubscriptionPlanCreateFeatures:
    def test_valid_features(self):
        plan = SubscriptionPlanCreate(
            plan_code="test",
            name="Test Plan",
            features='{"basic_appointment": true, "sms_notification": true}',
        )
        assert plan.features is not None

    def test_none_features(self):
        plan = SubscriptionPlanCreate(
            plan_code="test",
            name="Test Plan",
            features=None,
        )
        assert plan.features is None

    def test_invalid_features_raises(self):
        with pytest.raises(ValidationError):
            SubscriptionPlanCreate(
                plan_code="test",
                name="Test Plan",
                features='{"basic_appointment": 123}',
            )

    def test_non_json_features_raises(self):
        with pytest.raises(ValidationError):
            SubscriptionPlanCreate(
                plan_code="test",
                name="Test Plan",
                features="not-json",
            )


# ==================== SubscriptionPlanUpdate 校验测试 ====================


class TestSubscriptionPlanUpdateFeatures:
    def test_valid_features(self):
        plan = SubscriptionPlanUpdate(
            features='{"sso": true}',
        )
        assert plan.features is not None

    def test_invalid_features_raises(self):
        with pytest.raises(ValidationError):
            SubscriptionPlanUpdate(features='bad json')


# ==================== TenantCreate 校验测试 ====================


class TestTenantCreateFeatures:
    def test_valid_features(self):
        tenant = TenantCreate(
            tenant_code="test-tenant",
            name="Test Tenant",
            features='{"api_access": true}',
        )
        assert tenant.features is not None

    def test_none_features(self):
        tenant = TenantCreate(
            tenant_code="test-tenant",
            name="Test Tenant",
        )
        assert tenant.features is None

    def test_invalid_features_raises(self):
        with pytest.raises(ValidationError):
            TenantCreate(
                tenant_code="test-tenant",
                name="Test Tenant",
                features='invalid',
            )


# ==================== TenantUpdate 校验测试 ====================


class TestTenantUpdateFeatures:
    def test_valid_features(self):
        tenant = TenantUpdate(features='{"wechat_integration": true}')
        assert tenant.features is not None

    def test_invalid_features_raises(self):
        with pytest.raises(ValidationError):
            TenantUpdate(features='{"basic_appointment": "true"}')


# ==================== 向后兼容性测试 ====================


class TestBackwardCompatibility:
    """确保 init_subscription_plans.py 中已有的 features 数据都能通过校验"""

    BASIC = '{"basic_appointment": true, "basic_schedule": true, "basic_statistics": true}'

    PRO = (
        '{"basic_appointment": true, "basic_schedule": true, "basic_statistics": true,'
        ' "advanced_statistics": true, "wechat_integration": true, "sms_notification": true,'
        ' "export_data": true}'
    )

    ENTERPRISE = (
        '{"basic_appointment": true, "basic_schedule": true, "basic_statistics": true,'
        ' "advanced_statistics": true, "wechat_integration": true, "sms_notification": true,'
        ' "export_data": true, "api_access": true, "custom_branding": true,'
        ' "priority_support": true, "sso": true}'
    )

    @pytest.mark.parametrize("features_json", [BASIC, PRO, ENTERPRISE])
    def test_existing_plan_features_pass(self, features_json):
        result = _validate_features_json(features_json)
        assert result is not None
        parsed = json.loads(result)
        # 确保没有丢字段
        original = json.loads(features_json)
        for key in original:
            assert parsed[key] is True

    def test_router_example_features_pass(self):
        """router.py 文档中的示例：{"online_payment": true, "wechat_integration": true}"""
        result = _validate_features_json('{"online_payment": true, "wechat_integration": true}')
        assert result is not None
