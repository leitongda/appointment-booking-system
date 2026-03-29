"""
测试工具函数

提供测试中常用的辅助函数和数据生成器
"""
from datetime import datetime, date, time, timedelta
from typing import Optional
from uuid import uuid4


def generate_appointment_no() -> str:
    """生成预约号"""
    return f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid4())[:4].upper()}"


def generate_phone() -> str:
    """生成测试手机号"""
    return f"138{str(uuid4().int)[:8]}"


def get_tomorrow() -> date:
    """获取明天日期"""
    return date.today() + timedelta(days=1)


def get_next_week() -> date:
    """获取下周日期"""
    return date.today() + timedelta(days=7)


def make_appointment_data(
    schedule_id: str,
    patient_id: str,
    symptom_description: Optional[str] = None,
) -> dict:
    """构造预约创建数据"""
    return {
        "schedule_id": schedule_id,
        "patient_id": patient_id,
        "symptom_description": symptom_description,
    }


def make_time_slot(
    time_slot: str = "morning",
    start_hour: int = 8,
    end_hour: int = 12,
) -> dict:
    """构造时段数据"""
    return {
        "time_slot": time_slot,
        "start_time": time(start_hour, 0),
        "end_time": time(end_hour, 0),
    }


class AsyncContextManagerMock:
    """异步上下文管理器 Mock"""

    def __init__(self, return_value=None):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, *args):
        return None


def mock_distributed_lock(return_value: str = "lock_value"):
    """创建分布式锁 Mock"""
    return AsyncContextManagerMock(return_value)
