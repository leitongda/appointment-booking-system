"""
排班管理相关的工具函数
"""
from datetime import date, time
from typing import List, Tuple, Optional, Dict, Any


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


def get_time_slot_from_time(start_time: time, periods: Optional[List[Dict[str, Any]]] = None) -> str:
    """根据开始时间判断时段
    
    Args:
        start_time: 开始时间
        periods: 自定义时段配置列表，如 [{"key": "morning", "name": "上午", "startTime": "06:00", "endTime": "12:00"}]
    
    Returns:
        时段字符串: morning/afternoon/evening 或自定义时段的 key
    """
    if periods:
        # 使用自定义时段配置
        start_minutes = start_time.hour * 60 + start_time.minute
        for period in periods:
            period_start = period.get('startTime', '00:00')
            period_end = period.get('endTime', '24:00')
            
            # 解析时段时间
            try:
                ps_parts = period_start.split(':')
                pe_parts = period_end.split(':')
                period_start_minutes = int(ps_parts[0]) * 60 + int(ps_parts[1])
                period_end_minutes = int(pe_parts[0]) * 60 + int(pe_parts[1])
                
                # 处理跨越午夜的情况
                if period_end_minutes <= period_start_minutes:
                    period_end_minutes += 24 * 60
                
                if period_start_minutes <= start_minutes < period_end_minutes:
                    return period.get('key', 'morning')
            except (ValueError, IndexError):
                continue
    
    # 默认逻辑
    hour = start_time.hour
    if hour < 12:
        return "morning"
    elif hour < 18:
        return "afternoon"
    else:
        return "evening"


def get_period_name_from_time(start_time: time, periods: Optional[List[Dict[str, Any]]] = None) -> str:
    """根据开始时间获取时段名称
    
    Args:
        start_time: 开始时间
        periods: 自定义时段配置列表
    
    Returns:
        时段名称: 上午/下午/晚上 或自定义时段名称
    """
    if periods:
        start_minutes = start_time.hour * 60 + start_time.minute
        for period in periods:
            period_start = period.get('startTime', '00:00')
            period_end = period.get('endTime', '24:00')
            
            try:
                ps_parts = period_start.split(':')
                pe_parts = period_end.split(':')
                period_start_minutes = int(ps_parts[0]) * 60 + int(ps_parts[1])
                period_end_minutes = int(pe_parts[0]) * 60 + int(pe_parts[1])
                
                if period_end_minutes <= period_start_minutes:
                    period_end_minutes += 24 * 60
                
                if period_start_minutes <= start_minutes < period_end_minutes:
                    return period.get('name', '上午')
            except (ValueError, IndexError):
                continue
    
    # 默认名称
    hour = start_time.hour
    if hour < 12:
        return "上午"
    elif hour < 18:
        return "下午"
    else:
        return "晚上"


def calculate_working_duration(
    start: time, 
    end: time, 
    break_times: Optional[List[Dict[str, Any]]] = None
) -> int:
    """计算有效工作时长（分钟）
    
    Args:
        start: 开始时间
        end: 结束时间
        break_times: 排除时间段列表
    
    Returns:
        有效工作分钟数
    """
    start_minutes = time_to_minutes(start)
    end_minutes = time_to_minutes(end)
    total_minutes = end_minutes - start_minutes
    
    if total_minutes <= 0:
        return 0
    
    if not break_times:
        return total_minutes
    
    # 计算排除时间段的总时长
    excluded_minutes = 0
    for bt in break_times:
        try:
            bt_start, bt_end = parse_break_time(bt)
            bt_start_min = time_to_minutes(bt_start)
            bt_end_min = time_to_minutes(bt_end)
            
            # 计算与工作时间的交集
            overlap_start = max(bt_start_min, start_minutes)
            overlap_end = min(bt_end_min, end_minutes)
            
            if overlap_end > overlap_start:
                excluded_minutes += overlap_end - overlap_start
        except (ValueError, KeyError):
            continue
    
    return max(0, total_minutes - excluded_minutes)


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


def time_to_minutes(t: time) -> int:
    """将时间转换为分钟数"""
    return t.hour * 60 + t.minute


def minutes_to_time(minutes: int) -> time:
    """将分钟数转换为时间"""
    hours = minutes // 60
    mins = minutes % 60
    # 确保不超过23:59
    if hours >= 24:
        hours = 23
        mins = 59
    return time(hours, mins)


def parse_break_time(bt: Dict[str, Any]) -> Tuple[time, time]:
    """解析排除时间段
    
    支持以下格式：
    - {"startTime": "12:00", "endTime": "13:30"}
    - {"start_time": "12:00", "end_time": "13:30"}
    - {"startTime": time(12, 0), "endTime": time(13, 30)}
    """
    start_key = "startTime" if "startTime" in bt else "start_time"
    end_key = "endTime" if "endTime" in bt else "end_time"
    
    start_val = bt.get(start_key)
    end_val = bt.get(end_key)
    
    # 如果是字符串，转换为 time 对象
    if isinstance(start_val, str):
        parts = start_val.split(":")
        start_time = time(int(parts[0]), int(parts[1]))
    elif isinstance(start_val, time):
        start_time = start_val
    else:
        raise ValueError(f"Invalid start time format: {start_val}")
    
    if isinstance(end_val, str):
        parts = end_val.split(":")
        end_time = time(int(parts[0]), int(parts[1]))
    elif isinstance(end_val, time):
        end_time = end_val
    else:
        raise ValueError(f"Invalid end time format: {end_val}")
    
    return start_time, end_time


def get_working_periods(
    start: time, 
    end: time, 
    break_times: Optional[List[Dict[str, Any]]] = None
) -> List[Tuple[time, time]]:
    """根据排除时间段获取有效工作时间段
    
    Args:
        start: 工作开始时间
        end: 工作结束时间
        break_times: 排除时间段列表，如 [{"startTime": "12:00", "endTime": "13:30"}]
    
    Returns:
        有效工作时间段列表，如 [(09:00, 12:00), (13:30, 18:00)]
    """
    if not break_times:
        return [(start, end)]
    
    start_minutes = time_to_minutes(start)
    end_minutes = time_to_minutes(end)
    
    # 解析并排序排除时间段
    breaks = []
    for bt in break_times:
        try:
            bt_start, bt_end = parse_break_time(bt)
            bt_start_min = time_to_minutes(bt_start)
            bt_end_min = time_to_minutes(bt_end)
            # 只保留与工作时间有交集的排除时间
            if bt_end_min > start_minutes and bt_start_min < end_minutes:
                breaks.append((max(bt_start_min, start_minutes), min(bt_end_min, end_minutes)))
        except (ValueError, KeyError):
            continue
    
    # 按开始时间排序
    breaks.sort(key=lambda x: x[0])
    
    # 合并重叠的排除时间段
    merged_breaks = []
    for bt in breaks:
        if merged_breaks and bt[0] <= merged_breaks[-1][1]:
            merged_breaks[-1] = (merged_breaks[-1][0], max(merged_breaks[-1][1], bt[1]))
        else:
            merged_breaks.append(bt)
    
    # 生成有效工作时间段
    periods = []
    current_start = start_minutes
    
    for bt_start, bt_end in merged_breaks:
        if current_start < bt_start:
            periods.append((minutes_to_time(current_start), minutes_to_time(bt_start)))
        current_start = bt_end
    
    # 添加最后一个时间段
    if current_start < end_minutes:
        periods.append((minutes_to_time(current_start), minutes_to_time(end_minutes)))
    
    return periods


def split_time_range_with_breaks(
    start: time, 
    end: time, 
    count: int, 
    break_times: Optional[List[Dict[str, Any]]] = None
) -> List[Tuple[time, time]]:
    """将时间区间均分为多个班次，考虑排除时间段
    
    Args:
        start: 开始时间
        end: 结束时间
        count: 班次数量
        break_times: 排除时间段列表，如 [{"startTime": "12:00", "endTime": "13:30"}]
    
    Returns:
        班次时间列表，如 [(09:00, 10:30), (10:30, 12:00), (13:30, 15:45), (15:45, 18:00)]
        每个班次的时间范围不会跨越排除时间段
    """
    if count <= 0:
        return [(start, end)]
    
    # 如果没有排除时间，使用原来的函数
    if not break_times:
        return split_time_range(start, end, count)
    
    # 获取有效工作时间段
    working_periods = get_working_periods(start, end, break_times)
    
    if not working_periods:
        return [(start, end)]
    
    # 计算总有效工作分钟数
    total_working_minutes = 0
    for period_start, period_end in working_periods:
        total_working_minutes += time_to_minutes(period_end) - time_to_minutes(period_start)
    
    if total_working_minutes <= 0:
        return [(start, end)]
    
    # 每个班次的分钟数
    slot_minutes = total_working_minutes // count
    if slot_minutes <= 0:
        slot_minutes = 1
    
    # 在有效时间段内分配班次
    slots = []
    remaining_minutes = 0  # 上一个时间段剩余的分钟数
    slot_count = 0
    
    for period_idx, (period_start, period_end) in enumerate(working_periods):
        period_start_minutes = time_to_minutes(period_start)
        period_end_minutes = time_to_minutes(period_end)
        current_pos = period_start_minutes
        
        while current_pos < period_end_minutes and slot_count < count:
            # 计算当前班次在此时间段内可用的分钟数
            available_in_period = period_end_minutes - current_pos
            
            # 如果是最后一个班次，使用剩余所有时间
            if slot_count == count - 1:
                # 最后一个班次需要覆盖到整个工作时间结束
                # 但不能跨越排除时间，所以只能到当前时间段结束
                slot_end = period_end_minutes
                slots.append((minutes_to_time(current_pos), minutes_to_time(slot_end)))
                slot_count += 1
                current_pos = slot_end
            else:
                # 计算班次需要的分钟数
                needed_minutes = slot_minutes
                
                if needed_minutes <= available_in_period:
                    # 可以在当前时间段内完成这个班次
                    slot_end = current_pos + needed_minutes
                    slots.append((minutes_to_time(current_pos), minutes_to_time(slot_end)))
                    slot_count += 1
                    current_pos = slot_end
                else:
                    # 当前时间段不足以容纳一个完整班次
                    # 将剩余时间作为一个班次（不跨越排除时间）
                    slot_end = period_end_minutes
                    slots.append((minutes_to_time(current_pos), minutes_to_time(slot_end)))
                    slot_count += 1
                    current_pos = slot_end
    
    # 如果最后一个班次后还有剩余时间段，扩展最后一个班次
    if slots and slot_count == count:
        # 检查是否还有后续的工作时间段
        last_slot_end = time_to_minutes(slots[-1][1])
        for period_start, period_end in working_periods:
            period_end_minutes = time_to_minutes(period_end)
            if period_end_minutes > last_slot_end:
                # 将最后一个班次的结束时间延长到最后的工作时间段结束
                slots[-1] = (slots[-1][0], period_end)
                break
    
    return slots if slots else [(start, end)]

