"""初始化消息模板数据"""
import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 消息模板数据
MESSAGE_TEMPLATES = [
    {
        "code": "appointment_success",
        "name": "预约成功通知",
        "message_type": "appointment",
        "title_template": "预约成功提醒",
        "content_template": "您已成功预约{doctor_name}医生，就诊时间：{date} {time_slot}，请提前到院签到。",
        "description": "患者预约成功后发送"
    },
    {
        "code": "appointment_cancel",
        "name": "预约取消通知",
        "message_type": "appointment",
        "title_template": "预约取消通知",
        "content_template": "您{date}的预约已取消，如需就诊请重新预约。",
        "description": "患者取消预约后发送"
    },
    {
        "code": "appointment_reminder",
        "name": "就诊提醒",
        "message_type": "consultation",
        "title_template": "就诊提醒",
        "content_template": "温馨提醒：您预约的{doctor_name}医生将于明天{time_slot}出诊，请准时到院。",
        "description": "就诊前一天发送"
    },
    {
        "code": "sign_in_success",
        "name": "签到成功通知",
        "message_type": "consultation",
        "title_template": "签到成功",
        "content_template": "签到成功！您的排队号为{queue_number}号，前面还有{waiting_count}人，请耐心等候。",
        "description": "患者签到成功后发送"
    },
    {
        "code": "call_patient",
        "name": "叫号通知",
        "message_type": "consultation",
        "title_template": "请您就诊",
        "content_template": "请{patient_name}到{room}就诊，{doctor_name}医生正在等候您。",
        "description": "叫号时发送"
    },
    {
        "code": "stop_clinic_patient",
        "name": "停诊通知-患者",
        "message_type": "stop_clinic",
        "title_template": "停诊通知",
        "content_template": "非常抱歉，{doctor_name}医生{date}{time_slot}临时停诊，您的预约已自动取消，请重新预约其他时间。",
        "description": "医生停诊时通知患者"
    },
    {
        "code": "stop_clinic_approved",
        "name": "停诊申请通过",
        "message_type": "schedule",
        "title_template": "停诊申请已通过",
        "content_template": "您{date}{time_slot}的停诊申请已通过审核，系统已自动通知相关患者。",
        "description": "停诊申请通过时通知医生"
    },
    {
        "code": "stop_clinic_rejected",
        "name": "停诊申请拒绝",
        "message_type": "schedule",
        "title_template": "停诊申请被拒绝",
        "content_template": "您{date}{time_slot}的停诊申请未通过审核，原因：{reason}。请按原计划出诊。",
        "description": "停诊申请拒绝时通知医生"
    },
    {
        "code": "schedule_change_approved",
        "name": "调班申请通过",
        "message_type": "schedule",
        "title_template": "调班申请已通过",
        "content_template": "您的调班申请已通过，出诊时间已从{original_date}{original_period}调整为{target_date}{target_period}。",
        "description": "调班申请通过时通知医生"
    },
    {
        "code": "feedback_reply",
        "name": "反馈回复通知",
        "message_type": "system",
        "title_template": "您的反馈已回复",
        "content_template": "您提交的反馈「{title}」已收到回复，请查看详情。",
        "description": "反馈回复时通知用户"
    },
]


async def init_templates():
    """初始化消息模板"""
    from app.core.config import settings
    
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        for template_data in MESSAGE_TEMPLATES:
            # 检查是否已存在
            from sqlalchemy import select
            from app.models.message import MessageTemplate
            
            result = await session.execute(
                select(MessageTemplate).where(MessageTemplate.code == template_data["code"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                template = MessageTemplate(
                    id=str(uuid.uuid4()),
                    **template_data
                )
                session.add(template)
                print(f"添加模板: {template_data['name']}")
            else:
                print(f"模板已存在: {template_data['name']}")
        
        await session.commit()
    
    print("消息模板初始化完成")


if __name__ == "__main__":
    asyncio.run(init_templates())
