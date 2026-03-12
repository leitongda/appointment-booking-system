# Server Module Boundaries Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reorganize the FastAPI server into a modular monolith with enforceable boundaries while preserving existing API behavior.

**Architecture:** Start by freezing behavior with feature and architecture tests, then introduce the new module skeleton and migrate low-risk modules as templates. Split oversized routers and services only after the boundary rules and migration path are proven.

**Tech Stack:** FastAPI, SQLAlchemy async, Pydantic v2, pytest, Alembic

---

### Task 1: Create architecture guard tests

**Files:**
- Create: `apps/server/tests/unit/test_architecture_router_boundaries.py`
- Modify: `apps/server/tests/conftest.py`

**Step 1: Write the failing test**

```python
from pathlib import Path


def test_router_files_do_not_define_business_basemodels():
    router_dir = Path("apps/server/app/api/v1")
    offenders = []
    for file in router_dir.glob("*.py"):
        text = file.read_text(encoding="utf-8")
        if "class " in text and "(BaseModel)" in text:
            offenders.append(file.name)
    assert offenders == []
```

**Step 2: Run test to verify it fails**

Run: `cd apps/server && pytest tests/unit/test_architecture_router_boundaries.py -v`
Expected: FAIL because current router files still contain business DTO classes

**Step 3: Add a second guard for direct ORM access in router files**

```python
def test_router_files_do_not_execute_orm_queries_directly():
    router_dir = Path("apps/server/app/api/v1")
    offenders = []
    patterns = ("db.execute(", "db.scalar(", "select(")
    for file in router_dir.glob("*.py"):
        text = file.read_text(encoding="utf-8")
        if any(pattern in text for pattern in patterns):
            offenders.append(file.name)
    assert offenders == []
```

**Step 4: Run test to verify it fails**

Run: `cd apps/server && pytest tests/unit/test_architecture_router_boundaries.py -v`
Expected: FAIL because current router files still query ORM directly

**Step 5: Commit**

```bash
git add apps/server/tests/unit/test_architecture_router_boundaries.py apps/server/tests/conftest.py
git commit -m "test: add router boundary architecture guards"
```

### Task 2: Introduce the new server module skeleton

**Files:**
- Create: `apps/server/app/modules/__init__.py`
- Create: `apps/server/app/modules/content/__init__.py`
- Create: `apps/server/app/modules/content/router.py`
- Create: `apps/server/app/modules/content/schemas.py`
- Create: `apps/server/app/modules/content/service.py`
- Create: `apps/server/app/common/__init__.py`
- Create: `apps/server/app/common/deps/__init__.py`
- Create: `apps/server/app/infrastructure/__init__.py`
- Modify: `apps/server/app/api/v1/__init__.py`

**Step 1: Create empty package initializers**

```python
# modules package
```

**Step 2: Move content DTOs into module schemas**

```python
class NewsCreate(BaseModel):
    title: str
    content: str
```

**Step 3: Re-export or register module router**

```python
from app.modules.content.router import router as content_router

api_router.include_router(content_router, prefix="/content", tags=["内容管理"])
```

**Step 4: Run targeted tests**

Run: `cd apps/server && pytest tests/unit -k content -v`
Expected: Existing content behavior still passes

**Step 5: Commit**

```bash
git add apps/server/app/modules apps/server/app/common apps/server/app/infrastructure apps/server/app/api/v1/__init__.py
git commit -m "refactor: add modular server package skeleton"
```

### Task 3: Migrate the content module as the first template

**Files:**
- Modify: `apps/server/app/api/v1/content.py`
- Modify: `apps/server/app/services/content_service.py`
- Create: `apps/server/app/modules/content/queries.py`
- Create: `apps/server/tests/integration/test_content_module_compat.py`

**Step 1: Write compatibility tests for existing content endpoints**

```python
async def test_get_news_list_keeps_existing_shape(client, admin_token):
    response = await client.get("/api/v1/content/news", headers=admin_token)
    assert response.status_code == 200
```

**Step 2: Move request and response DTOs from router to module schemas**

```python
from app.modules.content.schemas import NewsCreate, NewsResponse
```

**Step 3: Extract list and detail queries into module query helpers**

```python
async def list_news(...):
    return await db.execute(query)
```

**Step 4: Keep legacy imports working while reducing router logic**

```python
from app.modules.content.service import NewsService
```

**Step 5: Run tests**

Run: `cd apps/server && pytest tests/integration/test_content_module_compat.py tests/unit -k content -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/server/app/api/v1/content.py apps/server/app/services/content_service.py apps/server/app/modules/content apps/server/tests/integration/test_content_module_compat.py
git commit -m "refactor: migrate content module to modular layout"
```

### Task 4: Move runtime data configuration out of the source tree

**Files:**
- Modify: `apps/server/app/core/config.py`
- Modify: `apps/server/app/services/storage/local_storage.py`
- Modify: `apps/server/.env.example`
- Modify: `.gitignore`
- Modify: `docs/server/config.md`

**Step 1: Add explicit runtime directory settings**

```python
RUNTIME_DATA_DIR: str = "var/server"
LOG_DIR: str = "var/server/logs"
LOCAL_UPLOAD_DIR: str = "var/server/uploads"
```

**Step 2: Make local storage resolve relative to runtime data**

```python
upload_dir = Path(settings.LOCAL_UPLOAD_DIR)
upload_dir.mkdir(parents=True, exist_ok=True)
```

**Step 3: Document the new defaults**

```md
- Logs default to `var/server/logs`
- Uploads default to `var/server/uploads`
```

**Step 4: Run targeted tests**

Run: `cd apps/server && pytest tests/unit -k upload -v`
Expected: PASS or no tests collected

**Step 5: Commit**

```bash
git add apps/server/app/core/config.py apps/server/app/services/storage/local_storage.py apps/server/.env.example .gitignore docs/server/config.md
git commit -m "refactor: isolate runtime data directories"
```

### Task 5: Split the oversized admin router

**Files:**
- Create: `apps/server/app/modules/admin/router_auth.py`
- Create: `apps/server/app/modules/admin/router_admins.py`
- Create: `apps/server/app/modules/admin/router_roles.py`
- Create: `apps/server/app/modules/admin/router_audit_logs.py`
- Create: `apps/server/app/modules/admin/schemas.py`
- Modify: `apps/server/app/api/v1/admin.py`
- Modify: `apps/server/app/api/v1/__init__.py`

**Step 1: Write compatibility tests for the highest-risk admin endpoints**

```python
async def test_admin_login_keeps_response_shape(...):
    ...
```

**Step 2: Move duplicated DTOs into shared admin schemas**

```python
class AdminLoginRequest(BaseModel):
    username: str
    password: str
```

**Step 3: Split routers by responsibility and aggregate them**

```python
router.include_router(auth_router)
router.include_router(role_router)
```

**Step 4: Run targeted tests**

Run: `cd apps/server && pytest tests/unit -k admin -v`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/server/app/modules/admin apps/server/app/api/v1/admin.py apps/server/app/api/v1/__init__.py
git commit -m "refactor: split admin router by responsibility"
```

### Task 6: Split appointment and patient services

**Files:**
- Create: `apps/server/app/modules/appointments/service_booking.py`
- Create: `apps/server/app/modules/appointments/service_checkin.py`
- Create: `apps/server/app/modules/patients/service_profile.py`
- Create: `apps/server/app/modules/patients/service_management.py`
- Modify: `apps/server/app/services/appointment_service.py`
- Modify: `apps/server/app/services/patient_service.py`
- Modify: `apps/server/tests/unit/test_appointment_create.py`
- Modify: `apps/server/tests/unit/test_appointment_checkin.py`

**Step 1: Freeze behavior with targeted unit tests**

```python
async def test_create_appointment_when_schedule_available(...):
    ...
```

**Step 2: Extract booking and check-in responsibilities into dedicated services**

```python
class AppointmentBookingService:
    async def create(...):
        ...
```

**Step 3: Extract patient profile and admin management responsibilities**

```python
class PatientManagementService:
    async def get_list(...):
        ...
```

**Step 4: Keep old service entry points delegating to new classes during transition**

```python
class AppointmentService:
    def __init__(self, db):
        self.booking = AppointmentBookingService(db)
```

**Step 5: Run tests**

Run: `cd apps/server && pytest tests/unit/test_appointment_create.py tests/unit/test_appointment_checkin.py tests/unit/test_appointment_status_flow.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/server/app/modules/appointments apps/server/app/modules/patients apps/server/app/services/appointment_service.py apps/server/app/services/patient_service.py apps/server/tests/unit/test_appointment_create.py apps/server/tests/unit/test_appointment_checkin.py
git commit -m "refactor: split appointment and patient services"
```

### Task 7: Final cleanup and docs

**Files:**
- Modify: `docs/server/README.md`
- Modify: `docs/architecture.md`
- Modify: `openspec/changes/refactor-server-module-boundaries/tasks.md`

**Step 1: Remove compatibility imports once migrations are complete**

```python
# delete legacy re-export paths after callers are migrated
```

**Step 2: Update architecture docs with the new placement rules**

```md
- Routers stay thin
- DTOs live in module schemas
- External integrations live in infrastructure
```

**Step 3: Run final verification**

Run: `cd apps/server && pytest`
Expected: PASS

**Step 4: Commit**

```bash
git add docs/server/README.md docs/architecture.md openspec/changes/refactor-server-module-boundaries/tasks.md
git commit -m "docs: finalize server modularization guidance"
```
