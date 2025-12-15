"""初始化基础数据"""
import asyncio
import sys
import uuid
sys.path.insert(0, '/Users/leijiadashao/leitond/appointment-booking-system/apps/server')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import hashlib

from app.core.config import settings as app_settings
from app.models.admin import Admin, Role
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.store import Store
from app.models.message import MessageTemplate


def hash_password(password: str) -> str:
    """简单的密码哈希（生产环境应使用 bcrypt）"""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


async def init_data():
    """初始化基础数据"""
    engine = create_async_engine(app_settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 1. 创建超级管理员角色
        result = await session.execute(select(Role).where(Role.code == "SUPER_ADMIN"))
        if not result.scalar_one_or_none():
            super_role = Role(
                id=str(uuid.uuid4()),
                name="超级管理员",
                code="SUPER_ADMIN",
                description="系统超级管理员，拥有所有权限",
                permissions='["*"]',
                status=1
            )
            session.add(super_role)
            print("✓ 创建超级管理员角色")
        
        # 2. 创建管理员账号
        result = await session.execute(select(Admin).where(Admin.username == "admin"))
        if not result.scalar_one_or_none():
            admin = Admin(
                id=str(uuid.uuid4()),
                username="admin",
                password_hash=hash_password("admin123"),
                name="系统管理员",
                phone="13800000000",
                email="admin@hospital.com",
                role_id=(await session.execute(select(Role.id).where(Role.code == "SUPER_ADMIN"))).scalar(),
                status=1
            )
            session.add(admin)
            print("✓ 创建管理员账号 (admin / admin123)")
        
        # 3. 创建门店
        result = await session.execute(select(Store).where(Store.code == "main"))
        if not result.scalar_one_or_none():
            store = Store(
                id=str(uuid.uuid4()),
                name="总院",
                code="main",
                address="北京市朝阳区XX路XX号",
                phone="010-12345678",
                business_hours="08:00-17:30",
                description="医院总院区",
                status=1,
                sort_order=1
            )
            session.add(store)
            print("✓ 创建门店：总院")
        
        # 4. 创建科室
        departments_data = [
            {"name": "内科", "description": "内科诊疗", "sort_order": 1},
            {"name": "外科", "description": "外科诊疗", "sort_order": 2},
            {"name": "儿科", "description": "儿童疾病诊疗", "sort_order": 3},
            {"name": "妇产科", "description": "妇产科诊疗", "sort_order": 4},
            {"name": "眼科", "description": "眼科诊疗", "sort_order": 5},
            {"name": "口腔科", "description": "口腔诊疗", "sort_order": 6},
            {"name": "皮肤科", "description": "皮肤病诊疗", "sort_order": 7},
            {"name": "中医科", "description": "中医诊疗", "sort_order": 8},
        ]
        
        for dept_data in departments_data:
            result = await session.execute(select(Department).where(Department.name == dept_data["name"]))
            if not result.scalar_one_or_none():
                dept = Department(
                    id=str(uuid.uuid4()),
                    **dept_data,
                    status=1
                )
                session.add(dept)
                print(f"✓ 创建科室：{dept_data['name']}")
        
        # 5. 创建消息模板
        templates_data = [
            {
                "code": "appointment_success",
                "name": "预约成功通知",
                "message_type": "appointment",
                "title_template": "预约成功提醒",
                "content_template": "您已成功预约{doctor_name}医生，就诊时间：{date} {time_slot}，请提前到院签到。",
            },
            {
                "code": "sign_in_success",
                "name": "签到成功通知",
                "message_type": "consultation",
                "title_template": "签到成功",
                "content_template": "签到成功！您的排队号为{queue_number}号，前面还有{waiting_count}人，请耐心等候。",
            },
            {
                "code": "call_patient",
                "name": "叫号通知",
                "message_type": "consultation",
                "title_template": "请您就诊",
                "content_template": "请{patient_name}到{room}就诊，{doctor_name}医生正在等候您。",
            },
        ]
        
        for tpl_data in templates_data:
            result = await session.execute(select(MessageTemplate).where(MessageTemplate.code == tpl_data["code"]))
            if not result.scalar_one_or_none():
                tpl = MessageTemplate(
                    id=str(uuid.uuid4()),
                    **tpl_data,
                    status=1
                )
                session.add(tpl)
                print(f"✓ 创建消息模板：{tpl_data['name']}")
        
        await session.commit()
        print("\n✅ 基础数据初始化完成!")
        print("\n登录信息:")
        print("  机构端: http://localhost:8001")
        print("  用户名: admin")
        print("  密码: admin123")


if __name__ == "__main__":
    asyncio.run(init_data())
