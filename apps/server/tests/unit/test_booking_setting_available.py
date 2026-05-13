import json
from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.middleware.tenant_context import get_current_tenant_id
from app.models.doctor_booking_setting import DoctorBookingSetting
from app.models.schedule import Schedule
from app.modules.schedules.service import ScheduleService


def _make_setting(
    store_id: str,
    doctor_id: str,
    tenant_id: str,
    booking_start_offset: int = 0,
    booking_range_days: int = 14,
    release_time: str = "00:00",
    status: int = 1,
) -> DoctorBookingSetting:
    return DoctorBookingSetting(
        id=str(uuid4()),
        store_id=store_id,
        doctor_id=doctor_id,
        tenant_id=tenant_id,
        booking_start_offset=booking_start_offset,
        booking_range_days=booking_range_days,
        release_time=release_time,
        status=status,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _make_schedule(
    doctor_id: str,
    store_id: str,
    tenant_id: str,
    schedule_date: date,
    time_slot: str = "morning",
    start_time: time = time(8, 0),
    end_time: time = time(12, 0),
    total_slots: int = 10,
    booked_slots: int = 0,
) -> Schedule:
    return Schedule(
        id=str(uuid4()),
        doctor_id=doctor_id,
        store_id=store_id,
        tenant_id=tenant_id,
        schedule_date=schedule_date,
        time_slot=time_slot,
        start_time=start_time,
        end_time=end_time,
        total_slots=total_slots,
        booked_slots=booked_slots,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.mark.unit
class TestGetAvailableWithBookingSetting:
    async def test_enabled_setting_overrides_days(
        self, db_session, test_doctor, test_store, test_tenant
    ):
        setting = _make_setting(
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            tenant_id=test_tenant.id,
            booking_start_offset=2,
            booking_range_days=5,
        )
        db_session.add(setting)

        today = date.today()
        for offset in range(15):
            s = _make_schedule(
                doctor_id=test_doctor.id,
                store_id=test_store.id,
                tenant_id=test_tenant.id,
                schedule_date=today + timedelta(days=offset),
            )
            db_session.add(s)
        await db_session.commit()

        service = ScheduleService(db_session)
        with patch.object(
            type(service),
            "_compute_booking_date_range",
            wraps=service._compute_booking_date_range,
        ):
            with patch(
                "app.modules.schedules.service_query.get_current_tenant_id",
                return_value=test_tenant.id,
            ):
                schedules, applied = await service.get_available(
                    doctor_id=test_doctor.id, days=14
                )

        assert applied is True
        assert len(schedules) == 5

    async def test_disabled_setting_falls_back_to_days(
        self, db_session, test_doctor, test_store, test_tenant
    ):
        setting = _make_setting(
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            tenant_id=test_tenant.id,
            booking_start_offset=2,
            booking_range_days=5,
            status=0,
        )
        db_session.add(setting)

        today = date.today()
        for offset in range(15):
            s = _make_schedule(
                doctor_id=test_doctor.id,
                store_id=test_store.id,
                tenant_id=test_tenant.id,
                schedule_date=today + timedelta(days=offset),
            )
            db_session.add(s)
        await db_session.commit()

        service = ScheduleService(db_session)
        with patch(
            "app.modules.schedules.service_query.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            schedules, applied = await service.get_available(
                doctor_id=test_doctor.id, days=14
            )

        assert applied is False
        assert len(schedules) == 14

    async def test_no_setting_falls_back_to_days(
        self, db_session, test_doctor, test_store, test_tenant
    ):
        today = date.today()
        for offset in range(15):
            s = _make_schedule(
                doctor_id=test_doctor.id,
                store_id=test_store.id,
                tenant_id=test_tenant.id,
                schedule_date=today + timedelta(days=offset),
            )
            db_session.add(s)
        await db_session.commit()

        service = ScheduleService(db_session)
        with patch(
            "app.modules.schedules.service_query.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            schedules, applied = await service.get_available(
                doctor_id=test_doctor.id, days=14
            )

        assert applied is False
        assert len(schedules) == 14

    async def test_release_time_before_cutoff(
        self, db_session, test_doctor, test_store, test_tenant
    ):
        setting = _make_setting(
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            tenant_id=test_tenant.id,
            booking_start_offset=0,
            booking_range_days=7,
            release_time="23:59",
        )
        db_session.add(setting)

        today = date.today()
        for offset in range(15):
            s = _make_schedule(
                doctor_id=test_doctor.id,
                store_id=test_store.id,
                tenant_id=test_tenant.id,
                schedule_date=today + timedelta(days=offset),
            )
            db_session.add(s)
        await db_session.commit()

        service = ScheduleService(db_session)
        with patch(
            "app.modules.schedules.service_query.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            schedules, applied = await service.get_available(
                doctor_id=test_doctor.id, days=14
            )

        assert applied is True
        today_offset_1 = today + timedelta(days=1)
        assert all(s.schedule_date >= today_offset_1 for s in schedules)

    async def test_release_time_after_cutoff(
        self, db_session, test_doctor, test_store, test_tenant
    ):
        setting = _make_setting(
            store_id=test_store.id,
            doctor_id=test_doctor.id,
            tenant_id=test_tenant.id,
            booking_start_offset=0,
            booking_range_days=7,
            release_time="00:00",
        )
        db_session.add(setting)

        today = date.today()
        for offset in range(15):
            s = _make_schedule(
                doctor_id=test_doctor.id,
                store_id=test_store.id,
                tenant_id=test_tenant.id,
                schedule_date=today + timedelta(days=offset),
            )
            db_session.add(s)
        await db_session.commit()

        service = ScheduleService(db_session)
        with patch(
            "app.modules.schedules.service_query.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            schedules, applied = await service.get_available(
                doctor_id=test_doctor.id, days=14
            )

        assert applied is True
        assert len(schedules) == 8

    async def test_store_id_filters_setting(
        self, db_session, test_doctor, test_store, test_tenant
    ):
        other_store_id = str(uuid4())
        setting = _make_setting(
            store_id=other_store_id,
            doctor_id=test_doctor.id,
            tenant_id=test_tenant.id,
            booking_start_offset=5,
            booking_range_days=3,
        )
        db_session.add(setting)

        today = date.today()
        for offset in range(15):
            s = _make_schedule(
                doctor_id=test_doctor.id,
                store_id=test_store.id,
                tenant_id=test_tenant.id,
                schedule_date=today + timedelta(days=offset),
            )
            db_session.add(s)
        await db_session.commit()

        service = ScheduleService(db_session)
        with patch(
            "app.modules.schedules.service_query.get_current_tenant_id",
            return_value=test_tenant.id,
        ):
            schedules, applied = await service.get_available(
                doctor_id=test_doctor.id, days=14, store_id=test_store.id
            )

        assert applied is False
        assert len(schedules) == 14


@pytest.mark.unit
class TestComputeBookingDateRange:
    async def test_no_release_time(self, db_session):
        service = ScheduleService(db_session)
        setting = _make_setting(
            store_id="s1",
            doctor_id="d1",
            tenant_id="t1",
            booking_start_offset=3,
            booking_range_days=10,
            release_time="00:00",
        )
        start, end = service._compute_booking_date_range(setting)
        today = date.today()
        assert start == today + timedelta(days=3)
        assert end == today + timedelta(days=13)

    async def test_release_time_already_passed(self, db_session):
        service = ScheduleService(db_session)
        setting = _make_setting(
            store_id="s1",
            doctor_id="d1",
            tenant_id="t1",
            booking_start_offset=0,
            booking_range_days=7,
            release_time="00:01",
        )
        start, end = service._compute_booking_date_range(setting)
        today = date.today()
        assert start == today
        assert end == today + timedelta(days=7)

    async def test_release_time_not_yet_reached(self, db_session):
        service = ScheduleService(db_session)
        setting = _make_setting(
            store_id="s1",
            doctor_id="d1",
            tenant_id="t1",
            booking_start_offset=0,
            booking_range_days=7,
            release_time="23:59",
        )
        start, end = service._compute_booking_date_range(setting)
        today = date.today()
        assert start == today + timedelta(days=1)
        assert end == today + timedelta(days=8)

    async def test_release_time_with_start_offset(self, db_session):
        service = ScheduleService(db_session)
        setting = _make_setting(
            store_id="s1",
            doctor_id="d1",
            tenant_id="t1",
            booking_start_offset=2,
            booking_range_days=5,
            release_time="23:59",
        )
        start, end = service._compute_booking_date_range(setting)
        today = date.today()
        assert start == today + timedelta(days=3)
        assert end == today + timedelta(days=8)
