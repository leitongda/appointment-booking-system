"""病历服务单元测试

覆盖:
- generate_record_no() 格式
- create() 成功路径 + 4 种 ValueError
- get_by_id() / get_by_appointment() 租户隔离
- get_list() 过滤 + 分页
- update() / delete() 基本路径
"""
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from unittest.mock import patch

from app.models.medical_record import MedicalRecord
from app.models.appointment import Appointment
from app.models.tenant import Tenant, SubscriptionPlan
from app.models.store import Store
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.user import User, Patient
from app.models.schedule import Schedule
from app.schemas.medical_record import MedicalRecordCreate, MedicalRecordUpdate
from app.modules.medical_records.service import MedicalRecordService, generate_record_no


@pytest.mark.unit
class TestGenerateRecordNo:
    """测试病历号生成"""

    def test_format(self):
        """病历号格式: MR + YYYYMMDDHHMMSS + 4位大写hex"""
        no = generate_record_no()
        assert no.startswith("MR")
        assert len(no) == 2 + 14 + 4  # MR + 14位时间 + 4位hex
        # 时间部分全部是数字
        time_part = no[2:16]
        assert time_part.isdigit()
        # 后4位是大写hex
        hex_part = no[16:]
        assert len(hex_part) == 4
        assert all(c in "0123456789ABCDEF" for c in hex_part)

    def test_uniqueness(self):
        """连续生成的病历号不同"""
        nos = {generate_record_no() for _ in range(100)}
        # 至少 95% 唯一（理论上 100% 唯一，但时间精度可能撞）
        assert len(nos) >= 95


@pytest.mark.unit
class TestMedicalRecordServiceCreate:
    """测试创建病历"""

    @pytest.fixture
    def _appointment_factory(self, db_session, test_tenant, test_doctor, test_schedule, test_patient, test_user):
        """创建指定状态的预约"""
        async def _make(status: int) -> Appointment:
            appt = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{uuid4().hex[:12].upper()}",
                user_id=test_user.id,
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                schedule_id=test_schedule.id,
                tenant_id=test_tenant.id,
                queue_number=1,
                status=status,
                patient_name=test_patient.name,
                patient_phone=test_patient.phone,
                doctor_name=test_doctor.name,
                doctor_title=test_doctor.title,
                department_name="测试科室",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(appt)
            await db_session.commit()
            await db_session.refresh(appt)
            return appt
        return _make

    async def test_create_success(self, db_session, test_tenant, test_doctor, _appointment_factory):
        """正常创建病历"""
        appt = await _appointment_factory(status=2)  # 已签到
        service = MedicalRecordService(db_session)

        data = MedicalRecordCreate(
            appointment_id=appt.id,
            chief_complaint="头痛3天",
            diagnosis="上呼吸道感染",
            status=1,
        )

        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            record = await service.create(test_doctor.id, data)

        assert record.id is not None
        assert record.record_no.startswith("MR")
        assert record.tenant_id == test_tenant.id
        assert record.appointment_id == appt.id
        assert record.patient_id == appt.patient_id
        assert record.doctor_id == test_doctor.id
        assert record.chief_complaint == "头痛3天"
        assert record.diagnosis == "上呼吸道感染"
        assert record.total_fee == 0

    @pytest.mark.parametrize("status_val", [2, 4, 5])
    async def test_create_allowed_statuses(self, db_session, test_tenant, test_doctor, _appointment_factory, status_val):
        """允许的状态: 已签到(2)、就诊中(4)、已完成(5)"""
        appt = await _appointment_factory(status=status_val)
        service = MedicalRecordService(db_session)

        data = MedicalRecordCreate(
            appointment_id=appt.id,
            chief_complaint="test",
            diagnosis="test",
        )

        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            record = await service.create(test_doctor.id, data)
        assert record is not None

    @pytest.mark.parametrize("status_val", [0, 1, 3, 6, 7, 8])
    async def test_create_rejects_invalid_status(self, db_session, test_tenant, test_doctor, _appointment_factory, status_val):
        """不允许的状态: 待支付(0)、已预约(1)、历史候诊(3)、已取消(6)、已过期(7)、已爽约(8)"""
        appt = await _appointment_factory(status=status_val)
        service = MedicalRecordService(db_session)

        data = MedicalRecordCreate(
            appointment_id=appt.id,
            chief_complaint="test",
            diagnosis="test",
        )

        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            with pytest.raises(ValueError, match="预约状态不允许"):
                await service.create(test_doctor.id, data)

    async def test_create_appointment_not_found(self, db_session, test_tenant, test_doctor):
        """预约不存在"""
        service = MedicalRecordService(db_session)
        data = MedicalRecordCreate(
            appointment_id="nonexistent",
            chief_complaint="test",
            diagnosis="test",
        )

        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            with pytest.raises(ValueError, match="预约不存在"):
                await service.create(test_doctor.id, data)

    async def test_create_duplicate_raises(self, db_session, test_tenant, test_doctor, _appointment_factory):
        """同一预约不能创建两次病历"""
        appt = await _appointment_factory(status=2)
        service = MedicalRecordService(db_session)

        data = MedicalRecordCreate(
            appointment_id=appt.id,
            chief_complaint="test",
            diagnosis="test",
        )

        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            await service.create(test_doctor.id, data)
            with pytest.raises(ValueError, match="该预约已有病历记录"):
                await service.create(test_doctor.id, data)

    async def test_create_doctor_not_found(self, db_session, test_tenant, _appointment_factory):
        """医生不存在"""
        appt = await _appointment_factory(status=2)
        service = MedicalRecordService(db_session)

        data = MedicalRecordCreate(
            appointment_id=appt.id,
            chief_complaint="test",
            diagnosis="test",
        )

        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            with pytest.raises(ValueError, match="医生不存在"):
                await service.create("nonexistent_doctor", data)

    async def test_create_with_optional_fields(self, db_session, test_tenant, test_doctor, _appointment_factory):
        """创建时填充所有可选字段"""
        appt = await _appointment_factory(status=5)
        service = MedicalRecordService(db_session)

        data = MedicalRecordCreate(
            appointment_id=appt.id,
            chief_complaint="头痛",
            present_illness="3天前开始",
            past_history="无特殊",
            allergy_history="青霉素过敏",
            physical_exam="体温37.5",
            auxiliary_exam="血常规正常",
            diagnosis="上呼吸道感染",
            treatment="口服药物",
            prescription="阿莫西林",
            advice="多休息",
            total_fee=Decimal("128.50"),
            status=2,
            visit_date=datetime(2026, 5, 27, 10, 30),
        )

        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            record = await service.create(test_doctor.id, data)

        assert record.present_illness == "3天前开始"
        assert record.allergy_history == "青霉素过敏"
        assert record.total_fee == Decimal("128.50")
        assert record.status == 2
        assert record.visit_date == datetime(2026, 5, 27, 10, 30)


@pytest.mark.unit
class TestMedicalRecordServiceGetById:
    """测试按 ID 查询病历"""

    async def _create_record(self, db_session, tenant_id, doctor_id, appointment_id, patient_id, department_id):
        record = MedicalRecord(
            id=str(uuid4()),
            tenant_id=tenant_id,
            record_no=generate_record_no(),
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            department_id=department_id,
            chief_complaint="test",
            diagnosis="test",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)
        return record

    async def test_get_by_id_found(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        """能找到自己的病历"""
        record = await self._create_record(
            db_session, test_tenant.id, test_doctor.id,
            test_appointment.id, test_patient.id, test_doctor.department_id,
        )
        service = MedicalRecordService(db_session)

        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.get_by_id(record.id)
        assert result is not None
        assert result.id == record.id

    async def test_get_by_id_not_found(self, db_session, test_tenant):
        """不存在的 ID 返回 None"""
        service = MedicalRecordService(db_session)
        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.get_by_id("nonexistent")
        assert result is None

    async def test_get_by_id_tenant_isolation(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        """租户隔离：不同租户看不到"""
        record = await self._create_record(
            db_session, test_tenant.id, test_doctor.id,
            test_appointment.id, test_patient.id, test_doctor.department_id,
        )
        service = MedicalRecordService(db_session)

        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value="other_tenant"):
            result = await service.get_by_id(record.id)
        assert result is None

    async def test_get_by_id_no_tenant_filter(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        """tenant_id 为 None 时不过滤"""
        record = await self._create_record(
            db_session, test_tenant.id, test_doctor.id,
            test_appointment.id, test_patient.id, test_doctor.department_id,
        )
        service = MedicalRecordService(db_session)

        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=None):
            result = await service.get_by_id(record.id)
        assert result is not None

    async def test_get_by_id_excludes_soft_deleted(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        """软删除的记录查不到"""
        record = await self._create_record(
            db_session, test_tenant.id, test_doctor.id,
            test_appointment.id, test_patient.id, test_doctor.department_id,
        )
        record.deleted_at = datetime.now()
        await db_session.commit()

        service = MedicalRecordService(db_session)
        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.get_by_id(record.id)
        assert result is None


@pytest.mark.unit
class TestMedicalRecordServiceGetByAppointment:
    """测试按预约 ID 查询病历"""

    async def _create_record(self, db_session, tenant_id, doctor_id, appointment_id, patient_id, department_id):
        record = MedicalRecord(
            id=str(uuid4()),
            tenant_id=tenant_id,
            record_no=generate_record_no(),
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            department_id=department_id,
            chief_complaint="test",
            diagnosis="test",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)
        return record

    async def test_found(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        record = await self._create_record(
            db_session, test_tenant.id, test_doctor.id,
            test_appointment.id, test_patient.id, test_doctor.department_id,
        )
        service = MedicalRecordService(db_session)
        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.get_by_appointment(test_appointment.id)
        assert result is not None
        assert result.id == record.id

    async def test_not_found(self, db_session, test_tenant):
        service = MedicalRecordService(db_session)
        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            result = await service.get_by_appointment("nonexistent")
        assert result is None


@pytest.mark.unit
class TestMedicalRecordServiceGetList:
    """测试病历列表查询"""

    async def _create_record(self, db_session, **kwargs):
        defaults = dict(
            id=str(uuid4()),
            record_no=generate_record_no(),
            chief_complaint="test complaint",
            diagnosis="test diagnosis",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        defaults.update(kwargs)
        record = MedicalRecord(**defaults)
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)
        return record

    async def test_list_basic(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        """基本列表查询"""
        await self._create_record(
            db_session,
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            department_id=test_doctor.department_id,
        )
        service = MedicalRecordService(db_session)
        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            items, total = await service.get_list()
        assert total == 1
        assert len(items) == 1

    async def test_list_filter_by_doctor(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        """按医生过滤"""
        await self._create_record(
            db_session,
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            department_id=test_doctor.department_id,
        )
        service = MedicalRecordService(db_session)
        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            items, total = await service.get_list(doctor_id=test_doctor.id)
            assert total == 1

            items, total = await service.get_list(doctor_id="other_doctor")
            assert total == 0

    async def test_list_filter_by_keyword(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        """按关键词搜索（诊断 + 主诉）"""
        await self._create_record(
            db_session,
            tenant_id=test_tenant.id,
            appointment_id=test_appointment.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            department_id=test_doctor.department_id,
            diagnosis="上呼吸道感染",
            chief_complaint="头痛",
        )
        service = MedicalRecordService(db_session)
        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            items, total = await service.get_list(keyword="感染")
            assert total == 1

            items, total = await service.get_list(keyword="头痛")
            assert total == 1

            items, total = await service.get_list(keyword="骨折")
            assert total == 0

    async def test_list_pagination(self, db_session, test_tenant, test_doctor, test_patient, test_schedule):
        """分页"""
        for i in range(5):
            appt = Appointment(
                id=str(uuid4()),
                appointment_no=f"YY{i:04d}{uuid4().hex[:8].upper()}",
                user_id=test_patient.user_id,
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                schedule_id=test_schedule.id,
                tenant_id=test_tenant.id,
                queue_number=i + 1,
                status=2,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(appt)
            await db_session.flush()

            await self._create_record(
                db_session,
                tenant_id=test_tenant.id,
                appointment_id=appt.id,
                patient_id=test_patient.id,
                doctor_id=test_doctor.id,
                department_id=test_doctor.department_id,
            )

        service = MedicalRecordService(db_session)
        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            items, total = await service.get_list(page=1, page_size=2)
            assert total == 5
            assert len(items) == 2

            items, total = await service.get_list(page=3, page_size=2)
            assert len(items) == 1


@pytest.mark.unit
class TestMedicalRecordServiceUpdate:
    """测试更新病历"""

    async def _create_record(self, db_session, tenant_id, doctor_id, appointment_id, patient_id, department_id):
        record = MedicalRecord(
            id=str(uuid4()),
            tenant_id=tenant_id,
            record_no=generate_record_no(),
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            department_id=department_id,
            chief_complaint="original",
            diagnosis="original",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)
        return record

    async def test_update_success(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        record = await self._create_record(
            db_session, test_tenant.id, test_doctor.id,
            test_appointment.id, test_patient.id, test_doctor.department_id,
        )
        service = MedicalRecordService(db_session)

        data = MedicalRecordUpdate(diagnosis="updated diagnosis", status=2)
        result = await service.update(record.id, data, operator_id=test_doctor.id)
        assert result is not None
        assert result.diagnosis == "updated diagnosis"
        assert result.status == 2

    async def test_update_not_found(self, db_session):
        service = MedicalRecordService(db_session)
        data = MedicalRecordUpdate(diagnosis="test")
        result = await service.update("nonexistent", data)
        assert result is None

    async def test_update_partial(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        """部分更新：只改 diagnosis，其他不动"""
        record = await self._create_record(
            db_session, test_tenant.id, test_doctor.id,
            test_appointment.id, test_patient.id, test_doctor.department_id,
        )
        service = MedicalRecordService(db_session)

        data = MedicalRecordUpdate(diagnosis="new")
        result = await service.update(record.id, data)
        assert result.diagnosis == "new"
        assert result.chief_complaint == "original"  # 未改


@pytest.mark.unit
class TestMedicalRecordServiceDelete:
    """测试软删除病历"""

    async def _create_record(self, db_session, tenant_id, doctor_id, appointment_id, patient_id, department_id):
        record = MedicalRecord(
            id=str(uuid4()),
            tenant_id=tenant_id,
            record_no=generate_record_no(),
            appointment_id=appointment_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            department_id=department_id,
            chief_complaint="test",
            diagnosis="test",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(record)
        await db_session.commit()
        await db_session.refresh(record)
        return record

    async def test_delete_success(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        record = await self._create_record(
            db_session, test_tenant.id, test_doctor.id,
            test_appointment.id, test_patient.id, test_doctor.department_id,
        )
        service = MedicalRecordService(db_session)
        result = await service.delete(record.id, operator_id=test_doctor.id)
        assert result is True

        # 删除后查不到
        with patch("app.modules.medical_records.service.get_current_tenant_id", return_value=test_tenant.id):
            assert await service.get_by_id(record.id) is None

    async def test_delete_not_found(self, db_session):
        service = MedicalRecordService(db_session)
        result = await service.delete("nonexistent")
        assert result is False

    async def test_delete_already_deleted(self, db_session, test_tenant, test_doctor, test_appointment, test_patient):
        record = await self._create_record(
            db_session, test_tenant.id, test_doctor.id,
            test_appointment.id, test_patient.id, test_doctor.department_id,
        )
        service = MedicalRecordService(db_session)
        await service.delete(record.id)

        # 重复删除返回 False
        result = await service.delete(record.id)
        assert result is False
