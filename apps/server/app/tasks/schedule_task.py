"""
排班相关定时任务
- 根据排班模板自动生成未来排班
"""
from datetime import datetime, date, timedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import Session
import logging
import uuid

from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.models.schedule_template import ScheduleTemplate
from app.models.schedule import Schedule
from app.models.rest_day import RestDay
from app.core.config import settings
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
    自动生成排班
    每天凌晨2点执行
    
    规则：
    - 查找所有启用的排班模板
    - 根据模板配置生成未来 N 天的排班
    - 跳过已存在的排班和休息日
    """
    logger.info("[定时任务] 开始执行：排班自动生成")
    
    generate_days = settings.SCHEDULE_AUTO_GENERATE_DAYS
    created_count = 0
    skipped_count = 0
    
    with get_sync_db() as db:
        try:
            today = date.today()
            end_date = today + timedelta(days=generate_days)
            
            # 查找所有启用的排班模板
            result = db.execute(
                select(ScheduleTemplate).where(ScheduleTemplate.status == 1)
            )
            templates = result.scalars().all()
            
            if not templates:
                logger.info("没有启用的排班模板")
                return {"created_count": 0, "skipped_count": 0}
            
            logger.info(f"找到 {len(templates)} 个启用的排班模板")
            
            for template in templates:
                # 获取星期列表（支持多星期）
                weekdays = template.weekday_list
                if not weekdays:
                    logger.warning(f"模板 {template.id} 没有配置星期，跳过")
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
                            if is_rest_day(db, current_date, template.store_id, template.doctor_id):
                                logger.debug(f"跳过休息日: {current_date}, doctor={template.doctor_id}")
                                skipped_count += 1
                                current_date += timedelta(days=1)
                                continue
                            
                            # 为每个班次生成排班记录
                            for slot_start, slot_end in time_slots:
                                # 检查是否已存在相同排班
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
                                
                                if existing:
                                    logger.debug(
                                        f"排班已存在: doctor={template.doctor_id}, "
                                        f"date={current_date}, time={slot_start}-{slot_end}"
                                    )
                                    skipped_count += 1
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
                                db.add(schedule)
                                created_count += 1
                                
                                logger.debug(
                                    f"创建排班: doctor={template.doctor_id}, "
                                    f"date={current_date}, slot={time_slot}, "
                                    f"time={slot_start}-{slot_end}"
                                )
                    
                    current_date += timedelta(days=1)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"排班自动生成任务执行失败: {e}")
            raise
    
    logger.info(
        f"[定时任务] 排班自动生成完成，新建 {created_count} 条，"
        f"跳过 {skipped_count} 条"
    )
    return {"created_count": created_count, "skipped_count": skipped_count}


@celery_app.task(name="app.tasks.schedule_task.generate_schedules_for_template")
def generate_schedules_for_template(
    template_id: str,
    start_date: str,
    end_date: str
):
    """
    为指定模板生成排班（手动触发）
    
    Args:
        template_id: 模板 ID
        start_date: 开始日期（格式：YYYY-MM-DD）
        end_date: 结束日期（格式：YYYY-MM-DD）
    """
    logger.info(f"[任务] 为模板生成排班: template_id={template_id}")
    
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    created_count = 0
    
    with get_sync_db() as db:
        try:
            template = db.get(ScheduleTemplate, template_id)
            if not template or template.status != 1:
                return {"created_count": 0, "reason": "模板不存在或未启用"}
            
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
    
    logger.info(f"[任务] 模板排班生成完成: created_count={created_count}")
    return {"created_count": created_count, "template_id": template_id}

