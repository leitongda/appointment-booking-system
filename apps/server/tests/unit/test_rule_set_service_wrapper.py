from app.modules.rule_sets.service import RuleSetService as modular_rule_set_service
from app.services.rule_set_service import RuleSetService as legacy_rule_set_service


def test_rule_set_service_wrapper_reuses_modular_service():
    assert legacy_rule_set_service is modular_rule_set_service
