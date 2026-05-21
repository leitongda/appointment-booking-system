from datetime import datetime

import pytest
from sqlalchemy import select

from app.models.user import Patient, User
from app.modules.patients.service_manage import PatientManageService
from app.modules.patients.service_users import UserManageService
from app.schemas.user import FamilyMemberCreate, PatientCreateByAdmin


class TestPatientManageService:
    @pytest.mark.asyncio
    async def test_create_patient_creates_user_and_card(
        self,
        db_session,
        test_store,
    ):
        service = PatientManageService(db_session)
        data = PatientCreateByAdmin(
            name="新患者",
            phone="13900139000",
            id_card="110101199201011234",
            gender=1,
            birthday="1992-01-01",
            relationship="本人",
            is_default=True,
        )

        detail = await service.create_patient(
            data,
            store_id=test_store.id,
            operator_id="admin-1",
        )

        created_user = await db_session.scalar(select(User).where(User.phone == "13900139000"))
        created_patient = await db_session.scalar(select(Patient).where(Patient.user_id == created_user.id))

        assert created_user is not None
        assert created_patient is not None
        assert created_patient.store_id == test_store.id
        assert detail["name"] == "新患者"
        assert detail["userId"] == created_user.id
        assert detail["familyMembers"][0]["name"] == "新患者"


class TestUserManageService:
    @pytest.mark.asyncio
    async def test_update_status_disables_user(
        self,
        db_session,
        test_user,
    ):
        service = UserManageService(db_session)

        success = await service.update_status(
            user_id=test_user.id,
            status=0,
            operator_id="admin-1",
        )

        refreshed_user = await db_session.scalar(select(User).where(User.id == test_user.id))

        assert success is True
        assert refreshed_user.status == 0

    @pytest.mark.asyncio
    async def test_create_card_can_replace_default_card(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        service = UserManageService(db_session)
        data = FamilyMemberCreate(
            name="家属A",
            phone="13900139001",
            id_card="110101199301011234",
            gender=2,
            birthday="1993-01-01",
            relationship="其他",
            is_default=True,
        )

        created = await service.create_card(
            user_id=test_user.id,
            data=data,
            operator_id="admin-1",
        )

        cards = (
            await db_session.execute(
                select(Patient).where(Patient.user_id == test_user.id).order_by(Patient.created_at.asc())
            )
        ).scalars().all()
        old_default = next(card for card in cards if card.id == test_patient.id)
        new_default = next(card for card in cards if card.id == created["id"])

        assert len(cards) == 2
        assert created["name"] == "家属A"
        assert old_default.is_default is False
        assert new_default.is_default is True
