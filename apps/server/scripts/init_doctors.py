"""初始化测试医生数据"""
import asyncio
import sys
import uuid
sys.path.insert(0, '/Users/leijiadashao/leitond/appointment-booking-system/apps/server')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import bcrypt

from app.core.config import settings as app_settings
from app.models.doctor import Doctor
from app.models.department import Department


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


async def init_doctors():
    """初始化测试医生"""
    engine = create_async_engine(app_settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # 获取科室
        result = await session.execute(select(Department).where(Department.name == "内科"))
        neike = result.scalar_one_or_none()
        
        result = await session.execute(select(Department).where(Department.name == "外科"))
        waike = result.scalar_one_or_none()
        
        if not neike or not waike:
            print("请先初始化科室数据")
            return
        
        doctors_data = [
            {
                "name": "张医生",
                "phone": "13900000001",
                "password": "doctor123",
                "department_id": neike.id,
                "title": "主任医师",
                "specialty": "心血管疾病、高血压、冠心病",
                "introduction": "从医30年，擅长心血管疾病诊治",
                "is_recommended": 1,
            },
            {
                "name": "李医生",
                "phone": "13900000002",
                "password": "doctor123",
                "department_id": neike.id,
                "title": "副主任医师",
                "specialty": "呼吸系统疾病、肺炎、哮喘",
                "introduction": "呼吸内科专家，擅长各类呼吸系统疾病",
                "is_recommended": 1,
            },
            {
                "name": "王医生",
                "phone": "13900000003",
                "password": "doctor123",
                "department_id": waike.id,
                "title": "主任医师",
                "specialty": "普外科手术、腹腔镜微创手术",
                "introduction": "外科专家，擅长微创手术",
                "is_recommended": 1,
            },
        ]
        
        for doc_data in doctors_data:
            result = await session.execute(select(Doctor).where(Doctor.phone == doc_data["phone"]))
            if not result.scalar_one_or_none():
                doctor = Doctor(
                    id=str(uuid.uuid4()),
                    name=doc_data["name"],
                    phone=doc_data["phone"],
                    password_hash=hash_password(doc_data["password"]),
                    department_id=doc_data["department_id"],
                    title=doc_data["title"],
                    specialty=doc_data["specialty"],
                    introduction=doc_data["introduction"],
                    is_recommended=doc_data["is_recommended"],
                    status=1
                )
                session.add(doctor)
                print(f"✓ 创建医生：{doc_data['name']} ({doc_data['phone']} / {doc_data['password']})")
        
        await session.commit()
        print("\n✅ 测试医生初始化完成!")
        print("\n医生登录信息:")
        print("  医生端: http://localhost:8003")
        print("  手机号: 13900000001 / 13900000002 / 13900000003")
        print("  密码: doctor123")


if __name__ == "__main__":
    asyncio.run(init_doctors())
