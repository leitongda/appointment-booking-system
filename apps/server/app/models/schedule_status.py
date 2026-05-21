"""排班发布状态机常量定义。

状态转换规则:
    draft -> published (publish action)
    published -> booking (when first appointment created)
    booking -> full (when booked_slots == total_slots)
    booking/full -> suspended (stop_clinic action)
    suspended -> booking/full (resume action, 恢复到暂停前状态)
    published/booking -> withdrawn (withdraw, only if no active appointments)
    any -> finished (when schedule_date passes, 由定时任务驱动)
"""


class ScheduleStatus:
    """排班状态 (schedule_status)"""
    DRAFT = "draft"
    PUBLISHED = "published"
    BOOKING = "booking"
    FULL = "full"
    SUSPENDED = "suspended"
    FINISHED = "finished"
    WITHDRAWN = "withdrawn"

    ALL = {DRAFT, PUBLISHED, BOOKING, FULL, SUSPENDED, FINISHED, WITHDRAWN}

    # 患者端可预约状态 (published/booking 且 publish_status=published)
    BOOKABLE = {PUBLISHED, BOOKING}

    # 管理端可操作状态
    ACTIVE = {PUBLISHED, BOOKING, FULL}


class PublishStatus:
    """发布状态 (publish_status)"""
    DRAFT = "draft"
    PUBLISHED = "published"
    WITHDRAWN = "withdrawn"

    ALL = {DRAFT, PUBLISHED, WITHDRAWN}
