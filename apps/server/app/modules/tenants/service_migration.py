"""租户数据迁移服务"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime
import uuid
import time

from sqlalchemy.orm import class_mapper

from app.models.store import Store
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.schedule_template import ScheduleTemplate
from app.models.doctor_booking_setting import DoctorBookingSetting
from app.models.booking_notice import BookingNotice
from app.models.email_template import EmailTemplate
from app.models.message import MessageTemplate
from app.models.rest_day import RestDay
from app.models.blacklist import Blacklist
from app.models.store_visit_type_config import StoreVisitTypeConfig
from app.models.store_email_recipient import StoreEmailRecipient
from app.models.consultation_fee import ConsultationFeeTemplate
from app.models.rule_set import RuleSet, RuleWindow, RuleBookingPolicy, RuleCheckinPolicy, RuleCapacityPolicy, RuleSetShiftType

from app.modules.tenants.service import TenantService


class TenantMigrationService:
    """跨租户数据迁移服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._tenant_svc = TenantService(db)

    async def precheck_migration(
        self,
        target_tenant_id: str,
        source_tenant_id: str,
        entity_types: Optional[List[str]] = None,
    ) -> dict:
        """迁移前预检：检查配额、数据量"""
        from app.modules.tenants.schemas import PrecheckQuotaItem

        target = await self._tenant_svc.get_by_id(target_tenant_id)
        if not target:
            raise ValueError("目标租户不存在")
        source = await self._tenant_svc.get_by_id(source_tenant_id)
        if not source:
            raise ValueError("源租户不存在")
        if target_tenant_id == source_tenant_id:
            raise ValueError("源租户和目标租户不能相同")

        warnings = []
        quota_checks = []
        entity_counts = {}

        count_models = {
            "stores": (Store, Store.tenant_id),
            "departments": (Department, Department.tenant_id),
            "doctors": (Doctor, Doctor.tenant_id),
            "schedule_templates": (ScheduleTemplate, ScheduleTemplate.tenant_id),
            "booking_notices": (BookingNotice, BookingNotice.tenant_id),
            "email_templates": (EmailTemplate, EmailTemplate.tenant_id),
            "message_templates": (MessageTemplate, MessageTemplate.tenant_id),
            "rest_days": (RestDay, RestDay.tenant_id),
            "blacklists": (Blacklist, Blacklist.tenant_id),
            "rule_sets": (RuleSet, RuleSet.tenant_id),
        }

        if entity_types:
            count_models = {k: v for k, v in count_models.items() if k in entity_types}

        for name, (model, filter_col) in count_models.items():
            result = await self.db.execute(
                select(func.count(model.id)).where(filter_col == source_tenant_id)
            )
            entity_counts[name] = result.scalar() or 0

        if "stores" in entity_counts:
            src = entity_counts["stores"]
            cur = await self._tenant_svc.get_store_count(target_tenant_id)
            mx = target.get_effective_max_stores()
            quota_checks.append(PrecheckQuotaItem(
                resource_name="门店", current_count=cur, max_count=mx,
                source_count=src, would_exceed=cur + src > mx,
            ))

        if "doctors" in entity_counts:
            src = entity_counts["doctors"]
            cur = await self._tenant_svc.get_doctor_count(target_tenant_id)
            mx = target.get_effective_max_doctors()
            quota_checks.append(PrecheckQuotaItem(
                resource_name="医生", current_count=cur, max_count=mx,
                source_count=src, would_exceed=cur + src > mx,
            ))

        if target.status == 3:
            warnings.append("目标租户处于试用期，功能可能受限")
        if source.status == 0:
            warnings.append("源租户已被禁用，数据可能不完整")

        can_migrate = not any(q.would_exceed for q in quota_checks)
        estimated_ms = sum(entity_counts.values()) * 15

        return {
            "can_migrate": can_migrate,
            "warnings": warnings,
            "quota_checks": quota_checks,
            "entity_counts": entity_counts,
            "estimated_duration_ms": estimated_ms,
        }

    async def migrate_data(
        self,
        target_tenant_id: str,
        source_tenant_id: str,
        preserve_ids: bool = False,
        entity_types: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> dict:
        """跨租户数据迁移

        将源租户的配置类数据复制到目标租户。
        支持按 entity_types 过滤，None 表示迁移全部支持的类型。
        """
        start_time = time.time()

        target_tenant = await self._tenant_svc.get_by_id(target_tenant_id)
        if not target_tenant:
            raise ValueError("目标租户不存在")

        source_tenant = await self._tenant_svc.get_by_id(source_tenant_id)
        if not source_tenant:
            raise ValueError("源租户不存在")

        if target_tenant_id == source_tenant_id:
            raise ValueError("源租户和目标租户不能相同")

        all_entity_configs = [
            {
                "name": "stores",
                "model": Store,
                "filter_col": Store.tenant_id,
                "quota_field": "max_stores",
                "quota_name": "门店",
            },
            {
                "name": "departments",
                "model": Department,
                "filter_col": Department.tenant_id,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "doctors",
                "model": Doctor,
                "filter_col": Doctor.tenant_id,
                "quota_field": "max_doctors",
                "quota_name": "医生",
                "depends_on": {"stores": "store_id", "departments": "department_id"},
            },
            {
                "name": "schedule_templates",
                "model": ScheduleTemplate,
                "filter_col": ScheduleTemplate.tenant_id,
                "depends_on": {"stores": "store_id", "departments": "department_id", "doctors": "doctor_id"},
            },
            {
                "name": "doctor_booking_settings",
                "model": DoctorBookingSetting,
                "filter_col": None,
                "depends_on": {"stores": "store_id", "doctors": "doctor_id"},
            },
            {
                "name": "booking_notices",
                "model": BookingNotice,
                "filter_col": BookingNotice.tenant_id,
            },
            {
                "name": "email_templates",
                "model": EmailTemplate,
                "filter_col": EmailTemplate.tenant_id,
            },
            {
                "name": "message_templates",
                "model": MessageTemplate,
                "filter_col": MessageTemplate.tenant_id,
            },
            {
                "name": "rest_days",
                "model": RestDay,
                "filter_col": RestDay.tenant_id,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "blacklists",
                "model": Blacklist,
                "filter_col": Blacklist.tenant_id,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "store_visit_type_configs",
                "model": StoreVisitTypeConfig,
                "filter_col": None,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "store_email_recipients",
                "model": StoreEmailRecipient,
                "filter_col": None,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "consultation_fee_templates",
                "model": ConsultationFeeTemplate,
                "filter_col": None,
                "depends_on": {"stores": "store_id"},
            },
            {
                "name": "rule_sets",
                "model": RuleSet,
                "filter_col": RuleSet.tenant_id,
                "depends_on": {"stores": "store_id", "departments": "department_id", "doctors": "doctor_id"},
                "has_nested": True,
            },
        ]

        if entity_types:
            entity_configs = [c for c in all_entity_configs if c["name"] in entity_types]
            valid_names = {c["name"] for c in all_entity_configs}
            invalid = set(entity_types) - valid_names
            if invalid:
                raise ValueError(f"不支持的实体类型: {', '.join(invalid)}")
        else:
            entity_configs = all_entity_configs

        # 配额预检查
        for config in entity_configs:
            quota_field = config.get("quota_field")
            if not quota_field:
                continue

            quota_name = config.get("quota_name", quota_field)
            model = config["model"]
            filter_col = config.get("filter_col")

            if filter_col is not None:
                source_count_result = await self.db.execute(
                    select(func.count(model.id)).where(filter_col == source_tenant_id)
                )
            else:
                if model == DoctorBookingSetting:
                    source_count_result = await self.db.execute(
                        select(func.count(DoctorBookingSetting.id))
                        .join(Store, DoctorBookingSetting.store_id == Store.id)
                        .where(Store.tenant_id == source_tenant_id)
                    )
                elif model == StoreVisitTypeConfig:
                    source_count_result = await self.db.execute(
                        select(func.count(StoreVisitTypeConfig.id))
                        .join(Store, StoreVisitTypeConfig.store_id == Store.id)
                        .where(Store.tenant_id == source_tenant_id)
                    )
                elif model == StoreEmailRecipient:
                    source_count_result = await self.db.execute(
                        select(func.count(StoreEmailRecipient.id))
                        .join(Store, StoreEmailRecipient.store_id == Store.id)
                        .where(Store.tenant_id == source_tenant_id)
                    )
                elif model == ConsultationFeeTemplate:
                    source_count_result = await self.db.execute(
                        select(func.count(ConsultationFeeTemplate.id))
                        .join(Store, ConsultationFeeTemplate.store_id == Store.id)
                        .where(Store.tenant_id == source_tenant_id)
                    )
                else:
                    continue

            source_count = source_count_result.scalar() or 0
            if source_count == 0:
                continue

            if quota_field == "max_stores":
                target_current = await self._tenant_svc.get_store_count(target_tenant_id)
                target_max = target_tenant.get_effective_max_stores()
            elif quota_field == "max_doctors":
                target_current = await self._tenant_svc.get_doctor_count(target_tenant_id)
                target_max = target_tenant.get_effective_max_doctors()
            else:
                continue

            if target_current + source_count > target_max:
                raise ValueError(
                    f"{quota_name}配额不足: 目标租户当前 {target_current}，"
                    f"需迁移 {source_count}，上限 {target_max}"
                )

        # 执行迁移
        copied_counts: dict = {}
        failures: List[dict] = []
        id_mappings: dict = {}

        now = datetime.utcnow()

        def _get_new_id(old_id: str) -> str:
            return old_id if preserve_ids else str(uuid.uuid4())

        def _copy_model_instance(instance, model_class, tenant_id_override: Optional[str] = None,
                                  id_override: Optional[str] = None,
                                  field_overrides: Optional[dict] = None):
            mapper = class_mapper(model_class)
            new_data = {}

            for col in mapper.columns:
                col_name = col.name
                if col.primary_key and id_override is None and not preserve_ids:
                    continue
                if col_name in ("created_at", "updated_at", "created_by", "updated_by", "deleted_at", "deleted_by"):
                    continue

                val = getattr(instance, col_name, None)

                if col_name == "tenant_id" and tenant_id_override is not None:
                    new_data[col_name] = tenant_id_override
                elif col.primary_key and id_override is not None:
                    new_data[col_name] = id_override
                elif field_overrides and col_name in field_overrides:
                    new_data[col_name] = field_overrides[col_name]
                else:
                    new_data[col_name] = val

            new_data["created_at"] = now
            new_data["updated_at"] = now
            if created_by:
                new_data["created_by"] = created_by
                new_data["updated_by"] = created_by

            return model_class(**new_data)

        for config in entity_configs:
            entity_name = config["name"]
            model = config["model"]
            filter_col = config.get("filter_col")
            depends_on = config.get("depends_on", {})
            has_nested = config.get("has_nested", False)

            try:
                if filter_col is not None:
                    result = await self.db.execute(
                        select(model).where(filter_col == source_tenant_id)
                    )
                else:
                    if model == DoctorBookingSetting:
                        result = await self.db.execute(
                            select(DoctorBookingSetting)
                            .join(Store, DoctorBookingSetting.store_id == Store.id)
                            .where(Store.tenant_id == source_tenant_id)
                        )
                    elif model == StoreVisitTypeConfig:
                        result = await self.db.execute(
                            select(StoreVisitTypeConfig)
                            .join(Store, StoreVisitTypeConfig.store_id == Store.id)
                            .where(Store.tenant_id == source_tenant_id)
                        )
                    elif model == StoreEmailRecipient:
                        result = await self.db.execute(
                            select(StoreEmailRecipient)
                            .join(Store, StoreEmailRecipient.store_id == Store.id)
                            .where(Store.tenant_id == source_tenant_id)
                        )
                    elif model == ConsultationFeeTemplate:
                        result = await self.db.execute(
                            select(ConsultationFeeTemplate)
                            .join(Store, ConsultationFeeTemplate.store_id == Store.id)
                            .where(Store.tenant_id == source_tenant_id)
                        )
                    else:
                        result = await self.db.execute(select(model).where(False))

                source_items = list(result.scalars().all())
                if not source_items:
                    copied_counts[entity_name] = 0
                    continue

                id_mappings[entity_name] = {}
                for item in source_items:
                    old_id = item.id
                    new_id = _get_new_id(old_id)
                    id_mappings[entity_name][old_id] = new_id

                copied = 0
                for item in source_items:
                    new_id = id_mappings[entity_name][item.id]

                    overrides = {"tenant_id": target_tenant_id}

                    for dep_name, fk_col in depends_on.items():
                        if dep_name in id_mappings:
                            old_fk = getattr(item, fk_col, None)
                            if old_fk and old_fk in id_mappings[dep_name]:
                                overrides[fk_col] = id_mappings[dep_name][old_fk]

                    new_instance = _copy_model_instance(
                        item, model,
                        tenant_id_override=target_tenant_id,
                        id_override=new_id,
                        field_overrides=overrides,
                    )
                    self.db.add(new_instance)
                    copied += 1

                await self.db.flush()
                copied_counts[entity_name] = copied

                if has_nested and entity_name == "rule_sets" and copied > 0:
                    total_windows = 0
                    for item in source_items:
                        old_rule_set_id = item.id
                        new_rule_set_id = id_mappings["rule_sets"][old_rule_set_id]

                        windows_result = await self.db.execute(
                            select(RuleWindow).where(RuleWindow.rule_set_id == old_rule_set_id)
                        )
                        windows = list(windows_result.scalars().all())
                        for w in windows:
                            new_w = _copy_model_instance(
                                w, RuleWindow,
                                field_overrides={"rule_set_id": new_rule_set_id, "tenant_id": target_tenant_id},
                            )
                            self.db.add(new_w)
                        total_windows += len(windows)

                        if item.booking_policy:
                            new_bp = _copy_model_instance(
                                item.booking_policy, RuleBookingPolicy,
                                field_overrides={"rule_set_id": new_rule_set_id},
                            )
                            self.db.add(new_bp)

                        if item.checkin_policy:
                            new_cp = _copy_model_instance(
                                item.checkin_policy, RuleCheckinPolicy,
                                field_overrides={"rule_set_id": new_rule_set_id},
                            )
                            self.db.add(new_cp)

                        if item.capacity_policy:
                            new_cap = _copy_model_instance(
                                item.capacity_policy, RuleCapacityPolicy,
                                field_overrides={"rule_set_id": new_rule_set_id},
                            )
                            self.db.add(new_cap)

                        if item.shift_types:
                            for st in item.shift_types:
                                new_assoc = RuleSetShiftType(
                                    rule_set_id=new_rule_set_id,
                                    shift_type_id=st.id,
                                )
                                self.db.add(new_assoc)

                    await self.db.flush()
                    if total_windows > 0:
                        copied_counts["rule_set_windows"] = total_windows

            except Exception as exc:
                failures.append({
                    "entity": entity_name,
                    "error": str(exc),
                })
                continue

        await self.db.commit()

        duration_ms = int((time.time() - start_time) * 1000)

        return {
            "copied": copied_counts,
            "failures": failures,
            "duration_ms": duration_ms,
        }
