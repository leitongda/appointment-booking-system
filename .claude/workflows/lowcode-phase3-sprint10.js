export const meta = {
  name: 'lowcode-phase3-sprint10',
  description: 'Sprint 10: Template marketplace frontend',
  phases: [
    { title: 'Marketplace Pages', detail: 'Create marketplace list and detail pages' },
    { title: 'Fork Dialog', detail: 'Create fork and share dialogs' },
    { title: 'API & Routes', detail: 'Add frontend API module and routes' },
    { title: 'Verify', detail: 'Verify all deliverables' },
  ],
};

phase('Marketplace Pages');

await parallel([
  () => agent(
    "Create the template marketplace list page. Create file: apps/admin/src/pages/lowcode/marketplace/index.tsx. Features: 1) PageContainer with header '模板市场'. 2) Category sidebar (left) with filter options. 3) Search bar with keyword input. 4) Template card grid showing: thumbnail, name, description, category tag, fork count, rating. 5) Sort dropdown (popular/newest/forks). 6) Pagination. 7) Click card to navigate to detail page. Use Ant Design Card, Row, Col, Input, Select, Pagination, Tag, Space, Rate. Follow patterns from apps/admin/src/pages/lowcode/list.tsx.",
    { label: 'create:marketplace-list', phase: 'Marketplace Pages' }
  ),
  () => agent(
    "Create the template detail page. Create file: apps/admin/src/pages/lowcode/marketplace/TemplateDetail.tsx. Features: 1) PageContainer with template name as title. 2) Preview images carousel (or placeholder). 3) Template info: name, description, author, category, tags, version. 4) Statistics: fork count, like count. 5) 'Use This Template' button that triggers fork. 6) Version history list. 7) Related templates section. Use Ant Design Descriptions, Carousel, Button, Tag, List, message. Read the template model to understand available fields.",
    { label: 'create:marketplace-detail', phase: 'Marketplace Pages' }
  ),
]);

phase('Fork Dialog');

await parallel([
  () => agent(
    "Create the fork dialog component. Create file: apps/admin/src/pages/lowcode/marketplace/ForkDialog.tsx. Modal that appears when user clicks 'Use This Template'. Features: 1) Shows template preview. 2) Input for new page name (default: template name + ' - 我的副本'). 3) Input for page slug (auto-generated from name). 4) Confirm button that calls POST /lowcode/templates/{id}/fork API. 5) Loading state during fork. 6) Success message and redirect to editor. Use Ant Design Modal, Form, Input, Button, message, Spin.",
    { label: 'create:fork-dialog', phase: 'Fork Dialog' }
  ),
  () => agent(
    "Create the share-to-marketplace dialog. Create file: apps/admin/src/pages/lowcode/editor/components/ShareDialog.tsx. Modal accessible from editor toolbar that publishes current page to marketplace. Features: 1) Form fields: name (default from page name), short description, detailed description (textarea), category (select), tags (select multiple). 2) Preview thumbnail upload. 3) Confirm button that calls POST /lowcode/pages/{id}/share-to-marketplace. 4) Loading and success states. Use Ant Design Modal, Form, Input, Select, Upload, Button, message.",
    { label: 'create:share-dialog', phase: 'Fork Dialog' }
  ),
]);

phase('API & Routes');

await parallel([
  () => agent(
    "Create the frontend API module for template marketplace. Create file: packages/api/src/modules/lowcode-template.ts. API methods: 1) getTemplates(params) - GET /lowcode/templates. 2) getTemplate(id) - GET /lowcode/templates/{id}. 3) createTemplate(data) - POST /lowcode/templates. 4) updateTemplate(id, data) - PUT /lowcode/templates/{id}. 5) deleteTemplate(id) - DELETE /lowcode/templates/{id}. 6) forkTemplate(id) - POST /lowcode/templates/{id}/fork. 7) getTemplateVersions(id) - GET /lowcode/templates/{id}/versions. 8) createVersion(id, data) - POST /lowcode/templates/{id}/versions. 9) getMyTemplates() - GET /lowcode/templates/my. 10) getCategories() - GET /lowcode/templates/categories. Follow pattern from packages/api/src/modules/lowcode.ts.",
    { label: 'create:template-api', phase: 'API & Routes' }
  ),
  () => agent(
    "Update the lowcode routes to include marketplace pages. Modify file: apps/admin/config/routes/lowcode.ts. Add routes: 1) /platform/lowcode/marketplace - template marketplace list page. 2) /platform/lowcode/marketplace/:id - template detail page. Also update access.ts to add canLowcodeMarketplace permission. Read the existing lowcode.ts routes file first.",
    { label: 'update:routes', phase: 'API & Routes' }
  ),
]);

phase('Verify');

await agent(
  "Verify Sprint 10: 1) Check marketplace list: ls apps/admin/src/pages/lowcode/marketplace/index.tsx, 2) Check detail page: ls apps/admin/src/pages/lowcode/marketplace/TemplateDetail.tsx, 3) Check fork dialog: ls apps/admin/src/pages/lowcode/marketplace/ForkDialog.tsx, 4) Check share dialog: ls apps/admin/src/pages/lowcode/editor/components/ShareDialog.tsx, 5) Check template API: ls packages/api/src/modules/lowcode-template.ts, 6) Check routes: grep 'marketplace' apps/admin/config/routes/lowcode.ts | head -3. Report each as PASS or FAIL.",
  { label: 'verify:sprint10', phase: 'Verify' }
);

log('Sprint 10 completed');
return { status: 'completed', sprint: 10 };
