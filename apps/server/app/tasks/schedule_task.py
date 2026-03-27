"""
排班相关定时任务
- 根据排班模板自动生成未来排班
- 支持多租户隔离：遍历所有活跃租户，在每个租户上下文中生成排班
"""
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
import logging
import uuid

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.tenant import Tenant
from app.models.schedule_template import ScheduleTemplate
from app.models.schedule import Schedule
from app.models.rest_day import RestDay
from app.core.config import settings
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context
from app.utils.schedule_utils import (
    should_generate_schedule,
    get_time_slot_from_time,
    split_time_range,
    split_time_range_with_breaks,
)

logger = logging.getLogger(__name__)


def is_rest_day(db: Session, check_date: date, store_id: str = None, doctor_id: str = None) -> bool:
    """检查是否为休息日
    
    Args:
        db: 数据库会话
        check_date: 要检查的日期
        store_id: 门店ID
        doctor_id: 医生ID
        
    Returns:
        True 表示是休息日，False 表示不是
    """
    import json
    try:
        query = select(RestDay).where(
            and_(
                RestDay.status == 1,
                RestDay.start_date <= check_date,  # 修复：使用日期范围检查
                RestDay.end_date >= check_date     # 修复：使用日期范围检查
            )
        )
        
        # 如果指定了门店，过滤门店
        if store_id:
            query = query.where(RestDay.store_id == store_id)
        
        result = db.execute(query)
        rest_days = result.scalars().all()
        
        for rd in rest_days:
            # 如果没有指定医生，或者休息日配置为所有医生（doctor_ids 为 NULL）
            if not doctor_id or rd.doctor_ids is None:
                return True
            # 检查医生是否在休息日列表中
            try:
                doctor_ids_list = json.loads(rd.doctor_ids)
                if doctor_id in doctor_ids_list:
                    return True
            except (json.JSONDecodeError, TypeError):
                pass
        
        return False
    except Exception:
        return False


@celery_app.task(name="app.tasks.schedule_task.auto_generate_schedules_task")
def auto_generate_schedules_task():
    """
    自动生成排班（多租户版本）
    每天凌晨2点执行

    规则：
    - 遍历所有活跃租户
    - 在每个租户上下文中查找启用的排班模板
    - 根据模板配置生成未来 N 天的排班
    - 跳过已存在的排班和休息日
    - 每个模板使用独立事务，单个模板失败不影响其他模板
    """
    logger.info("[定时任务] 开始执行：排班自动生成")

    generate_days = settings.SCHEDULE_AUTO_GENERATE_DAYS
    total_created = 0
    total_skipped = 0
    template_results = []  # 记录每个模板的处理结果

    # 第一步：查询所有活跃租户（使用独立会话）
    with get_sync_db() as db:
        try:
            result = db.execute(
                select(Tenant).where(Tenant.status.in_([1, 3]))  # 正常或试用状态
            )
            tenants = result.scalars().all()
        except Exception as e:
            logger.error(f"查询租户列表失败: {e}")
            raise

    if not tenants:
        logger.info("没有活跃租户，跳过排班生成")
        return {"created_count": 0, "skipped_count": 0, "template_results": []}

    logger.info(f"找到 {len(tenants)} 个活跃租户")

    # 第二步：遍历每个租户，在其上下文中生成排班
    for tenant in tenants:
        logger.info(f"开始处理租户: {tenant.name}({tenant.tenant_code}), id={tenant.id}")

        # 设置当前租户上下文
        set_tenant_context(tenant.id, tenant.tenant_code)

        try:
            # 使用独立的数据库会话查询该租户的模板列表
            with get_sync_db() as db:
                try:
                    today = date.today()
                    end_date = today + timedelta(days=generate_days)

                    # 查找该租户下所有启用的排班模板
                    result = db.execute(
                        select(ScheduleTemplate).where(
                            and_(
                                ScheduleTemplate.status == 1,
                                ScheduleTemplate.tenant_id == tenant.id
                            )
                        )
                    )
                    templates = result.scalars().all()

                    if not templates:
                        logger.info(f"租户 {tenant.name} 没有启用的排班模板，跳过")
                        continue

                    logger.info(f"租户 {tenant.name} 找到 {len(templates)} 个启用的排班模板")
                    template_list = list(templates)  # 转为列表保存

                except Exception as e:
                    logger.error(f"租户 {tenant.name} 查询排班模板失败: {e}")
                    continue

            # 为每个模板使用独立的事务处理
            for template in template_list:
                template_created = 0
                template_skipped = 0
                template_error = None

                # 每个模板使用独立的数据库会话和事务
                from app.db.session import SessionLocal
                template_db = SessionLocal()

                try:
                    # 获取星期列表（支持多星期）
                    weekdays = template.weekday_list
                    if not weekdays:
                        logger.warning(f"模板 {template.id} 没有配置星期，跳过")
                        template_results.append({
                            "template_id": template.id,
                            "template_name": template.name,
                            "doctor_id": template.doctor_id,
                            "created_count": 0,
                            "skipped_count": 0,
                            "error": "没有配置星期"
                        })
                        template_db.close()
                        continue

                    # 获取排除时间列表
                    break_times = template.break_times_list or []

                    # 均分时间生成多个班次（考虑排除时间）
                    time_slots = split_time_range_with_breaks(
                        template.start_time,
                        template.end_time,
                        template.slot_count,
                        break_times
                    )

                    current_date = today

                    while current_date <= end_date:
                        weekday = current_date.isoweekday()  # 1-7 代表周一到周日

                        # 检查星期是否匹配（支持多选）
                        if weekday in weekdays:
                            # 检查排班方式是否匹配
                            if should_generate_schedule(current_date, template.schedule_mode):
                                # 检查是否为休息日（传入医生ID以支持医生级别休息日）
                                if is_rest_day(template_db, current_date, template.store_id, template.doctor_id):
                                    logger.debug(f"跳过休息日: {current_date}, doctor={template.doctor_id}")
                                    template_skipped += 1
                                    current_date += timedelta(days=1)
                                    continue

                                # 为每个班次生成排班记录
                                for slot_start, slot_end in time_slots:
                                    # 检查是否已存在相同排班
                                    existing = template_db.execute(
                                        select(Schedule).where(
                                            and_(
                                                Schedule.doctor_id == template.doctor_id,
                                                Schedule.schedule_date == current_date,
                                                Schedule.start_time == slot_start,
                                                Schedule.end_time == slot_end
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

                                    # 创建新排班
                                    time_slot = get_time_slot_from_time(slot_start)
                                    schedule = Schedule(
                                        id=str(uuid.uuid4()),
                                        doctor_id=template.doctor_id,
                                        store_id=template.store_id,
                                        template_id=template.id,
                                        schedule_date=current_date,
                                        time_slot=time_slot,
                                        start_time=slot_start,
                                        end_time=slot_end,
                                        total_slots=template.slot_capacity,
                                        appointment_type=template.appointment_type,
                                        booked_slots=0,
                                        status=1
                                    )
                                    template_db.add(schedule)
                                    template_created += 1

                                    logger.debug(
                                        f"创建排班: doctor={template.doctor_id}, "
                                        f"date={current_date}, slot={time_slot}, "
                                        f"time={slot_start}-{slot_end}"
                                    )

                        current_date += timedelta(days=1)

                    # 提交当前模板的事务
                    template_db.commit()
                    logger.info(
                        f"模板 {template.id} ({template.name}) 处理完成: "
                        f"新建 {template_created} 条，跳过 {template_skipped} 条"
                    )

                except Exception as e:
                    # 当前模板失败，回滚但不影响其他模板
                    template_db.rollback()
                    template_error = str(e)
                    logger.error(
                        f"模板 {template.id} ({template.name}) 处理失败: {e}，"
                        f"跳过该模板，继续处理其他模板"
                    )
                finally:
                    template_db.close()

                # 记录模板处理结果
                template_results.append({
                    "template_id": template.id,
                    "template_name": template.name,
                    "doctor_id": template.doctor_id,
                    "created_count": template_created,
                    "skipped_count": template_skipped,
                    "error": template_error
                })

                # 累加总数
                total_created += template_created
                total_skipped += template_skipped

        except Exception as e:
            logger.error(f"租户 {tenant.name} 排班生成失败: {e}")
        finally:
            # 清除租户上下文
            clear_tenant_context()

    # 统计成功和失败的模板数
    success_count = sum(1 for r in template_results if r["error"] is None)
    failed_count = sum(1 for r in template_results if r["error"] is not None)

    logger.info(
        f"[定时任务] 排班自动生成完成，共处理 {len(template_results)} 个模板，"
        f"成功 {success_count} 个，失败 {failed_count} 个，"
        f"总计新建 {total_created} 条，跳过 {total_skipped} 条"
    )

    return {
        "created_count": total_created,
        "skipped_count": total_skipped,
        "template_count": len(template_results),
        "success_count": success_count,
        "failed_count": failed_count,
        "template_results": template_results
    }


@celery_app.task(name="app.tasks.schedule_task.generate_schedules_for_template")
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

    # 设置租户上下文
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

                # 校验模板归属租户（如果指定了 tenant_id）
                if tenant_id and template.tenant_id != tenant_id:
                    logger.warning(
                        f"模板 {template_id} 不属于租户 {tenant_id}，"
                        f"实际属于 {template.tenant_id}"
                    )
                    return {"created_count": 0, "reason": "模板不属于指定租户"}

                # 获取星期列表（支持多星期）
                weekdays = template.weekday_list
                if not weekdays:
                    return {"created_count": 0, "reason": "模板没有配置星期"}

                # 获取排除时间列表
                break_times = template.break_times_list or []

                # 均分时间生成多个班次（考虑排除时间）
                time_slots = split_time_range_with_breaks(
                    template.start_time,
                    template.end_time,
                    template.slot_count,
                    break_times
                )

                current_date = start
                while current_date <= end:
                    weekday = current_date.isoweekday()

                    # 检查星期是否匹配（支持多选）
                    if weekday in weekdays:
                        if should_generate_schedule(current_date, template.schedule_mode):
                            # 检查是否为休息日（传入医生ID以支持医生级别休息日）
                            if is_rest_day(db, current_date, template.store_id, template.doctor_id):
                                current_date += timedelta(days=1)
                                continue

                            # 为每个班次生成排班记录
                            for slot_start, slot_end in time_slots:
                                existing = db.execute(
                                    select(Schedule).where(
                                        and_(
                                            Schedule.doctor_id == template.doctor_id,
                                            Schedule.schedule_date == current_date,
                                            Schedule.start_time == slot_start,
                                            Schedule.end_time == slot_end
                                        )
                                    )
                                ).scalar_one_or_none()

                                if not existing:
                                    time_slot = get_time_slot_from_time(slot_start)
                                    schedule = Schedule(
                                        id=str(uuid.uuid4()),
                                        doctor_id=template.doctor_id,
                                        store_id=template.store_id,
                                        template_id=template.id,
                                        schedule_date=current_date,
                                        time_slot=time_slot,
                                        start_time=slot_start,
                                        end_time=slot_end,
                                        total_slots=template.slot_capacity,
                                        appointment_type=template.appointment_type,
                                        booked_slots=0,
                                        status=1
                                    )
                                    db.add(schedule)
                                    created_count += 1

                    current_date += timedelta(days=1)

                db.commit()

            except Exception as e:
                db.rollback()
                logger.error(f"为模板生成排班失败: {e}")
                raise

    finally:
        # 清除租户上下文
        clear_tenant_context()

    logger.info(f"[任务] 模板排班生成完成: created_count={created_count}")
    return {"created_count": created_count, "template_id": template_id, "tenant_id": tenant_id}

