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

logger = logging.getLogger(__name__)


def get_month_week(d: date) -> int:
    """获取日期在月内的周数"""
    return (d.day - 1) // 7 + 1


def get_year_week(d: date) -> int:
    """获取日期在年内的周数"""
    return d.isocalendar()[1]


def should_generate_schedule(d: date, schedule_mode: str) -> bool:
    """判断指定日期是否应该生成排班"""
    month_week = get_month_week(d)
    year_week = get_year_week(d)
    
    if schedule_mode == "weekly":
        return True
    elif schedule_mode == "month_week_1":
        return month_week == 1
    elif schedule_mode == "month_week_2":
        return month_week == 2
    elif schedule_mode == "month_week_3":
        return month_week == 3
    elif schedule_mode == "month_week_4":
        return month_week == 4
    elif schedule_mode == "month_week_5":
        return month_week == 5
    elif schedule_mode == "year_odd_week":
        return year_week % 2 == 1
    elif schedule_mode == "year_even_week":
        return year_week % 2 == 0
    return False


def get_time_slot_from_time(start_time) -> str:
    """根据开始时间判断时段"""
    hour = start_time.hour
    if hour < 12:
        return "morning"
    elif hour < 18:
        return "afternoon"
    else:
        return "evening"


def is_rest_day(db: Session, check_date: date, store_id: str = None) -> bool:
    """检查是否为休息日"""
    try:
        query = select(RestDay).where(
            and_(
                RestDay.rest_date == check_date,
                RestDay.status == 1
            )
        )
        
        # 如果指定了门店，还需要检查门店级别的休息日
        if store_id:
            query = query.where(
                (RestDay.store_id == None) | (RestDay.store_id == store_id)
            )
        else:
            query = query.where(RestDay.store_id == None)
        
        result = db.execute(query)
        return result.scalar_one_or_none() is not None
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
                current_date = today
                
                while current_date <= end_date:
                    weekday = current_date.isoweekday()  # 1-7 代表周一到周日
                    
                    # 检查星期是否匹配
                    if weekday == template.weekday:
                        # 检查排班方式是否匹配
                        if should_generate_schedule(current_date, template.schedule_mode):
                            # 检查是否为休息日
                            if is_rest_day(db, current_date, template.store_id):
                                logger.debug(f"跳过休息日: {current_date}")
                                skipped_count += 1
                                current_date += timedelta(days=1)
                                continue
                            
                            # 检查是否已存在相同排班
                            existing = db.execute(
                                select(Schedule).where(
                                    and_(
                                        Schedule.doctor_id == template.doctor_id,
                                        Schedule.schedule_date == current_date,
                                        Schedule.start_time == template.start_time,
                                        Schedule.end_time == template.end_time
                                    )
                                )
                            ).scalar_one_or_none()
                            
                            if existing:
                                logger.debug(
                                    f"排班已存在: doctor={template.doctor_id}, "
                                    f"date={current_date}"
                                )
                                skipped_count += 1
                                current_date += timedelta(days=1)
                                continue
                            
                            # 创建新排班
                            time_slot = get_time_slot_from_time(template.start_time)
                            schedule = Schedule(
                                id=str(uuid.uuid4()),
                                doctor_id=template.doctor_id,
                                store_id=template.store_id,
                                template_id=template.id,
                                schedule_date=current_date,
                                time_slot=time_slot,
                                start_time=template.start_time,
                                end_time=template.end_time,
                                total_slots=template.total_slots,
                                appointment_type=template.appointment_type,
                                booked_slots=0,
                                status=1
                            )
                            db.add(schedule)
                            created_count += 1
                            
                            logger.debug(
                                f"创建排班: doctor={template.doctor_id}, "
                                f"date={current_date}, slot={time_slot}"
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
            
            current_date = start
            while current_date <= end:
                weekday = current_date.isoweekday()
                
                if weekday == template.weekday:
                    if should_generate_schedule(current_date, template.schedule_mode):
                        if is_rest_day(db, current_date, template.store_id):
                            current_date += timedelta(days=1)
                            continue
                        
                        existing = db.execute(
                            select(Schedule).where(
                                and_(
                                    Schedule.doctor_id == template.doctor_id,
                                    Schedule.schedule_date == current_date,
                                    Schedule.start_time == template.start_time,
                                    Schedule.end_time == template.end_time
                                )
                            )
                        ).scalar_one_or_none()
                        
                        if not existing:
                            time_slot = get_time_slot_from_time(template.start_time)
                            schedule = Schedule(
                                id=str(uuid.uuid4()),
                                doctor_id=template.doctor_id,
                                store_id=template.store_id,
                                template_id=template.id,
                                schedule_date=current_date,
                                time_slot=time_slot,
                                start_time=template.start_time,
                                end_time=template.end_time,
                                total_slots=template.total_slots,
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

