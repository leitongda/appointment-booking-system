"""
排班相关定时任务
- 根据排班模板自动生成未来排班
- 自动排班按租户并行派发，租户内保持模板级事务隔离
"""
from datetime import datetime, date, timedelta
import logging
import uuid

import httpx
from celery import chord
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.core.config import settings
from app.db.session import get_sync_db
from app.middleware.tenant_context import clear_tenant_context, set_tenant_context
from app.models.rest_day import RestDay
from app.models.schedule import Schedule
from app.models.schedule_template import ScheduleTemplate
from app.models.tenant import Tenant
from app.utils.schedule_utils import (
    get_time_slot_from_time,
    should_generate_schedule,
    split_time_range_with_breaks,
)

logger = logging.getLogger(__name__)


def send_alert_webhook(task_name: str, error_message: str, retry_count: int):
    """发送失败告警到 Webhook"""
    webhook_url = settings.ALERT_WEBHOOK_URL
    if not webhook_url:
        logger.critical(
            f"[告警] 任务失败: task={task_name}, retry={retry_count}, error={error_message}"
        )
        return

    alert_data = {
        "task_name": task_name,
        "failed_time": datetime.now().isoformat(),
        "error_message": error_message,
        "retry_count": retry_count,
        "severity": "critical" if retry_count >= 2 else "warning",
    }

    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(webhook_url, json=alert_data)
            response.raise_for_status()
            logger.info(f"[告警] Webhook 发送成功: {webhook_url}")
    except Exception as exc:
        logger.error(f"[告警] Webhook 发送失败: {exc}")


class AlertTask(celery_app.Task):
    """支持失败告警的自定义任务基类"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        retry_count = 0
        try:
            if hasattr(self, "request") and hasattr(self.request, "retries"):
                retry_count = self.request.retries
        except Exception:
            retry_count = 0

        send_alert_webhook(
            task_name=self.name,
            error_message=str(exc),
            retry_count=retry_count,
        )


def is_rest_day(
    db: Session,
    check_date: date,
    store_id: str = None,
    doctor_id: str = None,
) -> bool:
    """检查是否为休息日"""
    import json

    try:
        query = select(RestDay).where(
            and_(
                RestDay.status == 1,
                RestDay.start_date <= check_date,
                RestDay.end_date >= check_date,
            )
        )

        if store_id:
            query = query.where(RestDay.store_id == store_id)

        result = db.execute(query)
        rest_days = result.scalars().all()

        for rest_day in rest_days:
            if not doctor_id or rest_day.doctor_ids is None:
                return True

            try:
                doctor_ids_list = json.loads(rest_day.doctor_ids)
                if doctor_id in doctor_ids_list:
                    return True
            except (json.JSONDecodeError, TypeError):
                pass

        return False
    except Exception:
        return False


def _empty_summary() -> dict:
    return {
        "created_count": 0,
        "skipped_count": 0,
        "template_count": 0,
        "success_count": 0,
        "failed_count": 0,
        "template_results": [],
    }


def _build_tenant_result(
    tenant_id: str,
    tenant_code: str,
    tenant_name: str,
    template_results: list[dict] | None = None,
    error: str | None = None,
) -> dict:
    template_results = template_results or []
    created_count = sum(item.get("created_count", 0) for item in template_results)
    skipped_count = sum(item.get("skipped_count", 0) for item in template_results)
    success_count = sum(1 for item in template_results if item.get("error") is None)
    failed_count = sum(1 for item in template_results if item.get("error") is not None)

    result = {
        "tenant_id": tenant_id,
        "tenant_code": tenant_code,
        "tenant_name": tenant_name,
        "created_count": created_count,
        "skipped_count": skipped_count,
        "template_count": len(template_results),
        "success_count": success_count,
        "failed_count": failed_count,
        "template_results": template_results,
        "error": error,
    }
    return result


def _get_active_tenants() -> list[Tenant]:
    with get_sync_db() as db:
        result = db.execute(select(Tenant).where(Tenant.status.in_([1, 3])))
        return list(result.scalars().all())


def _get_enabled_templates_for_tenant(tenant_id: str) -> list[ScheduleTemplate]:
    with get_sync_db() as db:
        result = db.execute(
            select(ScheduleTemplate).where(
                and_(
                    ScheduleTemplate.status == 1,
                    ScheduleTemplate.tenant_id == tenant_id,
                )
            )
        )
        return list(result.scalars().all())


def _generate_template_schedules(
    template: ScheduleTemplate,
    tenant_id: str,
    start_date: date,
    end_date: date,
) -> dict:
    from app.db.session import SessionLocal

    template_db = SessionLocal()
    template_created = 0
    template_skipped = 0
    template_error = None

    try:
        weekdays = template.weekday_list
        if not weekdays:
            logger.warning(f"模板 {template.id} 没有配置星期，跳过")
            return {
                "template_id": template.id,
                "template_name": template.name,
                "doctor_id": template.doctor_id,
                "created_count": 0,
                "skipped_count": 0,
                "error": "没有配置星期",
            }

        break_times = template.break_times_list or []
        time_slots = split_time_range_with_breaks(
            template.start_time,
            template.end_time,
            template.slot_count,
            break_times,
        )

        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.isoweekday()

            if weekday in weekdays and should_generate_schedule(
                current_date, template.schedule_mode
            ):
                if is_rest_day(
                    template_db,
                    current_date,
                    template.store_id,
                    template.doctor_id,
                ):
                    logger.debug(
                        f"跳过休息日: {current_date}, doctor={template.doctor_id}"
                    )
                    template_skipped += 1
                    current_date += timedelta(days=1)
                    continue

                for slot_start, slot_end in time_slots:
                    existing = template_db.execute(
                        select(Schedule).where(
                            and_(
                                Schedule.doctor_id == template.doctor_id,
                                Schedule.schedule_date == current_date,
                                Schedule.start_time == slot_start,
                                Schedule.end_time == slot_end,
                            )
                        )
                    ).scalar_one_or_none()

                    if existing:
                        logger.debug(
                            f"排班已存在: doctor={template.doctor_id}, "
                            f"date={current_date}, time={slot_start}-{slot_end}"
                        )
                        template_skipped += 1
                        continue

                    schedule = Schedule(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        doctor_id=template.doctor_id,
                        store_id=template.store_id,
                        template_id=template.id,
                        schedule_date=current_date,
                        time_slot=get_time_slot_from_time(slot_start),
                        start_time=slot_start,
                        end_time=slot_end,
                        total_slots=template.slot_capacity,
                        appointment_type=template.appointment_type,
                        booked_slots=0,
                        status=1,
                    )
                    template_db.add(schedule)
                    template_created += 1

            current_date += timedelta(days=1)

        template_db.commit()
        logger.info(
            f"模板 {template.id} ({template.name}) 处理完成: "
            f"新建 {template_created} 条，跳过 {template_skipped} 条"
        )
    except Exception as exc:
        template_db.rollback()
        template_error = str(exc)
        logger.error(
            f"模板 {template.id} ({template.name}) 处理失败: {exc}，"
            f"跳过该模板，继续处理其他模板"
        )
    finally:
        template_db.close()

    return {
        "template_id": template.id,
        "template_name": template.name,
        "doctor_id": template.doctor_id,
        "created_count": template_created,
        "skipped_count": template_skipped,
        "error": template_error,
    }


def _generate_schedules_for_tenant(
    tenant_id: str,
    tenant_code: str,
    tenant_name: str,
    generate_days: int | None = None,
) -> dict:
    generate_days = generate_days or settings.SCHEDULE_AUTO_GENERATE_DAYS
    start_date = date.today()
    end_date = start_date + timedelta(days=generate_days)

    logger.info(f"开始处理租户: {tenant_name}({tenant_code}), id={tenant_id}")
    set_tenant_context(tenant_id, tenant_code)

    try:
        templates = _get_enabled_templates_for_tenant(tenant_id)
        if not templates:
            logger.info(f"租户 {tenant_name} 没有启用的排班模板，跳过")
            return _build_tenant_result(tenant_id, tenant_code, tenant_name)

        logger.info(f"租户 {tenant_name} 找到 {len(templates)} 个启用的排班模板")
        template_results = [
            _generate_template_schedules(template, tenant_id, start_date, end_date)
            for template in templates
        ]
        return _build_tenant_result(
            tenant_id,
            tenant_code,
            tenant_name,
            template_results=template_results,
        )
    except Exception as exc:
        logger.error(f"租户 {tenant_name} 排班生成失败: {exc}")
        return _build_tenant_result(
            tenant_id,
            tenant_code,
            tenant_name,
            error=str(exc),
        )
    finally:
        clear_tenant_context()


@celery_app.task(
    name="app.tasks.schedule_task.auto_generate_schedules_task",
    base=AlertTask,
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def auto_generate_schedules_task(self):
    """自动生成排班调度器。"""
    logger.info("[定时任务] 开始执行：排班自动生成")

    generate_days = settings.SCHEDULE_AUTO_GENERATE_DAYS
    try:
        tenants = _get_active_tenants()
    except Exception as exc:
        logger.error(f"查询租户列表失败: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

    if not tenants:
        logger.info("没有活跃租户，跳过排班生成")
        return {
            "status": "noop",
            "dispatched_tenant_count": 0,
            **_empty_summary(),
            "tenant_results": [],
        }

    tenant_ids = [tenant.id for tenant in tenants]
    logger.info(f"找到 {len(tenants)} 个活跃租户，开始并行派发")

    try:
        header = [
            generate_schedules_for_tenant_task.s(
                tenant.id,
                tenant.tenant_code,
                tenant.name,
                generate_days,
            )
            for tenant in tenants
        ]
        callback = summarize_auto_generate_schedules_task.s(
            dispatched_tenant_count=len(tenants)
        )
        async_result = chord(header)(callback)
    except Exception as exc:
        logger.error(f"派发租户级排班生成任务失败: {exc}")
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))

    return {
        "status": "dispatched",
        "dispatched_tenant_count": len(tenants),
        "generate_days": generate_days,
        "tenant_ids": tenant_ids,
        "chord_id": async_result.id,
    }


@celery_app.task(
    name="app.tasks.schedule_task.generate_schedules_for_tenant_task",
    base=AlertTask,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def generate_schedules_for_tenant_task(
    tenant_id: str,
    tenant_code: str,
    tenant_name: str,
    generate_days: int | None = None,
):
    """为单租户生成自动排班。"""
    return _generate_schedules_for_tenant(
        tenant_id=tenant_id,
        tenant_code=tenant_code,
        tenant_name=tenant_name,
        generate_days=generate_days,
    )


@celery_app.task(
    name="app.tasks.schedule_task.summarize_auto_generate_schedules_task",
    base=AlertTask,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=180,
    soft_time_limit=150,
)
def summarize_auto_generate_schedules_task(
    tenant_results: list[dict] | None,
    dispatched_tenant_count: int = 0,
):
    """汇总租户级自动排班结果。"""
    tenant_results = tenant_results or []

    summary = {
        "status": "completed",
        "dispatched_tenant_count": dispatched_tenant_count,
        "completed_tenant_count": len(tenant_results),
        "successful_tenant_count": sum(
            1 for item in tenant_results if not item.get("error")
        ),
        "failed_tenant_count": sum(1 for item in tenant_results if item.get("error")),
        "created_count": sum(item.get("created_count", 0) for item in tenant_results),
        "skipped_count": sum(item.get("skipped_count", 0) for item in tenant_results),
        "template_count": sum(item.get("template_count", 0) for item in tenant_results),
        "success_count": sum(item.get("success_count", 0) for item in tenant_results),
        "failed_count": sum(item.get("failed_count", 0) for item in tenant_results),
        "tenant_results": tenant_results,
    }

    logger.info(
        "[定时任务] 排班自动生成完成，"
        f"派发租户 {summary['dispatched_tenant_count']} 个，"
        f"成功租户 {summary['successful_tenant_count']} 个，"
        f"失败租户 {summary['failed_tenant_count']} 个，"
        f"总计新建 {summary['created_count']} 条，"
        f"跳过 {summary['skipped_count']} 条"
    )
    return summary


@celery_app.task(
    name="app.tasks.schedule_task.generate_schedules_for_template",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    time_limit=600,
    soft_time_limit=480,
)
def generate_schedules_for_template(
    template_id: str,
    start_date: str,
    end_date: str,
    tenant_id: str = None,
    tenant_code: str = None,
):
    """
    为指定模板生成排班（手动触发，支持租户隔离）

    Args:
        template_id: 模板 ID
        start_date: 开始日期（格式：YYYY-MM-DD）
        end_date: 结束日期（格式：YYYY-MM-DD）
        tenant_id: 租户 ID（可选，用于设置租户上下文）
        tenant_code: 租户编码（可选，用于设置租户上下文）
    """
    logger.info(f"[任务] 为模板生成排班: template_id={template_id}, tenant_id={tenant_id}")

    set_tenant_context(tenant_id, tenant_code)

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        created_count = 0

        with get_sync_db() as db:
            try:
                template = db.get(ScheduleTemplate, template_id)
                if not template or template.status != 1:
                    return {"created_count": 0, "reason": "模板不存在或未启用"}

                if tenant_id and template.tenant_id != tenant_id:
                    logger.warning(
                        f"模板 {template_id} 不属于租户 {tenant_id}，"
                        f"实际属于 {template.tenant_id}"
                    )
                    return {"created_count": 0, "reason": "模板不属于指定租户"}

                weekdays = template.weekday_list
                if not weekdays:
                    return {"created_count": 0, "reason": "模板没有配置星期"}

                break_times = template.break_times_list or []
                time_slots = split_time_range_with_breaks(
                    template.start_time,
                    template.end_time,
                    template.slot_count,
                    break_times,
                )

                current_date = start
                while current_date <= end:
                    weekday = current_date.isoweekday()

                    if weekday in weekdays and should_generate_schedule(
                        current_date, template.schedule_mode
                    ):
                        if is_rest_day(
                            db,
                            current_date,
                            template.store_id,
                            template.doctor_id,
                        ):
                            current_date += timedelta(days=1)
                            continue

                        for slot_start, slot_end in time_slots:
                            existing = db.execute(
                                select(Schedule).where(
                                    and_(
                                        Schedule.doctor_id == template.doctor_id,
                                        Schedule.schedule_date == current_date,
                                        Schedule.start_time == slot_start,
                                        Schedule.end_time == slot_end,
                                    )
                                )
                            ).scalar_one_or_none()

                            if not existing:
                                schedule = Schedule(
                                    id=str(uuid.uuid4()),
                                    tenant_id=tenant_id,
                                    doctor_id=template.doctor_id,
                                    store_id=template.store_id,
                                    template_id=template.id,
                                    schedule_date=current_date,
                                    time_slot=get_time_slot_from_time(slot_start),
                                    start_time=slot_start,
                                    end_time=slot_end,
                                    total_slots=template.slot_capacity,
                                    appointment_type=template.appointment_type,
                                    booked_slots=0,
                                    status=1,
                                )
                                db.add(schedule)
                                created_count += 1

                    current_date += timedelta(days=1)

                db.commit()
            except Exception as exc:
                db.rollback()
                logger.error(f"为模板生成排班失败: {exc}")
                raise
    finally:
        clear_tenant_context()

    logger.info(f"[任务] 模板排班生成完成: created_count={created_count}")
    return {"created_count": created_count, "template_id": template_id, "tenant_id": tenant_id}
