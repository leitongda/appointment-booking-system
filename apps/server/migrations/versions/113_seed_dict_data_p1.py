"""seed dictionary data - second batch (P1 state-flow types)

Revision ID: 113
Revises: 112
Create Date: 2026-05-22
"""
from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime

revision = '113'
down_revision = '112'
branch_labels = None
depends_on = None

# P1 字典类型：有状态流转的字典
DICT_TYPES = [
    (
        "feedback_type",
        "反馈类型",
        "用户反馈的分类",
        [
            ("建议", "suggestion", 1),
            ("投诉", "complaint", 2),
            ("BUG", "bug", 3),
            ("其他", "other", 4),
        ],
    ),
    (
        "support_ticket_type",
        "工单类型",
        "支持工单的分类",
        [
            ("建议", "suggestion", 1),
            ("投诉", "complaint", 2),
            ("BUG", "bug", 3),
            ("其他", "other", 4),
        ],
    ),
    (
        "support_ticket_priority",
        "工单优先级",
        "支持工单的优先级",
        [
            ("低", "low", 1),
            ("中", "medium", 2),
            ("高", "high", 3),
            ("紧急", "urgent", 4),
        ],
    ),
    (
        "message_type",
        "消息类型",
        "系统消息的分类",
        [
            ("预约消息", "appointment", 1),
            ("问诊消息", "consultation", 2),
            ("排班消息", "schedule", 3),
            ("系统消息", "system", 4),
            ("停诊消息", "stop_clinic", 5),
            ("反馈消息", "feedback", 6),
        ],
    ),
    (
        "email_template_type",
        "邮件模板类型",
        "邮件模板的分类",
        [
            ("预约确认", "appointment_confirm", 1),
            ("就诊提醒", "appointment_remind", 2),
            ("预约取消", "appointment_cancel", 3),
            ("停诊通知（旧）", "stop_clinic", 4),
            ("自定义", "custom", 5),
            ("新预约通知", "appointment_created", 6),
            ("预约取消通知", "appointment_cancelled", 7),
            ("签到通知", "checkin", 8),
            ("叫号通知", "call_patient", 9),
            ("就诊完成通知", "visit_completed", 10),
            ("爽约通知", "no_show", 11),
            ("停诊通知", "schedule_suspended", 12),
        ],
    ),
    (
        "notification_event_type",
        "通知事件类型",
        "通知系统的事件分类",
        [
            ("预约成功", "appointment.success", 1),
            ("24小时就诊提醒", "appointment.reminder.24h", 2),
            ("1小时就诊提醒", "appointment.reminder.1h", 3),
            ("预约取消", "appointment.cancelled", 4),
            ("排班变更", "schedule.change", 5),
            ("排班停止", "schedule.stop", 6),
            ("停诊通知", "stop_clinic", 7),
            ("系统通知", "system", 8),
        ],
    ),
    (
        "rule_type",
        "接收人规则类型",
        "通知接收人规则的分类",
        [
            ("按角色", "role", 1),
            ("按科室", "department", 2),
            ("指定用户", "user_list", 3),
            ("动态规则", "dynamic", 4),
            ("事件驱动", "event_driven", 5),
        ],
    ),
    (
        "extra_quota_type",
        "加号类型",
        "额外号源的分类",
            [
            ("普通加号", "normal", 1),
            ("特殊加号", "special", 2),
            ("绿色通道", "green_channel", 3),
        ],
    ),
]


def upgrade() -> None:
    now = datetime.utcnow()
    conn = op.get_bind()

    for code, name, description, items in DICT_TYPES:
        dict_type_id = str(uuid.uuid4())

        conn.execute(
            sa.text(
                "INSERT INTO dict_types (id, code, name, description, status, tenant_id, created_at, updated_at) "
                "VALUES (:id, :code, :name, :description, 1, NULL, :now, :now)"
            ),
            {
                "id": dict_type_id,
                "code": code,
                "name": name,
                "description": description,
                "now": now,
            },
        )

        for label, value, sort_order in items:
            conn.execute(
                sa.text(
                    "INSERT INTO dict_items (id, dict_type_id, label, value, sort_order, status, extra, tenant_id, created_at, updated_at) "
                    "VALUES (:id, :type_id, :label, :value, :sort, 1, NULL, NULL, :now, :now)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "type_id": dict_type_id,
                    "label": label,
                    "value": value,
                    "sort": sort_order,
                    "now": now,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()
    codes = [dt[0] for dt in DICT_TYPES]
    placeholders = ", ".join([f"'{c}'" for c in codes])

    conn.execute(
        sa.text(
            f"DELETE FROM dict_items WHERE dict_type_id IN (SELECT id FROM dict_types WHERE code IN ({placeholders}))"
        )
    )
    conn.execute(sa.text(f"DELETE FROM dict_types WHERE code IN ({placeholders})"))
