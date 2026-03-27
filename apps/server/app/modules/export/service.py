"""数据导出服务 - 已升级为 Excel 格式"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Union
from datetime import date, datetime

from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.user import Patient
from app.models.doctor import Doctor
from app.models.department import Department
from app.infrastructure.excel.export_service import ExcelExportService


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
        store_ids: Optional[Union[str, List[str]]] = None,
        tenant_id: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """导出预约记录

        Args:
            store_ids: 门店过滤条件
                - None: 不过滤（超管）
                - str: 单个门店ID
                - List[str]: 多个门店ID列表
            tenant_id: 租户ID，用于租户隔离
        """
        query = select(Appointment).options(
            selectinload(Appointment.schedule),
            selectinload(Appointment.patient),
        )

        conditions = []
        if tenant_id:
            conditions.append(Appointment.tenant_id == tenant_id)
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
        # 门店过滤（空字符串或空列表不过滤）
        if store_ids:
            if isinstance(store_ids, list):
                if store_ids:  # 非空列表才过滤
                    conditions.append(Appointment.store_id.in_(store_ids))
            else:
                conditions.append(Appointment.store_id == store_ids)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Appointment.created_at.desc())

        result = await self.db.execute(query)
        appointments = result.unique().scalars().all()

        # 状态映射
        status_map = {
            0: '待支付', 1: '已预约', 2: '已签到', 3: '候诊中',
            4: '就诊中', 5: '已完成', 6: '已取消', 7: '已过期', 8: '已关闭'
        }
        time_slot_map = {'morning': '上午', 'afternoon': '下午', 'evening': '晚上', 'AM': '上午', 'PM': '下午'}

        # 构建 Excel
        headers = [
            '预约单号', '就诊日期', '时段', '排队号',
            '患者姓名', '患者手机', '身份证号',
            '医生', '科室', '状态',
            '签到时间', '完成时间', '取消时间', '取消原因',
            '创建时间'
        ]

        data = []
        for a in appointments:
            schedule = a.schedule
            patient = a.patient

            data.append([
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

        excel_bytes = ExcelExportService.create_workbook(headers, data, "预约记录")
        filename = f"appointments_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return excel_bytes, filename

    async def export_patients(
        self,
        keyword: Optional[str] = None,
        store_ids: Optional[Union[str, List[str]]] = None,
        tenant_id: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """导出患者列表

        注意：患者表没有直接的 store_id 字段，此过滤条件暂不生效。
        如需按门店过滤患者，需要通过预约记录关联查询。

        Args:
            tenant_id: 租户ID，用于租户隔离
        """
        query = select(Patient)

        conditions = []
        if tenant_id:
            conditions.append(Patient.tenant_id == tenant_id)
        if keyword:
            conditions.append(
                or_(
                    Patient.name.ilike(f"%{keyword}%"),
                    Patient.phone.ilike(f"%{keyword}%")
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Patient.created_at.desc())

        result = await self.db.execute(query)
        patients = result.scalars().all()

        gender_map = {0: '未知', 1: '男', 2: '女'}

        headers = [
            '就诊卡编号', '姓名', '手机号', '身份证号', '性别', '出生日期',
            '与本人关系', '省', '市', '区', '详细地址', '来源', '创建时间'
        ]

        source_map = {1: '用户添加', 2: '管理员添加'}

        data = []
        for p in patients:
            data.append([
                p.card_no or '',
                p.name,
                p.phone,
                p.id_card or '',
                gender_map.get(p.gender, ''),
                str(p.birthday) if p.birthday else '',
                p.relationship or '',
                p.province or '',
                p.city or '',
                p.district or '',
                p.address or '',
                source_map.get(p.source, ''),
                p.created_at.strftime('%Y-%m-%d %H:%M:%S') if p.created_at else '',
            ])

        excel_bytes = ExcelExportService.create_workbook(headers, data, "患者列表")
        filename = f"patients_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return excel_bytes, filename

    async def export_schedules(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        doctor_id: Optional[str] = None,
        store_ids: Optional[Union[str, List[str]]] = None,
        tenant_id: Optional[str] = None,
    ) -> tuple[bytes, str]:
        """导出排班记录

        Args:
            store_ids: 门店过滤条件
                - None: 不过滤（超管）
                - str: 单个门店ID
                - List[str]: 多个门店ID列表
            tenant_id: 租户ID，用于租户隔离
        """
        query = select(Schedule).options(
            selectinload(Schedule.doctor).selectinload(Doctor.department)
        )

        conditions = []
        if tenant_id:
            conditions.append(Schedule.tenant_id == tenant_id)
        if start_date:
            conditions.append(Schedule.schedule_date >= start_date)
        if end_date:
            conditions.append(Schedule.schedule_date <= end_date)
        if doctor_id:
            conditions.append(Schedule.doctor_id == doctor_id)
        # 门店过滤（空字符串或空列表不过滤）
        if store_ids:
            if isinstance(store_ids, list):
                if store_ids:  # 非空列表才过滤
                    conditions.append(Schedule.store_id.in_(store_ids))
            else:
                conditions.append(Schedule.store_id == store_ids)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(Schedule.schedule_date, Schedule.time_slot)

        result = await self.db.execute(query)
        schedules = result.unique().scalars().all()

        status_map = {0: '停诊', 1: '正常'}
        time_slot_map = {'morning': '上午', 'afternoon': '下午', 'evening': '晚上', 'AM': '上午', 'PM': '下午'}

        headers = [
            '排班日期', '时段', '医生', '科室',
            '总号源', '已预约', '剩余', '状态', '创建时间'
        ]

        data = []
        for s in schedules:
            doctor = s.doctor
            dept = doctor.department if doctor else None

            data.append([
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

        excel_bytes = ExcelExportService.create_workbook(headers, data, "排班记录")
        filename = f"schedules_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
        return excel_bytes, filename
