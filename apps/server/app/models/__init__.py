# Models module
from app.models.account import Account, AccountAdmin, AccountDoctor, AccountUser
from app.models.admin import Admin, AdminLoginHistory, OperationLog, Role
from app.models.appointment import Appointment
from app.models.appointment_satisfaction import AppointmentSatisfaction
from app.models.approval_flow import (
    ApprovalFlowCondition,
    ApprovalFlowDefinition,
    ApprovalFlowNode,
    ApprovalInstance,
    ApprovalRecord,
)
from app.models.behavior_log import UserBehaviorLog
from app.models.blacklist import Blacklist
from app.models.booking_notice import BookingNotice
from app.models.consultation_fee import (
    ConsultationFeeTemplate,
    ConsultationFeeType,
    DoctorConsultationFee,
    StoreFeeTemplate,
)
from app.models.content import Banner, News, Notice
from app.models.content_version import ContentVersion
from app.models.data_scope import DataScope
from app.models.department import Department
from app.models.dict_item import DictItem
from app.models.dict_type import DictType
from app.models.doctor import Doctor
from app.models.doctor_booking_setting import DoctorBookingSetting
from app.models.doctor_review import DoctorReview
from app.models.email_template import EmailTemplate, EmailTemplateType
from app.models.examination_report import ExaminationReport
from app.models.extra_quota_request import ExtraQuotaRequest
from app.models.feedback import Feedback
from app.models.follow_up_plan import FollowUpPlan, FollowUpPlanStep
from app.models.follow_up_record import FollowUpRecord
from app.models.follow_up_self_report import FollowUpSelfReport
from app.models.follow_up_task import FollowUpTask
from app.models.freelance import (
    FreelanceInteraction,
    Freelancer,
    FreelanceSettlement,
    FreelanceSettlementItem,
    FreelanceTask,
)
from app.models.leave_request import LeaveRequest
from app.models.lowcode_page import LowCodePage
from app.models.lowcode_page_version import LowCodePageVersion
from app.models.lowcode_template import LowCodeTemplate
from app.models.lowcode_template_version import LowCodeTemplateFork, LowCodeTemplateVersion
from app.models.medical_record import MedicalRecord
from app.models.message import Message, MessageTemplate
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
from app.models.platform_announcement import PlatformAnnouncement
from app.models.point_log import PointLog
from app.models.refund import RefundRecord

# CustomSchedule已合并到Schedule，不再需要单独导入
from app.models.rest_day import RestDay
from app.models.rule_set import (
    AppointmentCheckin,
    RuleBookingPolicy,
    RuleCapacityPolicy,
    RuleCheckinPolicy,
    RuleSet,
    RuleSetShiftType,
    RuleWindow,
)
from app.models.rule_set_audit import RuleSetAuditLog
from app.models.schedule import Schedule
from app.models.schedule_audit import ScheduleAuditLog
from app.models.schedule_generation_log import ScheduleGenerationLog
from app.models.schedule_holiday import ScheduleHoliday
from app.models.schedule_room import ScheduleRoom
from app.models.schedule_suspension import ScheduleSuspension
from app.models.schedule_template import ScheduleTemplate
from app.models.settings import SystemSetting
from app.models.shift_type import ShiftType
from app.models.store import Store
from app.models.store_email_recipient import StoreEmailRecipient
from app.models.store_metric import StoreDailyMetric
from app.models.store_visit_type_config import StoreVisitTypeConfig
from app.models.support_ticket import SupportTicket
from app.models.tenant import SubscriptionPlan, Tenant, TenantSubscription, TenantUsageLog
from app.models.tenant_audit_log import TenantAuditLog
from app.models.user import Patient, User
from app.models.user_favorite import UserFavorite
from app.models.waitlist import WaitlistEntry
from app.modules.unified_message.models import (
    ChannelStrategy,
    NotificationDelivery,
    NotificationGroup,
    NotificationRecipient,
    RecipientRule,
    UnifiedTemplate,
)
