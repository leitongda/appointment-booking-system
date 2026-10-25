#!/usr/bin/env python3
"""本地演示种子数据（仅本地测试用，不属于产品代码）。

向 DATABASE_URL 指向的库写入：租户/角色/管理员/门店/科室/医生/排班/首页公告。
用法（在 apps/server 下）：
  DATABASE_URL=postgresql+asyncpg://hospital:hospital123@localhost:5432/hospital_booking_tcm \
    python3 scripts/seed_local_demo.py
幂等：按 tenant_code / username / 名称判断跳过已存在数据。
"""
import asyncio
import os
import sys
from datetime import date, datetime, time, timedelta
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.models.admin import Admin, Role  # noqa: E402
from app.models.content import Banner  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.doctor import Doctor  # noqa: E402
from app.models.schedule import Schedule  # noqa: E402
from app.models.store import Store  # noqa: E402
from app.models.tenant import SubscriptionPlan, Tenant  # noqa: E402

TENANT_CODE = "tcm-demo"
ADMIN_USERNAME = "tcmadmin"
ADMIN_PASSWORD = "tcm123456"


async def main() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        # 租户
        plan = (await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.plan_code == "demo_plan"))).scalar_one_or_none()
        if plan is None:
            plan = SubscriptionPlan(id=str(uuid4()), plan_code="demo_plan", name="演示计划", status=1,
                                    created_at=datetime.now(), updated_at=datetime.now())
            db.add(plan)
            await db.flush()
        tenant = (await db.execute(select(Tenant).where(Tenant.tenant_code == TENANT_CODE))).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(id=str(uuid4()), tenant_code=TENANT_CODE, name="重庆颐草堂中医馆（本地演示）",
                            status=1, subscription_plan_id=plan.id,
                            created_at=datetime.now(), updated_at=datetime.now())
            db.add(tenant)
            await db.flush()
        print(f"tenant: {tenant.id} ({tenant.tenant_code})")

        # 角色与管理员（机构端登录用）
        role = (await db.execute(select(Role).where(Role.tenant_id == tenant.id, Role.code == "SUPER_ADMIN"))).scalar_one_or_none()
        if role is None:
            role = Role(id=str(uuid4()), name="机构管理员", code="SUPER_ADMIN", description="本地演示机构管理员",
                        tenant_id=tenant.id, status=1, permissions="[]",
                        created_at=datetime.now(), updated_at=datetime.now())
            db.add(role)
            await db.flush()

        # 门店（先建，管理员要挂 current_store_id）
        store = (await db.execute(select(Store).where(Store.tenant_id == tenant.id, Store.name.like("颐草堂%")))).scalar_one_or_none()
        if store is None:
            store = Store(id=str(uuid4()), name="颐草堂中医馆（巴南店）",
                          address="重庆市巴南区巴县大道57号附27号（本地演示）", phone="023-68888888",
                          latitude=29.382084, longitude=106.521194,
                          description="颐草堂中医诊所秉持「聚百草，传好方，承古法」的经营理念，汇聚名医大家。"
                                      "（本地演示数据，非真实机构信息）",
                          tenant_id=tenant.id, status=1, code="BA-NAN",
                          created_at=datetime.now(), updated_at=datetime.now())
            db.add(store)
            await db.flush()
        print(f"store: {store.id}")

        admin = (await db.execute(select(Admin).where(Admin.username == ADMIN_USERNAME))).scalar_one_or_none()
        if admin is None:
            admin = Admin(id=str(uuid4()), username=ADMIN_USERNAME,
                          password_hash=bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode(),
                          name="演示管理员", phone="13800000001", role_id=role.id,
                          current_store_id=store.id, tenant_id=tenant.id, status=1,
                          created_at=datetime.now(), updated_at=datetime.now())
            db.add(admin)
            print(f"admin created: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
        else:
            print(f"admin exists: {ADMIN_USERNAME}")

        # 科室
        dept_specs = [("中医科", "内科"), ("针灸推拿科", "推")]
        depts = {}
        for name, _kw in dept_specs:
            dept = (await db.execute(select(Department).where(Department.tenant_id == tenant.id, Department.name == name))).scalar_one_or_none()
            if dept is None:
                dept = Department(id=str(uuid4()), name=name, store_id=store.id, tenant_id=tenant.id, status=1,
                                  is_hot=1,
                                  created_at=datetime.now(), updated_at=datetime.now())
                db.add(dept)
                await db.flush()
            elif not dept.is_hot:
                dept.is_hot = 1  # 患者端科室列表走公开 /departments/hot（is_hot 过滤）
            depts[name] = dept
            print(f"department: {name}")

        # 医生
        doctor_specs = [
            ("罗医师（演示）", "资深中医师", "中医科", "妇科、备孕指导、内分泌调理、脾胃、失眠",
             "从业中医临床三十余年，医学功底系统扎实。师承多位民间名老中医，博采众长，"
             "熟练运用特色古法疗法，辨证调治各类急慢性疾患。（本地演示数据）"),
            ("赵医师（演示）", "主任医师", "针灸推拿科", "颈肩腰腿痛、中风康复、小儿推拿",
             "从事针灸推拿临床工作二十余年，擅长将传统针灸与现代康复理念结合。（本地演示数据）"),
        ]
        doctors = []
        for name, title, dept_name, specialty, introduction in doctor_specs:
            doctor = (await db.execute(select(Doctor).where(Doctor.tenant_id == tenant.id, Doctor.name == name))).scalar_one_or_none()
            if doctor is None:
                doctor = Doctor(id=str(uuid4()), name=name, title=title,
                                department_id=depts[dept_name].id, store_id=store.id, tenant_id=tenant.id,
                                specialty=specialty, introduction=introduction, status=1,
                                created_at=datetime.now(), updated_at=datetime.now())
                db.add(doctor)
                await db.flush()
            doctors.append(doctor)
            print(f"doctor: {name}")

        # 排班：今天+明天 上午/下午，号源充足（保证首页「有号」角标与预约流程可用）
        today = date.today()
        created = 0
        for doctor in doctors:
            for offset in (0, 1):
                for slot, (sh, eh) in (("morning", (8, 12)), ("afternoon", (14, 18))):
                    day = today + timedelta(days=offset)
                    exists = (await db.execute(select(Schedule).where(
                        Schedule.doctor_id == doctor.id, Schedule.schedule_date == day,
                        Schedule.time_slot == slot))).scalar_one_or_none()
                    if exists:
                        continue
                    db.add(Schedule(id=str(uuid4()), doctor_id=doctor.id, store_id=store.id,
                                    tenant_id=tenant.id, schedule_date=day, time_slot=slot,
                                    start_time=time(sh, 0), end_time=time(eh, 0),
                                    total_slots=10, booked_slots=0, status=1,
                                    created_at=datetime.now(), updated_at=datetime.now()))
                    created += 1
        print(f"schedules created: {created}")

        # 首页公告（首页公告栏回落到首条 banner 标题；Banner 模型无 tenant_id，按门店挂载）
        banner = (await db.execute(select(Banner).where(Banner.store_id == store.id, Banner.position == "home"))).scalar_one_or_none()
        if banner is None:
            db.add(Banner(id=str(uuid4()), store_id=store.id,
                          title="【预约提醒】请提前线上预约，不支持临时线下加号",
                          image_url="https://placeholder.local/cover.png", link_type=0, position="home",
                          sort_order=1, status=1, created_at=datetime.now(), updated_at=datetime.now()))
            print("banner created (home)")

        await db.commit()
    await engine.dispose()
    print("done.")


if __name__ == "__main__":
    asyncio.run(main())
