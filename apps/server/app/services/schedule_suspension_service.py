"""停诊管理服务 - 兼容层

实际实现已迁移至 app.modules.schedule_suspensions.service
"""
from app.modules.schedule_suspensions.service import ScheduleSuspensionService

__all__ = ["ScheduleSuspensionService"]
