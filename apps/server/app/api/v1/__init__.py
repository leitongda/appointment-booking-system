from dataclasses import dataclass
from importlib import import_module

from fastapi import APIRouter


@dataclass(frozen=True)
class RouterRegistration:
    module: str
    prefix: str
    tags: list[str]


ROUTER_REGISTRATIONS = [
    RouterRegistration("app.modules.auth.router", "/auth", ["认证"]),
    RouterRegistration("app.modules.upload.router", "/upload", ["文件上传"]),
    RouterRegistration("app.modules.users.router", "/users", ["用户"]),
    RouterRegistration("app.modules.stores.router", "/stores", ["门店管理"]),
    RouterRegistration("app.modules.messages.router", "/messages", ["消息中心"]),
    RouterRegistration("app.modules.departments.router", "/departments", ["科室"]),
    RouterRegistration("app.modules.doctors.router", "/doctors", ["医生"]),
    RouterRegistration("app.modules.schedules.router", "/schedules", ["排班"]),
    RouterRegistration("app.modules.appointments.router", "/appointments", ["预约"]),
    RouterRegistration("app.modules.medical_records.router", "/medical-records", ["病历"]),
    RouterRegistration("app.modules.content.router", "/content", ["内容管理"]),
    RouterRegistration("app.modules.statistics.router", "/statistics", ["数据统计"]),
    RouterRegistration("app.modules.admin.router", "/admin", ["权限管理"]),
    RouterRegistration("app.modules.settings.router", "/settings", ["系统设置"]),
    RouterRegistration("app.modules.patients.router_manage", "/patients", ["就诊卡管理"]),
    RouterRegistration("app.modules.patients.router_users", "/user-manage", ["患者管理"]),
    RouterRegistration("app.modules.export.router", "/export", ["数据导出"]),
    RouterRegistration("app.modules.leave_requests.router", "/leave-requests", ["停诊调班"]),
    RouterRegistration("app.modules.feedbacks.router", "/feedbacks", ["用户反馈"]),
    RouterRegistration("app.modules.consultation_fees.router", "/consultation-fees", ["诊费管理"]),
    RouterRegistration("app.modules.doctor_booking_settings.router", "/doctor-booking-settings", ["医生预约设置"]),
    RouterRegistration("app.modules.custom_schedules.router", "/custom-schedules", ["自定义排班"]),
    RouterRegistration("app.modules.rest_days.router", "/rest-days", ["休息日设置"]),
    RouterRegistration("app.modules.schedule_suspensions.router", "/schedule-suspensions", ["停诊管理"]),
    RouterRegistration("app.modules.schedule_templates.router", "/schedule-templates", ["排班模板"]),
    RouterRegistration("app.modules.blacklists.router", "/blacklists", ["黑名单管理"]),
    RouterRegistration("app.modules.email_templates.router", "/email-templates", ["邮件模板"]),
    RouterRegistration("app.modules.analytics.router", "/analytics", ["用户行为分析"]),
    RouterRegistration("app.modules.import_export.router", "/data", ["数据导入导出"]),
    RouterRegistration("app.modules.booking_notices.router", "/booking-notices", ["预约须知"]),
    RouterRegistration("app.modules.user_favorites.router", "/favorites", ["用户收藏"]),
    RouterRegistration("app.modules.store_visit_type_configs.router", "/visit-type-configs", ["复诊规则配置"]),
    RouterRegistration("app.modules.rule_sets.router", "/rule-sets", ["规则管理"]),
    RouterRegistration("app.modules.shift_types.router", "/shift-types", ["班次类型"]),
    RouterRegistration("app.modules.audit_logs.router", "/audit-logs", ["审计日志"]),
    RouterRegistration("app.modules.websocket.router", "/ws", ["WebSocket"]),
    RouterRegistration("app.modules.doctor_portal.router", "/doctor-portal", ["医生端"]),
    RouterRegistration("app.modules.store_email_recipients.router", "/store-email-recipients", ["门店邮件接收人"]),
    RouterRegistration("app.modules.tenants.router", "/tenants", ["租户管理"]),
    RouterRegistration("app.modules.miniapp_platform.router", "/miniapp-platform", ["小程序平台管理"]),
    RouterRegistration("app.modules.payments.router", "/payments", ["支付管理"]),
    RouterRegistration("app.modules.refunds.router", "/refunds", ["退款管理"]),
    RouterRegistration("app.modules.notification_logs.router", "/notification-logs", ["通知日志"]),
    RouterRegistration("app.modules.notification_preferences.router", "/notification-preferences", ["通知偏好"]),
]


def build_api_router() -> APIRouter:
    router = APIRouter()
    for registration in ROUTER_REGISTRATIONS:
        module = import_module(registration.module)
        router.include_router(module.router, prefix=registration.prefix, tags=registration.tags)
    return router


api_router = build_api_router()
