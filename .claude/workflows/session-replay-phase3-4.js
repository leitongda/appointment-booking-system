export const meta = {
  name: 'session-replay-phase3-4',
  description: 'Phase 3 热力图渲染页 + Phase 4 定期截图 + Phase 2 跟进修复（时区/cleanup 批量化/脱敏补覆盖）+ 终审',
  phases: [
    { title: 'P3热力图+P4截图', detail: '前端热力图渲染页 / 后端 playwright 截图任务（并行，文件不冲突）' },
    { title: 'P2跟进', detail: 'session_event_task 时区+批量化 / 脱敏补覆盖（并行，文件不冲突）' },
    { title: '终审', detail: '校验一致性 + 列手动跟进项' },
  ],
}

const RESULT = {
  type: 'object',
  properties: {
    filesWritten: { type: 'array', items: { type: 'string' } },
    filesEdited: { type: 'array', items: { type: 'string' } },
    decisions: { type: 'string', description: '关键设计决策（1-3 句）' },
    issues: { type: 'string', description: '遗留问题或需手动跟进项，无则填 none' },
  },
  required: ['filesWritten', 'filesEdited', 'decisions', 'issues'],
}

const ROOT = '/Users/leijiadashao/letond/appointment-booking-system'
const BACKEND_COMMON = `
项目根：${ROOT}。后端 apps/server (Python 3.12, FastAPI, SQLAlchemy 2 async, Celery)。回复中文，无 emoji。风格对齐现有代码。
重要参考：app/tasks/behavior_log_task.py（Celery 任务风格）、app/tasks/session_event_task.py（已有，含 cleanup 模式与 asyncio 桥接 storage）、app/celery_app.py（beat_schedule/task_routes/autodiscover_tasks）、app/infrastructure/storage/__init__.py（get_storage() async upload_bytes/get_url）、app/db/session.py get_sync_db。
`
const FRONTEND_COMMON = `
前端 apps/admin (React 18 + TS + Umi 4 + AntD 6 + ProComponents)。共享包 @hospital/api、@hospital/shared。回复中文，无 emoji。
重要参考：apps/admin/src/pages/session-replay/（Phase 2 已建的列表/回放页，照同样风格）、apps/admin/src/services/sessionReplay.ts（API 调用封装，复用 @hospital/api request，拦截器自动注入 token/tenant）、apps/admin/config/routes/session-replay.ts（路由模块格式）、apps/admin/package.json。
`

phase('P3热力图+P4截图')
const [heatmapRes, screenshotRes] = await parallel([
  () => agent(`${FRONTEND_COMMON}
【背景】后端已就绪：GET /api/v1/session-events/heatmap?pagePath=...&eventType=click|move&viewportBucket=lg|md|sm&days=30，返回 { pagePath, viewportBucket, eventType, points: [{ xRatio, yRatio, weight }] }（当前租户隔离，需 admin token，复用 sessionReplay.ts 的 request）。
【任务】Phase 3：实现热力图渲染页。
  1. apps/admin/package.json 加 "heatmap.js": "^2.0.5" 依赖（不要运行 pnpm install）。heatmap.js 是纯渲染库，MIT，canvas 热力图。
  2. apps/admin/src/services/sessionReplay.ts 加 getHeatmap(params) 封装（或新建 service，照现有函数风格）。
  3. 新建 apps/admin/src/pages/heatmap/index.tsx：
     - 顶部筛选：页面路径选择（下拉或输入，常用页面可写死几个 admin 路径如 /dashboard、/patient、/appointment、/schedule）、事件类型(click/move)、视口分桶(lg/md/sm，默认本机 innerWidth 推断)、天数(7/30/90)。
     - 中部 canvas 渲染区：用 heatmap.js h337.create({ container, radius: 40, maxOpacity: .8, minOpacity: 0, blur: .75 })，把 points 映射为 { x: xRatio*W, y: yRatio*H, value: weight }，W/H 取一个代表性 admin 画布尺寸（如 1440×900，对应视口分桶）。setValue 或 setData 喂数据。
     - 数据空态/加载态处理。
     - 备注（写在 issues）：v1 在空白画布渲染，未来增强可叠加真实页面截图作背景。
  4. 新建 apps/admin/config/routes/heatmap.ts 并在 config/routes/index.ts 聚合（照 session-replay.ts 路由模块格式），路径 /heatmap，挂「运营/系统」菜单下。
heatmap.js 导入用 import h337 from 'heatmap.js'；若无类型声明加 // @ts-ignore 或建 heatmap.d.ts module 声明。
只编辑：package.json、services/sessionReplay.ts（或新 service）、新建 pages/heatmap/index.tsx、config/routes/heatmap.ts、config/routes/index.ts。`, { label: 'frontend:heatmap', phase: 'P3热力图+P4截图', schema: RESULT, agentType: 'general-purpose' }),

  () => agent(`${BACKEND_COMMON}
【任务】Phase 4：实现定期网页截图（后端 Celery + Python playwright 路线，Docker 固定环境消除渲染漂移）。
先读 playwright.config.ts 与 apps/admin 的登录/认证方式（搜 getStorage/STORAGE_KEYS/token，admin 用 token 存哪），确定截图任务如何带上 admin 认证。
  1. apps/server/requirements.txt 加 playwright（确认现有文件格式，照风格追加；不要 pip install）。
  2. 新建 app/tasks/screenshot_task.py：
     - @celery_app.task(name="app.tasks.screenshot_task.capture_admin_screenshots", ...) 同步任务（用 sync_playwright），queue=scheduled，time_limit 充足（如 600s）。
     - 从 settings/env 读取配置：admin 基地址（如 ADMIN_BASE_URL）、截图目标账号（SCREENSHOT_ACCOUNT/SCREENSHOT_PASSWORD 或 SCREENSHOT_TOKEN）、目标页面列表（写死 admin 核心路由：/welcome、/dashboard、/patient、/appointment、/schedule/calendar 等，可配置）。
     - 流程：sync_playwright().start() → chromium.launch(headless=True) → new_context(viewport={1920,1080}) → 用 token 方案：若 SCREENSHOT_TOKEN 存在则注入 localStorage/cookie（按 admin 实际 token 存储位置，先读 admin 源码确认 key）；否则用账号密码走 /api/v1/auth/login 拿 token 后注入 → 逐页 page.goto(base+path, wait_until='networkidle') → page.screenshot(full_page=True) → 通过 get_storage()（asyncio 桥接，单次 asyncio.run 包裹一个协程把本批所有截图都 upload_bytes）存到 storage folder='admin-screenshots'，key 形如 admin-screenshots/{YYYYMMDD}/{path_slug}_{HHmmss}.png。
     - 记录每个页面结果（成功/失败/存储 url）到日志，返回 {success, captured:[...], failed:[...]}。
     - 异常隔离：单页失败不阻断整批。
  3. app/celery_app.py：在 beat_schedule 加 "admin-periodic-screenshot"（task="app.tasks.screenshot_task.capture_admin_screenshots", schedule=crontab(hour=2, minute=0), options={"queue":"scheduled"}）；task_routes 加 "app.tasks.screenshot_task.*":{"queue":"scheduled"}；autodiscover_tasks 列表加 "app.tasks.screenshot_task"。先读文件确认现有 beat/路由/autodiscover 结构再改，避免与 session-events-cleanup(3:25) 等冲突（2:00 无冲突）。
  4. Docker：查找 apps/server 的 Dockerfile（或 docker-compose 的 server 服务），加 RUN playwright install chromium --with-deps（或文档化需在部署时执行）。若改 Dockerfile 风险大则只在 issues 里说明部署需手动 playwright install。
只编辑：requirements.txt、新建 app/tasks/screenshot_task.py、app/celery_app.py、(可选)Dockerfile。`, { label: 'backend:screenshot', phase: 'P3热力图+P4截图', schema: RESULT, agentType: 'general-purpose' }),
])

phase('P2跟进')
const [fixRes, desensRes] = await parallel([
  () => agent(`${BACKEND_COMMON}
【任务】修复 app/tasks/session_event_task.py 两个 Low 问题（只编辑这一个文件）：
  1. day 计算时区不一致：router 用 datetime.isoformat()（naive 本地时间）传入 started_at，task 里补默认用 datetime.utcnow()，东八区可能跨天偏 8h。统一改为：day 一律按 UTC 计算——把 started_at 当 UTC 解析（若字符串带 tz 用 astimezone(UTC)，naive 则直接视为 UTC），ended_at/默认兜底也用 datetime.utcnow().date()。确保 heatmap 按天聚合不错位。
  2. cleanup_session_events 每个文件一次 asyncio.run(storage.delete(key)) 性能差：改为单次 asyncio.run 包裹一个 async 协程，协程内顺序 await storage.delete(key)（或 gather 有界并发），避免反复创建/销毁事件循环。
先读现有 session_event_task.py 全文，精准定位这两处再改，保持其余逻辑/风格不变。ruff 自检通过。
只编辑 app/tasks/session_event_task.py。`, { label: 'backend:task-fix', phase: 'P2跟进', schema: RESULT, agentType: 'general-purpose' }),

  () => agent(`${FRONTEND_COMMON}
【背景】Phase 2 脱敏只覆盖了 5 个核心页面（patient/index、patient/detail、appointment/detail、medical-record/index、AppointmentDetailModal），用 data-rrweb-mask-text（表格列 onCell 返回）、data-rrweb-input-mask（录入 ProFormText fieldProps 透传，加 as any）、className="rrweb-block"（高敏感区整块）三种方式。
先读 apps/admin/src/pages/patient/index.tsx 看 Phase 2 的 onCell 脱敏写法照搬风格。
【任务】补覆盖以下含患者敏感字段（姓名/手机号/身份证/病历）的页面，同样最小侵入：
  - apps/admin/src/pages/appointment/list.tsx
  - apps/admin/src/pages/appointment/queue.tsx
  - apps/admin/src/pages/user/detail.tsx
  - apps/admin/src/pages/user/index.tsx
  - apps/admin/src/pages/schedule/calendar/components/DayDetailDrawer.tsx
  - apps/admin/src/pages/schedule/calendar/components/CreateAppointmentModal.tsx
  - apps/admin/src/pages/waitlist/index.tsx
  - apps/admin/src/pages/follow-up/records.tsx
每个文件：grep 定位姓名/手机/phone/idCard/身份证/patientName 等敏感字段展示处；表格列用 onCell 返回 { 'data-rrweb-mask-text': '' }；录入框用 fieldProps={{ 'data-rrweb-input-mask': true } as any}；病历/详情高敏感整块用 className="rrweb-block"。ProDescriptions.Item 文本值在 render 包 span 加 data-rrweb-mask-text。
每个文件 tsc/ruff 无新增错误。无法干净处理的在某文件 issues 注明，不要硬改。
只编辑上述页面文件（文件已存在则编辑，不存在则在 issues 标注 skip）。`, { label: 'frontend:desens-expand', phase: 'P2跟进', schema: RESULT, agentType: 'general-purpose' }),
])

phase('终审')
const reviewRes = await agent(`${BACKEND_COMMON}
${FRONTEND_COMMON}
【任务】只读终审（不改代码），校验本轮新增/改动：
  - 前端：apps/admin/src/pages/heatmap/index.tsx、services heatmap 封装、config/routes/heatmap.ts + index.ts 聚合、package.json(heatmap.js)；脱敏补覆盖的 8 个页面改动。
  - 后端：app/tasks/screenshot_task.py、app/celery_app.py(beat/routes/autodiscover 新增段)、requirements.txt(playwright)；app/tasks/session_event_task.py(时区+cleanup 批量化两处改动)。
  检查：① heatmap 渲染：points {xRatio,yRatio,weight} → canvas 坐标换算正确（xRatio*W），heatmap.js h337.create/setData API 用法正确；② 截图任务：playwright sync_playwright 用法、token 注入位置是否与 admin 实际 token 存储 key 一致（核对 admin 源码 STORAGE_KEYS）、storage upload_bytes 调用、beat 任务名与 @task(name=) 一致、autodiscover 已收录；③ session_event_task：day 是否统一 UTC、cleanup 是否单次 asyncio.run；④ 脱敏 8 文件是否真加了属性、有无破坏现有渲染；⑤ ruff/tsc 层面明显错误。
  输出结构化：filesWritten/filesEdited 填 []，decisions 填终审结论，issues 按严重度列全部发现 + 需手动跟进项（pnpm install heatmap.js、pip install playwright + playwright install chromium、Docker 浏览器、截图任务需配 ADMIN_BASE_URL/SCREENSHOT_TOKEN 环境变量等）。`, { label: 'review', phase: '终审', schema: RESULT, agentType: 'general-purpose' })

return { heatmapRes, screenshotRes, fixRes, desensRes, reviewRes }
