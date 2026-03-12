from app.api import deps as legacy_deps
from app.common import deps as common_deps
from app.common.responses import ErrorResponse, PageResponse, Response
from app.schemas.response import ErrorResponse as SchemaErrorResponse
from app.schemas.response import PageResponse as SchemaPageResponse
from app.schemas.response import Response as SchemaResponse


def test_api_deps_wrapper_reuses_common_exports():
    assert legacy_deps.get_current_admin is common_deps.get_current_admin
    assert legacy_deps.get_current_user is common_deps.get_current_user
    assert legacy_deps.require_permission is common_deps.require_permission


def test_common_responses_reuse_schema_exports():
    assert Response is SchemaResponse
    assert PageResponse is SchemaPageResponse
    assert ErrorResponse is SchemaErrorResponse
