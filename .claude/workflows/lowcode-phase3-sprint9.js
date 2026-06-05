export const meta = {
  name: 'lowcode-phase3-sprint9',
  description: 'Sprint 9: Template marketplace backend',
  phases: [
    { title: 'Template Models', detail: 'Create template, version, fork models' },
    { title: 'Template Service', detail: 'Create template CRUD + search + fork service' },
    { title: 'Template Router', detail: 'Create template marketplace API endpoints' },
    { title: 'Tests', detail: 'Write template service unit tests' },
    { title: 'Verify', detail: 'Verify all deliverables' },
  ],
};

phase('Template Models');

await parallel([
  () => agent(
    "Create the marketplace template model. Create file: apps/server/app/models/lowcode_template.py. Model LowCodeTemplate (Base + AuditMixin). Fields: id (String(36) PK), source_page_id (FK lowcode_pages nullable), source_tenant_id (FK tenants), name (String(200)), description (Text), thumbnail_url (String(500)), category (String(50) not null), tags (JSONB default list), schema_data (JSONB not null), data_sources (JSONB default list), version (String(20) default '1.0.0'), is_public (Boolean default False), is_official (Boolean default False), download_count (Integer default 0), fork_count (Integer default 0), like_count (Integer default 0), status (Integer default 1), created_by (FK accounts). Indexes on category, status+is_public, source_tenant_id. UniqueConstraint on source_page_id if not null. Follow patterns in lowcode_page.py.",
    { label: 'create:template-model', phase: 'Template Models' }
  ),
  () => agent(
    "Create the template version and fork models. Create file: apps/server/app/models/lowcode_template_version.py. Two models: 1) LowCodeTemplateVersion (Base + AuditMixin): id, template_id (FK lowcode_templates, cascade delete), version (String(20)), schema_data (JSONB), data_sources (JSONB), changelog (Text), status (Integer), created_by. UniqueConstraint(template_id, version). 2) LowCodeTemplateFork (Base): id, original_template_id (FK), forked_page_id (FK lowcode_pages nullable), forked_by_tenant_id (FK tenants), forked_by_account_id (FK accounts), created_at. Follow patterns in lowcode_page_version.py.",
    { label: 'create:version-fork-models', phase: 'Template Models' }
  ),
]);

phase('Template Service');

await agent(
  "Create the template marketplace service. Create file: apps/server/app/modules/lowcode/template_service.py. LowCodeTemplateService class with __init__(self, db: AsyncSession). Methods: 1) list_templates(category, keyword, sort_by, page, page_size) - paginated list of public templates, support full-text search on name+description, sort by popular/newest/forks. 2) get_template(template_id) - get template with author info. 3) create_template(data) - create from page (copy schema_data). 4) update_template(template_id, data) - update metadata. 5) delete_template(template_id) - soft delete (status=0). 6) fork_template(template_id, tenant_id, account_id) - create LowCodePage from template schema, record fork, increment fork_count. 7) get_my_templates(tenant_id) - list templates published by this tenant. 8) get_template_versions(template_id) - list versions. 9) create_version(template_id, version, schema_data, changelog) - create new version. Read lowcode_page.py service for patterns.",
  { label: 'create:template-service', phase: 'Template Service' }
);

phase('Template Router');

await agent(
  "Create the template marketplace API router. Create file: apps/server/app/modules/lowcode/router_template.py. Endpoints: 1) GET /templates - marketplace list (public, paginated, filterable). 2) GET /templates/{id} - template detail. 3) POST /templates - create/publish template. 4) PUT /templates/{id} - update metadata. 5) DELETE /templates/{id} - soft delete. 6) POST /templates/{id}/fork - fork to current tenant. 7) GET /templates/{id}/versions - version history. 8) POST /templates/{id}/versions - create new version. 9) GET /templates/my - my published templates. 10) GET /templates/categories - list categories. All endpoints use get_current_admin for auth, require_permission for access control. Use PageResponse for list endpoints. Read router.py for patterns.",
  { label: 'create:template-router', phase: 'Template Router' }
);

phase('Tests');

await agent(
  "Write unit tests for the template service. Create file: apps/server/tests/unit/test_lowcode_template.py. Test cases: 1) create_template copies schema_data correctly. 2) list_templates returns paginated results. 3) list_templates filters by category. 4) list_templates searches by keyword. 5) fork_template creates new page with template schema. 6) fork_template increments fork_count. 7) create_version creates version record. 8) get_versions returns versions in order. 9) delete_template sets status=0. Use AsyncMock for db. Read template_service.py first.",
  { label: 'tests:template', phase: 'Tests' }
);

phase('Verify');

await agent(
  "Verify Sprint 9: 1) Check template model: ls apps/server/app/models/lowcode_template.py, 2) Check version/fork models: ls apps/server/app/models/lowcode_template_version.py, 3) Check template service: ls apps/server/app/modules/lowcode/template_service.py, 4) Check template router: ls apps/server/app/modules/lowcode/router_template.py, 5) Check tests: ls apps/server/tests/unit/test_lowcode_template.py, 6) Check router registered: grep 'router_template' apps/server/app/api/v1/__init__.py | head -3. Report each as PASS or FAIL.",
  { label: 'verify:sprint9', phase: 'Verify' }
);

log('Sprint 9 completed');
return { status: 'completed', sprint: 9 };
