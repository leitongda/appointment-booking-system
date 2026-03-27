"""
积分服务单元测试

测试 PointService 的积分相关方法：
- adjust_points: 积分调整（增加/减少）
- get_point_logs: 积分流水查询
- get_point_summary: 积分汇总
- 边界情况处理（余额不足、用户不存在等）
"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy import select

from app.models.user import User, Patient
from app.models.point_log import PointLog
from app.models.admin import Admin
from app.modules.points.service import PointService
from app.modules.patients.service_users import UserManageService


class TestAdjustPoints:
    """测试积分调整功能"""

    @pytest.mark.asyncio
    async def test_adjust_points_increase(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """增加积分"""
        # 设置初始积分
        test_user.points = 100
        await db_session.commit()

        service = PointService(db_session)
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=50,
            remark="测试增加积分",
            operator_id="admin-1",
            log_type=4,
        )

        assert result is not None
        assert result["changeAmount"] == 50
        assert result["balance"] == 150
        assert result["currentPoints"] == 150

        # 验证用户积分已更新
        await db_session.refresh(test_user)
        assert test_user.points == 150

    @pytest.mark.asyncio
    async def test_adjust_points_decrease(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """减少积分"""
        # 设置初始积分
        test_user.points = 100
        await db_session.commit()

        service = PointService(db_session)
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=-30,
            remark="测试减少积分",
            operator_id="admin-1",
            log_type=1,  # 消费
        )

        assert result is not None
        assert result["changeAmount"] == -30
        assert result["balance"] == 70
        assert result["currentPoints"] == 70

        # 验证用户积分已更新
        await db_session.refresh(test_user)
        assert test_user.points == 70

    @pytest.mark.asyncio
    async def test_adjust_points_insufficient_balance(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """积分不足时减少积分返回 None"""
        # 设置初始积分
        test_user.points = 50
        await db_session.commit()

        service = PointService(db_session)
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=-100,  # 尝试扣除超过余额
            remark="测试积分不足",
            operator_id="admin-1",
        )

        assert result is None

        # 验证积分未变化
        await db_session.refresh(test_user)
        assert test_user.points == 50

    @pytest.mark.asyncio
    async def test_adjust_points_patient_not_found(self, db_session):
        """患者不存在时调整积分返回 None"""
        service = PointService(db_session)
        result = await service.adjust_points(
            patient_id="non-existent-id",
            amount=100,
            remark="测试",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_adjust_points_zero(self, db_session, test_user, test_patient):
        """调整积分为 0"""
        test_user.points = 100
        await db_session.commit()

        service = PointService(db_session)
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=0,
            remark="测试零积分调整",
        )

        assert result is not None
        assert result["changeAmount"] == 0
        assert result["balance"] == 100

    @pytest.mark.asyncio
    async def test_adjust_points_creates_log(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """调整积分时创建流水记录"""
        test_user.points = 100
        await db_session.commit()

        service = PointService(db_session)
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=50,
            remark="测试流水记录",
            operator_id="admin-1",
            log_type=4,
        )

        assert result is not None

        # 验证流水记录已创建
        log_query = select(PointLog).where(PointLog.user_id == test_user.id)
        logs = (await db_session.execute(log_query)).scalars().all()

        assert len(logs) >= 1
        found_log = next((log for log in logs if log.id == result["id"]), None)
        assert found_log is not None
        assert found_log.change_amount == 50
        assert found_log.balance == 150
        assert found_log.remark == "测试流水记录"
        assert found_log.type == 4

    @pytest.mark.asyncio
    async def test_adjust_points_different_types(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """不同类型的积分调整"""
        test_user.points = 100
        await db_session.commit()

        service = PointService(db_session)

        # 类型1: 消费
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=-10,
            remark="消费",
            log_type=1,
        )
        assert result is not None
        assert result["type"] == 1

        # 类型2: 充值
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=100,
            remark="充值",
            log_type=2,
        )
        assert result is not None
        assert result["type"] == 2

        # 类型3: 赠送
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=50,
            remark="赠送",
            log_type=3,
        )
        assert result is not None
        assert result["type"] == 3

        # 类型4: 手动调整
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=25,
            remark="手动调整",
            log_type=4,
        )
        assert result is not None
        assert result["type"] == 4


class TestGetPointLogs:
    """测试积分流水查询功能"""

    @pytest.mark.asyncio
    async def test_get_point_logs_empty(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """无积分流水时返回空列表"""
        service = PointService(db_session)
        items, total, current_points = await service.get_point_logs(
            patient_id=test_patient.id,
        )

        assert total == 0
        assert items == []
        assert current_points == 0

    @pytest.mark.asyncio
    async def test_get_point_logs_with_data(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """有积分流水时返回列表"""
        # 设置初始积分
        test_user.points = 150
        await db_session.commit()

        # 创建几条流水记录
        for i in range(3):
            log = PointLog(
                id=str(uuid4()),
                user_id=test_user.id,
                change_amount=50,
                balance=50 * (i + 1),
                type=4,
                remark=f"测试流水{i + 1}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(log)
        await db_session.commit()

        service = PointService(db_session)
        items, total, current_points = await service.get_point_logs(
            patient_id=test_patient.id,
        )

        assert total == 3
        assert len(items) == 3
        assert current_points == 150

        # 验证返回字段
        for item in items:
            assert "id" in item
            assert "changeAmount" in item
            assert "balance" in item
            assert "type" in item
            assert "remark" in item
            assert "createdAt" in item

    @pytest.mark.asyncio
    async def test_get_point_logs_pagination(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """积分流水分页查询"""
        # 创建 25 条流水记录
        for i in range(25):
            log = PointLog(
                id=str(uuid4()),
                user_id=test_user.id,
                change_amount=10,
                balance=10 * (i + 1),
                type=4,
                remark=f"测试流水{i + 1}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(log)
        await db_session.commit()

        service = PointService(db_session)

        # 第一页
        items_page1, total, _ = await service.get_point_logs(
            patient_id=test_patient.id,
            page=1,
            page_size=10,
        )
        assert total == 25
        assert len(items_page1) == 10

        # 第二页
        items_page2, _, _ = await service.get_point_logs(
            patient_id=test_patient.id,
            page=2,
            page_size=10,
        )
        assert len(items_page2) == 10

        # 第三页
        items_page3, _, _ = await service.get_point_logs(
            patient_id=test_patient.id,
            page=3,
            page_size=10,
        )
        assert len(items_page3) == 5

    @pytest.mark.asyncio
    async def test_get_point_logs_patient_not_found(self, db_session):
        """患者不存在时返回空列表"""
        service = PointService(db_session)
        items, total, current_points = await service.get_point_logs(
            patient_id="non-existent-id",
        )

        assert total == 0
        assert items == []
        assert current_points == 0

    @pytest.mark.asyncio
    async def test_get_point_logs_order(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """积分流水按时间倒序排列"""
        import time

        # 创建多条流水记录，确保有时间间隔
        for i in range(5):
            log = PointLog(
                id=str(uuid4()),
                user_id=test_user.id,
                change_amount=10,
                balance=10 * (i + 1),
                type=4,
                remark=f"流水{i + 1}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(log)
            await db_session.commit()
            if i < 4:
                time.sleep(0.01)  # 确保时间不同

        service = PointService(db_session)
        items, _, _ = await service.get_point_logs(
            patient_id=test_patient.id,
        )

        # 验证按时间倒序
        timestamps = [item["createdAt"] for item in items]
        assert timestamps == sorted(timestamps, reverse=True)


class TestGetPointSummary:
    """测试积分汇总功能"""

    @pytest.mark.asyncio
    async def test_get_point_summary_empty(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """无积分记录时的汇总"""
        service = PointService(db_session)
        result = await service.get_point_summary(test_patient.id)

        assert result["currentPoints"] == 0
        assert result["totalEarned"] == 0
        assert result["totalSpent"] == 0

    @pytest.mark.asyncio
    async def test_get_point_summary_with_data(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """有积分记录时的汇总"""
        # 设置当前积分
        test_user.points = 120  # 150 - 30 = 120
        await db_session.commit()

        # 创建流水记录：获得 150，消费 30
        logs = [
            PointLog(
                id=str(uuid4()),
                user_id=test_user.id,
                change_amount=100,
                balance=100,
                type=2,  # 充值
                remark="充值",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            PointLog(
                id=str(uuid4()),
                user_id=test_user.id,
                change_amount=50,
                balance=150,
                type=3,  # 赠送
                remark="赠送",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            PointLog(
                id=str(uuid4()),
                user_id=test_user.id,
                change_amount=-30,
                balance=120,
                type=1,  # 消费
                remark="消费",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        db_session.add_all(logs)
        await db_session.commit()

        service = PointService(db_session)
        result = await service.get_point_summary(test_patient.id)

        assert result["currentPoints"] == 120
        assert result["totalEarned"] == 150  # 100 + 50
        assert result["totalSpent"] == 30  # abs(-30)

    @pytest.mark.asyncio
    async def test_get_point_summary_patient_not_found(self, db_session):
        """患者不存在时返回零值汇总"""
        service = PointService(db_session)
        result = await service.get_point_summary("non-existent-id")

        assert result["currentPoints"] == 0
        assert result["totalEarned"] == 0
        assert result["totalSpent"] == 0

    @pytest.mark.asyncio
    async def test_get_point_summary_only_positive(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """只有正积分变动时的汇总"""
        test_user.points = 200
        await db_session.commit()

        # 只创建正数变动
        logs = [
            PointLog(
                id=str(uuid4()),
                user_id=test_user.id,
                change_amount=100,
                balance=100,
                type=2,
                remark="充值1",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            PointLog(
                id=str(uuid4()),
                user_id=test_user.id,
                change_amount=100,
                balance=200,
                type=2,
                remark="充值2",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        db_session.add_all(logs)
        await db_session.commit()

        service = PointService(db_session)
        result = await service.get_point_summary(test_patient.id)

        assert result["currentPoints"] == 200
        assert result["totalEarned"] == 200
        assert result["totalSpent"] == 0

    @pytest.mark.asyncio
    async def test_get_point_summary_only_negative(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """只有负积分变动时的汇总（初始有积分）"""
        test_user.points = 50  # 100 - 50 = 50
        await db_session.commit()

        # 只创建负数变动
        logs = [
            PointLog(
                id=str(uuid4()),
                user_id=test_user.id,
                change_amount=-30,
                balance=70,
                type=1,
                remark="消费1",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            PointLog(
                id=str(uuid4()),
                user_id=test_user.id,
                change_amount=-20,
                balance=50,
                type=1,
                remark="消费2",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        db_session.add_all(logs)
        await db_session.commit()

        service = PointService(db_session)
        result = await service.get_point_summary(test_patient.id)

        assert result["currentPoints"] == 50
        assert result["totalEarned"] == 0
        assert result["totalSpent"] == 50  # abs(-30) + abs(-20)


class TestUserManageServicePoints:
    """测试 UserManageService 的积分调整功能"""

    @pytest.mark.asyncio
    async def test_adjust_points_success(
        self,
        db_session,
        test_user,
    ):
        """通过 UserManageService 调整积分"""
        test_user.points = 100
        await db_session.commit()

        service = UserManageService(db_session)
        result = await service.adjust_points(
            user_id=test_user.id,
            amount=50,
            remark="管理员调整",
            operator_id="admin-1",
        )

        assert result is True

        # 验证积分已更新
        await db_session.refresh(test_user)
        assert test_user.points == 150

    @pytest.mark.asyncio
    async def test_adjust_points_user_not_found(self, db_session):
        """用户不存在时调整积分返回 False"""
        service = UserManageService(db_session)
        result = await service.adjust_points(
            user_id="non-existent-id",
            amount=50,
            remark="测试",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_adjust_points_insufficient_balance(
        self,
        db_session,
        test_user,
    ):
        """积分不足时调整抛出异常"""
        test_user.points = 50
        await db_session.commit()

        service = UserManageService(db_session)

        with pytest.raises(ValueError, match="积分不足"):
            await service.adjust_points(
                user_id=test_user.id,
                amount=-100,
                remark="测试扣减",
            )

        # 验证积分未变化
        await db_session.refresh(test_user)
        assert test_user.points == 50

    @pytest.mark.asyncio
    async def test_adjust_points_creates_log(
        self,
        db_session,
        test_user,
    ):
        """调整积分时创建流水记录"""
        test_user.points = 100
        await db_session.commit()

        service = UserManageService(db_session)
        await service.adjust_points(
            user_id=test_user.id,
            amount=50,
            remark="测试流水",
            operator_id="admin-1",
        )

        # 验证流水记录已创建
        log_query = select(PointLog).where(PointLog.user_id == test_user.id)
        logs = (await db_session.execute(log_query)).scalars().all()

        assert len(logs) >= 1
        found_log = next((log for log in logs if log.remark == "测试流水"), None)
        assert found_log is not None
        assert found_log.change_amount == 50
        assert found_log.balance == 150


class TestPointServiceEdgeCases:
    """测试积分服务边界情况"""

    @pytest.mark.asyncio
    async def test_user_with_null_points(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """用户积分为 None 时的处理"""
        test_user.points = None
        await db_session.commit()

        service = PointService(db_session)

        # 增加积分
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=50,
            remark="测试",
        )

        assert result is not None
        assert result["balance"] == 50
        assert result["currentPoints"] == 50

    @pytest.mark.asyncio
    async def test_large_amount_adjustment(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """大额积分调整"""
        test_user.points = 0
        await db_session.commit()

        service = PointService(db_session)

        # 大额增加
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=1000000,
            remark="大额充值",
        )

        assert result is not None
        assert result["balance"] == 1000000

        # 大额减少
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=-999999,
            remark="大额消费",
        )

        assert result is not None
        assert result["balance"] == 1

    @pytest.mark.asyncio
    async def test_exact_balance_deduction(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """刚好扣完所有积分"""
        test_user.points = 100
        await db_session.commit()

        service = PointService(db_session)
        result = await service.adjust_points(
            patient_id=test_patient.id,
            amount=-100,
            remark="全部扣完",
        )

        assert result is not None
        assert result["balance"] == 0

        # 验证用户积分
        await db_session.refresh(test_user)
        assert test_user.points == 0

    @pytest.mark.asyncio
    async def test_concurrent_adjustments(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """连续多次积分调整"""
        test_user.points = 0
        await db_session.commit()

        service = PointService(db_session)

        # 连续增加
        for i in range(10):
            result = await service.adjust_points(
                patient_id=test_patient.id,
                amount=10,
                remark=f"第{i + 1}次增加",
            )
            assert result is not None
            assert result["balance"] == (i + 1) * 10

        # 验证最终积分
        await db_session.refresh(test_user)
        assert test_user.points == 100

        # 连续减少
        for i in range(5):
            result = await service.adjust_points(
                patient_id=test_patient.id,
                amount=-10,
                remark=f"第{i + 1}次减少",
            )
            assert result is not None
            assert result["balance"] == 100 - (i + 1) * 10

        # 验证最终积分
        await db_session.refresh(test_user)
        assert test_user.points == 50
