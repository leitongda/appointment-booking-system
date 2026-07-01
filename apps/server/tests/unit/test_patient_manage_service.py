"""
PatientManageService 单元测试

测试患者管理服务的核心方法：
1. get_list - 患者列表查询、关键词搜索、分页
2. get_detail - 患者详情、统计数据
3. create_patient - 创建患者（含用户自动创建）
4. update_patient - 更新患者信息
5. add_family_member - 添加家属
6. update_family_member - 更新家属
7. delete_family_member - 删除家属
8. get_appointments - 获取患者预约记录
9. get_consumption_records - 获取消费记录
"""
import pytest
from datetime import datetime, date, time, timedelta
from uuid import uuid4
from unittest.mock import MagicMock

from app.middleware.exception import BusinessError
from app.models.user import User, Patient
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.models.store import Store
from app.modules.patients.service_manage import PatientManageService
from app.schemas.user import PatientCreateByAdmin, PatientUpdate, FamilyMemberCreate


class TestGetList:
    """测试患者列表查询功能"""

    @pytest.mark.asyncio
    async def test_get_list_empty(self, db_session):
        """空列表查询"""
        service = PatientManageService(db_session)
        items, total = await service.get_list()

        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_get_list_with_data(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """正常查询返回患者列表"""
        service = PatientManageService(db_session)
        items, total = await service.get_list()

        assert total >= 1
        assert len(items) >= 1
        # 验证返回的字段
        item = items[0]
        assert "id" in item
        assert "name" in item
        assert "phone" in item
        assert "isBlacklist" in item

    @pytest.mark.asyncio
    async def test_get_list_with_keyword_search(
        self,
        db_session,
        test_user,
    ):
        """关键词搜索（姓名、手机、身份证）"""
        # 创建多个患者
        patient1 = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="张三",
            phone="13900000001",
            id_card="110101199001011111",
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        patient2 = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="李四",
            phone="13900000002",
            id_card="110101199001012222",
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add_all([patient1, patient2])
        await db_session.commit()

        service = PatientManageService(db_session)

        # 按姓名搜索
        items, total = await service.get_list(keyword="张三")
        assert total >= 1
        found = any(p["name"] == "张三" for p in items)
        assert found

        # 按手机搜索
        items, total = await service.get_list(keyword="13900000002")
        assert total >= 1
        found = any(p["phone"] == "13900000002" for p in items)
        assert found

        # 按身份证搜索
        items, total = await service.get_list(keyword="2222")
        assert total >= 1
        found = any(p["idCard"] == "110101199001012222" for p in items)
        assert found

    @pytest.mark.asyncio
    async def test_get_list_with_store_filter(
        self,
        db_session,
        test_store,
        test_user,
    ):
        """按门店筛选"""
        patient = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            store_id=test_store.id,
            name="门店患者",
            phone="13900000003",
            id_card="110101199001013333",
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(patient)
        await db_session.commit()

        service = PatientManageService(db_session)
        items, total = await service.get_list(store_id=test_store.id)

        assert total >= 1

    @pytest.mark.asyncio
    async def test_get_list_pagination(
        self,
        db_session,
        test_user,
    ):
        """分页查询"""
        # 创建 25 个患者
        for i in range(25):
            patient = Patient(
                id=str(uuid4()),
                user_id=test_user.id,
                name=f"患者{i:03d}",
                phone=f"1390001{i:04d}",
                id_card=f"110101199001014{i:03d}",
                is_default=(i == 0),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(patient)
        await db_session.commit()

        service = PatientManageService(db_session)

        # 第一页
        items_page1, total = await service.get_list(page=1, page_size=10)
        assert total >= 25
        assert len(items_page1) == 10

        # 第二页
        items_page2, _ = await service.get_list(page=2, page_size=10)
        assert len(items_page2) == 10

        # 第三页
        items_page3, _ = await service.get_list(page=3, page_size=10)
        assert len(items_page3) >= 5


class TestGetDetail:
    """测试患者详情查询"""

    @pytest.mark.asyncio
    async def test_get_detail_not_found(self, db_session):
        """查询不存在的患者"""
        service = PatientManageService(db_session)
        result = await service.get_detail("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_detail_success(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """正常获取患者详情"""
        service = PatientManageService(db_session)
        result = await service.get_detail(test_patient.id)

        assert result is not None
        assert result["id"] == test_patient.id
        assert result["name"] == test_patient.name
        assert result["phone"] == test_patient.phone
        assert "statistics" in result
        assert "familyMembers" in result

    @pytest.mark.asyncio
    async def test_get_detail_with_appointment_stats(
        self,
        db_session,
        test_user,
        test_patient,
        test_doctor,
        test_store,
    ):
        """详情包含预约统计"""
        # 创建排班和预约
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            schedule_date=date.today(),
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=1,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.flush()

        # 创建已完成的预约
        completed_appointment = Appointment(
            id=str(uuid4()),
            appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=test_user.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            schedule_id=schedule.id,
            status=5,  # 已完成
            patient_name=test_patient.name,
            patient_phone=test_patient.phone,
            doctor_name=test_doctor.name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            complete_time=datetime.now(),
        )
        db_session.add(completed_appointment)
        await db_session.commit()

        service = PatientManageService(db_session)
        result = await service.get_detail(test_patient.id)

        assert result is not None
        assert result["statistics"]["appointmentCount"] >= 1
        assert result["statistics"]["completedCount"] >= 1


class TestCreatePatient:
    """测试创建患者"""

    @pytest.mark.asyncio
    async def test_create_patient_new_user(
        self,
        db_session,
        test_store,
    ):
        """创建患者（新用户）"""
        service = PatientManageService(db_session)
        data = PatientCreateByAdmin(
            phone="13900009999",
            name="新患者",
            gender=1,
            id_card="110101199901019999",
            birthday="1999-01-01",
            relationship="本人",
            is_default=True,
        )

        result = await service.create_patient(
            data=data,
            store_id=test_store.id,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["name"] == "新患者"
        assert result["phone"] == "13900009999"
        assert result["source"] == 2  # 管理端创建

    @pytest.mark.asyncio
    async def test_create_patient_existing_user(
        self,
        db_session,
        test_store,
        test_user,
    ):
        """创建患者（已有用户）"""
        service = PatientManageService(db_session)
        data = PatientCreateByAdmin(
            phone=test_user.phone,  # 使用已有用户手机号
            name="已有用户的家属",
            gender=2,
            id_card="110101199901018888",
            birthday="1999-01-01",
            relationship="配偶",
            is_default=False,
        )

        result = await service.create_patient(
            data=data,
            store_id=test_store.id,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["name"] == "已有用户的家属"

    @pytest.mark.asyncio
    async def test_create_patient_duplicate_name(
        self,
        db_session,
        test_store,
        test_user,
        test_patient,
    ):
        """创建重复名称的患者应失败"""
        service = PatientManageService(db_session)
        data = PatientCreateByAdmin(
            phone=test_user.phone,
            name=test_patient.name,  # 同名
            gender=1,
            id_card="110101199901017777",
            is_default=False,
        )

        with pytest.raises(BusinessError, match="已存在"):
            await service.create_patient(
                data=data,
                store_id=test_store.id,
                operator_id="admin-1",
            )


class TestUpdatePatient:
    """测试更新患者"""

    @pytest.mark.asyncio
    async def test_update_patient_not_found(self, db_session):
        """更新不存在的患者"""
        service = PatientManageService(db_session)
        data = PatientUpdate(name="新名字")

        result = await service.update_patient(
            patient_id="non-existent-id",
            data=data,
            operator_id="admin-1",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_patient_success(
        self,
        db_session,
        test_patient,
    ):
        """正常更新患者"""
        service = PatientManageService(db_session)
        data = PatientUpdate(
            name="更新后的名字",
            phone="13900008888",
        )

        result = await service.update_patient(
            patient_id=test_patient.id,
            data=data,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["name"] == "更新后的名字"
        assert result["phone"] == "13900008888"


class TestFamilyMember:
    """测试家属管理"""

    @pytest.mark.asyncio
    async def test_add_family_member(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """添加家属"""
        service = PatientManageService(db_session)
        data = FamilyMemberCreate(
            name="家属成员",
            phone="13900007777",
            id_card="110101199901016666",
            gender=2,
            birthday="1995-05-15",
            relationship="子女",
            is_default=False,
        )

        result = await service.add_family_member(
            patient_id=test_patient.id,
            data=data,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["name"] == "家属成员"
        assert result["relationship"] == "子女"
        assert result["userId"] == test_user.id

    @pytest.mark.asyncio
    async def test_add_family_member_patient_not_found(self, db_session):
        """患者不存在时添加家属"""
        service = PatientManageService(db_session)
        data = FamilyMemberCreate(
            name="家属",
            phone="13900007777",
            id_card="110101199901016666",
        )

        result = await service.add_family_member(
            patient_id="non-existent-id",
            data=data,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_add_family_member_duplicate_name(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """添加同名家属应失败"""
        service = PatientManageService(db_session)
        data = FamilyMemberCreate(
            name=test_patient.name,  # 同名
            phone="13900007777",
            id_card="110101199901016666",
        )

        with pytest.raises(BusinessError, match="已存在"):
            await service.add_family_member(
                patient_id=test_patient.id,
                data=data,
            )

    @pytest.mark.asyncio
    async def test_add_family_member_as_default(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """添加默认家属时，其他家属的默认状态应被清除"""
        service = PatientManageService(db_session)
        data = FamilyMemberCreate(
            name="新的默认家属",
            phone="13900007777",
            id_card="110101199901016666",
            is_default=True,
        )

        result = await service.add_family_member(
            patient_id=test_patient.id,
            data=data,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["isDefault"] is True

        # 验证原患者的默认状态被清除
        await db_session.refresh(test_patient)
        assert test_patient.is_default is False

    @pytest.mark.asyncio
    async def test_update_family_member(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """更新家属"""
        # 先添加家属
        member = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="原家属名",
            phone="13900006666",
            id_card="110101199901015555",
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(member)
        await db_session.commit()

        service = PatientManageService(db_session)
        data = PatientUpdate(name="更新后家属名")

        result = await service.update_family_member(
            patient_id=test_patient.id,
            member_id=member.id,
            data=data,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["name"] == "更新后家属名"

    @pytest.mark.asyncio
    async def test_update_family_member_wrong_user(
        self,
        db_session,
        test_patient,
    ):
        """更新其他用户的家属应失败"""
        # 创建另一个用户
        other_user = User(
            id=str(uuid4()),
            phone="13900005555",
            password_hash="hash",
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        other_member = Patient(
            id=str(uuid4()),
            user_id=other_user.id,
            name="其他用户家属",
            phone="13900005556",
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add_all([other_user, other_member])
        await db_session.commit()

        service = PatientManageService(db_session)
        data = PatientUpdate(name="尝试更新")

        result = await service.update_family_member(
            patient_id=test_patient.id,
            member_id=other_member.id,
            data=data,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_family_member(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """删除家属"""
        # 添加家属
        member = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="待删除家属",
            phone="13900004444",
            id_card="110101199901014444",
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(member)
        await db_session.commit()

        service = PatientManageService(db_session)
        result = await service.delete_family_member(
            patient_id=test_patient.id,
            member_id=member.id,
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_family_member_with_appointments(
        self,
        db_session,
        test_user,
        test_patient,
        test_doctor,
        test_store,
    ):
        """有预约记录的家属无法删除"""
        # 添加家属
        member = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="有预约的家属",
            phone="13900004444",
            id_card="110101199901014444",
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(member)

        # 创建排班
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            schedule_date=date.today(),
            time_slot="morning",
            total_slots=10,
            booked_slots=1,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.flush()

        # 创建预约
        appointment = Appointment(
            id=str(uuid4()),
            appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=test_user.id,
            patient_id=member.id,
            doctor_id=test_doctor.id,
            schedule_id=schedule.id,
            status=1,
            patient_name=member.name,
            doctor_name=test_doctor.name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(appointment)
        await db_session.commit()

        service = PatientManageService(db_session)

        with pytest.raises(BusinessError, match="预约记录"):
            await service.delete_family_member(
                patient_id=test_patient.id,
                member_id=member.id,
            )

    @pytest.mark.asyncio
    async def test_delete_self_not_allowed(
        self,
        db_session,
        test_patient,
    ):
        """不能删除自己"""
        service = PatientManageService(db_session)
        result = await service.delete_family_member(
            patient_id=test_patient.id,
            member_id=test_patient.id,
        )

        assert result is False


class TestGetAppointments:
    """测试获取患者预约记录"""

    @pytest.mark.asyncio
    async def test_get_appointments_empty(
        self,
        db_session,
        test_patient,
    ):
        """无预约记录"""
        service = PatientManageService(db_session)
        items, total = await service.get_appointments(test_patient.id)

        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_get_appointments_with_data(
        self,
        db_session,
        test_user,
        test_patient,
        test_doctor,
        test_store,
    ):
        """有预约记录"""
        # 创建排班
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            schedule_date=date.today(),
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=1,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.flush()

        # 创建预约
        appointment = Appointment(
            id=str(uuid4()),
            appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=test_user.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            schedule_id=schedule.id,
            status=1,
            queue_number=1,
            patient_name=test_patient.name,
            patient_phone=test_patient.phone,
            doctor_name=test_doctor.name,
            doctor_title=test_doctor.title,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(appointment)
        await db_session.commit()

        service = PatientManageService(db_session)
        items, total = await service.get_appointments(test_patient.id)

        assert total >= 1
        assert len(items) >= 1
        assert items[0]["doctorName"] == test_doctor.name

    @pytest.mark.asyncio
    async def test_get_appointments_with_filters(
        self,
        db_session,
        test_user,
        test_patient,
        test_doctor,
        test_store,
    ):
        """带筛选条件的预约查询"""
        # 创建排班
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            schedule_date=date.today() + timedelta(days=1),
            time_slot="morning",
            total_slots=10,
            booked_slots=1,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.flush()

        # 创建预约
        appointment = Appointment(
            id=str(uuid4()),
            appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=test_user.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            schedule_id=schedule.id,
            status=5,  # 已完成
            patient_name=test_patient.name,
            doctor_name=test_doctor.name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(appointment)
        await db_session.commit()

        service = PatientManageService(db_session)

        # 按医生筛选
        items, total = await service.get_appointments(
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
        )
        assert total >= 1

        # 按状态筛选
        items, total = await service.get_appointments(
            patient_id=test_patient.id,
            status=5,
        )
        assert total >= 1
        for item in items:
            assert item["status"] == 5


class TestGetConsumptionRecords:
    """测试获取消费记录"""

    @pytest.mark.asyncio
    async def test_get_consumption_records_empty(
        self,
        db_session,
        test_patient,
    ):
        """无消费记录"""
        service = PatientManageService(db_session)
        items, total = await service.get_consumption_records(test_patient.id)

        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_get_consumption_records_with_data(
        self,
        db_session,
        test_user,
        test_patient,
        test_doctor,
        test_store,
    ):
        """有消费记录（已完成的预约）"""
        # 创建排班
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            schedule_date=date.today(),
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=10,
            booked_slots=1,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.flush()

        # 创建已完成的预约
        appointment = Appointment(
            id=str(uuid4()),
            appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=test_user.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            schedule_id=schedule.id,
            status=5,  # 已完成
            patient_name=test_patient.name,
            doctor_name=test_doctor.name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            complete_time=datetime.now(),
        )
        # 创建未完成的预约（不应出现在消费记录中）
        pending_appointment = Appointment(
            id=str(uuid4()),
            appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}2",
            user_id=test_user.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            schedule_id=schedule.id,
            status=1,  # 已预约
            patient_name=test_patient.name,
            doctor_name=test_doctor.name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add_all([appointment, pending_appointment])
        await db_session.commit()

        service = PatientManageService(db_session)
        items, total = await service.get_consumption_records(test_patient.id)

        assert total >= 1
        # 只返回已完成的预约
        for item in items:
            assert item["status"] == 5
            assert "itemName" in item
            assert "storeName" in item


class TestDeletePatient:
    """测试删除患者"""

    @pytest.mark.asyncio
    async def test_delete_patient_not_found(self, db_session):
        """删除不存在的患者"""
        service = PatientManageService(db_session)
        result = await service.delete_patient("non-existent-id")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_patient_with_appointments(
        self,
        db_session,
        test_user,
        test_patient,
        test_doctor,
        test_store,
    ):
        """有预约记录的患者无法删除"""
        # 创建排班和预约
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            schedule_date=date.today(),
            time_slot="morning",
            total_slots=10,
            booked_slots=1,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(schedule)
        await db_session.flush()

        appointment = Appointment(
            id=str(uuid4()),
            appointment_no=f"YY{datetime.now().strftime('%Y%m%d%H%M%S')}",
            user_id=test_user.id,
            patient_id=test_patient.id,
            doctor_id=test_doctor.id,
            schedule_id=schedule.id,
            status=1,
            patient_name=test_patient.name,
            doctor_name=test_doctor.name,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(appointment)
        await db_session.commit()

        service = PatientManageService(db_session)

        with pytest.raises(BusinessError, match="预约记录"):
            await service.delete_patient(test_patient.id)

    @pytest.mark.asyncio
    async def test_delete_last_patient(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """删除用户最后一张就诊卡应失败"""
        service = PatientManageService(db_session)

        with pytest.raises(BusinessError, match="至少需要保留一张"):
            await service.delete_patient(test_patient.id)

    @pytest.mark.asyncio
    async def test_delete_patient_success(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """正常删除患者（有多张就诊卡时）"""
        # 添加第二张就诊卡
        second_patient = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="第二张卡",
            phone="13900003333",
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(second_patient)
        await db_session.commit()

        service = PatientManageService(db_session)
        result = await service.delete_patient(test_patient.id)

        assert result is True
