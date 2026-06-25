export const meta = {
  name: 'session-replay-phase2',
  description: 'Phase 2: 实现 admin 会话回放 — 后端 schema/task/router/注册 + 前端 rrweb 录制/回放页 + 脱敏打标 + 终审',
  phases: [
    { title: '后端核心', detail: 'schema + Celery 任务（并行，文件不冲突）' },
    { title: '后端 API', detail: 'router 模块 + 路由/beat 注册（并行）' },
    { title: '前端', detail: 'rrweb 录制上报 + 回放页（并行）' },
    { title: '脱敏打标', detail: '患者敏感字段加 rrweb 属性' },
    { title: '终审', detail: '校验 import 一致性与前后端契约' },
  ],
}

// ---------- 共享上下文：API 契约（前后端 agent 必须遵守） ----------
const API_CONTRACT = `
【后端路由前缀】/api/v1/session-events （在 app/api/v1/__init__.py 注册为 RouterRegistration("app.modules.session_events.router","/session-events",[...])）
【数据模型】app/models/session_event.py 已存在 SessionEvent + HeatmapPoint（不要改它）。
  - SessionEvent：每行=一个 rrweb 事件批次段；session_id 串联完整会话；原始事件 JSON 落对象存储，本表存 storage_url/storage_key。
  - HeatmapPoint：相对坐标(x_ratio/y_ratio 0~1，量化0.01)+viewport_bucket(lg/md/sm)+event_type(click/move)+weight+day，唯一约束 upsert 聚合。
【上传接口】POST /session-events/batch （无需认证，用 get_optional_account 提取 actor，与 analytics 一致）
  请求体(camelCase)：
    { sessionId: str, viewportW: int, viewportH: int, pagePath: str|null,
      sequence: int, startedAt: ISO8601|null, endedAt: ISO8601|null,
      events: [ <rrweb 原始事件对象数组> ] }
  响应：{ success: true, count: <event_count>, segmentId: <str> }
  行为：IP 限流；Celery batch_save_session_events.delay(...)；Celery 不可用时回退直写（参考 analytics router 的 try/except）。
【会话列表】GET /session-events （需 get_current_admin 认证）
  查询参数：platform, actorId, pagePath, sessionId, startTime, endTime, page, pageSize
  返回 PageResponse，每项含：id, sessionId, actorId, actorName, pagePath, viewportW/H, eventCount, sequence, startedAt, endedAt, createdAt。
  按 session_id 聚合返回（每个 session 一行，event_count 求和），便于列表展示。
【回放数据】GET /session-events/{session_id}/replay （需 get_current_admin 认证）
  返回该 session 所有批次段（按 sequence/created_at 排序）：{ sessionId, viewportW, viewportH, segments: [{ segmentId, sequence, eventCount, eventsUrl(presigned storage url) }] }
  前端按顺序拉取各 eventsUrl、拼接 events 数组后喂给 rrweb-player。
【热力图查询】GET /session-events/heatmap （需 get_current_admin 认证）
  查询参数：pagePath(必填), eventType=click|move, viewportBucket, days=30
  返回 { pagePath, viewportBucket, eventType, points: [{ xRatio, yRatio, weight }] }（当前租户隔离）。
`

const SCHEMA_RESULT = {
  type: 'object',
  properties: {
    filesWritten: { type: 'array', items: { type: 'string' } },
    filesEdited: { type: 'array', items: { type: 'string' } },
    decisions: { type: 'string', description: '关键设计决策（1-3 句）' },
    issues: { type: 'string', description: '遗留问题或需手动跟进项，无则填 none' },
  },
  required: ['filesWritten', 'filesEdited', 'decisions', 'issues'],
}

const COMMON = `
项目根：/Users/leijiadashao/letond/appointment-booking-system
后端：apps/server (Python 3.12, FastAPI, SQLAlchemy 2 async, Pydantic)。回复用中文。风格对齐现有代码，禁止 emoji。
重要参考文件（必须先读以匹配风格）：
  - app/models/session_event.py （已存在，SessionEvent + HeatmapPoint 定义）
  - app/models/behavior_log.py （模型风格）
  - app/schemas/behavior_log.py （schema 风格：ConfigDict alias_generator=to_camel, populate_by_name=True；BaseSchema 见 app/schemas/base.py）
  - app/modules/analytics/router.py （router 风格、限流、get_optional_account、Celery delay+回退）
  - app/tasks/behavior_log_task.py （Celery 任务风格、get_sync_db、cleanup 分批删除）
  - app/infrastructure/storage/__init__.py （get_storage()，async upload_bytes(data,key,content_type) + get_url(key,expires)）
  - app/db/session.py 的 get_sync_db（同步会话上下文管理器，Celery 用）
  - app/middleware/tenant_context.py 的 get_current_tenant_id()
  - app/api/v1/__init__.py 的 RouterRegistration dataclass 注册模式
  - app/celery_app.py 的 beat_schedule / task_routes / autodiscover_tasks
`

phase('后端核心')
const [schemaRes, taskRes] = await parallel([
  () => agent(`${COMMON}
${API_CONTRACT}
任务：新建 app/schemas/session_event.py，定义所有 Phase2 需要的 Pydantic schema。参考 app/schemas/behavior_log.py 的 ConfigDict 写法。
需要定义：
  1. SessionEventBatchRequest —— /batch 上传请求体（camelCase 字段见契约；events 字段类型为 list[dict]，不加严格校验因为 rrweb 事件结构动态；events 列表长度 1~500；sessionId 必填 max_length 64；viewportW/H 可选 int；pagePath 可选；sequence 可选 int；startedAt/endedAt 可选 datetime）
  2. SessionSegmentResponse、SessionListResponse、SessionReplayResponse、HeatmapPointItem、HeatmapQueryResponse —— 见契约
  3. 响应类统一用 alias_generator=to_camel, populate_by_name=True, by_alias=True, from_attributes=True（list 响应）
  4. PageResponse 复用 app.schemas.response.PageResponse
只创建 app/schemas/session_event.py 这一个文件。不要创建别的文件，不要改模型。`, { label: 'backend:schemas', phase: '后端核心', schema: SCHEMA_RESULT, agentType: 'general-purpose' }),
  () => agent(`${COMMON}
${API_CONTRACT}
任务：新建 app/tasks/session_event_task.py。参考 app/tasks/behavior_log_task.py 风格（@celery_app.task 装饰器、autoretry、time_limit、get_sync_db 上下文、cleanup 分批删除）。
需要实现 3 个任务：
  1. batch_save_session_events(batch_payload: dict)
     - 入参含：tenant_id, actor_id, actor_name, ip, user_agent, platform(默认'admin'), session_id, viewport_w, viewport_h, page_path, sequence, started_at, ended_at, events(list[dict])
     - 步骤：
       a) 将 events 序列化为 JSON bytes（json.dumps ensure_ascii=False → encode）
       b) 用 asyncio.run() 桥接调用 async storage：from app.infrastructure.storage import get_storage; storage=get_storage(); result=asyncio.run(storage.upload_bytes(data, key, 'application/json'))，key 形如 session-replay/{YYYYMM}/{uuid}.json（参考 base.py _generate_key 思路，folder='session-replay'，但 upload_bytes 需要完整 key，自己拼）。注意 LocalStorage 的 upload_bytes 签名。
       c) 同步 DB 写 SessionEvent 行（storage_url=result.url, storage_key=result.key, event_count=len(events)）
       d) 从 events 中提取热力图坐标并 upsert HeatmapPoint：
          - rrweb 事件结构：{type, data:{source, x, y, id, ...}}。type==2(IncrementalSnapshot) 且 data.source==2(MouseMove) → move；data.source==1(MouseInteraction) 且 data.type in ('click','dblclick','touchstart') → click。坐标在 data.x/data.y（相对文档）。
          - 需要 viewport_w/h（用批次传入的，若缺失则跳过该坐标提取）。
          - 计算 x_ratio=round(x/viewport_w, 2), y_ratio=round(y/viewport_h, 2)，clamp 到 [0,1]。
          - viewport_bucket：>1440→lg，768~1440→md，<768→sm。
          - page_path 用批次 page_path；event_type 'click'/'move'；day=started_at 或 utcnow 的 date。
          - 用 PostgreSQL upsert：dialect insert(HeatmapPoint.__table__).values(...).on_conflict_do_update(index_elements=[...7列...], set_={'weight': HeatmapPoint.__table__.c.weight+1, 'updated_at': datetime.utcnow()})，按 (tenant_id, page_path, viewport_bucket, event_type, x_ratio, y_ratio, day) 冲突。注意 tenant_id 为 None 时冲突处理（PostgreSQL 中 NULL 不参与 unique，可直接 insert；记录这一点到 issues）。
          - mousemove 数据量大，对 move 类型按固定步长采样（如每 5 个取 1 个）后再 upsert，避免每次移动都写库。
     - 失败 rollback + raise（与 behavior_log_task 一致）。
  2. cleanup_session_events(retention_days=30)
     - 分批删除 created_at < cutoff 的 SessionEvent；删除前先按 storage_key 调 storage.delete 清理对象存储文件（asyncio.run 桥接，失败仅 warning 不阻断）。
  3. cleanup_heatmap_points(retention_days=180)
     - 分批删除 day < cutoff 的 HeatmapPoint。
保留期常量：SESSION_EVENT_RETENTION_DAYS=30, HEATMAP_RETENTION_DAYS=180（文件顶部）。
只创建 app/tasks/session_event_task.py。不要改模型、不要注册 beat（注册由别的 agent 做）。`, { label: 'backend:celery-task', phase: '后端核心', schema: SCHEMA_RESULT, agentType: 'general-purpose' }),
])

phase('后端 API')
const [routerRes, registerRes] = await parallel([
  () => agent(`${COMMON}
${API_CONTRACT}
任务：新建模块 app/modules/session_events/ 下的 __init__.py + router.py。参考 app/modules/analytics/router.py（限流 _check_rate_limit、_get_client_ip、_parse_user_agent、get_optional_account、get_current_admin、Celery delay + try/except 回退直写）。
实现契约里的全部 4 个端点：
  - POST /batch：限流(120/min/IP)；提取 actor（get_optional_account）、tenant(get_current_tenant_id)、ip、ua；组装 batch_payload dict；调 from app.tasks.session_event_task import batch_save_session_events; batch_save_session_events.delay(payload)；Celery 失败回退：直接 asyncio 调 storage 上传 + 同步写库 + 坐标 upsert（简化：回退路径可只写 SessionEvent 行 + 跳过热力图，记录到 issues）。返回 {success, count, segmentId}。
  - GET /：需 get_current_admin；按 session_id 聚合（func.sum event_count, group by session_id 取最新 created_at/started_at），支持 platform/actorId/pagePath/sessionId/startTime/endTime 过滤；返回 PageResponse[SessionListResponse]。
  - GET /{session_id}/replay：需 get_current_admin；查该 session 所有 SessionEvent 行按 sequence,created_at 排序；对每行用 storage.get_url(storage_key, expires=3600) 生成 presigned eventsUrl（asyncio 桥接或 await——router 是 async 函数可直接 await get_storage().get_url(...)）；返回 SessionReplayResponse（viewportW/H 取首段）。
  - GET /heatmap：需 get_current_admin；按 page_path+eventType(+viewportBucket 可选)+当前租户+近 N 天聚合 HeatmapPoint（sum weight, group by x_ratio,y_ratio）；返回 HeatmapQueryResponse。
schema 从 app.schemas.session_event 导入。模型从 app.models.session_event 导入。只创建 app/modules/session_events/__init__.py 和 router.py。不要注册路由（注册由别的 agent 做）。`, { label: 'backend:router', phase: '后端 API', schema: SCHEMA_RESULT, agentType: 'general-purpose' }),
  () => agent(`${COMMON}
${API_CONTRACT}
任务：注册新模块，共 2 处编辑（不同文件）：
  1. app/api/v1/__init__.py —— 在 RouterRegistration 列表里新增一行注册 session_events。先读该文件看 analytics 那行的写法（约 75 行 RouterRegistration("app.modules.analytics.router","/analytics",["用户行为分析"])），照同样格式加：RouterRegistration("app.modules.session_events.router","/session-events",["会话回放/热力图"])。插入位置按文件现有顺序（analytics 附近）。
  2. app/celery_app.py —— 先读该文件，找到 beat_schedule、task_routes、autodiscover_tasks 三处：
     - beat_schedule 加一项 "session-events-cleanup"：task="app.tasks.session_event_task.cleanup_session_events", schedule=crontab(hour=3, minute=25)（避开已有 03:00/03:20 的任务）, options={"queue":"scheduled"}。再加 "heatmap-points-cleanup"：task="app.tasks.session_event_task.cleanup_heatmap_points", schedule=crontab(hour=3,minute=30), options={"queue":"scheduled"}。
     - task_routes 加 "app.tasks.session_event_task.*": {"queue": "scheduled"}（仿已有 app.tasks.behavior_log_task.* 写法）。
     - autodiscover_tasks：若它是显式列出模块名，确认 session_event_task 在内；若是 glob 自动发现（如 "app.tasks.*"），则无需改动，在 issues 里说明。
只编辑这 2 个文件。不要改其它。`, { label: 'backend:register', phase: '后端 API', schema: SCHEMA_RESULT, agentType: 'general-purpose' }),
])

phase('前端')
const FRONTEND_COMMON = `
前端：apps/admin (React 18 + TypeScript + Umi 4 + AntD 6 + ProComponents)。共享包 @hospital/shared / @hospital/api。回复中文，无 emoji。
重要参考：
  - apps/admin/src/utils/initApp.ts （应用初始化，已调 initTracker；在此加 initSessionRecorder()）
  - packages/shared/src/analytics/tracker.ts （批量队列 + sendBeacon + beforeunload/visibilitychange 兜底 flush 模式，必须复刻这套上报机制）
  - packages/shared/src/analytics/index.ts （getTracker 导出，getSessionId() 复用会话 ID）
  - apps/admin/src/app.tsx （onRouteChange 里已有 getTracker().trackPageView）
  - apps/admin/config/routes/ 路由模块（按业务域拆分，加新路由照同样格式）
  - apps/admin/package.json （加依赖）
`
const [recordRes, replayRes] = await parallel([
  () => agent(`${FRONTEND_COMMON}
${API_CONTRACT}
任务：接入 rrweb 录制 + 批量上报。
  1. 在 apps/admin/package.json 的 dependencies 加 "rrweb": "^2.0.0-alpha.18"（rrweb 2.x 当前 alpha；若不确定精确版本，写 "^2.0.0-alpha.18" 并在 issues 注明需 pnpm install 后确认）。不要运行 pnpm install。
  2. 新建 apps/admin/src/utils/sessionRecorder.ts：
     - import { record } from 'rrweb'
     - initSessionRecorder(): 用 getTracker()?.getSessionId() 取 session_id（与 behavior_log 同会话）；若拿不到则用 sessionStorage 生成。
     - 启动 record({ emit(event){ queue.push(event) } })，emit 收到事件入队。
     - 复刻 tracker.ts 的批量上报机制：batchSize(如 30 条或 10s 定时) + beforeunload/visibilitychange 兜底 flush + sendBeacon(URL, blob) 优先、fetch keepalive 兜底 + 失败回插队列(上限 500)。
     - 上报体按契约 camelCase：{ sessionId, viewportW: innerWidth, viewportH: innerHeight, pagePath: location.pathname, sequence: 递增序号, startedAt: 首事件 timestamp(ISO), endedAt: 末事件 timestamp(ISO), events: [...] }
     - URL: 用 @hospital/api 的 getBaseURL() + '/session-events/batch'（参考 initApp.ts 里 apiBaseUrl 拼法）。
     - 提供 stopSessionRecorder()/forceFlush() 导出。
  3. 在 apps/admin/src/utils/initApp.ts 末尾加一行 initSessionRecorder() 调用（确保 DOM 可用——Umi 运行时 initApp 在客户端执行，可直接调；若 record 需 document，加 typeof document!=='undefined' 守卫）。
  4. 开发环境默认开启（与 initTracker enableInDev 一致）。
只编辑 package.json、新建 sessionRecorder.ts、编辑 initApp.ts。`, { label: 'frontend:record', phase: '前端', schema: SCHEMA_RESULT, agentType: 'general-purpose' }),
  () => agent(`${FRONTEND_COMMON}
${API_CONTRACT}
任务：新建「会话回放」页面 + 路由 + API 调用。
  1. 在 apps/admin/src/pages/session-replay/ 下建 index.tsx（列表页）：ProTable 展示会话列表（columns: sessionId, actorName, pagePath, eventCount, startedAt, duration 推算），查询参数对应 GET /session-events 的过滤项；行操作「回放」跳详情页 /session-replay/:sessionId。
  2. 建 apps/admin/src/pages/session-replay/replay.tsx（回放页）：从 URL 取 sessionId；调 GET /session-events/{sessionId}/replay 拿 segments；按顺序 fetch 每个 eventsUrl（注意 CORS/鉴权——eventsUrl 是对象存储 presigned url，直接 fetch）；拼接所有 events 数组；用 rrweb-player 渲染（<RRWebPlayer events={...} />，依赖 "@types/rrweb-player" 和 "rrweb-player"）。在 package.json 加 "rrweb-player": "^2.0.0-alpha.4"。
  3. 在 apps/admin/src/services 或直接在页面内封装 API 调用：用现有请求封装（参考 packages/api 或 admin src/utils/request 模式，GET 需带 admin token）。可新建 apps/admin/src/services/sessionReplay.ts 封装 listSessionEvents / getSessionReplay。
  4. 在 apps/admin/config/routes/ 加路由模块（参考已有 routes 文件命名与导出格式），路径 /session-replay 和 /session-replay/:sessionId，挂在「系统/运营」类菜单下（参考现有 routes 归类）。在主 routes index 里 import 聚合（照现有模式）。
只新建/编辑：pages/session-replay/*、services/sessionReplay.ts、package.json(加 rrweb-player 依赖)、config/routes/* 相关。不要碰 initApp.ts（由录制 agent 负责）。`, { label: 'frontend:replay-page', phase: '前端', schema: SCHEMA_RESULT, agentType: 'general-purpose' }),
])

phase('脱敏打标')
const desensRes = await agent(`${COMMON}
任务（脱敏打标，黑名单精准脱敏）：给 admin 中显示患者敏感信息（姓名/手机号/身份证/病历）的组件加 rrweb 原生脱敏属性，让 rrweb 录制时自动遮蔽。
rrweb 属性：
  - data-rrweb-mask-text：遮蔽元素文本内容（用于展示患者姓名/手机/身份证的只读文本、表格列单元格）
  - data-rrweb-input-mask：遮蔽输入框的输入值（用于录入手机号/身份证/姓名的 Input）
  - class="rrweb-block"：整块不录制（用于病历详情、完整患者档案抽屉等高敏感区）
先用 grep 定位敏感字段出现处（关键词：手机号/phone/idCard/身份证/姓名/患者姓名/patientName/medicalRecord/病历），参考 packages/shared/src/utils/format.ts 的 maskPhone/maskIdCard 知道哪些是敏感字段。
范围控制：只处理 admin 端最核心的几处（患者列表表格列、预约详情/抽屉、患者详情、病历查看）。不要大改逻辑，只在合适的 DOM/组件属性上加 data-* 属性或 className。ProComponents 的 Column/ProDescriptions 字段可通过 render 或 column 的 onCell/className 加属性；优先用最小侵入方式（如给单元格 className 加 'rrweb-mask-text' 对应的 data 属性——注意 rrweb 识别的是 data-rrweb-mask-text 属性或 .rrweb-block class，文本遮蔽需 data-rrweb-mask-text 属性）。
如果某处无法干净加属性，记录到 issues，不要硬改。
返回结构化结果，列明改了哪些文件、哪些字段、用了哪种属性。`, { label: 'desensitize', phase: '脱敏打标', schema: SCHEMA_RESULT, agentType: 'general-purpose' })

phase('终审')
const reviewRes = await agent(`${COMMON}
${API_CONTRACT}
任务（只读终审，不要改代码）：校验本次 Phase2 所有新增/改动文件的一致性：
  - 读 app/schemas/session_event.py、app/tasks/session_event_task.py、app/modules/session_events/router.py、app/api/v1/__init__.py(改动行)、app/celery_app.py(改动段)、apps/admin/src/utils/sessionRecorder.ts、apps/admin/src/utils/initApp.ts(改动)、apps/admin/src/pages/session-replay/*、apps/admin/src/services/sessionReplay.ts、config/routes 改动。
  - 检查：① import 路径与符号是否真实存在（模型字段名、schema 类名、storage 方法签名 upload_bytes(data,key,content_type)/get_url(key,expires)、Celery 任务名）；② 前端上报体 camelCase 字段与后端 schema 期望是否一致（sessionId/viewportW/pagePath/sequence/startedAt/endedAt/events）；③ router 注册的模块路径与文件是否匹配；④ beat 任务名与 task 函数 name 是否一致；⑤ 热力图 upsert 的 on_conflict 列是否与唯一约束 uq_heatmap_point_cell 的 7 列一致；⑥ 明显 bug。
  - 输出结构化：filesWritten/filesEdited 填 []（你没改文件），decisions 填"终审结论"，issues 填发现的所有问题（按严重度排序，含需手动跟进项如 pnpm install、alembic upgrade 123、null tenant_id unique 冲突等）。`, { label: 'review', phase: '终审', schema: SCHEMA_RESULT, agentType: 'general-purpose' })

return {
  schemaRes, taskRes, routerRes, registerRes,
  recordRes, replayRes, desensRes, reviewRes,
}
