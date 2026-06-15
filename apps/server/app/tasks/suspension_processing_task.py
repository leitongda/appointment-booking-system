"""
停诊处置补偿定时任务

扫描 pending 状态的停诊记录，自动重试处置。
超过最大重试次数后标记为 failed 并发送告警通知。
"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import and_, select

from app.celery_app import celery_app
from app.core.redis import SyncRedisCache
from app.db.session import get_sync_db
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.schedule_suspension import ScheduleSuspension
from app.tasks.schedule_task import AlertTask, send_alert_webhook

logger = logging.getLogger(__name__)

# 最大重试次数
MAX_RETRY_COUNT = 3
# pending 超过此时间（分钟）才触发补偿
PENDING_THRESHOLD_MINUTES = 30


def _process_suspension_sync(db, suspension: ScheduleSuspension) -> bool:
    """
    同步处置单条停诊记录。

    根据 processing_method 调用对应的处置逻辑。
    使用同步数据库连接（Celery 任务环境）。

    Args:
        db: 同步数据库会话
        suspension: 停诊记录

    Returns:
        处置是否成功
    """
    method = suspension.processing_method
    if not method:
        logger.warning(
            f"[补偿任务] 停诊 {suspension.id} 无处置方式，标记为 completed"
        )
        return True

    # 获取受影响的排班 ID
    affected_schedule_ids = _get_affected_schedule_ids_sync(db, suspension)
    if not affected_schedule_ids:
        logger.info(
            f"[补偿任务] 停诊 {suspension.id} 无受影响排班，标记为 completed"
        )
        return True

    # 获取受影响的活跃预约
    appointment_conditions = [
        Appointment.schedule_id.in_(affected_schedule_ids),
        Appointment.status.in_([0, 1, 2, 4]),  # 待支付/已预约/已签到/就诊中
    ]
    if suspension.tenant_id:
        appointment_conditions.append(Appointment.tenant_id == suspension.tenant_id)

    appointments = db.execute(
        select(Appointment).where(and_(*appointment_conditions))
    ).scalars().all()

    if not appointments:
        logger.info(
            f"[补偿任务] 停诊 {suspension.id} 无受影响预约，标记为 completed"
        )
        return True

    success_count = 0
    failed_count = 0

    for appointment in appointments:
        try:
            if method == "auto_refund":
                _auto_refund_sync(db, appointment, suspension)
            elif method == "reschedule":
                _mark_appointment_remark_sync(
                    appointment, suspension,
                    "[停诊待转约] 停诊ID: {sid}，请患者选择其他医生重新预约",
                )
            elif method == "change_date":
                _mark_appointment_remark_sync(
                    appointment, suspension,
                    "[停诊待改期] 停诊ID: {sid}，请患者选择其他日期重新预约",
                )
            elif method == "manual":
                _mark_appointment_remark_sync(
                    appointment, suspension,
                    "[停诊待人工处理] 停诊ID: {sid}",
                )
            else:
                logger.warning(
                    f"[补偿任务] 未知处置方式: {method}, "
                    f"suspension={suspension.id}"
                )
                failed_count += 1
                continue
            success_count += 1
        except Exception as exc:
            failed_count += 1
            logger.warning(
                f"[补偿任务] 处置预约失败: appointment_id={appointment.id}, "
                f"method={method}, error={exc}"
            )

    # 更新受影响预约数
    suspension.affected_appointment_count = len(appointments)

    logger.info(
        f"[补偿任务] 停诊 {suspension.id} 处置完成: "
        f"method={method}, total={len(appointments)}, "
        f"success={success_count}, failed={failed_count}"
    )

    # 只要有成功的就认为处置完成（部分成功仍标记为 completed）
    return success_count > 0 or failed_count == 0


def _get_affected_schedule_ids_sync(db, suspension: ScheduleSuspension) -> list:
    """同步获取停诊影响的排班 ID 列表"""
    if suspension.schedule_ids:
        try:
            return json.loads(suspension.schedule_ids)
        except (json.JSONDecodeError, TypeError):
            return []

    conditions = [
        Schedule.doctor_id == suspension.doctor_id,
        Schedule.schedule_date == suspension.suspension_date,
        Schedule.status == 0,
    ]
    if suspension.tenant_id:
        conditions.append(Schedule.tenant_id == suspension.tenant_id)

    result = db.execute(select(Schedule.id).where(and_(*conditions)))
    return [row[0] for row in result.fetchall()]


def _auto_refund_sync(db, appointment: Appointment, suspension: ScheduleSuspension):
    """
    同步取消预约并触发退款（补偿任务简化版）。

    注意: 微信退款是异步操作，在 Celery 同步环境中仅标记取消状态，
    退款由单独的退款同步任务处理。
    """
    schedule = appointment.schedule if hasattr(appointment, 'schedule') else None

    # 标记取消
    appointment.status = 5  # CANCELLED
    appointment.cancel_time = datetime.now()
    appointment.cancel_reason = f"停诊自动取消（停诊ID: {suspension.id}）"

    # 释放排班号源
    if schedule:
        schedule.booked_slots = max(0, schedule.booked_slots - 1)

    logger.info(
        f"[补偿任务] 预约 {appointment.id} 已取消，"
        f"payment_amount={appointment.payment_amount}"
    )


def _mark_appointment_remark_sync(
    appointment: Appointment,
    suspension: ScheduleSuspension,
    remark_template: str,
):
    """同步标记预约备注"""
    remark = remark_template.format(sid=suspension.id)
    appointment.remark = (appointment.remark or "") + f"\n{remark}"


@celery_app.task(
    name="app.tasks.suspension_processing_task.check_pending_suspension_processing",
    base=AlertTask,
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=300,
    soft_time_limit=240,
)
def check_pending_suspension_processing(self):
    """
    扫描 pending 状态的停诊记录，自动重试处置。

    执行逻辑：
    1. 获取分布式锁，防止并发执行
    2. 查询 processing_status='pending' 且创建时间 > 30 分钟的停诊记录
    3. 对每条记录独立处理（一条失败不影响其他）
    4. 成功则更新 processing_status='completed'
    5. 失败则累加重试计数，超过 3 次标记为 'failed' 并发送告警
    """
    logger.info("[定时任务] 开始执行：停诊处置补偿检查")

    # 分布式锁，防止多实例并发执行
    lock_name = "suspension:processing:compensation"
    lock_value = SyncRedisCache.acquire_lock(
        lock_name, timeout=300, retry_times=1, retry_delay=0
    )
    if not lock_value:
        logger.info("[定时任务] 停诊处置补偿被跳过，另一实例正在执行")
        return {"status": "skipped", "reason": "another instance running"}

    try:
        return _do_check_pending()
    finally:
        SyncRedisCache.release_lock(lock_name, lock_value)


def _do_check_pending() -> dict:
    """执行实际的补偿检查逻辑（已持有分布式锁）"""
    threshold = datetime.now() - timedelta(minutes=PENDING_THRESHOLD_MINUTES)

    with get_sync_db() as db:
        # 查询需要补偿的停诊记录
        pending_suspensions = db.execute(
            select(ScheduleSuspension).where(
                and_(
                    ScheduleSuspension.processing_status == "pending",
                    ScheduleSuspension.status == 1,  # 仅生效中的停诊
                    ScheduleSuspension.created_at < threshold,
                    ScheduleSuspension.processing_method.isnot(None),
                )
            )
        ).scalars().all()

        if not pending_suspensions:
            logger.info("[定时任务] 无待补偿的停诊记录")
            return {"status": "noop", "scanned_count": 0}

        logger.info(
            f"[定时任务] 发现 {len(pending_suspensions)} 条待补偿停诊记录"
        )

        success_count = 0
        failed_count = 0
        skipped_count = 0

        for suspension in pending_suspensions:
            try:
                result = _process_single_suspension(db, suspension)
                if result == "completed":
                    success_count += 1
                elif result == "failed":
                    failed_count += 1
                else:
                    skipped_count += 1
            except Exception as exc:
                logger.error(
                    f"[定时任务] 处理停诊 {suspension.id} 异常: {exc}",
                    exc_info=True,
                )
                failed_count += 1

        summary = {
            "status": "completed",
            "scanned_count": len(pending_suspensions),
            "success_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
        }
        logger.info(
            f"[定时任务] 停诊处置补偿完成: "
            f"scanned={summary['scanned_count']}, "
            f"success={summary['success_count']}, "
            f"failed={summary['failed_count']}, "
            f"skipped={summary['skipped_count']}"
        )
        return summary


def _process_single_suspension(db, suspension: ScheduleSuspension) -> str:
    """
    处理单条停诊记录的补偿。

    Args:
        db: 同步数据库会话
        suspension: 停诊记录

    Returns:
        "completed" | "failed" | "skipped"
    """
    suspension_id = suspension.id
    retry_count = suspension.retry_count or 0

    logger.info(
        f"[补偿任务] 开始处理停诊 {suspension_id}, "
        f"method={suspension.processing_method}, "
        f"retry_count={retry_count}/{MAX_RETRY_COUNT}"
    )

    # 标记为处理中
    suspension.processing_status = "processing"
    suspension.retry_count = retry_count + 1
    suspension.last_retry_at = datetime.now()
    db.flush()

    try:
        success = _process_suspension_sync(db, suspension)

        if success:
            suspension.processing_status = "completed"
            db.commit()
            logger.info(
                f"[补偿任务] 停诊 {suspension_id} 处置成功 "
                f"(第 {suspension.retry_count} 次重试)"
            )
            return "completed"
        else:
            # 处置部分失败，检查是否超过最大重试次数
            return _handle_retry_failure(db, suspension)

    except Exception as exc:
        logger.error(
            f"[补偿任务] 停诊 {suspension_id} 处置异常: {exc}",
            exc_info=True,
        )
        return _handle_retry_failure(db, suspension, error=str(exc))


def _handle_retry_failure(
    db,
    suspension: ScheduleSuspension,
    error: str | None = None,
) -> str:
    """处理重试失败：超过最大次数则标记 failed 并告警，否则保持 pending"""
    if suspension.retry_count >= MAX_RETRY_COUNT:
        suspension.processing_status = "failed"
        db.commit()
        logger.error(
            f"[补偿任务] 停诊 {suspension.id} 超过最大重试次数 "
            f"({MAX_RETRY_COUNT})，标记为 failed"
        )
        # 发送告警通知
        _send_retry_exhausted_alert(suspension, error)
        return "failed"
    else:
        # 恢复为 pending，等待下次定时任务重试
        suspension.processing_status = "pending"
        db.commit()
        logger.warning(
            f"[补偿任务] 停诊 {suspension.id} 处置失败，"
            f"恢复为 pending (retry_count={suspension.retry_count})"
        )
        return "skipped"


def _send_retry_exhausted_alert(
    suspension: ScheduleSuspension,
    error: str | None = None,
):
    """发送重试耗尽告警"""
    error_msg = error or "处置失败，已超过最大重试次数"
    send_alert_webhook(
        task_name="suspension_processing_compensation",
        error_message=(
            f"停诊 {suspension.id} 处置补偿失败: "
            f"method={suspension.processing_method}, "
            f"retry_count={suspension.retry_count}, "
            f"tenant_id={suspension.tenant_id}, "
            f"doctor_id={suspension.doctor_id}, "
            f"date={suspension.suspension_date}, "
            f"error={error_msg}"
        ),
        retry_count=suspension.retry_count,
    )
