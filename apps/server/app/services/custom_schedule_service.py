"""自定义排班服务 - 兼容层

实际实现已迁移至 app.modules.custom_schedules.service
"""
from app.modules.custom_schedules.service import (
    CustomScheduleService,
    add_minutes,
    generate_time_slots,
)

__all__ = ["CustomScheduleService", "add_minutes", "generate_time_slots"]
