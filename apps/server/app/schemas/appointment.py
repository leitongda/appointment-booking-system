from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import inspect as sa_inspect

from app.core.config import settings
from app.schemas.base import BaseRequestSchema, BaseSchema
from app.schemas.response import to_camel


class AppointmentCreate(BaseModel):
    """创建预约请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "scheduleId": "sch_abc123def456",
                "patientId": "pat_xyz789abc",
                "symptomDescription": "头痛三天，伴有轻微发热"
            }
        }
    )
    
    schedule_id: str = Field(..., description="排班ID", examples=["sch_abc123def456"])
    patient_id: str = Field(..., description="就诊人ID", examples=["pat_xyz789abc"])
    symptom_description: str | None = Field(None, max_length=500, description="病情描述/预填信息", examples=["头痛三天，伴有轻微发热"])

class AppointmentResponse(BaseSchema):
    """预约信息响应"""

    id: str = Field(..., description="预约ID")
    appointment_no: str | None = Field(None, description="预约编号")
    user_id: str | None = Field(None, description="用户ID")
    patient_id: str | None = Field(None, description="就诊人ID")
    patient_name: str | None = Field(None, description="就诊人姓名")
    patient_phone: str | None = Field(None, description="就诊人手机号")
    doctor_id: str | None = Field(None, description="医生ID")
    doctor_name: str | None = Field(None, description="医生姓名")
    doctor_title: str | None = Field(None, description="医生职称")
    department_name: str | None = Field(None, description="科室名称")
    store_name: str | None = Field(None, description="门店名称")
    schedule_id: str | None = Field(None, description="排班ID")
    schedule_date: date | None = Field(None, description="就诊日期")
    time_slot: str | None = Field(None, description="时段: morning上午/afternoon下午/evening晚间")
    start_time: time | None = Field(None, description="开始时间")
    end_time: time | None = Field(None, description="结束时间")
    queue_number: int | None = Field(None, description="排队序号")
    status: int | None = Field(None, description="状态: 0待支付 1已预约 2已签到 3历史候诊(遗留) 4就诊中 5已完成 6已取消 7已过期 8已爽约")
    sign_in_time: datetime | None = Field(None, description="签到时间")
    check_in_method: str | None = Field(None, description="签到方式")
    call_time: datetime | None = Field(None, description="叫号时间")
    complete_time: datetime | None = Field(None, description="完成就诊时间")
    cancel_time: datetime | None = Field(None, description="取消时间")
    cancel_reason: str | None = Field(None, description="取消原因")
    symptom_description: str | None = Field(None, description="病情描述")
    created_at: datetime | None = Field(None, description="创建时间")
    payment_amount: float | None = Field(None, description="支付金额（元）")
    payment_time: datetime | None = Field(None, description="支付完成时间")
    payment_transaction_id: str | None = Field(None, description="支付交易号")
    refund_status: str | None = Field(None, description="退款状态")
    refunded_amount: float | None = Field(None, description="已退款金额（元）")
    rescheduled_from_id: str | None = Field(None, description="转约/改期来源预约ID")

    @staticmethod
    def _decimal_to_float(value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    @staticmethod
    def _resolve_check_in_method(appointment) -> str | None:
        checkin_logs = AppointmentResponse._safe_get_relation(appointment, "checkin_logs") or []
        successful_logs = [log for log in checkin_logs if getattr(log, "status", None) == "SUCCESS"]
        if not successful_logs:
            return None

        latest_log = max(
            successful_logs,
            key=lambda log: getattr(log, "checkin_time", None) or getattr(log, "created_at", None) or datetime.min,
        )
        return getattr(latest_log, "checkin_method", None)

    @staticmethod
    def _safe_get_relation(obj, attr: str):
        """安全获取 SQLAlchemy 关系属性，避免在 async 上下文中触发懒加载"""
        try:
            state = sa_inspect(obj)
            if attr in state.unloaded:
                return None
        except Exception:
            pass
        return getattr(obj, attr, None)

    @classmethod
    def from_appointment(cls, appointment) -> "AppointmentResponse":
        """从 Appointment ORM 对象构造响应，自动提取排班关联字段。"""
        schedule = cls._safe_get_relation(appointment, "schedule")
        store = cls._safe_get_relation(schedule, "store") if schedule else None
        return cls(
            id=appointment.id,
            appointment_no=appointment.appointment_no,
            user_id=appointment.user_id,
            patient_id=appointment.patient_id,
            patient_name=appointment.patient_name,
            patient_phone=appointment.patient_phone,
            doctor_id=appointment.doctor_id,
            doctor_name=appointment.doctor_name,
            doctor_title=appointment.doctor_title,
            department_name=appointment.department_name,
            store_name=store.name if store else None,
            schedule_id=appointment.schedule_id,
            schedule_date=schedule.schedule_date if schedule else None,
            time_slot=schedule.time_slot if schedule else None,
            start_time=schedule.start_time if schedule else None,
            end_time=schedule.end_time if schedule else None,
            queue_number=appointment.queue_number,
            status=appointment.status,
            sign_in_time=appointment.sign_in_time,
            check_in_method=cls._resolve_check_in_method(appointment),
            call_time=appointment.call_time,
            complete_time=appointment.complete_time,
            cancel_time=appointment.cancel_time,
            cancel_reason=appointment.cancel_reason,
            symptom_description=appointment.symptom_description,
            created_at=appointment.created_at,
            payment_amount=cls._decimal_to_float(appointment.payment_amount),
            payment_time=appointment.paid_at,
            payment_transaction_id=appointment.payment_transaction_id,
            refund_status=appointment.refund_status,
            refunded_amount=cls._decimal_to_float(appointment.refund_amount),
            rescheduled_from_id=appointment.rescheduled_from_id,
        )

class AppointmentPaymentParams(BaseModel):
    """预约创建后可直接使用的支付参数。"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    time_stamp: str = Field(..., description="支付时间戳")
    nonce_str: str = Field(..., description="随机字符串")
    package: str = Field(..., description="预支付会话标识")
    sign_type: str = Field(..., description="签名类型")
    pay_sign: str = Field(..., description="支付签名")

class AppointmentPendingPaymentResponse(BaseModel):
    """收费预约创建响应。"""
    appointment: AppointmentResponse = Field(..., description="预约信息")
    payment_required: bool = Field(True, description="是否需要支付")
    payment_amount: float | None = Field(None, description="支付金额（元）")
    payment_params: AppointmentPaymentParams | None = Field(None, description="支付参数")

    @classmethod
    def from_result(cls, result: dict) -> "AppointmentPendingPaymentResponse":
        appointment = result["appointment"]
        return cls(
            appointment=AppointmentResponse.from_appointment(appointment),
            payment_required=bool(result.get("payment_required", False)),
            payment_amount=result.get("payment_amount"),
            payment_params=result.get("payment_params"),
        )

class AppointmentListQuery(BaseRequestSchema):
    """预约列表查询参数

    注意：当 page_size > 100 时，需要管理员权限且必须提供 start_date 和 end_date。
    """

    status: int | None = Field(None, description="状态: 0待支付 1已预约 2已签到 3历史候诊(遗留) 4就诊中 5已完成 6已取消 7已过期 8已爽约")
    patient_id: str | None = Field(None, description="就诊人ID")
    doctor_id: str | None = Field(None, description="医生ID")
    start_date: date | None = Field(None, description="开始日期")
    end_date: date | None = Field(None, description="结束日期")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=settings.APPOINTMENTS_MAX_PAGE_SIZE, description="每页数量（默认10，普通用户上限100，管理员+日期范围可至500）")

class AppointmentCancelRequest(BaseModel):
    """取消预约请求"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "reason": "临时有事无法前往"
            }
        }
    )
    
    reason: str | None = Field(None, max_length=200, description="取消原因", examples=["临时有事无法前往", "预约错误", "身体不适已恢复"])

class AppointmentStatistics(BaseModel):
    """预约统计信息"""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        by_alias=True,
    )

    total: int = Field(0, description="总预约数")
    confirmed: int = Field(0, description="已预约数")
    signed_in: int = Field(0, description="已签到数")
    in_progress: int = Field(0, description="就诊中数")
    completed: int = Field(0, description="已完成数")
    cancelled: int = Field(0, description="已取消数")
    no_show: int = Field(0, description="爽约数")
