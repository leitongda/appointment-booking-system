"""预约相关常量

注意：这些常量保持 dict/tuple 格式，不转为 Enum。
原因：数据库使用 Integer 存储，API 返回数字值，代码中 100% 使用 dict 访问模式。
转为 IntEnum 会破坏数据库兼容性和 API 契约。
"""
from sqlalchemy.orm import selectinload

from app.models.appointment import Appointment
from app.models.schedule import Schedule

# 预约状态映射（name → Integer 值）
APPOINTMENT_STATUS = {
    "CONFIRMED": 1,
    "SIGNED": 2,
    "SEEING": 4,
    "COMPLETED": 5,
    "CANCELLED": 6,
    "EXPIRED": 7,
    "NO_SHOW": 8,
}

# 活跃预约状态集合（用于查询过滤）
ACTIVE_APPOINTMENT_STATUSES = (
    0,  # 待支付
    APPOINTMENT_STATUS["CONFIRMED"],
    APPOINTMENT_STATUS["SIGNED"],
    APPOINTMENT_STATUS["SEEING"],
)

# 已到院及之后的状态（签到/历史候诊/就诊中/已完成）—— 经营统计"已到院"语义
# 注：status 3 为历史候诊(WAITING)遗留值，不在 APPOINTMENT_STATUS 中，故显式列出
VISITED_STATUSES = (
    APPOINTMENT_STATUS["SIGNED"],
    3,
    APPOINTMENT_STATUS["SEEING"],
    APPOINTMENT_STATUS["COMPLETED"],
)
# 产生营收的状态（与 RevenueService.calculate_total_revenue 默认口径一致）
REVENUE_STATUSES = VISITED_STATUSES
# 取消类状态（取消/过期）
CANCELLED_STATUSES = (
    APPOINTMENT_STATUS["CANCELLED"],
    APPOINTMENT_STATUS["EXPIRED"],
)

# 预约查询的默认 eager-loading 选项
APPOINTMENT_QUERY_OPTIONS = (
    selectinload(Appointment.schedule).selectinload(Schedule.store),
    selectinload(Appointment.checkin_logs),
)
