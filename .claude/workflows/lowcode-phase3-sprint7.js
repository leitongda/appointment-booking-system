export const meta = {
  name: 'lowcode-phase3-sprint7',
  description: 'Sprint 7: Low-code feature gating + subscription plan integration',
  phases: [
    { title: 'Feature Flags', detail: 'Add lowcode feature flags to TenantFeatures' },
    { title: 'Feature Gate Service', detail: 'Create LowCodeFeatureGate service' },
    { title: 'Router Integration', detail: 'Integrate gating into router endpoints' },
    { title: 'Tests', detail: 'Write feature gate unit tests' },
    { title: 'Verify', detail: 'Verify all deliverables' },
  ],
};

phase('Feature Flags');

await parallel([
  () => agent(
    "Add lowcode-specific feature flags to the TenantFeatures model. Modify file: apps/server/app/schemas/tenants.py (or wherever TenantFeatures is defined). Add these optional boolean fields with defaults: lowcode_basic (default=True for backward compat), lowcode_advanced_components (default=False), lowcode_custom_components (default=False), lowcode_data_binding (default=False), lowcode_codegen (default=False), lowcode_marketplace (default=False), lowcode_publish_miniapp (default=False), lowcode_export_code (default=False). Also add quota fields: lowcode_max_pages (int, default=5). All fields must be Optional with defaults for backward compatibility. Read the file first to find the TenantFeatures class.",
    { label: 'add:feature-flags', phase: 'Feature Flags' }
  ),
  () => agent(
    "Add max_lowcode_pages quota field to the SubscriptionPlan model. Modify file: apps/server/app/models/tenant.py. Add a new column: max_lowcode_pages = Column(Integer, default=5, comment='最大低代码页面数'). Also check if there are other lowcode-related quota fields that should be added (max_lowcode_materials, max_miniapp_instances). Read the file first to understand the existing pattern.",
    { label: 'add:quota-fields', phase: 'Feature Flags' }
  ),
]);

phase('Feature Gate Service');

await agent(
  "Create the LowCodeFeatureGate service. Create file: apps/server/app/modules/lowcode/feature_gate.py. This service checks subscription-gated features for the low-code platform. Requirements: 1) LowCodeFeatureGate class with __init__(self, db: AsyncSession). 2) async check_feature(tenant_id, feature_name) -> bool - loads tenant features, checks if lowcode_* flag is enabled. 3) async check_page_limit(tenant_id) -> tuple[bool, int, int] - returns (allowed, current_count, max_limit). 4) async enforce_feature(tenant_id, feature_name) - raises HTTPException(403) if not allowed. 5) async enforce_page_limit(tenant_id) - raises HTTPException(403) if at limit. 6) Integration with existing FeatureFlagService if available. Read apps/server/app/modules/lowcode/service.py and apps/server/app/modules/tenants/schemas.py to understand existing patterns.",
  { label: 'create:feature-gate', phase: 'Feature Gate Service' }
);

phase('Router Integration');

await agent(
  "Integrate feature gating into the lowcode router. Modify file: apps/server/app/modules/lowcode/router.py. Add feature gate checks to: 1) POST /pages - check lowcode_basic feature and page limit before create. 2) POST /pages/{id}/publish - check lowcode_advanced if schema has dataBindings. 3) POST /pages/{id}/codegen/* - check lowcode_codegen feature. 4) POST /pages/{id}/publish-to-marketplace - check lowcode_marketplace feature. 5) POST /pages/{id}/deploy - check lowcode_publish_miniapp feature. Import and use LowCodeFeatureGate. Read the file first, then add the checks.",
  { label: 'integrate:gating', phase: 'Router Integration' }
);

phase('Tests');

await agent(
  "Write unit tests for the feature gate service. Create file: apps/server/tests/unit/test_lowcode_feature_gate.py. Test cases: 1) check_feature returns True when flag is enabled. 2) check_feature returns False when flag is disabled. 3) check_feature returns True for lowcode_basic (default True). 4) check_page_limit returns (True, 3, 5) when under limit. 5) check_page_limit returns (False, 5, 5) when at limit. 6) enforce_feature raises 403 when disabled. 7) enforce_page_limit raises 403 when at limit. Use AsyncMock for db session. Read the feature_gate.py file first to understand the API.",
  { label: 'tests:feature-gate', phase: 'Tests' }
);

phase('Verify');

await agent(
  "Verify Sprint 7 deliverables: 1) Check feature flags: grep 'lowcode_basic\|lowcode_codegen\|lowcode_marketplace' apps/server/app/schemas/tenants.py | head -5, 2) Check quota field: grep 'max_lowcode_pages' apps/server/app/models/tenant.py, 3) Check feature gate service: ls apps/server/app/modules/lowcode/feature_gate.py, 4) Check router integration: grep 'feature_gate\|enforce_feature\|enforce_page_limit' apps/server/app/modules/lowcode/router.py | head -5, 5) Check tests: ls apps/server/tests/unit/test_lowcode_feature_gate.py. Report each as PASS or FAIL.",
  { label: 'verify:sprint7', phase: 'Verify' }
);

log('Sprint 7 completed');
return { status: 'completed', sprint: 7 };
