"""停诊处置补偿任务单元测试"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call

import pytest

from app.tasks.suspension_processing_task import (
    MAX_RETRY_COUNT,
    _do_check_pending,
    _handle_retry_failure,
    _process_single_suspension,
    _process_suspension_sync,
    check_pending_suspension_processing,
)


# ---- 辅助函数 ----

def _make_suspension(
    suspension_id="susp-001",
    processing_status="pending",
    processing_method="auto_refund",
    retry_count=0,
    status=1,
    tenant_id="tenant-1",
    doctor_id="doctor-1",
    suspension_date=None,
    schedule_ids=None,
    last_retry_at=None,
):
    """创建模拟的停诊记录"""
    s = MagicMock()
    s.id = suspension_id
    s.processing_status = processing_status
    s.processing_method = processing_method
    s.retry_count = retry_count
    s.status = status
    s.tenant_id = tenant_id
    s.doctor_id = doctor_id
    s.suspension_date = suspension_date or datetime.now().date()
    s.schedule_ids = schedule_ids
    s.last_retry_at = last_retry_at
    s.affected_appointment_count = 0
    return s


def _make_appointment(appointment_id="appt-001", status=1, remark=None):
    """创建模拟的预约记录"""
    a = MagicMock()
    a.id = appointment_id
    a.status = status
    a.remark = remark
    a.payment_amount = 100
    a.payment_transaction_id = "txn-001"
    a.cancel_time = None
    a.cancel_reason = None
    a.schedule = MagicMock()
    a.schedule.booked_slots = 2
    return a


def _mock_scalars_result(items):
    """模拟 db.execute(...).scalars().all() 的返回链"""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


def _mock_scalar_one_or_none(value):
    """模拟 db.execute(...).scalar_one_or_none() 的返回"""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _mock_scalars_first(value):
    """模拟 db.execute(...).scalars().first() 的返回"""
    result = MagicMock()
    result.scalars.return_value.first.return_value = value
    return result


# ---- 测试：pending 记录被扫描到 ----

@patch("app.tasks.suspension_processing_task.send_alert_webhook")
@patch("app.tasks.suspension_processing_task.SyncRedisCache")
@patch("app.tasks.suspension_processing_task.get_sync_db")
def test_pending_records_are_scanned(mock_get_sync_db, mock_redis, mock_alert):
    """验证 pending 且超时的记录会被扫描到"""
    suspension = _make_suspension()
    db = MagicMock()
    db.execute.return_value = _mock_scalars_result([suspension])

    ctx = MagicMock()
    ctx.__enter__.return_value = db
    ctx.__exit__.return_value = False
    mock_get_sync_db.return_value = ctx
    mock_redis.acquire_lock.return_value = "lock-value"

    # _process_suspension_sync 需要的排班查询返回空列表
    # 第一次 execute: 查询 pending 停诊, 第二次: 查询排班ID, 第三次: 查询预约
    db.execute.side_effect = [
        _mock_scalars_result([suspension]),      # pending 查询
        _mock_scalars_result([]),                 # schedule_ids 查询
    ]

    result = check_pending_suspension_processing()

    assert result["scanned_count"] == 1


# ---- 测试：成功重试后状态变为 completed ----

@patch("app.tasks.suspension_processing_task.send_alert_webhook")
@patch("app.tasks.suspension_processing_task.SyncRedisCache")
@patch("app.tasks.suspension_processing_task.get_sync_db")
def test_success_retry_marks_completed(mock_get_sync_db, mock_redis, mock_alert):
    """验证处置成功后 processing_status 变为 completed"""
    import json

    suspension = _make_suspension(schedule_ids=json.dumps(["sched-001"]))
    db = MagicMock()
    db.execute.return_value = _mock_scalars_result([])  # 无受影响预约 -> 成功

    ctx = MagicMock()
    ctx.__enter__.return_value = db
    ctx.__exit__.return_value = False
    mock_get_sync_db.return_value = ctx
    mock_redis.acquire_lock.return_value = "lock-value"

    db.execute.side_effect = [
        _mock_scalars_result([suspension]),  # pending 查询
        _mock_scalars_result([]),            # 无排班 -> 无预约 -> completed
    ]

    result = check_pending_suspension_processing()

    assert result["success_count"] == 1
    assert result["failed_count"] == 0
    assert suspension.processing_status == "completed"


# ---- 测试：超过重试次数后状态变为 failed ----

@patch("app.tasks.suspension_processing_task.send_alert_webhook")
def test_max_retries_marks_failed(mock_alert):
    """验证超过最大重试次数后标记为 failed 并发送告警"""
    db = MagicMock()
    suspension = _make_suspension(retry_count=MAX_RETRY_COUNT)

    result = _handle_retry_failure(db, suspension)

    assert result == "failed"
    assert suspension.processing_status == "failed"
    db.commit.assert_called_once()
    mock_alert.assert_called_once()


# ---- 测试：未超过重试次数恢复为 pending ----

@patch("app.tasks.suspension_processing_task.send_alert_webhook")
def test_below_max_retries_restores_pending(mock_alert):
    """验证未超过最大重试次数时恢复为 pending"""
    db = MagicMock()
    suspension = _make_suspension(retry_count=1)

    result = _handle_retry_failure(db, suspension)

    assert result == "skipped"
    assert suspension.processing_status == "pending"
    db.commit.assert_called_once()
    mock_alert.assert_not_called()


# ---- 测试：非 pending 记录被跳过 ----

@patch("app.tasks.suspension_processing_task.SyncRedisCache")
@patch("app.tasks.suspension_processing_task.get_sync_db")
def test_non_pending_records_skipped(mock_get_sync_db, mock_redis):
    """验证非 pending 状态的记录不会被查询到"""
    db = MagicMock()
    db.execute.return_value = _mock_scalars_result([])  # 无 pending 记录

    ctx = MagicMock()
    ctx.__enter__.return_value = db
    ctx.__exit__.return_value = False
    mock_get_sync_db.return_value = ctx
    mock_redis.acquire_lock.return_value = "lock-value"

    result = check_pending_suspension_processing()

    assert result["status"] == "noop"
    assert result["scanned_count"] == 0


# ---- 测试：分布式锁保护 ----

@patch("app.tasks.suspension_processing_task.SyncRedisCache")
def test_lock_not_acquired_skips_execution(mock_redis):
    """验证无法获取锁时跳过执行"""
    mock_redis.acquire_lock.return_value = None

    result = check_pending_suspension_processing()

    assert result["status"] == "skipped"
    assert result["reason"] == "another instance running"
    mock_redis.release_lock.assert_not_called()


@patch("app.tasks.suspension_processing_task.SyncRedisCache")
@patch("app.tasks.suspension_processing_task.get_sync_db")
def test_lock_released_after_execution(mock_get_sync_db, mock_redis):
    """验证执行完成后释放锁"""
    db = MagicMock()
    db.execute.return_value = _mock_scalars_result([])

    ctx = MagicMock()
    ctx.__enter__.return_value = db
    ctx.__exit__.return_value = False
    mock_get_sync_db.return_value = ctx
    mock_redis.acquire_lock.return_value = "lock-value"

    check_pending_suspension_processing()

    mock_redis.release_lock.assert_called_once_with(
        "suspension:processing:compensation", "lock-value"
    )


# ---- 测试：每条停诊独立处理，一条失败不影响其他 ----

@patch("app.tasks.suspension_processing_task.send_alert_webhook")
@patch("app.tasks.suspension_processing_task.SyncRedisCache")
@patch("app.tasks.suspension_processing_task.get_sync_db")
def test_independent_processing(mock_get_sync_db, mock_redis, mock_alert):
    """验证一条停诊处置失败不影响其他记录"""
    s1 = _make_suspension(suspension_id="s1", processing_method="manual")
    s2 = _make_suspension(suspension_id="s2", processing_method="manual")

    db = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = db
    ctx.__exit__.return_value = False
    mock_get_sync_db.return_value = ctx
    mock_redis.acquire_lock.return_value = "lock-value"

    # pending 查询返回两条记录
    # 每条记录后续的排班查询返回空列表 -> completed
    db.execute.side_effect = [
        _mock_scalars_result([s1, s2]),  # pending 查询
        _mock_scalars_result([]),        # s1 排班查询
        _mock_scalars_result([]),        # s2 排班查询
    ]

    result = check_pending_suspension_processing()

    assert result["scanned_count"] == 2
    assert result["success_count"] == 2


# ---- 测试：auto_refund 处置逻辑 ----

def test_auto_refund_cancels_appointment():
    """验证 auto_refund 取消预约并释放号源"""
    import json

    db = MagicMock()
    suspension = _make_suspension(
        processing_method="auto_refund",
        schedule_ids=json.dumps(["sched-001"]),
    )
    appointment = _make_appointment(status=1)
    appointment.schedule = MagicMock()
    appointment.schedule.booked_slots = 2

    # 排班查询、预约查询
    db.execute.side_effect = [
        _mock_scalars_result([appointment]),  # 受影响预约
    ]

    result = _process_suspension_sync(db, suspension)

    assert result is True
    assert appointment.status == 5  # CANCELLED
    assert appointment.cancel_reason is not None
    assert appointment.schedule.booked_slots == 1


# ---- 测试：reschedule 处置逻辑 ----

def test_reschedule_marks_remark():
    """验证 reschedule 在预约备注中标记待转约"""
    import json

    db = MagicMock()
    suspension = _make_suspension(
        processing_method="reschedule",
        schedule_ids=json.dumps(["sched-001"]),
    )
    appointment = _make_appointment(remark="")

    db.execute.side_effect = [
        _mock_scalars_result([appointment]),
    ]

    result = _process_suspension_sync(db, suspension)

    assert result is True
    assert "停诊待转约" in appointment.remark


# ---- 测试：无处置方式标记为 completed ----

def test_no_processing_method_marks_completed():
    """验证无处置方式时标记为 completed"""
    db = MagicMock()
    suspension = _make_suspension(processing_method=None)

    result = _process_suspension_sync(db, suspension)

    assert result is True


# ---- 测试：无受影响排班标记为 completed ----

def test_no_affected_schedules_marks_completed():
    """验证无受影响排班时标记为 completed"""
    import json

    db = MagicMock()
    suspension = _make_suspension(
        processing_method="auto_refund",
        schedule_ids=json.dumps(["sched-nonexistent"]),
    )

    # 查询排班返回空
    db.execute.return_value = _mock_scalars_result([])

    result = _process_suspension_sync(db, suspension)

    assert result is True


# ---- 测试：重试计数递增 ----

@patch("app.tasks.suspension_processing_task.send_alert_webhook")
@patch("app.tasks.suspension_processing_task.SyncRedisCache")
@patch("app.tasks.suspension_processing_task.get_sync_db")
def test_retry_count_increments(mock_get_sync_db, mock_redis, mock_alert):
    """验证每次重试 retry_count 递增"""
    suspension = _make_suspension(retry_count=0)

    db = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = db
    ctx.__exit__.return_value = False
    mock_get_sync_db.return_value = ctx
    mock_redis.acquire_lock.return_value = "lock-value"

    db.execute.side_effect = [
        _mock_scalars_result([suspension]),  # pending 查询
        _mock_scalars_result([]),            # 排班查询 -> completed
    ]

    check_pending_suspension_processing()

    assert suspension.retry_count == 1
    assert suspension.last_retry_at is not None


# ---- 测试：手动(manual)处置逻辑 ----

def test_manual_marks_remark():
    """验证 manual 在预约备注中标记待人工处理"""
    import json

    db = MagicMock()
    suspension = _make_suspension(
        processing_method="manual",
        schedule_ids=json.dumps(["sched-001"]),
    )
    appointment = _make_appointment(remark="")

    db.execute.side_effect = [
        _mock_scalars_result([appointment]),
    ]

    result = _process_suspension_sync(db, suspension)

    assert result is True
    assert "停诊待人工处理" in appointment.remark


# ---- 测试：change_date 处置逻辑 ----

def test_change_date_marks_remark():
    """验证 change_date 在预约备注中标记待改期"""
    import json

    db = MagicMock()
    suspension = _make_suspension(
        processing_method="change_date",
        schedule_ids=json.dumps(["sched-001"]),
    )
    appointment = _make_appointment(remark="")

    db.execute.side_effect = [
        _mock_scalars_result([appointment]),
    ]

    result = _process_suspension_sync(db, suspension)

    assert result is True
    assert "停诊待改期" in appointment.remark
