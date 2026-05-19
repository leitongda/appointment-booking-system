"""seed default email templates for event hooks

Revision ID: 086_seed_default_email_templates
Revises: 085_add_consultation_feedback_to_notification_preferences
Create Date: 2026-05-19
"""
import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy import table, column, String, Integer, Text


revision = '086_seed_default_email_templates'
down_revision = '085_add_consultation_feedback_to_notification_preferences'
branch_labels = None
depends_on = None


# ── 公共样式 ──────────────────────────────────────────────
WRAP_OPEN = '<div style="font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 0 16px;">'
WRAP_CLOSE = '</div>'

HEADER_BLUE = '<div style="background: #1890ff; color: #fff; padding: 24px 20px; border-radius: 8px 8px 0 0;"><h2 style="margin:0; font-size:20px;">{{hospital_name}}</h2></div>'
HEADER_GREEN = '<div style="background: #52c41a; color: #fff; padding: 24px 20px; border-radius: 8px 8px 0 0;"><h2 style="margin:0; font-size:20px;">{{hospital_name}}</h2></div>'
HEADER_RED = '<div style="background: #ff4d4f; color: #fff; padding: 24px 20px; border-radius: 8px 8px 0 0;"><h2 style="margin:0; font-size:20px;">{{hospital_name}}</h2></div>'
HEADER_ORANGE = '<div style="background: #fa8c16; color: #fff; padding: 24px 20px; border-radius: 8px 8px 0 0;"><h2 style="margin:0; font-size:20px;">{{hospital_name}}</h2></div>'

BODY_WRAP_OPEN = '<div style="background: #fff; border: 1px solid #f0f0f0; border-top: none; padding: 24px 20px; border-radius: 0 0 8px 8px;">'
BODY_WRAP_CLOSE = '</div>'

INFO_TABLE = '''
    <table style="width:100%; border-collapse:collapse; margin:16px 0;">
        <tr><td style="padding:10px 8px; color:#888; width:90px; border-bottom:1px solid #f5f5f5;">预约编号</td><td style="padding:10px 8px; border-bottom:1px solid #f5f5f5;">{{appointment_no}}</td></tr>
        <tr><td style="padding:10px 8px; color:#888; border-bottom:1px solid #f5f5f5;">患者姓名</td><td style="padding:10px 8px; border-bottom:1px solid #f5f5f5;">{{patient_name}}</td></tr>
        <tr><td style="padding:10px 8px; color:#888; border-bottom:1px solid #f5f5f5;">科室</td><td style="padding:10px 8px; border-bottom:1px solid #f5f5f5;">{{department_name}}</td></tr>
        <tr><td style="padding:10px 8px; color:#888; border-bottom:1px solid #f5f5f5;">医生</td><td style="padding:10px 8px; border-bottom:1px solid #f5f5f5;">{{doctor_name}}</td></tr>
        <tr><td style="padding:10px 8px; color:#888; border-bottom:1px solid #f5f5f5;">就诊日期</td><td style="padding:10px 8px; border-bottom:1px solid #f5f5f5;">{{appointment_date}}</td></tr>
        <tr><td style="padding:10px 8px; color:#888;">就诊时段</td><td style="padding:10px 8px;">{{appointment_time}}</td></tr>
    </table>'''

FOOTER = '<p style="color:#bbb; font-size:12px; text-align:center; margin-top:20px;">此邮件由系统自动发送，请勿回复。如有疑问请联系 {{hospital_phone}}</p>'


def _wrap(header, title, body_extra):
    return (
        f'{WRAP_OPEN}'
        f'{header}'
        f'{BODY_WRAP_OPEN}'
        f'<p style="font-size:16px; font-weight:600; color:#333; margin:0 0 16px 0;">{title}</p>'
        f'{body_extra}'
        f'{FOOTER}'
        f'{BODY_WRAP_CLOSE}'
        f'{WRAP_CLOSE}'
    )


# ── 模版数据 ──────────────────────────────────────────────
TEMPLATES = [
    {
        "id": str(uuid.uuid4()),
        "code": "sys_appointment_created",
        "name": "新预约通知",
        "template_type": "appointment_created",
        "subject_template": "[{{hospital_name}}] 新预约通知 — {{patient_name}}",
        "content_template": _wrap(
            HEADER_BLUE,
            "您有一条新的预约",
            f'<p style="color:#555; line-height:1.8;">您好，<strong>{{patient_name}}</strong> 已成功预约，请做好接诊准备。</p>'
            f'{INFO_TABLE}'
        ),
        "description": "系统默认：新预约创建时通知医生/门店",
    },
    {
        "id": str(uuid.uuid4()),
        "code": "sys_appointment_cancelled",
        "name": "预约取消通知",
        "template_type": "appointment_cancelled",
        "subject_template": "[{{hospital_name}}] 预约取消通知 — {{patient_name}}",
        "content_template": _wrap(
            HEADER_RED,
            "预约已取消",
            f'<p style="color:#555; line-height:1.8;">以下预约已被取消，请知悉。</p>'
            f'{INFO_TABLE}'
        ),
        "description": "系统默认：预约被取消时通知",
    },
    {
        "id": str(uuid.uuid4()),
        "code": "sys_checkin",
        "name": "签到通知",
        "template_type": "checkin",
        "subject_template": "[{{hospital_name}}] 患者签到通知 — {{patient_name}}",
        "content_template": _wrap(
            HEADER_GREEN,
            "患者已签到",
            f'<p style="color:#555; line-height:1.8;">患者 <strong>{{patient_name}}</strong> 已到达签到，请准备接诊。</p>'
            f'{INFO_TABLE}'
        ),
        "description": "系统默认：患者签到时通知",
    },
    {
        "id": str(uuid.uuid4()),
        "code": "sys_call_patient",
        "name": "叫号通知",
        "template_type": "call_patient",
        "subject_template": "[{{hospital_name}}] 叫号通知 — {{patient_name}}",
        "content_template": _wrap(
            HEADER_BLUE,
            "请到诊室就诊",
            f'<p style="color:#555; line-height:1.8;">尊敬的 <strong>{{patient_name}}</strong>，您的号码已叫到，请前往 <strong>{{department_name}}</strong> <strong>{{doctor_name}}</strong> 诊室就诊。</p>'
            f'{INFO_TABLE}'
        ),
        "description": "系统默认：叫号时通知患者",
    },
    {
        "id": str(uuid.uuid4()),
        "code": "sys_visit_completed",
        "name": "就诊完成通知",
        "template_type": "visit_completed",
        "subject_template": "[{{hospital_name}}] 就诊完成 — {{patient_name}}",
        "content_template": _wrap(
            HEADER_GREEN,
            "就诊已完成",
            f'<p style="color:#555; line-height:1.8;">尊敬的 <strong>{{patient_name}}</strong>，您的本次就诊已完成。感谢您的信任，祝您早日康复！</p>'
            f'{INFO_TABLE}'
        ),
        "description": "系统默认：就诊完成时通知",
    },
    {
        "id": str(uuid.uuid4()),
        "code": "sys_no_show",
        "name": "爽约通知",
        "template_type": "no_show",
        "subject_template": "[{{hospital_name}}] 爽约通知 — {{patient_name}}",
        "content_template": _wrap(
            HEADER_ORANGE,
            "预约未按时就诊",
            f'<p style="color:#555; line-height:1.8;">患者 <strong>{{patient_name}}</strong> 未按时就诊（爽约），请记录。</p>'
            f'{INFO_TABLE}'
        ),
        "description": "系统默认：患者爽约时通知",
    },
    {
        "id": str(uuid.uuid4()),
        "code": "sys_schedule_suspended",
        "name": "停诊通知",
        "template_type": "schedule_suspended",
        "subject_template": "[{{hospital_name}}] 停诊通知 — {{department_name}} {{doctor_name}}",
        "content_template": _wrap(
            HEADER_RED,
            "停诊通知",
            f'<p style="color:#555; line-height:1.8;"><strong>{{department_name}}</strong> <strong>{{doctor_name}}</strong> 医生于 <strong>{{appointment_date}}</strong> 停诊，请相关患者知悉并重新预约。</p>'
            f'<table style="width:100%; border-collapse:collapse; margin:16px 0;">'
            f'<tr><td style="padding:10px 8px; color:#888; width:90px; border-bottom:1px solid #f5f5f5;">科室</td><td style="padding:10px 8px; border-bottom:1px solid #f5f5f5;">{{department_name}}</td></tr>'
            f'<tr><td style="padding:10px 8px; color:#888; border-bottom:1px solid #f5f5f5;">医生</td><td style="padding:10px 8px; border-bottom:1px solid #f5f5f5;">{{doctor_name}}</td></tr>'
            f'<tr><td style="padding:10px 8px; color:#888;">停诊日期</td><td style="padding:10px 8px;">{{appointment_date}}</td></tr>'
            f'</table>'
        ),
        "description": "系统默认：医生停诊时通知受影响的患者",
    },
]


def upgrade() -> None:
    email_templates = table(
        'email_templates',
        column('id', String),
        column('code', String),
        column('name', String),
        column('template_type', String),
        column('subject_template', String),
        column('content_template', Text),
        column('description', String),
        column('status', Integer),
    )

    for t in TEMPLATES:
        op.execute(
            email_templates.insert().values(
                id=t["id"],
                code=t["code"],
                name=t["name"],
                template_type=t["template_type"],
                subject_template=t["subject_template"],
                content_template=t["content_template"],
                description=t["description"],
                status=1,
            )
        )


def downgrade() -> None:
    codes = [t["code"] for t in TEMPLATES]
    for code in codes:
        op.execute(
            f"DELETE FROM email_templates WHERE code = '{code}'"
        )
