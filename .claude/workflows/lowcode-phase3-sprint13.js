export const meta = {
  name: 'lowcode-phase3-sprint13',
  description: 'Sprint 13: Integration testing and polish',
  phases: [
    { title: 'Run Tests', detail: 'Run all lowcode unit tests' },
    { title: 'Documentation', detail: 'Update README and API docs' },
    { title: 'Final Verify', detail: 'Final verification of all deliverables' },
  ],
};

phase('Run Tests');

await agent(
  "Run all lowcode-related unit tests and report results. Execute: cd apps/server && python -m pytest tests/unit/test_lowcode_page.py tests/unit/test_lowcode_feature_gate.py tests/unit/test_lowcode_version.py tests/unit/test_lowcode_template.py tests/unit/test_lowcode_deploy.py -v 2>&1 | tail -40. Report pass/fail count and any failures.",
  { label: 'run:tests', phase: 'Run Tests' }
);

phase('Documentation');

await agent(
  "Update the lowcode module documentation. Modify file: apps/server/app/modules/lowcode/README.md. Add sections for: 1) Phase 2 features (data binding, expression engine, code generation). 2) Phase 3 features (feature gating, versioning, template marketplace, deployment pipeline). 3) API endpoint reference for all new endpoints. 4) Template marketplace workflow. 5) Deployment pipeline workflow. Read the existing README first, then update.",
  { label: 'update:docs', phase: 'Documentation' }
);

phase('Final Verify');

await agent(
  "Final Phase 3 verification - comprehensive check of all deliverables. Check: 1) Backend models: ls apps/server/app/models/lowcode*.py, 2) Backend services: ls apps/server/app/modules/lowcode/*.py, 3) Backend tests: ls apps/server/tests/unit/test_lowcode*.py, 4) Frontend editor components: find apps/admin/src/pages/lowcode/editor/components -name '*.tsx' | wc -l, 5) Frontend marketplace: find apps/admin/src/pages/lowcode/marketplace -name '*.tsx' | wc -l, 6) Frontend API modules: ls packages/api/src/modules/lowcode*.ts, 7) Shared types: grep 'ApiDataSource\|LoopConfig\|EventHandler\|DataSource\|LowCodeTemplate' packages/shared/src/types/lowcode.ts | wc -l, 8) Total lowcode files: find . -path '*/lowcode*' -type f -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/__pycache__/*' 2>/dev/null | wc -l. Report comprehensive summary.",
  { label: 'verify:final', phase: 'Final Verify' }
);

log('Phase 3 completed');
return { status: 'completed', sprint: 13, phase3Complete: true };
