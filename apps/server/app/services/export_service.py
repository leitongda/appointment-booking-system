"""数据导出服务"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import date, datetime
import io
import csv

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.user import Patient
from app.models.doctor import Doctor
from app.models.department import Department


class ExportService:
    """数据导出服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def export_appointments(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[int] = None,
        doctor_id: Optional[str] = None,
        department_id: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """导出预约记录"""
        query = select(Appointment).options(
            selectinload(Appointment.schedule),
            selectinload(Appointment.patient),
        )
        
        conditions = []
        if start_date:
            query = query.join(Schedule)
            conditions.append(Schedule.schedule_date >= start_date)
        if end_date:
            if Schedule not in [mapper.class_ for mapper in query.column_descriptions]:
                query = query.join(Schedule)
            conditions.append(Schedule.schedule_date <= end_date)
        if status is not None:
            conditions.append(Appointment.status == status)
        if doctor_id:
            conditions.append(Appointment.doctor_id == doctor_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Appointment.created_at.desc())
        
        result = await self.db.execute(query)
        appointments = result.unique().scalars().all()
        
        # 状态映射
        status_map = {
            1: '待就诊', 2: '已签到', 3: '就诊中', 4: '已过号',
            5: '已完成', 6: '已取消', 7: '爽约'
        }
        time_slot_map = {'AM': '上午', 'PM': '下午'}
        
        # 构建CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 表头
        writer.writerow([
            '预约单号', '就诊日期', '时段', '排队号',
            '患者姓名', '患者手机', '身份证号',
            '医生', '科室', '状态',
            '签到时间', '完成时间', '取消时间', '取消原因',
            '创建时间'
        ])
        
        # 数据
        for a in appointments:
            schedule = a.schedule
            patient = a.patient
            
            writer.writerow([
                a.appointment_no,
                str(schedule.schedule_date) if schedule else '',
                time_slot_map.get(schedule.time_slot, '') if schedule else '',
                a.queue_number,
                patient.name if patient else '',
                patient.phone if patient else '',
                patient.id_card if patient else '',
                a.doctor_name or '',
                a.department_name or '',
                status_map.get(a.status, ''),
                a.sign_in_time.strftime('%Y-%m-%d %H:%M:%S') if a.sign_in_time else '',
                a.complete_time.strftime('%Y-%m-%d %H:%M:%S') if a.complete_time else '',
                a.cancel_time.strftime('%Y-%m-%d %H:%M:%S') if a.cancel_time else '',
                a.cancel_reason or '',
                a.created_at.strftime('%Y-%m-%d %H:%M:%S') if a.created_at else '',
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        # 添加BOM头，让Excel正确识别UTF-8
        csv_bytes = b'\xef\xbb\xbf' + csv_content.encode('utf-8')
        
        filename = f"appointments_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        return csv_bytes, filename
    
    async def export_patients(
        self,
        keyword: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """导出患者列表"""
        query = select(Patient)
        
        if keyword:
            from sqlalchemy import or_
            query = query.where(
                or_(
                    Patient.name.ilike(f"%{keyword}%"),
                    Patient.phone.ilike(f"%{keyword}%")
                )
            )
        
        query = query.order_by(Patient.created_at.desc())
        
        result = await self.db.execute(query)
        patients = result.scalars().all()
        
        gender_map = {0: '未知', 1: '男', 2: '女'}
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            '姓名', '手机号', '身份证号', '性别', '出生日期',
            '与用户关系', '是否默认', '创建时间'
        ])
        
        for p in patients:
            writer.writerow([
                p.name,
                p.phone,
                p.id_card or '',
                gender_map.get(p.gender, ''),
                str(p.birthday) if p.birthday else '',
                p.relationship or '',
                '是' if p.is_default else '否',
                p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else '',
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        csv_bytes = b'\xef\xbb\xbf' + csv_content.encode('utf-8')
        filename = f"patients_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        return csv_bytes, filename
    
    async def export_schedules(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        doctor_id: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """导出排班记录"""
        query = select(Schedule).options(
            selectinload(Schedule.doctor).selectinload(Doctor.department)
        )
        
        conditions = []
        if start_date:
            conditions.append(Schedule.schedule_date >= start_date)
        if end_date:
            conditions.append(Schedule.schedule_date <= end_date)
        if doctor_id:
            conditions.append(Schedule.doctor_id == doctor_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Schedule.schedule_date, Schedule.time_slot)
        
        result = await self.db.execute(query)
        schedules = result.unique().scalars().all()
        
        status_map = {0: '停诊', 1: '正常'}
        time_slot_map = {'AM': '上午', 'PM': '下午'}
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            '排班日期', '时段', '医生', '科室',
            '总号源', '已预约', '剩余', '状态', '创建时间'
        ])
        
        for s in schedules:
            doctor = s.doctor
            dept = doctor.department if doctor else None
            
            writer.writerow([
                str(s.schedule_date),
                time_slot_map.get(s.time_slot, ''),
                doctor.name if doctor else '',
                dept.name if dept else '',
                s.total_slots,
                s.booked_slots,
                s.total_slots - s.booked_slots,
                status_map.get(s.status, ''),
                s.created_at.strftime('%Y-%m-%d %H:%M:%S') if s.created_at else '',
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        csv_bytes = b'\xef\xbb\xbf' + csv_content.encode('utf-8')
        filename = f"schedules_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        return csv_bytes, filename

