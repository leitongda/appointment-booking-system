from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, or_, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from decimal import Decimal
import uuid

from app.models.consultation_fee import ConsultationFeeType, ConsultationFeeTemplate, StoreFeeTemplate, DoctorConsultationFee
from app.models.doctor import Doctor
from app.schemas.consultation_fee import (
    ConsultationFeeTypeCreate, ConsultationFeeTypeUpdate,
    ConsultationFeeTemplateCreate, ConsultationFeeTemplateUpdate,
    DoctorConsultationFeeCreate, DoctorConsultationFeeUpdate,
    DoctorConsultationFeeBatchCreate, DoctorConsultationFeeItem,
    StoreFeeTemplateCreate, StoreFeeTemplateItem, StoreFeeTemplateBatchCreate
)


class ConsultationFeeService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ========== 诊费类型相关 ==========
    
    async def get_fee_types(
        self, 
        status: Optional[int] = None,
        store_id: Optional[str] = None,
        include_global: bool = True
    ) -> List[ConsultationFeeType]:
        """
        获取诊费类型列表
        
        Args:
            status: 状态筛选
            store_id: 门店ID，如果提供则返回该门店的专属类型
            include_global: 是否包含全局类型（store_id=None的类型）
        """
        query = select(ConsultationFeeType).options(
            selectinload(ConsultationFeeType.store)
        )
        
        if status is not None:
            query = query.where(ConsultationFeeType.status == status)
        
        if store_id:
            if include_global:
                # 返回全局类型 + 门店专属类型
                query = query.where(
                    or_(
                        ConsultationFeeType.store_id.is_(None),
                        ConsultationFeeType.store_id == store_id
                    )
                )
            else:
                # 仅返回门店专属类型
                query = query.where(ConsultationFeeType.store_id == store_id)
        else:
            if not include_global:
                # 不包含全局类型时返回空
                return []
            # 仅返回全局类型
            query = query.where(ConsultationFeeType.store_id.is_(None))
        
        query = query.order_by(ConsultationFeeType.sort_order.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_store_available_fee_types(self, store_id: str, status: int = 1) -> List[ConsultationFeeType]:
        """获取门店可用的诊费类型（全局类型 + 门店专属类型）"""
        return await self.get_fee_types(status=status, store_id=store_id, include_global=True)
    
    async def get_fee_type_by_id(self, fee_type_id: str) -> Optional[ConsultationFeeType]:
        """根据ID获取诊费类型"""
        result = await self.db.execute(
            select(ConsultationFeeType)
            .options(selectinload(ConsultationFeeType.store))
            .where(ConsultationFeeType.id == fee_type_id)
        )
        return result.scalar_one_or_none()
    
    async def get_fee_type_by_code(self, code: str, store_id: Optional[str] = None) -> Optional[ConsultationFeeType]:
        """根据编码获取诊费类型"""
        query = select(ConsultationFeeType).where(ConsultationFeeType.code == code)
        if store_id:
            query = query.where(ConsultationFeeType.store_id == store_id)
        else:
            query = query.where(ConsultationFeeType.store_id.is_(None))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_fee_type(self, data: ConsultationFeeTypeCreate) -> ConsultationFeeType:
        """创建诊费类型"""
        fee_type = ConsultationFeeType(
            id=str(uuid.uuid4()),
            store_id=data.store_id,
            name=data.name,
            code=data.code,
            description=data.description,
            sort_order=data.sort_order,
            status=data.status
        )
        self.db.add(fee_type)
        await self.db.commit()
        await self.db.refresh(fee_type)
        return fee_type
    
    async def update_fee_type(self, fee_type_id: str, data: ConsultationFeeTypeUpdate) -> Optional[ConsultationFeeType]:
        """更新诊费类型"""
        fee_type = await self.get_fee_type_by_id(fee_type_id)
        if not fee_type:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(fee_type, field):
                setattr(fee_type, field, value)
        
        await self.db.commit()
        await self.db.refresh(fee_type)
        return fee_type
    
    async def delete_fee_type(self, fee_type_id: str) -> bool:
        """删除诊费类型"""
        fee_type = await self.get_fee_type_by_id(fee_type_id)
        if not fee_type:
            return False
        
        await self.db.delete(fee_type)
        await self.db.commit()
        return True
    
    # ========== 全局诊费模板相关 ==========
    
    async def get_fee_templates(self) -> List[ConsultationFeeTemplate]:
        """获取全局诊费模板列表"""
        result = await self.db.execute(
            select(ConsultationFeeTemplate)
            .options(selectinload(ConsultationFeeTemplate.fee_type))
        )
        return list(result.scalars().all())
    
    async def get_fee_templates_with_types(self) -> List[dict]:
        """获取全局诊费模板列表（带类型信息，包含未配置的类型）"""
        # 获取所有启用的全局诊费类型
        fee_types = await self.get_fee_types(status=1, store_id=None, include_global=True)
        # 仅保留全局类型
        fee_types = [ft for ft in fee_types if ft.store_id is None]
        # 获取所有模板
        templates = await self.get_fee_templates()
        template_map = {t.fee_type_id: t for t in templates}
        
        result = []
        for ft in fee_types:
            template = template_map.get(ft.id)
            result.append({
                'id': template.id if template else None,
                'fee_type_id': ft.id,
                'fee_type_name': ft.name,
                'fee_type_code': ft.code,
                'initial_fee': template.initial_fee if template else Decimal('0'),
                'follow_up_fee': template.follow_up_fee if template else Decimal('0'),
                'status': template.status if template else 1
            })
        return result
    
    async def get_fee_template_by_id(self, template_id: str) -> Optional[ConsultationFeeTemplate]:
        """根据ID获取诊费模板"""
        result = await self.db.execute(
            select(ConsultationFeeTemplate)
            .options(selectinload(ConsultationFeeTemplate.fee_type))
            .where(ConsultationFeeTemplate.id == template_id)
        )
        return result.scalar_one_or_none()
    
    async def get_fee_template_by_type(self, fee_type_id: str) -> Optional[ConsultationFeeTemplate]:
        """根据诊费类型ID获取全局模板"""
        result = await self.db.execute(
            select(ConsultationFeeTemplate)
            .options(selectinload(ConsultationFeeTemplate.fee_type))
            .where(ConsultationFeeTemplate.fee_type_id == fee_type_id)
        )
        return result.scalar_one_or_none()
    
    async def create_or_update_fee_template(self, data: ConsultationFeeTemplateCreate) -> ConsultationFeeTemplate:
        """创建或更新全局诊费模板"""
        template = await self.get_fee_template_by_type(data.fee_type_id)
        
        if template:
            template.initial_fee = data.initial_fee
            template.follow_up_fee = data.follow_up_fee
            template.status = data.status
        else:
            template = ConsultationFeeTemplate(
                id=str(uuid.uuid4()),
                fee_type_id=data.fee_type_id,
                initial_fee=data.initial_fee,
                follow_up_fee=data.follow_up_fee,
                status=data.status
            )
            self.db.add(template)
        
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def batch_update_fee_templates(self, templates: List[dict]) -> List[ConsultationFeeTemplate]:
        """批量更新全局诊费模板"""
        result = []
        for t in templates:
            data = ConsultationFeeTemplateCreate(
                fee_type_id=t['fee_type_id'],
                initial_fee=Decimal(str(t.get('initial_fee', 0))),
                follow_up_fee=Decimal(str(t.get('follow_up_fee', 0))),
                status=t.get('status', 1)
            )
            template = await self.create_or_update_fee_template(data)
            result.append(template)
        return result
    
    # ========== 门店诊费模板相关 ==========
    
    async def get_store_fee_templates(self, store_id: str) -> List[StoreFeeTemplate]:
        """获取门店诊费模板列表"""
        result = await self.db.execute(
            select(StoreFeeTemplate)
            .options(
                selectinload(StoreFeeTemplate.store),
                selectinload(StoreFeeTemplate.fee_type)
            )
            .where(StoreFeeTemplate.store_id == store_id)
        )
        return list(result.scalars().all())
    
    async def get_store_fee_template_by_type(self, store_id: str, fee_type_id: str) -> Optional[StoreFeeTemplate]:
        """根据门店ID和诊费类型ID获取门店模板"""
        result = await self.db.execute(
            select(StoreFeeTemplate)
            .options(
                selectinload(StoreFeeTemplate.store),
                selectinload(StoreFeeTemplate.fee_type)
            )
            .where(
                StoreFeeTemplate.store_id == store_id,
                StoreFeeTemplate.fee_type_id == fee_type_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_store_fee_templates_with_types(self, store_id: str) -> List[dict]:
        """
        获取门店诊费模板列表（带类型信息，包含未配置的类型）
        返回门店可用的所有诊费类型及其模板配置（门店模板优先，否则显示全局模板作为参考）
        """
        # 获取门店可用的所有诊费类型（全局 + 门店专属）
        fee_types = await self.get_store_available_fee_types(store_id, status=1)
        
        # 获取门店模板
        store_templates = await self.get_store_fee_templates(store_id)
        store_template_map = {t.fee_type_id: t for t in store_templates}
        
        # 获取全局模板（用于参考）
        global_templates = await self.get_fee_templates()
        global_template_map = {t.fee_type_id: t for t in global_templates}
        
        result = []
        for ft in fee_types:
            store_template = store_template_map.get(ft.id)
            global_template = global_template_map.get(ft.id)
            is_global_type = ft.store_id is None
            
            result.append({
                'id': store_template.id if store_template else None,
                'store_id': store_id,
                'fee_type_id': ft.id,
                'fee_type_name': ft.name,
                'fee_type_code': ft.code,
                'initial_fee': store_template.initial_fee if store_template else Decimal('0'),
                'follow_up_fee': store_template.follow_up_fee if store_template else Decimal('0'),
                'global_initial_fee': global_template.initial_fee if global_template else Decimal('0'),
                'global_follow_up_fee': global_template.follow_up_fee if global_template else Decimal('0'),
                'status': store_template.status if store_template else 1,
                'is_global_type': is_global_type
            })
        return result
    
    async def create_or_update_store_fee_template(
        self, store_id: str, fee_type_id: str, initial_fee: Decimal, follow_up_fee: Decimal, status: int = 1
    ) -> StoreFeeTemplate:
        """创建或更新门店诊费模板"""
        template = await self.get_store_fee_template_by_type(store_id, fee_type_id)
        
        if template:
            template.initial_fee = initial_fee
            template.follow_up_fee = follow_up_fee
            template.status = status
        else:
            template = StoreFeeTemplate(
                id=str(uuid.uuid4()),
                store_id=store_id,
                fee_type_id=fee_type_id,
                initial_fee=initial_fee,
                follow_up_fee=follow_up_fee,
                status=status
            )
            self.db.add(template)
        
        await self.db.commit()
        await self.db.refresh(template)
        return template
    
    async def batch_save_store_fee_templates(self, data: StoreFeeTemplateBatchCreate) -> List[StoreFeeTemplate]:
        """批量保存门店诊费模板"""
        result = []
        for item in data.templates:
            template = await self.create_or_update_store_fee_template(
                store_id=data.store_id,
                fee_type_id=item.fee_type_id,
                initial_fee=item.initial_fee,
                follow_up_fee=item.follow_up_fee
            )
            result.append(template)
        return result
    
    async def delete_store_fee_template(self, store_id: str, fee_type_id: str) -> bool:
        """删除门店诊费模板"""
        template = await self.get_store_fee_template_by_type(store_id, fee_type_id)
        if not template:
            return False
        
        await self.db.delete(template)
        await self.db.commit()
        return True
    
    async def get_effective_template(self, store_id: str, fee_type_id: str) -> dict:
        """
        获取有效的模板金额
        优先使用门店模板，如果门店未配置则使用全局模板
        """
        # 先查门店模板
        store_template = await self.get_store_fee_template_by_type(store_id, fee_type_id)
        if store_template:
            return {
                'initial_fee': store_template.initial_fee,
                'follow_up_fee': store_template.follow_up_fee,
                'source': 'store'
            }
        
        # 再查全局模板
        global_template = await self.get_fee_template_by_type(fee_type_id)
        if global_template:
            return {
                'initial_fee': global_template.initial_fee,
                'follow_up_fee': global_template.follow_up_fee,
                'source': 'global'
            }
        
        # 都没有配置
        return {
            'initial_fee': Decimal('0'),
            'follow_up_fee': Decimal('0'),
            'source': 'default'
        }
    
    async def apply_template_to_doctor(
        self, 
        doctor_id: str, 
        store_id: str, 
        department_id: str
    ) -> List[DoctorConsultationFee]:
        """
        一键带入模板：将门店模板的金额应用到医生诊费配置
        优先使用门店模板，如果门店未配置则使用全局模板
        """
        # 获取门店可用的所有诊费类型
        fee_types = await self.get_store_available_fee_types(store_id, status=1)
        
        fees = []
        for ft in fee_types:
            # 获取有效的模板金额
            template_data = await self.get_effective_template(store_id, ft.id)
            
            fees.append(DoctorConsultationFeeItem(
                fee_type_id=ft.id,
                fee_type_name=ft.name,
                fee_type_code=ft.code,
                initial_fee=template_data['initial_fee'],
                follow_up_fee=template_data['follow_up_fee']
            ))
        
        # 批量保存
        batch_data = DoctorConsultationFeeBatchCreate(
            doctor_id=doctor_id,
            store_id=store_id,
            department_id=department_id,
            fees=fees
        )
        
        return await self.batch_save_doctor_fees(batch_data)
    
    # ========== 医生诊费配置相关 ==========
    
    async def get_doctor_fees(
        self,
        doctor_id: str,
        store_id: Optional[str] = None,
        department_id: Optional[str] = None
    ) -> List[DoctorConsultationFee]:
        """获取医生诊费配置"""
        query = select(DoctorConsultationFee).options(
            selectinload(DoctorConsultationFee.store),
            selectinload(DoctorConsultationFee.department),
            selectinload(DoctorConsultationFee.fee_type)
        ).where(DoctorConsultationFee.doctor_id == doctor_id)
        
        if store_id:
            query = query.where(DoctorConsultationFee.store_id == store_id)
        if department_id:
            query = query.where(DoctorConsultationFee.department_id == department_id)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_doctor_fee_by_id(self, fee_id: str) -> Optional[DoctorConsultationFee]:
        """根据ID获取医生诊费配置"""
        result = await self.db.execute(
            select(DoctorConsultationFee).options(
                selectinload(DoctorConsultationFee.store),
                selectinload(DoctorConsultationFee.department),
                selectinload(DoctorConsultationFee.fee_type)
            ).where(DoctorConsultationFee.id == fee_id)
        )
        return result.scalar_one_or_none()
    
    async def get_doctor_fee_unique(
        self, doctor_id: str, store_id: str, department_id: str, fee_type_id: str
    ) -> Optional[DoctorConsultationFee]:
        """获取唯一的医生诊费配置"""
        result = await self.db.execute(
            select(DoctorConsultationFee).where(
                DoctorConsultationFee.doctor_id == doctor_id,
                DoctorConsultationFee.store_id == store_id,
                DoctorConsultationFee.department_id == department_id,
                DoctorConsultationFee.fee_type_id == fee_type_id
            )
        )
        return result.scalar_one_or_none()
    
    async def create_doctor_fee(self, data: DoctorConsultationFeeCreate) -> DoctorConsultationFee:
        """创建医生诊费配置"""
        fee = DoctorConsultationFee(
            id=str(uuid.uuid4()),
            doctor_id=data.doctor_id,
            store_id=data.store_id,
            department_id=data.department_id,
            fee_type_id=data.fee_type_id,
            initial_fee=data.initial_fee,
            follow_up_fee=data.follow_up_fee,
            status=data.status
        )
        self.db.add(fee)
        await self.db.commit()
        await self.db.refresh(fee)
        return fee
    
    async def update_doctor_fee(self, fee_id: str, data: DoctorConsultationFeeUpdate) -> Optional[DoctorConsultationFee]:
        """更新医生诊费配置"""
        fee = await self.get_doctor_fee_by_id(fee_id)
        if not fee:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(fee, field):
                setattr(fee, field, value)
        
        await self.db.commit()
        await self.db.refresh(fee)
        return fee
    
    async def batch_save_doctor_fees(self, data: DoctorConsultationFeeBatchCreate) -> List[DoctorConsultationFee]:
        """批量保存医生诊费配置"""
        result = []
        
        for item in data.fees:
            existing = await self.get_doctor_fee_unique(
                data.doctor_id, data.store_id, data.department_id, item.fee_type_id
            )
            
            if existing:
                existing.initial_fee = item.initial_fee
                existing.follow_up_fee = item.follow_up_fee
                await self.db.flush()
                result.append(existing)
            else:
                fee = DoctorConsultationFee(
                    id=str(uuid.uuid4()),
                    doctor_id=data.doctor_id,
                    store_id=data.store_id,
                    department_id=data.department_id,
                    fee_type_id=item.fee_type_id,
                    initial_fee=item.initial_fee,
                    follow_up_fee=item.follow_up_fee,
                    status=1
                )
                self.db.add(fee)
                await self.db.flush()
                result.append(fee)
        
        await self.db.commit()
        return result
    
    async def delete_doctor_fee(self, fee_id: str) -> bool:
        """删除医生诊费配置"""
        fee = await self.get_doctor_fee_by_id(fee_id)
        if not fee:
            return False
        
        await self.db.delete(fee)
        await self.db.commit()
        return True
    
    async def delete_doctor_fees_by_store_department(
        self, doctor_id: str, store_id: str, department_id: str
    ) -> int:
        """删除医生在指定门店科室的所有诊费配置"""
        result = await self.db.execute(
            delete(DoctorConsultationFee).where(
                DoctorConsultationFee.doctor_id == doctor_id,
                DoctorConsultationFee.store_id == store_id,
                DoctorConsultationFee.department_id == department_id
            )
        )
        await self.db.commit()
        return result.rowcount
    
    async def get_doctor_fee_setting(self, doctor_id: str) -> dict:
        """获取医生诊费设置（包含是否使用模板）"""
        from app.models.doctor import Doctor
        
        result = await self.db.execute(
            select(Doctor).where(Doctor.id == doctor_id)
        )
        doctor = result.scalar_one_or_none()
        
        if not doctor:
            return None
        
        fees = await self.get_doctor_fees(doctor_id)
        
        return {
            'doctor_id': doctor.id,
            'doctor_name': doctor.name,
            'use_fee_template': doctor.use_fee_template or 0,
            'fees': fees
        }
    
    async def update_doctor_use_template(self, doctor_id: str, use_template: int) -> bool:
        """更新医生是否使用诊费模板"""
        from app.models.doctor import Doctor
        
        result = await self.db.execute(
            select(Doctor).where(Doctor.id == doctor_id)
        )
        doctor = result.scalar_one_or_none()
        
        if not doctor:
            return False
        
        doctor.use_fee_template = use_template
        await self.db.commit()
        return True
    
    async def get_doctor_fees_grouped(self, doctor_id: str) -> List[dict]:
        """获取医生诊费配置（按门店-科室分组）"""
        fees = await self.get_doctor_fees(doctor_id)
        
        # 按门店-科室分组
        groups = {}
        for fee in fees:
            key = f"{fee.store_id}_{fee.department_id}"
            if key not in groups:
                groups[key] = {
                    'store_id': fee.store_id,
                    'store_name': fee.store.name if fee.store else '',
                    'department_id': fee.department_id,
                    'department_name': fee.department.name if fee.department else '',
                    'fees': []
                }
            groups[key]['fees'].append({
                'fee_type_id': fee.fee_type_id,
                'fee_type_name': fee.fee_type.name if fee.fee_type else '',
                'fee_type_code': fee.fee_type.code if fee.fee_type else '',
                'initial_fee': fee.initial_fee,
                'follow_up_fee': fee.follow_up_fee
            })
        
        return list(groups.values())
