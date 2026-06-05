export const meta = {
  name: 'lowcode-phase3-sprint11',
  description: 'Sprint 11: Deployment pipeline backend',
  phases: [
    { title: 'Model Extensions', detail: 'Extend LowCodePage and BuildJob models' },
    { title: 'WeChat Publisher', detail: 'Create WeChat API client for upload/audit/publish' },
    { title: 'Celery Tasks', detail: 'Create build, upload, audit, publish tasks' },
    { title: 'Deploy Endpoints', detail: 'Add deploy trigger, status, rollback endpoints' },
    { title: 'Tests', detail: 'Write deploy service unit tests' },
    { title: 'Verify', detail: 'Verify all deliverables' },
  ],
};

phase('Model Extensions');

await parallel([
  () => agent(
    "Extend LowCodePage model with deployment fields. Modify file: apps/server/app/models/lowcode_page.py. Add columns: deploy_status (String(30) default='idle', comment='idle|building|built|uploading|uploaded|auditing|published|failed'), last_deploy_at (DateTime nullable), last_build_job_id (FK build_jobs nullable). Read the file first, then add the columns.",
    { label: 'extend:page-deploy', phase: 'Model Extensions' }
  ),
  () => agent(
    "Extend BuildJob model with lowcode fields. Modify file: apps/server/app/models/miniapp_platform.py. Add column to BuildJob: lowcode_page_id (FK lowcode_pages nullable, comment='关联低代码页面ID'). Also add build_log (Text nullable) and artifact_url (String(500) nullable). Read the file first to find the BuildJob class.",
    { label: 'extend:buildjob', phase: 'Model Extensions' }
  ),
]);

phase('WeChat Publisher');

await agent(
  "Create the WeChat mini-program publisher client. Create file: apps/server/app/infrastructure/wechat/miniapp_publisher.py. MiniappPublisher class with methods: 1) __init__(self, app_id, app_secret) - initializes WechatTokenManager. 2) async upload_code(appid, project_path, version, desc) - uses miniprogram-ci via subprocess to upload code. 3) async submit_audit(access_token) - POST /wxa/submit_audit. 4) async get_audit_status(access_token, auditid) - POST /wxa/get_auditstatus. 5) async release(access_token) - GET /wxa/release. 6) async rollback(access_token) - POST /wxa/revertcoderelease. 7) async get_preview_qrcode(access_token, page_path) - GET /wxa/get_qrcode for preview. Use httpx for HTTP requests. Read apps/server/app/infrastructure/wechat/token_manager.py for token management pattern.",
  { label: 'create:wechat-publisher', phase: 'WeChat Publisher' }
);

phase('Celery Tasks');

await agent(
  "Create Celery tasks for the deployment pipeline. Create file: apps/server/app/tasks/lowcode_deploy_task.py. Tasks: 1) build_lowcode_page_task(page_id, tenant_id) - load page, call codegen service, create BuildJob, execute Taro build via subprocess, store artifact, update BuildJob status. 2) upload_to_wechat_task(build_job_id, instance_id) - load build artifact, call MiniappPublisher.upload_code, create ReleaseJob. 3) submit_audit_task(release_job_id) - call MiniappPublisher.submit_audit, update status. 4) publish_release_task(release_job_id) - call MiniappPublisher.release, update status, create version snapshot. 5) rollback_task(release_job_id, target_version) - rollback to previous version. All tasks use @celery_app.task decorator, handle errors with try/except, update job status on failure. Read apps/server/app/tasks/ for existing task patterns.",
  { label: 'create:celery-tasks', phase: 'Celery Tasks' }
);

phase('Deploy Endpoints');

await agent(
  "Add deployment API endpoints to the lowcode router. Modify file: apps/server/app/modules/lowcode/router.py. Add endpoints: 1) POST /pages/{id}/deploy - trigger full deploy pipeline (codegen -> build -> upload -> audit). 2) GET /pages/{id}/deploy-status - get current deployment status. 3) POST /pages/{id}/deploy-rollback - rollback to previous version. 4) POST /pages/{id}/preview-deploy - generate preview QR code. 5) POST /deploy/wechat-audit-callback - webhook for WeChat audit status updates. All endpoints require lowcode_publish_miniapp feature flag. Use LowCodeFeatureGate for checks. Read the existing router.py first.",
  { label: 'add:deploy-endpoints', phase: 'Deploy Endpoints' }
);

phase('Tests');

await agent(
  "Write unit tests for the deployment pipeline. Create file: apps/server/tests/unit/test_lowcode_deploy.py. Test cases: 1) build task creates BuildJob record. 2) build task updates page deploy_status to 'building'. 3) upload task creates ReleaseJob record. 4) submit_audit task calls WeChat API. 5) publish task updates deploy_status to 'published'. 6) rollback task restores previous version. 7) deploy-status endpoint returns correct status. 8) deploy endpoint enforces feature flag. Use AsyncMock for db and mock WeChat API calls. Read the celery tasks file first.",
  { label: 'tests:deploy', phase: 'Tests' }
);

phase('Verify');

await agent(
  "Verify Sprint 11: 1) Check page model extended: grep 'deploy_status\|last_deploy_at' apps/server/app/models/lowcode_page.py | head -3, 2) Check BuildJob extended: grep 'lowcode_page_id\|build_log' apps/server/app/models/miniapp_platform.py | head -3, 3) Check WeChat publisher: ls apps/server/app/infrastructure/wechat/miniapp_publisher.py, 4) Check Celery tasks: ls apps/server/app/tasks/lowcode_deploy_task.py, 5) Check deploy endpoints: grep 'deploy-status\|deploy-rollback\|preview-deploy' apps/server/app/modules/lowcode/router.py | head -5, 6) Check tests: ls apps/server/tests/unit/test_lowcode_deploy.py. Report each as PASS or FAIL.",
  { label: 'verify:sprint11', phase: 'Verify' }
);

log('Sprint 11 completed');
return { status: 'completed', sprint: 11 };
