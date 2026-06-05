export const meta = {
  name: 'lowcode-phase3-sprint8',
  description: 'Sprint 8: Page versioning and rollback',
  phases: [
    { title: 'Version Model', detail: 'Create lowcode_page_versions model and migration' },
    { title: 'Version Service', detail: 'Create version snapshot and rollback service' },
    { title: 'Frontend', detail: 'Create version history panel in editor' },
    { title: 'Tests', detail: 'Write version service unit tests' },
    { title: 'Verify', detail: 'Verify all deliverables' },
  ],
};

phase('Version Model');

await parallel([
  () => agent(
    "Create the lowcode_page_versions model for page version history. Create file: apps/server/app/models/lowcode_page_version.py. Model LowCodePageVersion inheriting from Base + AuditMixin. Fields: id (String(36) PK), page_id (FK to lowcode_pages, nullable=False, index), tenant_id (FK to tenants, nullable=False, index), version (Integer, nullable=False), schema_data (JSONB, nullable=False), data_sources (JSONB, default=list), snapshot_label (String(200), nullable=True, e.g. '发布 v1.2'), created_by (FK to accounts). Table args: UniqueConstraint(page_id, version), Index on page_id, Index on tenant_id. Follow existing model patterns in apps/server/app/models/lowcode_page.py. Read that file first.",
    { label: 'create:version-model', phase: 'Version Model' }
  ),
  () => agent(
    "Extend the lowcode_pages model with version tracking fields. Modify file: apps/server/app/models/lowcode_page.py. Add columns: current_version (Integer, default=0, comment='当前版本号'), publish_count (Integer, default=0, comment='发布次数'). These fields track the latest version number and total publish count for each page. Read the file first, then add the columns.",
    { label: 'extend:page-model', phase: 'Version Model' }
  ),
]);

phase('Version Service');

await agent(
  "Create the version snapshot and rollback service. Create file: apps/server/app/modules/lowcode/version_service.py. LowCodePageVersionService class with __init__(self, db: AsyncSession). Methods: 1) create_snapshot(page_id, tenant_id, label, created_by) - loads LowCodePage, increments version, creates LowCodePageVersion record with schema_data snapshot, updates page current_version and publish_count. 2) get_versions(page_id, tenant_id) - list all versions ordered by version desc. 3) get_version(version_id) - get single version. 4) rollback_to_version(page_id, version_id, tenant_id) - load version's schema_data, update LowCodePage.schema_data, create new version record (increment), return updated page. 5) get_latest_version(page_id) - get the latest version record. Read apps/server/app/modules/lowcode/service.py first for patterns.",
  { label: 'create:version-service', phase: 'Version Service' }
);

phase('Frontend');

await agent(
  "Create the version history panel for the low-code editor. Create file: apps/admin/src/pages/lowcode/editor/components/VersionHistory.tsx. This component shows version history in a sidebar panel or modal. Features: 1) List of versions with version number, label, timestamp, author. 2) Current version highlighted. 3) 'Restore' button per version that calls rollback API and reloads the schema. 4) 'View' button to show schema diff (optional, can be simple). 5) Auto-refresh after rollback. Use Ant Design List, Tag, Button, Popconfirm, message. Read apps/admin/src/pages/lowcode/editor/index.tsx to understand how to integrate.",
  { label: 'create:version-history', phase: 'Frontend' }
);

phase('Tests');

await agent(
  "Write unit tests for the version service. Create file: apps/server/tests/unit/test_lowcode_version.py. Test cases: 1) create_snapshot creates version record with correct version number. 2) create_snapshot increments page current_version. 3) create_snapshot increments page publish_count. 4) get_versions returns versions in descending order. 5) rollback_to_version restores schema_data from target version. 6) rollback_to_version creates a new version record (rollback itself is versioned). 7) get_latest_version returns the most recent version. Use AsyncMock for db. Read the version_service.py file first.",
  { label: 'tests:version', phase: 'Tests' }
);

phase('Verify');

await agent(
  "Verify Sprint 8: 1) Check version model: ls apps/server/app/models/lowcode_page_version.py, 2) Check page model extended: grep 'current_version\|publish_count' apps/server/app/models/lowcode_page.py, 3) Check version service: ls apps/server/app/modules/lowcode/version_service.py, 4) Check version history component: ls apps/admin/src/pages/lowcode/editor/components/VersionHistory.tsx, 5) Check tests: ls apps/server/tests/unit/test_lowcode_version.py. Report each as PASS or FAIL.",
  { label: 'verify:sprint8', phase: 'Verify' }
);

log('Sprint 8 completed');
return { status: 'completed', sprint: 8 };
