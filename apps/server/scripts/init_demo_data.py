"""初始化演示数据"""
import asyncio
import sys
import uuid
import os
from datetime import datetime, date

# 添加项目根目录到 python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert, and_
import bcrypt

from app.core.config import settings as app_settings
from app.models.admin import Admin, Role, admin_stores
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.store import Store
from app.models.user import User, Patient
from app.models.message import MessageTemplate

def hash_password(password: str) -> str:
    """简单的密码哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

async def init_demo_data():
    """初始化全套演示数据"""
    print("🚀 开始初始化演示数据...")
    engine = create_async_engine(app_settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # -------------------------------------------
        # 1. 角色初始化
        # -------------------------------------------
        roles = {
            "SUPER_ADMIN": {
                "name": "超级管理员",
                "description": "系统超级管理员，拥有所有权限",
                "permissions": '["*"]'
            },
            "STORE_ADMIN": {
                "name": "门店管理员",
                "description": "门店管理员，管理所属门店",
                "permissions": '["store:view", "department:list", "doctor:list", "schedule:list", "appointment:list", "order:list"]' 
            }
        }
        
        roles_map = {}
        for code, data in roles.items():
            result = await session.execute(select(Role).where(Role.code == code))
            role = result.scalar_one_or_none()
            if not role:
                role = Role(
                    id=str(uuid.uuid4()),
                    name=data["name"],
                    code=code,
                    description=data["description"],
                    permissions=data["permissions"],
                    status=1
                )
                session.add(role)
                print(f"✓ 创建角色: {data['name']}")
            else:
                roles_map[code] = role
        
        await session.flush()
        if not roles_map:
             for code in roles.keys():
                result = await session.execute(select(Role).where(Role.code == code))
                roles_map[code] = result.scalar_one()

        # -------------------------------------------
        # 2. 门店初始化
        # -------------------------------------------
        stores_list = [
            {
                "name": "总院",
                "code": "main",
                "address": "北京市朝阳区演示路88号",
                "phone": "010-88888888",
                "business_hours": "08:00-17:30",
                "description": "中心医院总院区，设备先进，专家云集。",
                "sort_order": 1
            },
            {
                "name": "西城分院",
                "code": "branch_west",
                "address": "北京市西城区西单路66号",
                "phone": "010-66666666",
                "business_hours": "09:00-18:00",
                "description": "专注社区医疗服务。",
                "sort_order": 2
            }
        ]
        
        store_map = {}
        for s_data in stores_list:
            result = await session.execute(select(Store).where(Store.code == s_data["code"]))
            store = result.scalar_one_or_none()
            if not store:
                store = Store(
                    id=str(uuid.uuid4()),
                    **s_data,
                    status=1
                )
                session.add(store)
                print(f"✓ 创建门店: {s_data['name']}")
            store_map[s_data["code"]] = store
            
        await session.flush()
        # 重新获取 flush 后的对象，以防 ID 为空
        for code, store_obj in store_map.items():
            if not store_obj.id: 
                 res = await session.execute(select(Store).where(Store.code == code))
                 store_map[code] = res.scalar_one()

        main_store = store_map["main"]
        branch_store = store_map["branch_west"]

        # -------------------------------------------
        # 3. 管理员初始化
        # -------------------------------------------
        # 3.1 超级管理员
        result = await session.execute(select(Admin).where(Admin.username == "admin"))
        if not result.scalar_one_or_none():
            admin = Admin(
                id=str(uuid.uuid4()),
                username="admin",
                password_hash=hash_password("admin123"),
                name="系统管理员",
                phone="13800000000",
                email="admin@hospital.com",
                role_id=roles_map["SUPER_ADMIN"].id,
                status=1
            )
            session.add(admin)
            print("✓ 创建超级管理员: admin / admin123")

        # 3.2 门店管理员 (总院)
        result = await session.execute(select(Admin).where(Admin.username == "manager"))
        if not result.scalar_one_or_none():
            manager = Admin(
                id=str(uuid.uuid4()),
                username="manager",
                password_hash=hash_password("manager123"),
                name="总院经理",
                phone="13800000001",
                email="manager@hospital.com",
                role_id=roles_map["STORE_ADMIN"].id,
                current_store_id=main_store.id,
                status=1
            )
            session.add(manager)
            await session.flush()
            stmt = insert(admin_stores).values(
                admin_id=manager.id,
                store_id=main_store.id,
                is_manager=1,
                created_at=datetime.utcnow()
            )
            await session.execute(stmt)
            print("✓ 创建门店管理员: manager / manager123")

        # 3.3 分院管理员
        result = await session.execute(select(Admin).where(Admin.username == "manager_west"))
        if not result.scalar_one_or_none():
            manager_west = Admin(
                id=str(uuid.uuid4()),
                username="manager_west",
                password_hash=hash_password("manager123"),
                name="西城分院经理",
                phone="13800000002",
                email="west@hospital.com",
                role_id=roles_map["STORE_ADMIN"].id,
                current_store_id=branch_store.id,
                status=1
            )
            session.add(manager_west)
            await session.flush()
            stmt = insert(admin_stores).values(
                admin_id=manager_west.id,
                store_id=branch_store.id,
                is_manager=1,
                created_at=datetime.utcnow()
            )
            await session.execute(stmt)
            print("✓ 创建分院管理员: manager_west / manager123")

        # -------------------------------------------
        # 4. 科室初始化
        # -------------------------------------------
        departments_config = {
            "main": [
                {"name": "内科", "description": "常见内科疾病诊疗", "sort_order": 1},
                {"name": "外科", "description": "各类外科手术", "sort_order": 2},
                {"name": "儿科", "description": "儿童常见病预防与治疗", "sort_order": 3},
                {"name": "妇产科", "description": "妇科与产科专业诊疗", "sort_order": 4},
                {"name": "口腔科", "description": "牙齿健康护理", "sort_order": 5},
                {"name": "中医科", "description": "传统中医理疗", "sort_order": 6},
                {"name": "眼科", "description": "视力矫正与眼病治疗", "sort_order": 7},
            ],
            "branch_west": [
                {"name": "综合内科", "description": "社区常见病", "sort_order": 1},
                {"name": "外伤处置", "description": "简单外伤处理", "sort_order": 2},
                {"name": "中医理疗", "description": "推拿针灸", "sort_order": 3},
            ]
        }
        
        dept_map = {} # key: store_code:dept_name -> value: dept_obj

        for store_code, depts in departments_config.items():
            current_store = store_map[store_code]
            for dept_data in depts:
                result = await session.execute(select(Department).where(
                    and_(Department.name == dept_data["name"], Department.store_id == current_store.id)
                ))
                dept = result.scalar_one_or_none()
                if not dept:
                    dept = Department(
                        id=str(uuid.uuid4()),
                        store_id=current_store.id,
                        **dept_data,
                        status=1,
                        is_hot=1 if dept_data["sort_order"] <= 3 else 0
                    )
                    session.add(dept)
                    print(f"✓ 创建科室({store_code}): {dept_data['name']}")
                dept_map[f"{store_code}:{dept_data['name']}"] = dept
            
        await session.flush()
        # Refresh IDs
        for key, dept_obj in dept_map.items():
            if not dept_obj.id:
                 store_code, dept_name = key.split(":")
                 res = await session.execute(select(Department).where(
                    and_(Department.name == dept_name, Department.store_id == store_map[store_code].id)
                ))
                 dept_map[key] = res.scalar_one()

        # -------------------------------------------
        # 5. 医生初始化
        # -------------------------------------------
        doctors_list = [
            # 总院
            {"name": "张主任", "phone": "13911110001", "store": "main", "dept": "内科", "title": "主任医师", "fee": 100.00, "spec": "心血管、高血压"},
            {"name": "李医师", "phone": "13911110002", "store": "main", "dept": "内科", "title": "主治医师", "fee": 50.00, "spec": "呼吸道感染、哮喘"},
            {"name": "王一刀", "phone": "13911110003", "store": "main", "dept": "外科", "title": "副主任医师", "fee": 80.00, "spec": "微创手术、普外"},
            {"name": "赵儿科", "phone": "13911110004", "store": "main", "dept": "儿科", "title": "主任医师", "fee": 60.00, "spec": "小儿感冒、发烧"},
            {"name": "孙眼科", "phone": "13911110005", "store": "main", "dept": "眼科", "title": "副主任医师", "fee": 70.00, "spec": "近视矫正、白内障"},
            {"name": "周中医", "phone": "13911110006", "store": "main", "dept": "中医科", "title": "主任医师", "fee": 120.00, "spec": "中医调理、针灸"},
            
            # 总院新增
            {"name": "钱妇产", "phone": "13911110007", "store": "main", "dept": "妇产科", "title": "主任医师", "fee": 90.00, "spec": "产前检查、妇科病"},
            {"name": "孙牙医", "phone": "13911110008", "store": "main", "dept": "口腔科", "title": "主治医师", "fee": 60.00, "spec": "牙齿矫正、种植牙"},
            {"name": "刘内科", "phone": "13911110009", "store": "main", "dept": "内科", "title": "医师", "fee": 30.00, "spec": "消化系统、胃炎"},
            {"name": "陈外科", "phone": "13911110010", "store": "main", "dept": "外科", "title": "医师", "fee": 40.00, "spec": "骨折处理、外伤"},
            {"name": "林儿科", "phone": "13911110011", "store": "main", "dept": "儿科", "title": "主治医师", "fee": 50.00, "spec": "儿童营养、发育"},
            {"name": "郑口腔", "phone": "13911110012", "store": "main", "dept": "口腔科", "title": "副主任医师", "fee": 80.00, "spec": "根管治疗、拔牙"},

            # 分院
            {"name": "吴全科", "phone": "13922220001", "store": "branch_west", "dept": "综合内科", "title": "主治医师", "fee": 40.00, "spec": "高血压糖尿病"},
            {"name": "郑外伤", "phone": "13922220002", "store": "branch_west", "dept": "外伤处置", "title": "医师", "fee": 30.00, "spec": "清创缝合"},
            
            # 分院新增
            {"name": "冯理疗", "phone": "13922220003", "store": "branch_west", "dept": "中医理疗", "title": "技师", "fee": 50.00, "spec": "推拿、拔罐"},
            {"name": "褚全科", "phone": "13922220004", "store": "branch_west", "dept": "综合内科", "title": "医师", "fee": 20.00, "spec": "社区常见病、感冒"},
            {"name": "卫针灸", "phone": "13922220005", "store": "branch_west", "dept": "中医理疗", "title": "医师", "fee": 60.00, "spec": "针灸治疗、颈椎病"}
        ]
        
        for doc_data in doctors_list:
            result = await session.execute(select(Doctor).where(Doctor.phone == doc_data["phone"]))
            if not result.scalar_one_or_none():
                dept_key = f"{doc_data['store']}:{doc_data['dept']}"
                dept = dept_map.get(dept_key)
                if not dept:
                    print(f"⚠️ 找不到科室: {dept_key}，跳过医生 {doc_data['name']}")
                    continue

                doctor = Doctor(
                    id=str(uuid.uuid4()),
                    name=doc_data["name"],
                    username=doc_data["phone"],
                    phone=doc_data["phone"],
                    password_hash=hash_password("doctor123"),
                    store_id=store_map[doc_data["store"]].id,
                    department_id=dept.id,
                    title=doc_data["title"],
                    specialty=doc_data["spec"],
                    introduction=f"擅长{doc_data['spec']}",
                    registration_fee=doc_data["fee"],
                    is_recommended=1,
                    status=1,
                    gender=1
                )
                session.add(doctor)
                print(f"✓ 创建医生: {doc_data['name']} ({doc_data['store']})")

        # -------------------------------------------
        # 6. 用户与就诊人初始化
        # -------------------------------------------
        users_data = [
            {"phone": "13500000001", "nickname": "测试用户A", "patient_name": "张三", "relation": "本人"},
            {"phone": "13500000002", "nickname": "测试用户B", "patient_name": "李四", "relation": "本人"},
            {"phone": "13500000003", "nickname": "测试用户C", "patient_name": "王五", "relation": "本人"},
        ]
        
        for u_data in users_data:
            result = await session.execute(select(User).where(User.phone == u_data["phone"]))
            user = result.scalar_one_or_none()
            if not user:
                user = User(
                    id=str(uuid.uuid4()),
                    phone=u_data["phone"],
                    password_hash=hash_password("user123"),
                    nickname=u_data["nickname"],
                    status=1
                )
                session.add(user)
                await session.flush()
                print(f"✓ 创建用户: {u_data['nickname']}")
                
                patient = Patient(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    store_id=main_store.id,
                    name=u_data["patient_name"],
                    phone=u_data["phone"],
                    gender=1,
                    age=30,
                    relationship=u_data["relation"],
                    is_default=True,
                    card_no=f"P{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:4]}",
                    source=2
                )
                session.add(patient)

        # -------------------------------------------
        # 7. 消息模板
        # -------------------------------------------
        templates_data = [
            {
                "code": "appointment_success",
                "name": "预约成功通知",
                "message_type": "appointment",
                "title_template": "预约成功提醒",
                "content_template": "您已成功预约{doctor_name}医生，就诊时间：{date} {time_slot}，请提前到院签到。",
            }
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
                print(f"✓ 创建消息模板: {tpl_data['name']}")

        await session.commit()
        
        print("\n✅ 演示数据初始化完成!")
        print("-----------------------------------")
        print("后台管理: http://localhost:8001")
        print("  - 超级管理员: admin / admin123")
        print("  - 总院管理员: manager / manager123")
        print("  - 分院管理员: manager_west / manager123")
        print("\n医生端: http://localhost:8003")
        print("  - 密码均为: doctor123")
        print("  - 总院示例: 13911110007 (钱妇产), 13911110008 (孙牙医)")
        print("  - 分院示例: 13922220003 (冯理疗), 13922220005 (卫针灸)")
        print("-----------------------------------")

if __name__ == "__main__":
    try:
        asyncio.run(init_demo_data())
    except Exception as e:
        print(f"\n❌ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
