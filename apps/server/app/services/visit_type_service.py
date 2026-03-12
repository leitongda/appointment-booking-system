"""复诊规则配置服务 - 兼容层

实际实现已迁移至 app.modules.visit_types.service
"""
from app.modules.visit_types.service import VisitTypeService

__all__ = ["VisitTypeService"]
