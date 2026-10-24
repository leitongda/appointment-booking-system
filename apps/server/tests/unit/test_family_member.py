"""
家庭成员功能单元测试

测试 PatientManageService 的家庭成员相关方法：
- add_family_member: 添加家庭成员
- update_family_member: 更新家庭成员
- delete_family_member: 删除家庭成员
- 家庭成员关系验证
"""

import pytest
from datetime import datetime, date, time
from uuid import uuid4
from sqlalchemy import select

from app.middleware.exception import BusinessError
from app.models.user import User, Patient
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.modules.patients.service_manage import PatientManageService
from app.modules.patients.service_users import UserManageService
from app.schemas.user import FamilyMemberCreate, PatientUpdate


class TestAddFamilyMember:
    """测试添加家庭成员功能"""

    @pytest.mark.asyncio
    async def test_add_family_member_success(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """成功添加家庭成员"""
        service = PatientManageService(db_session)
        data = FamilyMemberCreate(
            name="家庭成员A",
            phone="13900001111",
            id_card="110101199001011111",
            gender=1,
            birthday="1990-01-01",
            relationship="配偶",
            is_default=False,
        )

        result = await service.add_family_member(
            patient_id=test_patient.id,
            data=data,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["name"] == "家庭成员A"
        assert result["phone"] == "13900001111"
        assert result["relationship"] == "配偶"
        assert result["userId"] == test_user.id
        assert result["isDefault"] is False
        assert result["appointmentCount"] == 0
        assert result["noShowCount"] == 0

    @pytest.mark.asyncio
    async def test_add_family_member_patient_not_found(self, db_session):
        """患者不存在时添加家庭成员返回 None"""
        service = PatientManageService(db_session)
        data = FamilyMemberCreate(
            name="家庭成员",
            phone="13900001111",
            id_card="110101199001011111",
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
        """添加同名家庭成员应失败"""
        service = PatientManageService(db_session)
        data = FamilyMemberCreate(
            name=test_patient.name,  # 同名
            phone="13900001111",
            id_card="110101199001011111",
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
        """添加默认家庭成员时，其他成员的默认状态应被清除"""
        # 确保原患者是默认的
        test_patient.is_default = True
        await db_session.commit()

        service = PatientManageService(db_session)
        data = FamilyMemberCreate(
            name="新的默认成员",
            phone="13900002222",
            id_card="110101199001012222",
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
    async def test_add_family_member_with_full_info(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """添加完整信息的家庭成员"""
        service = PatientManageService(db_session)
        data = FamilyMemberCreate(
            name="完整信息成员",
            phone="13900003333",
            id_card="110101199001013333",
            gender=2,
            age=25,
            birthday="1998-05-15",
            relationship="子女",
            is_default=False,
            province="北京市",
            city="北京市",
            district="朝阳区",
            street="望京街道",
            id_card_type=1,
            ethnicity="汉族",
            address="望京SOHO T1",
        )

        result = await service.add_family_member(
            patient_id=test_patient.id,
            data=data,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["name"] == "完整信息成员"
        assert result["relationship"] == "子女"

    @pytest.mark.asyncio
    async def test_add_multiple_family_members(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """添加多个家庭成员"""
        service = PatientManageService(db_session)

        # 添加第一个家庭成员
        data1 = FamilyMemberCreate(
            name="家庭成员1",
            phone="13900001111",
            id_card="110101199001011111",
            relationship="配偶",
        )
        result1 = await service.add_family_member(
            patient_id=test_patient.id,
            data=data1,
        )

        # 添加第二个家庭成员
        data2 = FamilyMemberCreate(
            name="家庭成员2",
            phone="13900002222",
            id_card="110101199001012222",
            relationship="子女",
        )
        result2 = await service.add_family_member(
            patient_id=test_patient.id,
            data=data2,
        )

        assert result1 is not None
        assert result2 is not None
        assert result1["userId"] == result2["userId"] == test_user.id

        # 验证家庭成员数量
        members = await db_session.execute(
            select(Patient).where(Patient.user_id == test_user.id)
        )
        member_list = members.scalars().all()
        assert len(member_list) == 3  # 原患者 + 2个家庭成员


class TestUpdateFamilyMember:
    """测试更新家庭成员功能"""

    @pytest.mark.asyncio
    async def test_update_family_member_success(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """成功更新家庭成员"""
        # 先添加一个家庭成员
        member = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="原家庭成员",
            phone="13900001111",
            id_card="110101199001011111",
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(member)
        await db_session.commit()

        service = PatientManageService(db_session)
        data = PatientUpdate(
            name="更新后名称",
            phone="13900009999",
        )

        result = await service.update_family_member(
            patient_id=test_patient.id,
            member_id=member.id,
            data=data,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["name"] == "更新后名称"
        assert result["phone"] == "13900009999"

    @pytest.mark.asyncio
    async def test_update_family_member_not_found(
        self,
        db_session,
        test_patient,
    ):
        """更新不存在的家庭成员"""
        service = PatientManageService(db_session)
        data = PatientUpdate(name="新名字")

        result = await service.update_family_member(
            patient_id=test_patient.id,
            member_id="non-existent-id",
            data=data,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_family_member_wrong_user(
        self,
        db_session,
        test_patient,
    ):
        """更新其他用户的家庭成员应失败"""
        # 创建另一个用户和患者
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
            name="其他用户成员",
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
    async def test_update_family_member_patient_not_found(
        self,
        db_session,
    ):
        """患者不存在时更新家庭成员"""
        service = PatientManageService(db_session)
        data = PatientUpdate(name="新名字")

        result = await service.update_family_member(
            patient_id="non-existent-patient",
            member_id="non-existent-member",
            data=data,
        )

        assert result is None


class TestDeleteFamilyMember:
    """测试删除家庭成员功能"""

    @pytest.mark.asyncio
    async def test_delete_family_member_success(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """成功删除家庭成员"""
        # 添加一个家庭成员
        member = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="待删除成员",
            phone="13900001111",
            id_card="110101199001011111",
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

        # 验证已删除
        deleted_member = await db_session.get(Patient, member.id)
        assert deleted_member is None

    @pytest.mark.asyncio
    async def test_delete_family_member_not_found(
        self,
        db_session,
        test_patient,
    ):
        """删除不存在的家庭成员"""
        service = PatientManageService(db_session)

        result = await service.delete_family_member(
            patient_id=test_patient.id,
            member_id="non-existent-id",
        )

        assert result is False

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

    @pytest.mark.asyncio
    async def test_delete_family_member_with_appointments(
        self,
        db_session,
        test_user,
        test_patient,
        test_doctor,
        test_store,
    ):
        """有预约记录的家庭成员无法删除"""
        # 添加家庭成员
        member = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="有预约的成员",
            phone="13900001111",
            id_card="110101199001011111",
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
    async def test_delete_family_member_wrong_user(
        self,
        db_session,
        test_patient,
    ):
        """删除其他用户的家庭成员应失败"""
        # 创建另一个用户和患者
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
            name="其他用户成员",
            phone="13900005556",
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add_all([other_user, other_member])
        await db_session.commit()

        service = PatientManageService(db_session)

        result = await service.delete_family_member(
            patient_id=test_patient.id,
            member_id=other_member.id,
        )

        assert result is False


class TestFamilyMemberRelationship:
    """测试家庭成员关系验证"""

    @pytest.mark.asyncio
    async def test_family_member_inherits_user_id(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """家庭成员继承主用户的 user_id"""
        service = PatientManageService(db_session)
        data = FamilyMemberCreate(
            name="家庭成员",
            phone="13900001111",
            id_card="110101199001011111",
            relationship="父母",
        )

        result = await service.add_family_member(
            patient_id=test_patient.id,
            data=data,
        )

        assert result is not None
        assert result["userId"] == test_user.id

    @pytest.mark.asyncio
    async def test_family_members_same_user(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """同一用户下的所有家庭成员共享相同的 user_id"""
        service = PatientManageService(db_session)

        # 添加多个家庭成员
        for i in range(3):
            data = FamilyMemberCreate(
                name=f"成员{i}",
                phone=f"1390000111{i}",
                id_card=f"11010119900101111{i}",
                relationship=["配偶", "子女", "父母"][i],
            )
            await service.add_family_member(
                patient_id=test_patient.id,
                data=data,
            )

        # 验证所有成员的 user_id 相同
        members = await db_session.execute(
            select(Patient).where(Patient.user_id == test_user.id)
        )
        member_list = members.scalars().all()

        for member in member_list:
            assert member.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_get_detail_includes_family_members(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """患者详情包含家庭成员列表"""
        service = PatientManageService(db_session)

        # 添加家庭成员
        data = FamilyMemberCreate(
            name="家庭成员A",
            phone="13900001111",
            id_card="110101199001011111",
            relationship="配偶",
        )
        await service.add_family_member(
            patient_id=test_patient.id,
            data=data,
        )

        # 获取详情
        detail = await service.get_detail(test_patient.id)

        assert detail is not None
        assert "familyMembers" in detail
        assert len(detail["familyMembers"]) >= 2  # 主患者 + 家庭成员

        # 验证家庭成员信息
        family_names = [m["name"] for m in detail["familyMembers"]]
        assert "家庭成员A" in family_names

    @pytest.mark.asyncio
    async def test_family_member_relationship_types(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """测试不同的家庭成员关系类型"""
        service = PatientManageService(db_session)

        relationships = ["本人", "配偶", "子女", "父母", "其他"]

        for rel in relationships:
            if rel == "本人":
                continue  # 跳过"本人"，因为已有 test_patient
            data = FamilyMemberCreate(
                name=f"{rel}成员",
                phone=f"1390001{rel[:2].ljust(4, '0')}",
                id_card=f"11010119900101{rel[:2].ljust(4, '0')}",
                relationship=rel,
            )
            result = await service.add_family_member(
                patient_id=test_patient.id,
                data=data,
            )
            assert result is not None
            assert result["relationship"] == rel


class TestUserManageServiceFamilyMember:
    """测试 UserManageService 的家庭成员（就诊卡）功能"""

    @pytest.mark.asyncio
    async def test_create_card_success(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """成功创建就诊卡"""
        service = UserManageService(db_session)
        data = FamilyMemberCreate(
            name="新就诊卡",
            phone="13900009999",
            id_card="110101199001019999",
            gender=1,
            birthday="1990-01-01",
            relationship="本人",
            is_default=False,
        )

        result = await service.create_card(
            user_id=test_user.id,
            data=data,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["name"] == "新就诊卡"
        assert result["userId"] == test_user.id

    @pytest.mark.asyncio
    async def test_create_card_duplicate_name(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """创建同名就诊卡应失败"""
        service = UserManageService(db_session)
        data = FamilyMemberCreate(
            name=test_patient.name,  # 同名
            phone="13900009999",
            id_card="110101199001019999",
        )

        with pytest.raises(BusinessError, match="已存在"):
            await service.create_card(
                user_id=test_user.id,
                data=data,
            )

    @pytest.mark.asyncio
    async def test_create_card_user_not_found(self, db_session):
        """用户不存在时创建就诊卡返回 None"""
        service = UserManageService(db_session)
        data = FamilyMemberCreate(
            name="新就诊卡",
            phone="13900009999",
            id_card="110101199001019999",
        )

        result = await service.create_card(
            user_id="non-existent-id",
            data=data,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_update_card_success(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """成功更新就诊卡"""
        service = UserManageService(db_session)
        data = PatientUpdate(
            name="更新后名字",
            phone="13900008888",
        )

        result = await service.update_card(
            user_id=test_user.id,
            card_id=test_patient.id,
            data=data,
            operator_id="admin-1",
        )

        assert result is not None
        assert result["name"] == "更新后名字"
        assert result["phone"] == "13900008888"

    @pytest.mark.asyncio
    async def test_update_card_not_found(
        self,
        db_session,
        test_user,
    ):
        """更新不存在的就诊卡"""
        service = UserManageService(db_session)
        data = PatientUpdate(name="新名字")

        result = await service.update_card(
            user_id=test_user.id,
            card_id="non-existent-id",
            data=data,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_card_with_appointments(
        self,
        db_session,
        test_user,
        test_patient,
        test_doctor,
        test_store,
    ):
        """有预约记录的就诊卡无法删除"""
        # 先添加第二张就诊卡（避免"至少保留一张"的检查）
        second_card = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="第二张卡",
            phone="13900003333",
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(second_card)

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

        service = UserManageService(db_session)

        with pytest.raises(BusinessError, match="预约记录"):
            await service.delete_card(
                user_id=test_user.id,
                card_id=test_patient.id,
            )

    @pytest.mark.asyncio
    async def test_delete_last_card(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """删除用户最后一张就诊卡应失败"""
        service = UserManageService(db_session)

        with pytest.raises(BusinessError, match="至少需要保留一张"):
            await service.delete_card(
                user_id=test_user.id,
                card_id=test_patient.id,
            )

    @pytest.mark.asyncio
    async def test_delete_card_success(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """成功删除就诊卡（有多张卡时）"""
        # 添加第二张就诊卡
        second_card = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="第二张卡",
            phone="13900003333",
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(second_card)
        await db_session.commit()

        service = UserManageService(db_session)
        result = await service.delete_card(
            user_id=test_user.id,
            card_id=second_card.id,
        )

        assert result is True

        # 验证已删除
        deleted_card = await db_session.get(Patient, second_card.id)
        assert deleted_card is None

    @pytest.mark.asyncio
    async def test_delete_default_card_transfers_default(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """删除默认就诊卡时，默认状态转移给其他卡"""
        # 确保主患者是默认的
        test_patient.is_default = True

        # 添加第二张就诊卡
        second_card = Patient(
            id=str(uuid4()),
            user_id=test_user.id,
            name="第二张卡",
            phone="13900003333",
            is_default=False,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(second_card)
        await db_session.commit()

        service = UserManageService(db_session)

        # 删除默认卡
        result = await service.delete_card(
            user_id=test_user.id,
            card_id=test_patient.id,
        )

        assert result is True

        # 验证第二张卡成为默认卡
        await db_session.refresh(second_card)
        assert second_card.is_default is True


class TestPatientCardLimit:
    """就诊卡数量上限（每账号限绑定 5 位成员）"""

    def _make_card(self, user_id: str, tenant_id: str | None, name: str) -> Patient:
        return Patient(
            id=str(uuid4()),
            user_id=user_id,
            tenant_id=tenant_id,
            name=name,
            phone="13900000000",
            gender=1,
            is_default=False,
            card_no=f"CK{uuid4().hex[:10].upper()}",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_create_card_rejected_at_limit(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """已有 5 张就诊卡时再创建应被拒绝"""
        for i in range(4):  # test_patient 已占 1 张，补到 5 张
            db_session.add(
                self._make_card(test_user.id, test_patient.tenant_id, f"成员{i}")
            )
        await db_session.commit()

        service = UserManageService(db_session)
        data = FamilyMemberCreate(
            name="第六位",
            phone="13900008888",
            id_card="110101199001018888",
        )

        with pytest.raises(BusinessError, match="限绑定"):
            await service.create_card(user_id=test_user.id, data=data)

    @pytest.mark.asyncio
    async def test_create_card_allowed_below_limit(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """未达上限时创建正常"""
        service = UserManageService(db_session)
        data = FamilyMemberCreate(
            name="第二位",
            phone="13900007777",
            id_card="110101199001017777",
        )

        result = await service.create_card(user_id=test_user.id, data=data)
        assert result is not None
        assert result["name"] == "第二位"
