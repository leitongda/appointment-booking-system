# Models module
from app.models.user import User, Patient
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.models.medical_record import MedicalRecord
from app.models.content import News, Notice, Banner
from app.models.admin import Admin, Role, OperationLog, AdminLoginHistory
from app.models.settings import SystemSetting
from app.models.store import Store
from app.models.message import Message, MessageTemplate
from app.models.leave_request import LeaveRequest
from app.models.feedback import Feedback
from app.models.consultation_fee import ConsultationFeeType, ConsultationFeeTemplate, StoreFeeTemplate, DoctorConsultationFee
from app.models.doctor_booking_setting import DoctorBookingSetting
from app.models.point_log import PointLog
from app.models.schedule_template import ScheduleTemplate
# CustomSchedule已合并到Schedule，不再需要单独导入
from app.models.rest_day import RestDay
from app.models.schedule_suspension import ScheduleSuspension
from app.models.schedule_holiday import ScheduleHoliday
from app.models.blacklist import Blacklist
from app.models.email_template import EmailTemplate, EmailTemplateType
from app.models.behavior_log import UserBehaviorLog
from app.models.schedule_generation_log import ScheduleGenerationLog
from app.models.booking_notice import BookingNotice
from app.models.user_favorite import UserFavorite
from app.models.store_visit_type_config import StoreVisitTypeConfig
from app.models.waitlist import WaitlistEntry
from app.models.store_email_recipient import StoreEmailRecipient
from app.models.shift_type import ShiftType
from app.models.rule_set import RuleSet, RuleSetShiftType, RuleWindow, RuleBookingPolicy, RuleCheckinPolicy, RuleCapacityPolicy, AppointmentCheckin
from app.models.rule_set_audit import RuleSetAuditLog
from app.models.schedule_audit import ScheduleAuditLog
from app.models.tenant import Tenant, TenantSubscription, TenantUsageLog, SubscriptionPlan
from app.models.tenant_audit_log import TenantAuditLog
from app.models.refund import RefundRecord
from app.models.miniapp_platform import (
    AppTemplate,
    BuildJob,
    Company,
    MiniappInstance,
    PaymentProfile,
    PaymentRoute,
    ReleaseArtifact,
    ReleaseJob,
    TemplateVersion,
)
from app.models.notification_log import NotificationLog
from app.models.notification_preference import NotificationPreference
from app.models.approval_flow import (
    ApprovalFlowDefinition,
    ApprovalFlowNode,
    ApprovalFlowCondition,
    ApprovalInstance,
    ApprovalRecord,
)
from app.modules.unified_message.models import (
    NotificationGroup,
    NotificationRecipient,
    NotificationDelivery,
    UnifiedTemplate,
    ChannelStrategy,
    RecipientRule,
)
from app.models.platform_announcement import PlatformAnnouncement
from app.models.support_ticket import SupportTicket
from app.models.account import Account, AccountAdmin, AccountDoctor, AccountUser
from app.models.examination_report import ExaminationReport
from app.models.extra_quota_request import ExtraQuotaRequest
from app.models.schedule_room import ScheduleRoom
