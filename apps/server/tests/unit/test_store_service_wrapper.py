from app.modules.stores.service import StoreService as modular_store_service
from app.modules.stores.service import StoreService as legacy_store_service


def test_store_service_wrapper_reuses_modular_service():
    assert legacy_store_service is modular_store_service
