export const meta = {
  name: 'lowcode-phase3-sprint12',
  description: 'Sprint 12: Deployment pipeline frontend',
  phases: [
    { title: 'DeployPanel', detail: 'Create deployment panel component' },
    { title: 'DeployStatus', detail: 'Create deploy status and log viewer' },
    { title: 'PreviewQR', detail: 'Create WeChat preview QR code display' },
    { title: 'Verify', detail: 'Verify all deliverables' },
  ],
};

phase('DeployPanel');

await agent(
  "Create the deployment panel component for the low-code editor. Create file: apps/admin/src/pages/lowcode/editor/components/DeployPanel.tsx. This is a sidebar panel or modal that manages deployment of the current page. Features: 1) Current deploy status display (idle/building/built/uploading/auditing/published/failed) with status tags. 2) Deploy button that triggers full pipeline (POST /pages/{id}/deploy). 3) Preview button for preview QR code. 4) Rollback button with version selector. 5) Deploy history list showing recent deployments with timestamps and status. 6) Real-time status updates (polling every 5s when building). Use Ant Design Card, Button, Tag, Timeline, Select, message, Spin. Read the existing editor/index.tsx to understand how to integrate.",
  { label: 'create:deploy-panel', phase: 'DeployPanel' }
);

phase('DeployStatus');

await parallel([
  () => agent(
    "Create the deploy status indicator component. Create file: apps/admin/src/pages/lowcode/editor/components/DeployStatus.tsx. A compact status display that shows the current deployment state. Features: 1) Status badge with color coding (green=published, blue=building, orange=auditing, red=failed, gray=idle). 2) Last deploy time. 3) Click to expand showing detailed status. 4) Auto-refresh when status is transitional. Use Ant Design Badge, Tooltip, Typography.",
    { label: 'create:deploy-status', phase: 'DeployStatus' }
  ),
  () => agent(
    "Create the build log viewer component. Create file: apps/admin/src/pages/lowcode/editor/components/BuildLogViewer.tsx. A modal that shows build logs. Features: 1) Monospace text display of build log. 2) Auto-scroll to bottom. 3) Copy log button. 4) Error highlighting. 5) Refresh button. Use Ant Design Modal, Button, Typography, message.",
    { label: 'create:build-log', phase: 'DeployStatus' }
  ),
]);

phase('PreviewQR');

await agent(
  "Create the WeChat preview QR code display component. Create file: apps/admin/src/pages/lowcode/editor/components/PreviewQRCode.tsx. Modal that shows the preview QR code. Features: 1) QR code image display. 2) Expiration timer. 3) Instructions text. 4) Refresh button. 5) Loading and error states. Use Ant Design Modal, Button, Image, Spin, Typography.",
  { label: 'create:preview-qr', phase: 'PreviewQR' }
);

phase('Verify');

await agent(
  "Verify Sprint 12: 1) Check DeployPanel: ls apps/admin/src/pages/lowcode/editor/components/DeployPanel.tsx, 2) Check DeployStatus: ls apps/admin/src/pages/lowcode/editor/components/DeployStatus.tsx, 3) Check BuildLogViewer: ls apps/admin/src/pages/lowcode/editor/components/BuildLogViewer.tsx, 4) Check PreviewQRCode: ls apps/admin/src/pages/lowcode/editor/components/PreviewQRCode.tsx, 5) Count total editor components: find apps/admin/src/pages/lowcode/editor/components -type f -name '*.tsx' | wc -l. Report each as PASS or FAIL.",
  { label: 'verify:sprint12', phase: 'Verify' }
);

log('Sprint 12 completed');
return { status: 'completed', sprint: 12 };
