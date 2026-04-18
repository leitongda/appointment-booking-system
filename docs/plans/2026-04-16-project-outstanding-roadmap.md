# Project Outstanding Roadmap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Close the current high-value unfinished work in a safe order, reduce architectural drift, and create a realistic path for the remaining OpenSpec changes.

**Architecture:** Resolve governance and isolation gaps first, then deliver small scoped product improvements with low coupling, then execute the approved admin information architecture refactor, and finally start the template-driven miniapp platform as a dedicated project. Do not start large structural work until its OpenSpec change is aligned and explicitly approved.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Redis, Celery, React, Umi, Ant Design, pnpm monorepo, OpenSpec docs.

---

## Planning Assumptions

- Use local `openspec/` files as the source of truth. The `openspec` CLI is not available in the current shell, so all planning references are based on repository files instead of command output.
- Treat `openspec/changes/refactor-admin-menu-information-architecture/` and `openspec/changes/add-template-driven-miniapp-platform/` as approved planning inputs but not yet approved implementation work.
- Treat `openspec/changes/enhance-schedule-rule-management/` as duplicate work that should be archived instead of implemented.
- Prefer finishing tenant safety and small backlog items before starting large UX or platform rewrites.

## Recommended Delivery Order

### Phase 0: Governance and backlog hygiene (0.5-1 day)

**Outcome:** Eliminate duplicated planning work and make the active backlog trustworthy.

**Files:**
- Modify: `openspec/STATUS.md`
- Modify: `openspec/changes/enhance-schedule-rule-management/tasks.md`
- Review: `openspec/changes/archive/2026-03-27-add-schedule-rule-enhancements/tasks.md`
- Review: `openspec/changes/refactor-admin-menu-information-architecture/tasks.md`
- Review: `openspec/changes/update-appointment-list-page-size/tasks.md`
- Review: `openspec/changes/add-template-driven-miniapp-platform/tasks.md`

**Steps:**
1. Mark the duplicate `enhance-schedule-rule-management` change as archive-only work in the backlog tracker.
2. Normalize `openspec/STATUS.md` so the active changes list has no duplicates and reflects a single recommended execution order.
3. Add explicit blockers to the two large changes:
   - admin menu IA requires naming and compatibility approval
   - miniapp platform requires product and release ownership confirmation
4. Freeze the next executable scope as:
   - multi-tenant P1 closure
   - appointment list page size
   - targeted code TODO cleanup

**Verification:**
- `openspec/STATUS.md` shows one source of truth for active work.
- No team member can mistake the duplicate schedule-rule change as active delivery scope.

## Phase 1: Multi-tenant P1 closure (3-5 days)

**Outcome:** Finish the remaining tenant isolation and quota work before new product surface area is added.

**Files:**
- Modify: `apps/server/app/common/quota.py`
- Modify: `apps/server/app/modules/tenants/service.py`
- Modify: `apps/server/app/modules/import_export/service_import.py`
- Modify: `apps/server/app/core/redis.py`
- Modify: `apps/server/app/tasks/notification_task.py`
- Test: `apps/server/tests/tenants/test_quota.py`
- Test: `apps/server/tests/tenants/test_import_tenant_isolation.py`
- Test: `apps/server/tests/tenants/test_cache_isolation.py`
- Test: `apps/server/tests/tenants/test_distributed_lock_isolation.py`
- Test: `apps/server/tests/integration/test_import_export_endpoints.py`

### Task 1.1: Integrate real-time quota checks into create flows

**Steps:**
1. Inventory all resource creation paths that must enforce subscription limits:
   - store
   - admin
   - doctor
   - appointment
2. Add one failing test per resource in the existing tenant/quota test suite.
3. Wire quota checks into the corresponding service-layer create methods instead of router-only guards.
4. Return domain-specific validation errors that identify the exceeded limit.
5. Re-run the quota and affected integration tests.

**Verification:**
- Over-limit creation attempts fail consistently in service and API layers.
- Existing in-limit scenarios continue to pass.

### Task 1.2: Finish import service tenant isolation

**Steps:**
1. Review `service_import.py` for any query, create, or upsert path that does not bind tenant scope explicitly.
2. Add failing tests that import data from tenant A while authenticated as tenant B.
3. Apply explicit tenant filters and ownership assignment to imported resources.
4. Re-run import/export integration tests.

**Verification:**
- Cross-tenant import is rejected or correctly re-bound.
- Imported resources always receive the current tenant context.

### Task 1.3: Close cache and lock isolation gaps

**Steps:**
1. Audit Redis key helpers for missing tenant dimensions beyond admin session coverage.
2. Update lock keys and cache keys to include `tenant_id` where collisions or leakage are possible.
3. Add or extend tests in `test_cache_isolation.py` and `test_distributed_lock_isolation.py`.
4. Re-run tenant isolation tests.

**Verification:**
- Redis key generation is tenant-aware for business-critical paths.
- Tenant A cache or lock operations cannot affect tenant B.

### Task 1.4: Implement storage usage accounting

**Steps:**
1. Decide the authoritative source of storage usage:
   - uploaded file metadata table if available
   - object storage metadata if not
2. Add a failing unit test for `_get_storage_usage`.
3. Implement `apps/server/app/modules/tenants/service.py` storage aggregation.
4. Re-run tenant usage tests.

**Verification:**
- Tenant usage endpoints return non-zero storage figures when data exists.
- Returned value matches the selected storage accounting rule.

## Phase 2: Fast-return backlog items (2-3 days)

**Outcome:** Deliver the smallest useful unfinished features before touching large navigation or platform work.

**Files:**
- Modify: `apps/server/app/core/config.py`
- Modify: `apps/server/app/modules/appointments/router_query.py`
- Modify: `apps/server/app/schemas` related appointment query schema files
- Modify: `packages/api/src/modules/appointment.ts`
- Modify: `docs/api/README.md`
- Test: `apps/server/tests/integration/test_appointments_router_endpoints.py`
- Test: `apps/server/tests/unit/test_appointment_create.py`

### Task 2.1: Deliver `update-appointment-list-page-size`

**Steps:**
1. Add `APPOINTMENTS_MAX_PAGE_SIZE` config and `.env.example` documentation.
2. Add failing API tests for:
   - admin + date range + large page size succeeds
   - non-admin large page size fails
   - admin without date range fails
   - value over configured max fails
3. Implement router or schema validation with clear error messages.
4. Update API docs and package comments.
5. Re-run appointment endpoint tests.

**Verification:**
- OpenSpec task list for this change can be checked off end to end.
- Large exports or operational queries no longer require code-side pagination workarounds.

### Task 2.2: Add store filter support to appointment statistics

**Files:**
- Modify: `apps/server/app/modules/appointments/router_query.py`
- Modify: appointment statistics service/query implementation under `apps/server/app/modules/appointments/`
- Test: `apps/server/tests/integration/test_appointments_router_endpoints.py`

**Steps:**
1. Add a failing test for statistics filtered by store.
2. Extend service query parameters and tenant-safe store permission checks.
3. Update response documentation.
4. Re-run statistics-related tests.

**Verification:**
- Admin users can filter appointment statistics by store where authorized.

## Phase 3: External-integration TODO cleanup (2-4 days, blocked by vendor choice)

**Outcome:** Remove "fake send" behavior from SMS-related flows, or explicitly document that the project is still in mock mode.

**Files:**
- Modify: `apps/server/app/infrastructure/sms/service.py`
- Modify: `apps/server/app/infrastructure/notification/service.py`
- Modify: `apps/server/app/core/config.py`
- Modify: `apps/server/.env.example`
- Test: `apps/server/tests/` new provider-agnostic SMS tests
- Doc: provider setup notes under `docs/server/`

### Task 3.1: Decide SMS strategy

**Decision gate:**
- Pick one provider first: Aliyun or Tencent.
- Define whether local/dev keeps console output while staging/prod uses provider SDK.

### Task 3.2: Implement provider adapter

**Steps:**
1. Introduce a provider interface instead of hard-coding SDK branches into service methods.
2. Add config flags and environment variables for credentials and template IDs.
3. Replace console-only sending in verification and notification flows with adapter calls.
4. Add tests that mock the provider adapter instead of calling real vendor APIs.

**Verification:**
- Verification codes and suspension notices use a real adapter path in non-dev environments.
- Local development still works without external credentials.

## Phase 4: Admin menu information architecture refactor (5-8 days, blocked by approval)

**Outcome:** Restructure admin navigation only after the naming, permission, and compatibility decisions are approved.

**Files:**
- Modify: `apps/admin/config/routes.ts`
- Modify: `apps/admin/src/access.ts`
- Modify: `apps/admin/src/pages/system/settings.tsx`
- Create: `apps/admin/src/pages/tenant/usage.tsx`
- Create: `apps/admin/src/pages/medical-record/detail.tsx`
- Create: `apps/admin/src/pages/medical-record/form.tsx`
- Create: `apps/admin/src/pages/configuration/booking-rules.tsx`
- Create: `apps/admin/src/pages/configuration/blacklist.tsx`
- Create: `apps/admin/src/pages/configuration/wechat-config.tsx`
- Create: `apps/admin/src/pages/configuration/booking-fields.tsx`
- Create: `apps/admin/src/pages/configuration/patient-card-config.tsx`
- Create: `apps/admin/src/pages/configuration/hospital-info.tsx`
- Create: `apps/admin/src/pages/configuration/email-config.tsx`
- Create: `apps/admin/src/pages/configuration/image-config.tsx`
- Optional Create: `apps/admin/src/pages/system/monitoring/index.tsx`
- Optional Create: `apps/admin/src/pages/system/analytics.tsx`

### Task 4.1: Approval and scope freeze

**Steps:**
1. Confirm the final一级菜单命名.
2. Confirm whether `system/settings` remains as a compatibility entry during rollout.
3. Confirm whether tenant usage and monitoring pages are required in v1 or postponed.
4. Update the OpenSpec task checklist with the agreed scope split before coding.

### Task 4.2: Route and permission skeleton

**Steps:**
1. Move only routing and access control first.
2. Keep existing pages alive behind new paths before any content extraction.
3. Add redirect and compatibility coverage for old settings routes.

**Verification:**
- Navigation changes can ship independently from page decomposition.

### Task 4.3: Extract settings tabs into independent pages

**Steps:**
1. Split the largest tabs out of `system/settings.tsx` first.
2. Keep shared form sections in reusable components instead of duplicating tab content.
3. Add smoke verification for role-based menu visibility and route guards.

**Verification:**
- `system/settings.tsx` stops being the only source of truth for multiple unrelated domains.
- Old deep links still resolve during the transition period.

## Phase 5: Deprecated schedule cleanup (1-2 days)

**Outcome:** Remove the stale `custom_schedule` compatibility layer only after schedule module work is otherwise stable.

**Files:**
- Modify/Delete: `apps/server/app/models/custom_schedule.py`
- Modify/Delete: `apps/server/app/modules/custom_schedules/router.py`
- Modify/Delete: `apps/server/app/modules/custom_schedules/service.py`
- Modify: `apps/server/app/schemas/custom_schedule.py`
- Review: any references in `packages/api/` and admin pages
- Test: schedule endpoint integration tests

**Steps:**
1. Identify whether any live endpoint or frontend page still depends on `custom_schedules`.
2. Add regression tests around the surviving `schedules` behavior.
3. Remove dead code only after replacement routes and types are confirmed.

**Verification:**
- No code path depends on the deprecated table model.
- Schedule APIs use a single consistent data model.

## Phase 6: Template-driven miniapp platform (3-5 weeks, separate project track)

**Outcome:** Run the miniapp platform as a dedicated project, not as overflow work mixed into backlog cleanup.

**Files:**
- Primary planning source: `openspec/changes/add-template-driven-miniapp-platform/`
- Likely backend: `apps/server/app/modules/*`, new models, migrations, build/release jobs
- Likely admin: `apps/admin/src/pages/` new platform pages
- Likely scripts/config: miniapp build and release tooling

### Track A: Discovery and ownership (2-3 days)

**Steps:**
1. Confirm product owner, release owner, and operations owner.
2. Freeze MVP scope:
   - template management
   - instance management
   - payment profile routing
   - build/release task visibility
3. Confirm secret management rule before any schema work.

### Track B: Backend foundation (1-1.5 weeks)

**Steps:**
1. Build schema, migrations, and compatibility reads from legacy store fields.
2. Add management APIs for templates, instances, and payment routing.
3. Add build/release job records with auditable status transitions.

### Track C: Admin console (1 week)

**Steps:**
1. Ship template, instance, payment, and release-task pages.
2. Keep the UI read-heavy first; do not combine CRUD complexity with release automation on day one.

### Track D: Build/release automation and migration (1-2 weeks)

**Steps:**
1. Templatize `project.config.json`.
2. Generate build parameters from template + instance.
3. Implement upload/review/release/rollback tasks.
4. Add migration bootstrap and end-to-end verification.

**Verification:**
- The new platform can manage at least one live miniapp instance end to end without reading legacy `stores.wechat_*` fields directly.

## Suggested Milestone Plan

### Milestone M1: backlog cleanup and safety (this week)
- Phase 0
- Phase 1
- Task 2.1

### Milestone M2: small product wins (next week)
- Task 2.2
- Phase 3 decision and implementation if provider is ready
- Phase 5 discovery

### Milestone M3: approved admin restructure (after team alignment)
- Phase 4

### Milestone M4: dedicated platform buildout
- Phase 6

## Risks and Mitigations

- Risk: The team starts menu refactor before approval.
  - Mitigation: Treat Phase 4 as blocked until naming and compatibility decisions are written down.
- Risk: SMS integration stalls because secrets and templates are not ready.
  - Mitigation: Split provider decision from adapter implementation and keep a mock adapter for development.
- Risk: Miniapp platform consumes the whole roadmap.
  - Mitigation: Run it as a separate project track with explicit ownership and milestone gates.
- Risk: Tenant safety gaps remain while new features ship.
  - Mitigation: Finish Phase 1 before any large frontend or platform expansion work.

## Definition of Done for the Roadmap

- `openspec/STATUS.md` matches real project execution order.
- Remaining multi-tenant items in `openspec/STATUS.md` are either completed or re-estimated with owners.
- `update-appointment-list-page-size` can be archived after implementation and verification.
- SMS-related TODOs are either implemented or reclassified as intentionally mocked with documentation.
- Admin menu IA work starts only with approved scope.
- Miniapp platform has its own delivery track, not an undefined backlog blob.
