"""Fee-type and global-template operations."""

import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.models.consultation_fee import ConsultationFeeTemplate, ConsultationFeeType
from app.schemas.consultation_fee import (
    ConsultationFeeTemplateCreate,
    ConsultationFeeTypeCreate,
    ConsultationFeeTypeUpdate,
)
from app.utils.audit import set_create_audit, set_update_audit


class ConsultationFeeTypeMixin:
    async def get_fee_types(
        self,
        status: Optional[int] = None,
        store_id: Optional[str] = None,
        include_global: bool = True,
    ) -> List[ConsultationFeeType]:
        query = select(ConsultationFeeType).options(selectinload(ConsultationFeeType.store))

        if status is not None:
            query = query.where(ConsultationFeeType.status == status)

        if store_id:
            if include_global:
                query = query.where(
                    or_(ConsultationFeeType.store_id.is_(None), ConsultationFeeType.store_id == store_id)
                )
            else:
                query = query.where(ConsultationFeeType.store_id == store_id)
        else:
            if not include_global:
                return []
            query = query.where(ConsultationFeeType.store_id.is_(None))

        query = query.order_by(ConsultationFeeType.sort_order.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_store_available_fee_types(
        self, store_id: str, status: int = 1
    ) -> List[ConsultationFeeType]:
        return await self.get_fee_types(status=status, store_id=store_id, include_global=True)

    async def get_fee_type_by_id(self, fee_type_id: str) -> Optional[ConsultationFeeType]:
        result = await self.db.execute(
            select(ConsultationFeeType)
            .options(selectinload(ConsultationFeeType.store))
            .where(ConsultationFeeType.id == fee_type_id)
        )
        return result.scalar_one_or_none()

    async def get_fee_type_by_code(
        self, code: str, store_id: Optional[str] = None
    ) -> Optional[ConsultationFeeType]:
        query = select(ConsultationFeeType).where(ConsultationFeeType.code == code)
        if store_id:
            query = query.where(ConsultationFeeType.store_id == store_id)
        else:
            query = query.where(ConsultationFeeType.store_id.is_(None))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_fee_type(
        self, data: ConsultationFeeTypeCreate, operator_id: Optional[str] = None
    ) -> ConsultationFeeType:
        fee_type = ConsultationFeeType(
            id=str(uuid.uuid4()),
            store_id=data.store_id,
            name=data.name,
            code=data.code,
            description=data.description,
            sort_order=data.sort_order,
            status=data.status,
        )
        set_create_audit(fee_type, operator_id)
        self.db.add(fee_type)
        await self.db.commit()
        await self.db.refresh(fee_type)
        return fee_type

    async def update_fee_type(
        self, fee_type_id: str, data: ConsultationFeeTypeUpdate, operator_id: Optional[str] = None
    ) -> Optional[ConsultationFeeType]:
        fee_type = await self.get_fee_type_by_id(fee_type_id)
        if not fee_type:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(fee_type, field):
                setattr(fee_type, field, value)

        set_update_audit(fee_type, operator_id)
        await self.db.commit()
        await self.db.refresh(fee_type)
        return fee_type

    async def delete_fee_type(self, fee_type_id: str) -> bool:
        fee_type = await self.get_fee_type_by_id(fee_type_id)
        if not fee_type:
            return False
        await self.db.delete(fee_type)
        await self.db.commit()
        return True

    async def get_fee_templates(self) -> List[ConsultationFeeTemplate]:
        result = await self.db.execute(
            select(ConsultationFeeTemplate).options(selectinload(ConsultationFeeTemplate.fee_type))
        )
        return list(result.scalars().all())

    async def get_fee_templates_with_types(self) -> List[dict]:
        fee_types = await self.get_fee_types(status=1, store_id=None, include_global=True)
        fee_types = [ft for ft in fee_types if ft.store_id is None]
        templates = await self.get_fee_templates()
        template_map = {t.fee_type_id: t for t in templates}

        result = []
        for ft in fee_types:
            template = template_map.get(ft.id)
            result.append(
                {
                    "id": template.id if template else None,
                    "fee_type_id": ft.id,
                    "fee_type_name": ft.name,
                    "fee_type_code": ft.code,
                    "initial_fee": template.initial_fee if template else Decimal("0"),
                    "follow_up_fee": template.follow_up_fee if template else Decimal("0"),
                    "status": template.status if template else 1,
                }
            )
        return result

    async def get_fee_template_by_id(self, template_id: str) -> Optional[ConsultationFeeTemplate]:
        result = await self.db.execute(
            select(ConsultationFeeTemplate)
            .options(selectinload(ConsultationFeeTemplate.fee_type))
            .where(ConsultationFeeTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def get_fee_template_by_type(self, fee_type_id: str) -> Optional[ConsultationFeeTemplate]:
        result = await self.db.execute(
            select(ConsultationFeeTemplate)
            .options(selectinload(ConsultationFeeTemplate.fee_type))
            .where(ConsultationFeeTemplate.fee_type_id == fee_type_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update_fee_template(
        self, data: ConsultationFeeTemplateCreate, operator_id: Optional[str] = None
    ) -> ConsultationFeeTemplate:
        template = await self.get_fee_template_by_type(data.fee_type_id)
        if template:
            template.initial_fee = data.initial_fee
            template.follow_up_fee = data.follow_up_fee
            template.status = data.status
            set_update_audit(template, operator_id)
        else:
            template = ConsultationFeeTemplate(
                id=str(uuid.uuid4()),
                fee_type_id=data.fee_type_id,
                initial_fee=data.initial_fee,
                follow_up_fee=data.follow_up_fee,
                status=data.status,
            )
            set_create_audit(template, operator_id)
            self.db.add(template)

        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def batch_update_fee_templates(self, templates: List[dict]) -> List[ConsultationFeeTemplate]:
        result = []
        for t in templates:
            fee_type_id = t.get("fee_type_id") or t.get("feeTypeId")
            initial_fee = t.get("initial_fee") or t.get("initialFee") or 0
            follow_up_fee = t.get("follow_up_fee") or t.get("followUpFee") or 0
            status = t.get("status", 1)
            if not fee_type_id:
                continue

            data = ConsultationFeeTemplateCreate(
                fee_type_id=fee_type_id,
                initial_fee=Decimal(str(initial_fee)),
                follow_up_fee=Decimal(str(follow_up_fee)),
                status=status,
            )
            template = await self.create_or_update_fee_template(data)
            result.append(template)
        return result
