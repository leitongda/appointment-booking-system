from app.modules.consultation_fees.service import (
    ConsultationFeeService as modular_consultation_fee_service,
)
from app.services.consultation_fee_service import (
    ConsultationFeeService as legacy_consultation_fee_service,
)


def test_consultation_fee_service_wrapper_reuses_modular_service():
    assert legacy_consultation_fee_service is modular_consultation_fee_service
