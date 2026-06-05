export const meta = {
  name: 'lowcode-phase1-p1-fixes',
  description: 'Fix P1 issues: schema validation, tests, docs, form materials',
  phases: [
    { title: 'Schema Validation', detail: 'Add backend schema_data validation' },
    { title: 'Expand Tests', detail: 'Expand unit test coverage' },
    { title: 'Documentation', detail: 'Create README and Schema DSL docs' },
    { title: 'Form Materials', detail: 'Add form component materials' },
    { title: 'Verify', detail: 'Run tests and verify' },
  ],
};

// Phase 1: Schema Validation
phase('Schema Validation');

await agent(
  'Add schema_data structural validation to the low-code backend. File: apps/server/app/schemas/lowcode.py. Add a field_validator on schema_data that checks: 1) componentName must exist as string, 2) props must exist as dict, 3) children must be array if present, 4) max depth 10 levels. Read the file first, then add the validator.',
  { label: 'fix:schema-validation', phase: 'Schema Validation' }
);

// Phase 2: Expand Tests
phase('Expand Tests');

await parallel([
  () => agent(
    'Expand backend unit tests. File: apps/server/tests/unit/test_lowcode_page.py. Add tests for: get_list with pagination/status/keyword filters, update single field, delete nonexistent page, slug uniqueness with exclude_id. Read the file first.',
    { label: 'test:expand-backend', phase: 'Expand Tests', isolation: 'worktree' }
  ),
  () => agent(
    'Expand frontend store tests. File: apps/admin/src/pages/lowcode/editor/__tests__/store.test.ts. Add tests for: addNode to empty/existing children, addNode at index, moveNode between/within parents, updateNodeProps nested, removeNode nested clears selection, undo/redo cycle, history limit. Read the file first.',
    { label: 'test:expand-frontend', phase: 'Expand Tests', isolation: 'worktree' }
  ),
]);

// Phase 3: Documentation
phase('Documentation');

await agent(
  'Create documentation for the low-code module. Create: 1) apps/server/app/modules/lowcode/README.md with module overview, API endpoints, Schema DSL docs, data model, materials guide. 2) apps/admin/src/pages/lowcode/README.md with editor usage guide, adding materials, rendering pipeline. Read the code first to understand the structure.',
  { label: 'docs:readme', phase: 'Documentation' }
);

// Phase 4: Form Materials
phase('Form Materials');

await agent(
  'Add form component materials for the low-code editor. Create apps/admin/src/pages/lowcode/editor/materials/form.tsx with: NutInput (text input), NutTextarea (multi-line), NutSwitch (toggle), NutPicker (selection), NutForm (container). Follow the pattern in basic.tsx. Also update materials/index.ts to register them, SchemaRenderer.tsx to render them, and patient-miniapp LowCodeRenderer to render them with Taro components.',
  { label: 'materials:form', phase: 'Form Materials' }
);

// Phase 5: Verify
phase('Verify');

await agent(
  'Run verification: 1) cd apps/server && python -m pytest tests/unit/test_lowcode_page.py -v, 2) Check docs exist: ls apps/server/app/modules/lowcode/README.md and apps/admin/src/pages/lowcode/README.md, 3) Check form materials: ls apps/admin/src/pages/lowcode/editor/materials/form.tsx, 4) grep validate_schema_data in schemas/lowcode.py, 5) grep formMaterials in materials/index.ts, 6) grep NutInput in SchemaRenderer.tsx. Report each as PASS or FAIL.',
  { label: 'verify:p1', phase: 'Verify' }
);

log('All P1 fixes completed');
return { status: 'completed' };
