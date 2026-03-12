"""用户服务 - 兼容层

实际实现已迁移至 app.modules.users.service
"""
from app.modules.users.service import UserService, PatientService

__all__ = ["UserService", "PatientService"]
