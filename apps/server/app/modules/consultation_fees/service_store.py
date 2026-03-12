"""Store-level consultation-fee template operations."""

import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.models.consultation_fee import ConsultationFeeTemplate, StoreFeeTemplate
from app.schemas.consultation_fee import StoreFeeTemplateBatchCreate
from app.utils.audit import set_create_audit, set_update_audit


class ConsultationFeeStoreMixin:
    async def get_store_fee_templates(self, store_id: str) -> List[StoreFeeTemplate]:
        result = await self.db.execute(
            select(StoreFeeTemplate)
            .options(selectinload(StoreFeeTemplate.store), selectinload(StoreFeeTemplate.fee_type))
            .where(StoreFeeTemplate.store_id == store_id)
        )
        return list(result.scalars().all())

    async def get_store_fee_template_by_type(
        self, store_id: str, fee_type_id: str
    ) -> Optional[StoreFeeTemplate]:
        result = await self.db.execute(
            select(StoreFeeTemplate)
            .options(selectinload(StoreFeeTemplate.store), selectinload(StoreFeeTemplate.fee_type))
            .where(
                StoreFeeTemplate.store_id == store_id,
                StoreFeeTemplate.fee_type_id == fee_type_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_store_fee_templates_with_types(self, store_id: str) -> List[dict]:
        fee_types = await self.get_store_available_fee_types(store_id, status=1)
        store_templates = await self.get_store_fee_templates(store_id)
        store_template_map = {t.fee_type_id: t for t in store_templates}
        global_templates = await self.get_fee_templates()
        global_template_map = {t.fee_type_id: t for t in global_templates}

        result = []
        for ft in fee_types:
            store_template = store_template_map.get(ft.id)
            global_template = global_template_map.get(ft.id)
            result.append(
                {
                    "id": store_template.id if store_template else None,
                    "store_id": store_id,
                    "fee_type_id": ft.id,
                    "fee_type_name": ft.name,
                    "fee_type_code": ft.code,
                    "initial_fee": store_template.initial_fee if store_template else Decimal("0"),
                    "follow_up_fee": store_template.follow_up_fee if store_template else Decimal("0"),
                    "global_initial_fee": global_template.initial_fee if global_template else Decimal("0"),
                    "global_follow_up_fee": global_template.follow_up_fee if global_template else Decimal("0"),
                    "status": store_template.status if store_template else 1,
                    "is_global_type": ft.store_id is None,
                }
            )
        return result

    async def create_or_update_store_fee_template(
        self,
        store_id: str,
        fee_type_id: str,
        initial_fee: Decimal,
        follow_up_fee: Decimal,
        status: int = 1,
        operator_id: Optional[str] = None,
    ) -> StoreFeeTemplate:
        template = await self.get_store_fee_template_by_type(store_id, fee_type_id)
        if template:
            template.initial_fee = initial_fee
            template.follow_up_fee = follow_up_fee
            template.status = status
            set_update_audit(template, operator_id)
        else:
            template = StoreFeeTemplate(
                id=str(uuid.uuid4()),
                store_id=store_id,
                fee_type_id=fee_type_id,
                initial_fee=initial_fee,
                follow_up_fee=follow_up_fee,
                status=status,
            )
            set_create_audit(template, operator_id)
            self.db.add(template)

        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def batch_save_store_fee_templates(
        self, data: StoreFeeTemplateBatchCreate
    ) -> List[StoreFeeTemplate]:
        result = []
        for item in data.templates:
            template = await self.create_or_update_store_fee_template(
                store_id=data.store_id,
                fee_type_id=item.fee_type_id,
                initial_fee=item.initial_fee,
                follow_up_fee=item.follow_up_fee,
            )
            result.append(template)
        return result

    async def delete_store_fee_template(self, store_id: str, fee_type_id: str) -> bool:
        template = await self.get_store_fee_template_by_type(store_id, fee_type_id)
        if not template:
            return False
        await self.db.delete(template)
        await self.db.commit()
        return True

    async def get_effective_template(self, store_id: str, fee_type_id: str) -> dict:
        store_template = await self.get_store_fee_template_by_type(store_id, fee_type_id)
        if store_template:
            return {
                "source": "store",
                "template": store_template,
                "initial_fee": store_template.initial_fee,
                "follow_up_fee": store_template.follow_up_fee,
            }

        global_template = await self.get_fee_template_by_type(fee_type_id)
        if global_template:
            return {
                "source": "global",
                "template": global_template,
                "initial_fee": global_template.initial_fee,
                "follow_up_fee": global_template.follow_up_fee,
            }

        return {"source": None, "template": None, "initial_fee": Decimal("0"), "follow_up_fee": Decimal("0")}

    async def apply_template_to_doctor(
        self,
        doctor_id: str,
        store_id: str,
        fee_type_id: str,
        operator_id: Optional[str] = None,
    ) -> bool:
        effective = await self.get_effective_template(store_id, fee_type_id)
        if not effective["template"]:
            return False

        existing = await self.get_doctor_fee_unique(doctor_id, store_id, fee_type_id)
        if existing:
            existing.initial_fee = effective["initial_fee"]
            existing.follow_up_fee = effective["follow_up_fee"]
            set_update_audit(existing, operator_id)
        else:
            from app.models.consultation_fee import DoctorConsultationFee

            fee = DoctorConsultationFee(
                id=str(uuid.uuid4()),
                doctor_id=doctor_id,
                store_id=store_id,
                fee_type_id=fee_type_id,
                initial_fee=effective["initial_fee"],
                follow_up_fee=effective["follow_up_fee"],
                use_template=1,
                status=1,
            )
            set_create_audit(fee, operator_id)
            self.db.add(fee)

        await self.db.commit()
        return True
