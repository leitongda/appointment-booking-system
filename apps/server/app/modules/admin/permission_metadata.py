"""Permission metadata helpers."""

from __future__ import annotations

from typing import Literal, Optional, Sequence


PermissionControlType = Literal["page", "tab", "action", "api"]

ACTION_SEGMENTS = {
    "create",
    "update",
    "delete",
    "approve",
    "refund",
    "send",
    "reply",
    "reset-password",
    "manage",
    "cancel",
    "bind",
    "import",
    "batch",
    "sort",
    "kick",
    "generate-username",
    "check-username",
    "check-unique",
    "status",
}

API_SEGMENTS = {
    "list",
    "detail",
    "view",
    "export",
    "statistics",
    "all",
    "history",
}


def infer_permission_control_type(
    code: str,
    permission_type: str,
    depth: int = 0,
    has_children: bool = False,
) -> PermissionControlType:
    """Infer control type from permission metadata."""
    last_segment = code.split(":")[-1]

    if depth == 0:
        return "page"

    if has_children:
        return "tab"

    if last_segment in ACTION_SEGMENTS:
        return "action"

    if last_segment in API_SEGMENTS:
        return "api"

    if depth == 1 or permission_type == "menu":
        return "tab"

    return "action"


def infer_permission_control_type_for_seed(
    permission: dict,
    all_permissions: Sequence[dict],
) -> PermissionControlType:
    """Infer control type for seed data using parent/child relations."""
    code = permission["code"]
    parent_code = permission.get("parent_code")
    depth = 0
    visited = set()

    while parent_code and parent_code not in visited:
        visited.add(parent_code)
        depth += 1
        parent = next((item for item in all_permissions if item["code"] == parent_code), None)
        parent_code = parent.get("parent_code") if parent else None

    has_children = any(item.get("parent_code") == code for item in all_permissions)
    return infer_permission_control_type(
        code=code,
        permission_type=permission["type"],
        depth=depth,
        has_children=has_children,
    )


def normalize_control_type(value: Optional[str]) -> Optional[PermissionControlType]:
    if value in {"page", "tab", "action", "api"}:
        return value
    return None
