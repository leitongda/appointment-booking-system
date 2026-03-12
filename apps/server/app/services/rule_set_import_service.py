"""规则组导入服务 - 兼容层

实际实现已迁移至 app.modules.import_export.service_rule_set_import
"""
from app.modules.import_export.service_rule_set_import import RuleSetImportService

__all__ = ["RuleSetImportService"]
