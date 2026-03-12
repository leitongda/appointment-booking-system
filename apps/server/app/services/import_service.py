"""数据导入服务 - 兼容层

实际实现已迁移至 app.modules.import_export.service_import
"""
from app.modules.import_export.service_import import ImportService

__all__ = ["ImportService"]
