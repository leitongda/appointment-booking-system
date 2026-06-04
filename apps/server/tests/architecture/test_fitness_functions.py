"""Architecture Fitness Functions — Automated Architecture Constraint Checks

Based on the Fitness Function concept from "Building Evolutionary Architectures",
encoding architectural rules as automatically executable tests.
"""
import ast
from pathlib import Path

import pytest

SERVER_ROOT = Path(__file__).resolve().parent.parent.parent
MODULES_DIR = SERVER_ROOT / "app" / "modules"


@pytest.mark.architecture
class TestFileSizeLimits:
    """Fitness Function #1: Per-file line count thresholds"""

    ROUTER_LIMIT = 300
    SERVICE_LIMIT = 500
    SCHEMA_LIMIT = 200

    def _count_lines(self, path: Path) -> int:
        return len(path.read_text(encoding="utf-8").splitlines())

    def test_routers_within_limit(self):
        """router.py files should not exceed ROUTER_LIMIT lines"""
        violations = []
        for router_file in MODULES_DIR.rglob("router*.py"):
            lines = self._count_lines(router_file)
            if lines > self.ROUTER_LIMIT:
                violations.append(f"{router_file.relative_to(SERVER_ROOT)}: {lines} lines")
        assert not violations, (
            f"Router files exceed {self.ROUTER_LIMIT} lines:\n" + "\n".join(violations)
        )

    def test_services_within_limit(self):
        """service*.py files should not exceed SERVICE_LIMIT lines"""
        violations = []
        for service_file in MODULES_DIR.rglob("service*.py"):
            if service_file.name == "__init__.py":
                continue
            lines = self._count_lines(service_file)
            if lines > self.SERVICE_LIMIT:
                violations.append(f"{service_file.relative_to(SERVER_ROOT)}: {lines} lines")
        assert not violations, (
            f"Service files exceed {self.SERVICE_LIMIT} lines:\n" + "\n".join(violations)
        )

    def test_schemas_within_limit(self):
        """schemas.py files should not exceed SCHEMA_LIMIT lines"""
        violations = []
        # Check module-internal schemas.py files
        for schema_file in MODULES_DIR.rglob("schemas.py"):
            lines = self._count_lines(schema_file)
            if lines > self.SCHEMA_LIMIT:
                violations.append(f"{schema_file.relative_to(SERVER_ROOT)}: {lines} lines")
        # Also check global schemas directory
        global_schemas = SERVER_ROOT / "app" / "schemas"
        if global_schemas.exists():
            for schema_file in global_schemas.glob("*.py"):
                if schema_file.name.startswith("_"):
                    continue
                lines = self._count_lines(schema_file)
                if lines > self.SCHEMA_LIMIT:
                    violations.append(f"{schema_file.relative_to(SERVER_ROOT)}: {lines} lines")
        assert not violations, (
            f"Schema files exceed {self.SCHEMA_LIMIT} lines:\n" + "\n".join(violations)
        )


@pytest.mark.architecture
class TestModuleTestCoverage:
    """Fitness Function #2: Every business module must have corresponding tests"""

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

        test_files = {f.stem.replace("test_", "") for f in test_dir.glob("test_*.py")}

        missing = [m for m in modules_with_service if m not in test_files]
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
