from app.modules.doctors.service import DoctorService as modular_doctor_service
from app.services.doctor_service import DoctorService as legacy_doctor_service


def test_doctor_service_wrapper_reuses_modular_service():
    assert legacy_doctor_service is modular_doctor_service
