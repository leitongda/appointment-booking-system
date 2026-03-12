from app.common.utils import format_client_ip as common_format_client_ip
from app.common.utils import get_client_ip as common_get_client_ip
from app.common.utils import get_client_ips as common_get_client_ips
from app.common.utils import is_private_ip as common_is_private_ip
from app.utils.ip import format_client_ip, get_client_ip, get_client_ips, is_private_ip


def test_ip_utils_wrapper_reuses_common_exports():
    assert get_client_ip is common_get_client_ip
    assert get_client_ips is common_get_client_ips
    assert format_client_ip is common_format_client_ip
    assert is_private_ip is common_is_private_ip
