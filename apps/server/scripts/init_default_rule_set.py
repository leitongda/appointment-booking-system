"""
初始化默认规则组

创建基础规则组，定义预约和签到的时间窗口规则：
- 预约必须在班次开始时间之前
- 签到必须在班次结束时间之前
"""
import asyncio
import sys
import uuid

sys.path.insert(0, '/Users/leijiadashao/leitond/appointment-booking-system/apps/server')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.core.config import settings as app_settings
from app.models.rule_set import (
    RuleSet, RuleSetShiftType, RuleWindow,
    RuleBookingPolicy, RuleCheckinPolicy, RuleCapacityPolicy, ShiftType
)
from app.utils.audit import set_create_audit


async def init_default_rule_set():
    """初始化默认规则组"""
    engine = create_async_engine(app_settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. 创建班次类型（如果不存在）
        shift_types_data = [
            {"code": "OPD", "name": "门诊", "description": "普通门诊班次"},
            {"code": "CHECKUP", "name": "体检", "description": "体检班次"},
            {"code": "EXAM", "name": "检查", "description": "检查项目班次"},
            {"code": "NURSING", "name": "护理", "description": "护理班次"},
            {"code": "SPECIAL", "name": "专科", "description": "专科门诊班次"},
        ]

        shift_type_ids = []
        for st_data in shift_types_data:
            result = await session.execute(
                select(ShiftType).where(ShiftType.code == st_data["code"])
            )
            shift_type = result.scalar_one_or_none()
            if not shift_type:
                shift_type = ShiftType(
                    id=str(uuid.uuid4()),
                    **st_data,
                    enabled=True
                )
                set_create_audit(shift_type)
                session.add(shift_type)
                await session.flush()
                print(f"✓ 创建班次类型：{st_data['name']}")
            shift_type_ids.append(shift_type.id)

        # 2. 检查默认规则组是否已存在
        result = await session.execute(
            select(RuleSet).where(RuleSet.name == "默认规则组")
        )
        existing_rule_set = result.scalar_one_or_none()

        if existing_rule_set:
            print(f"\n⚠️ 默认规则组已存在 (ID: {existing_rule_set.id})")
            print("如需重新创建，请先删除现有规则组")
            return

        # 3. 创建规则组
        rule_set = RuleSet(
            id=str(uuid.uuid4()),
            name="默认规则组",
            enabled=True,
            priority=100,
            time_source="SERVER",
            timezone_source="HOSPITAL",
            compare_precision="SECOND",
            default_open_inclusive=True,
            default_close_inclusive=False,
            rounding_mode="NONE",
            clock_skew_tolerance_sec=5,
            description="默认规则组：预约必须在开始时间之前，签到必须在结束时间之前"
        )
        set_create_audit(rule_set)
        session.add(rule_set)
        await session.flush()
        print(f"\n✓ 创建规则组：{rule_set.name} (ID: {rule_set.id})")

        # 4. 关联班次类型
        for shift_type_id in shift_type_ids:
            rs_st = RuleSetShiftType(
                rule_set_id=rule_set.id,
                shift_type_id=shift_type_id
            )
            session.add(rs_st)
        print(f"✓ 关联 {len(shift_type_ids)} 个班次类型")

        # 5. 创建预约时间窗
        # 预约必须在班次开始时间之前
        book_window = RuleWindow(
            id=str(uuid.uuid4()),
            rule_set_id=rule_set.id,
            action="BOOK",
            reference_point="SHIFT_START",
            open_offset_sec=-86400,  # 提前1天开放
            close_offset_sec=0,       # 在开始时间时关闭（不包含）
            open_inclusive=True,
            close_inclusive=False,
            fail_policy="REJECT",
            enabled=True,
            description="预约窗口：班次开始前1天开放，开始时关闭"
        )
        set_create_audit(book_window)
        session.add(book_window)
        print("✓ 创建预约时间窗：必须在班次开始时间之前预约")

        # 6. 创建签到时间窗
        # 签到必须在班次结束时间之前
        checkin_window = RuleWindow(
            id=str(uuid.uuid4()),
            rule_set_id=rule_set.id,
            action="CHECKIN",
            reference_point="SHIFT_END",
            open_offset_sec=-3600,    # 班次开始后1小时开放
            close_offset_sec=0,       # 在结束时间时关闭（不包含）
            open_inclusive=True,
            close_inclusive=False,
            fail_policy="REJECT",
            enabled=True,
            description="签到窗口：班次结束前都可以签到"
        )
        set_create_audit(checkin_window)
        session.add(checkin_window)
        print("✓ 创建签到时间窗：必须在班次结束时间之前签到")

        # 7. 创建取消时间窗
        cancel_window = RuleWindow(
            id=str(uuid.uuid4()),
            rule_set_id=rule_set.id,
            action="CANCEL",
            reference_point="SHIFT_START",
            open_offset_sec=-86400,  # 提前1天开放
            close_offset_sec=-1800,  # 开始前30分钟关闭
            open_inclusive=True,
            close_inclusive=True,
            fail_policy="REJECT",
            enabled=True,
            description="取消窗口：班次开始前30分钟可以取消"
        )
        set_create_audit(cancel_window)
        session.add(cancel_window)
        print("✓ 创建取消时间窗：班次开始前30分钟可以取消")

        # 8. 创建预约策略
        booking_policy = RuleBookingPolicy(
            rule_set_id=rule_set.id,
            require_auth=True,
            require_patient_profile_complete=True,
            per_user_per_shift=1,
            per_user_per_day=3,
            per_user_per_week=10,
            conflict_same_shift="REJECT",
            conflict_overlap_time="REJECT",
            conflict_same_type_same_day="ALLOW"
        )
        set_create_audit(booking_policy)
        session.add(booking_policy)
        print("✓ 创建预约策略：每用户每班次1次，每天3次，每周10次")

        # 9. 创建签到策略
        checkin_policy = RuleCheckinPolicy(
            rule_set_id=rule_set.id,
            require_booking=True,
            allow_onsite_booking=False,
            max_times=1,
            audit_log=True,
            grace_period_sec=900,     # 15分钟宽限期
            after_grace_status="LATE",
            no_checkin_after_close="KEEP_BOOKED"
        )
        set_create_audit(checkin_policy)
        session.add(checkin_policy)
        print("✓ 创建签到策略：必须预约，15分钟宽限期，记录审计日志")

        # 10. 创建容量策略
        capacity_policy = RuleCapacityPolicy(
            rule_set_id=rule_set.id,
            total_capacity=50,
            per_user_capacity=1,
            waitlist_enabled=True,
            waitlist_max_size=10,
            waitlist_promote_policy="MANUAL",
            overbooking_enabled=False,
            overbooking_max=0
        )
        set_create_audit(capacity_policy)
        session.add(capacity_policy)
        print("✓ 创建容量策略：总容量50，启用候补队列")

        await session.commit()
        print("\n✅ 默认规则组初始化完成!")
        print(f"\n规则组 ID: {rule_set.id}")
        print(f"规则组名称: {rule_set.name}")
        print(f"关联班次类型: {len(shift_type_ids)} 个")
        print(f"时间窗: 3 个（预约、签到、取消）")
        print(f"策略: 3 个（预约、签到、容量）")


if __name__ == "__main__":
    asyncio.run(init_default_rule_set())
