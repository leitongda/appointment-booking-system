"""
排班管理相关的工具函数
"""
from datetime import date, time
from typing import List, Tuple


def get_month_week(d: date) -> int:
    """获取日期在月内的周数
    1-7号为第1周，8-14号为第2周，15-21号为第3周，22-28号为第4周，29号-月底为第5周
    """
    return (d.day - 1) // 7 + 1


def get_year_week(d: date) -> int:
    """获取日期在年内的周数"""
    return d.isocalendar()[1]


def should_generate_schedule(d: date, schedule_mode: str) -> bool:
    """判断指定日期是否应该生成排班
    
    Args:
        d: 日期
        schedule_mode: 排班方式
            - weekly: 每周
            - month_week_1~5: 每月第N周
            - year_odd_week: 奇数周
            - year_even_week: 偶数周
    
    Returns:
        是否应该生成排班
    """
    month_week = get_month_week(d)
    year_week = get_year_week(d)
    
    if schedule_mode == "weekly":
        return True
    elif schedule_mode == "month_week_1":
        return month_week == 1
    elif schedule_mode == "month_week_2":
        return month_week == 2
    elif schedule_mode == "month_week_3":
        return month_week == 3
    elif schedule_mode == "month_week_4":
        return month_week == 4
    elif schedule_mode == "month_week_5":
        return month_week == 5
    elif schedule_mode == "year_odd_week":
        return year_week % 2 == 1
    elif schedule_mode == "year_even_week":
        return year_week % 2 == 0
    return False


def get_time_slot_from_time(start_time: time) -> str:
    """根据开始时间判断时段
    
    Args:
        start_time: 开始时间
    
    Returns:
        时段字符串: morning/afternoon/evening
    """
    hour = start_time.hour
    if hour < 12:
        return "morning"
    elif hour < 18:
        return "afternoon"
    else:
        return "evening"


def split_time_range(start: time, end: time, count: int) -> List[Tuple[time, time]]:
    """将时间区间均分为多个班次
    
    Args:
        start: 开始时间
        end: 结束时间
        count: 班次数量
    
    Returns:
        班次时间列表，如 [(09:00, 11:00), (11:00, 13:00), ...]
    """
    if count <= 0:
        return [(start, end)]
    
    # 计算总分钟数
    start_minutes = start.hour * 60 + start.minute
    end_minutes = end.hour * 60 + end.minute
    total_minutes = end_minutes - start_minutes
    
    if total_minutes <= 0:
        return [(start, end)]
    
    # 每个班次的分钟数
    slot_minutes = total_minutes // count
    
    slots = []
    current_start = start
    
    for i in range(count):
        # 计算当前班次的结束时间
        current_start_minutes = current_start.hour * 60 + current_start.minute
        current_end_minutes = current_start_minutes + slot_minutes
        
        # 最后一个班次使用结束时间，确保覆盖完整区间
        if i == count - 1:
            current_end = end
        else:
            current_end_hour = current_end_minutes // 60
            current_end_minute = current_end_minutes % 60
            current_end = time(current_end_hour, current_end_minute)
        
        slots.append((current_start, current_end))
        current_start = current_end
    
    return slots

