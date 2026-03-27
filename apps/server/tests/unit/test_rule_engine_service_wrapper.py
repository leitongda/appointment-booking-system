from app.modules.rule_engine import RuleEngineService as modular_rule_engine_service
from app.modules.rule_engine import RuleEngineService as legacy_rule_engine_service


def test_rule_engine_service_wrapper_reuses_modular_service():
    assert legacy_rule_engine_service is modular_rule_engine_service
