"""Architecture Fitness Functions — Automated Architecture Constraint Checks

Based on the Fitness Function concept from "Building Evolutionary Architectures",
encoding architectural rules as automatically executable tests.
"""
import ast
from pathlib import Path

import pytest

SERVER_ROOT = Path(__file__).resolve().parent.parent.parent
MODULES_DIR = SERVER_ROOT / "app" / "modules"

LEGACY_OVERSIZED_ROUTERS = {
    "app/modules/accounts/router.py": 379,
    "app/modules/admin/router_auth_integration.py": 366,
    "app/modules/admin/router_auth_login.py": 500,
    "app/modules/admin/router_monitoring.py": 540,
    "app/modules/analytics/router.py": 626,
    "app/modules/appointments/router_flow.py": 407,
    "app/modules/appointments/router_query.py": 722,
    "app/modules/approval_flows/router.py": 446,
    "app/modules/attendance_records/router.py": 307,
    "app/modules/auth/router.py": 1035,
    "app/modules/consultation_fees/router.py": 479,
    "app/modules/contacts/router.py": 364,
    "app/modules/content/router.py": 603,
    "app/modules/departments/router.py": 413,
    "app/modules/doctors/router.py": 979,
    "app/modules/doctor_portal/router_queue.py": 353,
    "app/modules/follow_up/router.py": 870,
    "app/modules/freelance_fees/router.py": 677,
    "app/modules/import_export/router_export.py": 883,
    "app/modules/import_export/router_import.py": 628,
    "app/modules/integration_gateway/router.py": 323,
    "app/modules/lowcode/router.py": 1117,
    "app/modules/lowcode/router_template.py": 639,
    "app/modules/messages/router.py": 345,
    "app/modules/miniapp_platform/router_build_release.py": 321,
    "app/modules/miniapp_platform/router_instance.py": 331,
    "app/modules/patients/router_manage.py": 347,
    "app/modules/rule_sets/router.py": 963,
    "app/modules/schedule_templates/router.py": 964,
    "app/modules/schedules/router.py": 949,
    "app/modules/schedules/router_custom.py": 455,
    "app/modules/schedules/router_statistics.py": 508,
    "app/modules/session_events/router.py": 489,
    "app/modules/settings/router.py": 714,
    "app/modules/statistics/router_overview.py": 348,
    "app/modules/stores/router.py": 884,
    "app/modules/tenants/router.py": 480,
    "app/modules/tenants/router_current_tenant.py": 353,
    "app/modules/unified_message/router.py": 391,
    "app/modules/upload/router.py": 325,
    "app/modules/waitlist/router.py": 532,
}

LEGACY_OVERSIZED_SERVICES = {
    "app/modules/appointments/service_booking.py": 935,
    "app/modules/appointments/service_flow.py": 514,
    "app/modules/approval_flows/service_definitions.py": 647,
    "app/modules/attendance_records/service.py": 518,
    "app/modules/content/service.py": 598,
    "app/modules/follow_up/service.py": 643,
    "app/modules/lowcode/service.py": 552,
    "app/modules/messages/service_messages.py": 708,
    "app/modules/miniapp_platform/service_instance.py": 718,
    "app/modules/patients/service_manage.py": 722,
    "app/modules/payments/service.py": 539,
    "app/modules/rule_sets/service_mutation.py": 588,
    "app/modules/schedule_suspensions/service_processing.py": 690,
    "app/modules/schedule_templates/service_generation.py": 659,
    "app/modules/schedules/service_conflict.py": 632,
    "app/modules/schedules/service_create.py": 515,
    "app/modules/tenants/service_migration.py": 501,
    "app/modules/tenants/service_tenant.py": 539,
    "app/modules/unified_message/service_send.py": 648,
}

LEGACY_OVERSIZED_SCHEMAS = {
    "app/modules/admin/schemas.py": 333,
    "app/modules/approval_flows/schemas.py": 234,
    "app/modules/contacts/schemas.py": 302,
    "app/modules/freelance_fees/schemas.py": 232,
    "app/modules/lowcode/schemas.py": 287,
    "app/modules/tenants/schemas.py": 736,
    "app/modules/unified_message/schemas.py": 238,
    "app/schemas/appointment.py": 209,
    "app/schemas/consultation_fee.py": 271,
    "app/schemas/follow_up.py": 242,
    "app/schemas/lowcode.py": 203,
    "app/schemas/rule_set.py": 309,
    "app/schemas/schedule.py": 383,
    "app/schemas/schedule_template.py": 216,
    "app/schemas/user.py": 265,
}

LEGACY_MODULES_WITHOUT_UNIT_TESTS = {
    "appointment_satisfactions",
    "attendance_groups",
    "attendance_leave",
    "attendance_records",
    "attendance_rules",
    "attendance_shifts",
    "backup",
    "booking_notices",
    "contacts",
    "dictionaries",
    "doctor_reviews",
    "email_templates",
    "examination_reports",
    "export",
    "feedbacks",
    "freelance_fees",
    "messages",
    "notification_logs",
    "notification_preferences",
    "platform_announcements",
    "rest_days",
    "revenue",
    "schedule_suspensions",
    "shift_types",
    "store_email_recipients",
    "support_tickets",
    "user_favorites",
    "users",
    "visit_types",
}


@pytest.mark.architecture
class TestFileSizeLimits:
    """Fitness Function #1: Per-file line count thresholds"""

    ROUTER_LIMIT = 300
    SERVICE_LIMIT = 500
    SCHEMA_LIMIT = 200

    def _count_lines(self, path: Path) -> int:
        return len(path.read_text(encoding="utf-8").splitlines())

    def _check_limit(self, path: Path, lines: int, limit: int, legacy_baseline: dict[str, int]) -> str | None:
        rel = str(path.relative_to(SERVER_ROOT))
        baseline = legacy_baseline.get(rel)
        if baseline is not None:
            if lines > baseline:
                return f"{rel}: {lines} lines (legacy baseline {baseline})"
            return None
        if lines > limit:
            return f"{rel}: {lines} lines"
        return None

    def test_routers_within_limit(self):
        """router.py files should not exceed ROUTER_LIMIT lines or legacy baseline"""
        violations = []
        for router_file in MODULES_DIR.rglob("router*.py"):
            lines = self._count_lines(router_file)
            violation = self._check_limit(
                router_file, lines, self.ROUTER_LIMIT, LEGACY_OVERSIZED_ROUTERS
            )
            if violation:
                violations.append(violation)
        assert not violations, (
            f"Router files exceed {self.ROUTER_LIMIT} lines:\n" + "\n".join(violations)
        )

    def test_services_within_limit(self):
        """service*.py files should not exceed SERVICE_LIMIT lines or legacy baseline"""
        violations = []
        for service_file in MODULES_DIR.rglob("service*.py"):
            if service_file.name == "__init__.py":
                continue
            lines = self._count_lines(service_file)
            violation = self._check_limit(
                service_file, lines, self.SERVICE_LIMIT, LEGACY_OVERSIZED_SERVICES
            )
            if violation:
                violations.append(violation)
        assert not violations, (
            f"Service files exceed {self.SERVICE_LIMIT} lines:\n" + "\n".join(violations)
        )

    def test_schemas_within_limit(self):
        """schema files should not exceed SCHEMA_LIMIT lines or legacy baseline"""
        violations = []
        # Check module-internal schemas.py files
        for schema_file in MODULES_DIR.rglob("schemas.py"):
            lines = self._count_lines(schema_file)
            violation = self._check_limit(
                schema_file, lines, self.SCHEMA_LIMIT, LEGACY_OVERSIZED_SCHEMAS
            )
            if violation:
                violations.append(violation)
        # Also check global schemas directory
        global_schemas = SERVER_ROOT / "app" / "schemas"
        if global_schemas.exists():
            for schema_file in global_schemas.glob("*.py"):
                if schema_file.name.startswith("_"):
                    continue
                lines = self._count_lines(schema_file)
                violation = self._check_limit(
                    schema_file, lines, self.SCHEMA_LIMIT, LEGACY_OVERSIZED_SCHEMAS
                )
                if violation:
                    violations.append(violation)
        assert not violations, (
            f"Schema files exceed {self.SCHEMA_LIMIT} lines:\n" + "\n".join(violations)
        )


@pytest.mark.architecture
class TestModuleTestCoverage:
    """Fitness Function #2: Every business module must have corresponding tests"""

    def _has_corresponding_test(self, module_name: str, test_files: set[str]) -> bool:
        candidates = {module_name}
        if module_name.endswith("s"):
            candidates.add(module_name[:-1])
        for test_name in test_files:
            for candidate in candidates:
                if test_name == candidate or test_name.startswith(f"{candidate}_"):
                    return True
        return False

    def test_all_modules_have_tests(self):
        """Every module with service.py must have a corresponding test file"""
        test_dir = SERVER_ROOT / "tests" / "unit"
        if not test_dir.exists():
            pytest.skip("tests/unit/ directory does not exist")

        modules_with_service = []
        for module_dir in sorted(MODULES_DIR.iterdir()):
            if not module_dir.is_dir():
                continue
            if module_dir.name.startswith("_"):
                continue
            service_files = list(module_dir.glob("service*.py"))
            service_files = [f for f in service_files if f.name != "__init__.py"]
            if service_files:
                modules_with_service.append(module_dir.name)

        test_files = {f.stem.removeprefix("test_") for f in test_dir.glob("test_*.py")}

        missing = [
            m for m in modules_with_service
            if not self._has_corresponding_test(m, test_files)
            and m not in LEGACY_MODULES_WITHOUT_UNIT_TESTS
        ]
        assert not missing, (
            "The following modules lack unit tests:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )


@pytest.mark.architecture
class TestNoPrintStatements:
    """Fitness Function #3: No print() calls in module code"""

    def test_no_print_in_modules(self):
        """modules/ should not contain print() statements"""
        violations = []
        for py_file in MODULES_DIR.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func = node.func
                        if isinstance(func, ast.Name) and func.id == "print":
                            violations.append(f"{py_file.relative_to(SERVER_ROOT)}:{node.lineno}")
            except SyntaxError:
                pass
        assert not violations, "print() calls found:\n" + "\n".join(violations)


@pytest.mark.architecture
class TestNoHardcodedPasswords:
    """Fitness Function #4: No hardcoded passwords"""

    # Directories to skip entirely (contain legitimate example values)
    EXCLUDED_DIRS = {"schemas", "docs", "scripts"}

    def _should_skip_file(self, py_file: Path) -> bool:
        rel = str(py_file.relative_to(SERVER_ROOT))
        if "__pycache__" in rel:
            return True
        if "test" in rel:
            return True
        # Skip files under schemas/ or similar example/documentation directories
        parts = py_file.relative_to(SERVER_ROOT / "app").parts
        if any(part in self.EXCLUDED_DIRS for part in parts):
            return True
        return False

    def _is_in_documentation_context(self, line: str) -> bool:
        """Heuristic: skip lines that are clearly comments or documentation examples."""
        stripped = line.strip()
        # Python comments
        if stripped.startswith("#"):
            return True
        # JSON-style examples inside docstrings / triple-quoted strings
        # e.g.  "verificationCode": "123456",
        if stripped.startswith('"') and stripped.endswith('",') or stripped.endswith('"'):
            return True
        if stripped.startswith("'") and (stripped.endswith("',") or stripped.endswith("'")):
            return True
        return False

    def test_no_hardcoded_123456(self):
        """Source code should not contain the string '123456' (excluding tests, schemas, and docstrings)"""
        violations = []
        for py_file in (SERVER_ROOT / "app").rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    if '"123456"' not in line and "'123456'" not in line:
                        continue
                    if self._is_in_documentation_context(line):
                        continue
                    violations.append(f"{py_file.relative_to(SERVER_ROOT)}:{i}")
            except Exception:
                pass
        assert not violations, (
            "Hardcoded password '123456' found:\n" + "\n".join(violations)
        )
