"""检查报告服务"""
import uuid
from typing import Optional, List, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.examination_report import ExaminationReport
from app.models.appointment import Appointment
from app.models.user import Patient
from app.middleware.tenant_context import get_current_tenant_id
from app.utils.audit import set_create_audit


class ExaminationReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, doctor_id: str, data) -> ExaminationReport:
        """创建检查报告"""
        tenant_id = get_current_tenant_id()

        # 验证预约存在且属于该医生
        appointment = await self.db.get(Appointment, data.appointment_id)
        if not appointment:
            raise ValueError("预约不存在")

        # 获取患者信息
        patient_id = appointment.patient_id or appointment.user_id
        if not patient_id:
            raise ValueError("无法确定患者")

        report = ExaminationReport(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            store_id=appointment.store_id,
            record_id=data.record_id,
            appointment_id=data.appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            report_type=data.report_type,
            title=data.title,
            description=data.description,
            file_name=data.file_name,
            file_key=data.file_key,
            file_size=data.file_size,
            file_type=data.file_type,
            file_url=data.file_url,
        )
        set_create_audit(report, doctor_id)

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_by_id(self, report_id: str) -> Optional[ExaminationReport]:
        """根据ID获取报告"""
        stmt = select(ExaminationReport).where(ExaminationReport.id == report_id)
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(ExaminationReport.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_appointment(
        self, appointment_id: str
    ) -> List[ExaminationReport]:
        """按预约获取报告列表"""
        stmt = (
            select(ExaminationReport)
            .where(ExaminationReport.appointment_id == appointment_id)
            .order_by(ExaminationReport.created_at.desc())
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(ExaminationReport.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_patient(
        self,
        patient_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[ExaminationReport], int]:
        """按患者获取报告列表（分页）"""
        conditions = [ExaminationReport.patient_id == patient_id]
        tenant_id = get_current_tenant_id()
        if tenant_id:
            conditions.append(ExaminationReport.tenant_id == tenant_id)

        where_clause = and_(*conditions)

        # 统计总数
        count_stmt = select(func.count(ExaminationReport.id)).where(where_clause)
        total = await self.db.scalar(count_stmt) or 0

        # 分页查询
        stmt = (
            select(ExaminationReport)
            .where(where_clause)
            .order_by(ExaminationReport.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        reports = list(result.scalars().all())
        return reports, total

    async def get_by_record(self, record_id: str) -> List[ExaminationReport]:
        """按病历获取报告列表"""
        stmt = (
            select(ExaminationReport)
            .where(ExaminationReport.record_id == record_id)
            .order_by(ExaminationReport.created_at.desc())
        )
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(ExaminationReport.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_list(
        self,
        keyword: Optional[str] = None,
        report_type: Optional[str] = None,
        store_id: Optional[str] = None,
        doctor_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[ExaminationReport], int]:
        """获取报告列表（分页，支持多条件筛选）"""
        conditions = []
        tenant_id = get_current_tenant_id()
        if tenant_id:
            conditions.append(ExaminationReport.tenant_id == tenant_id)
        if report_type:
            conditions.append(ExaminationReport.report_type == report_type)
        if store_id:
            conditions.append(ExaminationReport.store_id == store_id)
        if doctor_id:
            conditions.append(ExaminationReport.doctor_id == doctor_id)
        if patient_id:
            conditions.append(ExaminationReport.patient_id == patient_id)
        if start_date:
            conditions.append(ExaminationReport.created_at >= start_date)
        if end_date:
            conditions.append(ExaminationReport.created_at <= end_date)

        # 关键字搜索：标题、文件名
        if keyword:
            from sqlalchemy import or_
            conditions.append(
                or_(
                    ExaminationReport.title.ilike(f'%{keyword}%'),
                    ExaminationReport.file_name.ilike(f'%{keyword}%'),
                )
            )

        where_clause = and_(*conditions) if conditions else None

        # 统计总数
        count_stmt = select(func.count(ExaminationReport.id))
        if where_clause is not None:
            count_stmt = count_stmt.where(where_clause)
        total = await self.db.scalar(count_stmt) or 0

        # 分页查询
        stmt = select(ExaminationReport)
        if where_clause is not None:
            stmt = stmt.where(where_clause)
        stmt = (
            stmt
            .order_by(ExaminationReport.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(stmt)
        reports = list(result.scalars().all())
        return reports, total

    async def delete(self, report_id: str, doctor_id: str) -> bool:
        """删除报告（仅创建者医生可删除）"""
        report = await self.get_by_id(report_id)
        if not report:
            return False
        if report.doctor_id != doctor_id:
            raise PermissionError("仅创建报告的医生可删除")

        await self.db.delete(report)
        await self.db.commit()
        return True
