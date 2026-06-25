# Admin 端 网页埋点 + 会话回放 + 热力图 + 定期截图 — 落地实施方案

> 状态：决策已确认，进入 Phase 1（核实埋点现状）
> 日期：2026-06-17
> 关联：基于 deep-research 工作流结论（rrweb 自建 + 黑名单精准脱敏 + 热力图视口分桶）

## 一、背景与目标

为机构端（admin）实现四项能力：

1. **网页埋点** — PV / 点击 / 错误 / 自定义事件
2. **用户操作回放** — 会话级 DOM 录制与回放
3. **访问热力图** — 点击/鼠标移动热区可视化
4. **定期截图** — 核心页面定时归档快照

使用者是**内部员工**，因此 PIPL 合规成本主要落在**患者敏感数据侧**（admin 页面会显示患者姓名/手机号/身份证/病历，属 Art.28 敏感个人信息），而非操作者侧。

## 二、技术选型结论（已定）

| 层 | 需求 | 方案 | 关键理由 |
|---|---|---|---|
| 采集+回放 | 操作回放 | **rrweb 自建** | DOM 增量录制，不录像素；数据自主、可复用现有基础设施；Sentry 云版数据出境对患者敏感数据是硬伤 |
| 热力图渲染 | 热区可视化 | **heatmap.js（纯渲染角色）** | 不采集只画图；rrweb 事件聚合后喂数据 |
| 定期截图 | 页面归档 | **Playwright（后端 Celery 路线）** | 与 22 个 beat 任务架构一致；环境可控 |
| 脱敏 | 患者数据保护 | **黑名单精准脱敏（rrweb-mask 属性）** | 回放可读性 + 患者数据合规的平衡点 |

**核心洞察**：rrweb 录制的 mouse/click 事件本就是结构化坐标，**热力图与回放同源**，不需要双采集依赖。

## 三、现状澄清（复用现有基础设施）

调研发现项目**已有埋点基础设施**，避免重复造轮子：

| 能力 | 现状 | 文件 |
|---|---|---|
| 网页埋点 SDK | ✅ 已有 `Tracker`（sendBeacon + beforeunload 兜底） | `packages/shared/src/analytics/tracker.ts` |
| 埋点数据模型 | ✅ `UserBehaviorLog`（platform/session_id/event_type/page_path/extra_data） | `apps/server/app/models/behavior_log.py` |
| 埋点落库任务 | ✅ `batch_save_behavior_logs` | `apps/server/app/tasks/behavior_log_task.py` |
| 埋点接收 API | ✅ analytics `/batch` | `apps/server/app/modules/analytics/router.py` |
| TTL 清理 | ✅ `behavior-log-cleanup`（保留 90 天） | `celery_app.py:222` |
| 操作行为日志 | ✅ OperationLog 中间件（仅写操作，Celery 落库） | `apps/server/app/middleware/operation_log.py` |
| 脱敏工具 | ✅ `maskPhone/maskIdCard` | `packages/shared/src/utils/format.ts:32-43` |
| 后端脱敏字段表 | ✅ `SENSITIVE_FIELDS` + `_sanitize_params` | `operation_log.py:83,135-159` |
| 对象存储抽象 | ✅ local/minio/cos | `apps/server/app/infrastructure/storage/` |
| WebSocket | ✅ `ws_manager`（Redis Pub/Sub，按 doctor/patient 维度） | `apps/server/app/core/websocket.py` |
| Playwright test | ✅ 已装 `@playwright/test ^1.58.2` | 根 `package.json`、`playwright.config.ts` |
| Celery beat | ✅ 22 个定时任务，3 队列（default/scheduled/notification） | `apps/server/app/celery_app.py` |

**缺口（全新工作）**：rrweb 录制、热力图聚合、定期截图、DOM 级脱敏打标。

**第一步**：先读 `apps/admin/src/utils/initApp.ts` + `analytics/router.py` 确认 Tracker 是否已接入 admin，决定 Phase 1 是「补全」还是「已可跳过」。

## 四、总体架构

```
admin 浏览器
 ├─ initApp.ts
 │   ├─ initTracker()          [已有] PV/点击/错误埋点 → behavior_log
 │   └─ initRrweb()            [新增] rrweb record → 批量上报
 ├─ rrweb record
 │   ├─ emit events → 批量队列（仿 Tracker 的 flush）
 │   ├─ 脱敏：rrweb-mask class + DOM 打标（复用 maskPhone 字段定位）
 │   └─ 上报：POST /api/v1/session-events/batch（sendBeacon + keepalive）
 │
后端 FastAPI
 ├─ modules/session_events/router.py    [新增] /batch 接收
 ├─ tasks/session_event_task.py         [新增] batch_save + 聚合热力图坐标
 ├─ models/session_event.py             [新增] SessionEvent + HeatmapPoint
 ├─ infrastructure/storage/             [复用] rrweb 原始事件落对象存储
 ├─ celery_app.py beat_schedule         [新增] 定期截图任务
 └─ core/websocket.py                   [复用] 截图完成通知（扩展 admin 维度）
```

## 五、数据模型设计

### 表 1：`session_events`（会话级元数据 + rrweb 事件索引）

仿 `behavior_log.py`。**rrweb 原始事件不进 Postgres**（体量太大），只存会话索引，事件 JSON 落对象存储。

```python
class SessionEvent(Base):
    __tablename__ = "session_events"
    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id     = Column(String(36), ForeignKey("tenants.id"), index=True, comment="租户ID")
    session_id    = Column(String(64), index=True, comment="会话ID，与 Tracker 共用")
    actor_id      = Column(String(36), index=True, comment="员工 account_id")
    actor_name    = Column(String(100), comment="员工姓名")
    viewport_w    = Column(Integer, comment="录制视口宽，热力图分桶用")
    viewport_h    = Column(Integer, comment="录制视口高")
    page_path     = Column(String(255), comment="起始/主要页面")
    event_count   = Column(Integer, default=0, comment="事件总数")
    storage_url   = Column(String(512), comment="rrweb 事件 JSON 的对象存储路径")
    started_at    = Column(DateTime, comment="会话开始")
    ended_at      = Column(DateTime, comment="会话结束")
    created_at    = Column(DateTime, default=now)
    # 索引：(tenant_id, started_at), (session_id)
```

### 表 2：`heatmap_points`（热力图坐标 — 解决屏幕比例问题的核心）

```python
class HeatmapPoint(Base):
    __tablename__ = "heatmap_points"
    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id       = Column(String(36), ForeignKey("tenants.id"), index=True, comment="租户ID")
    page_path       = Column(String(255), index=True, comment="页面路径")
    viewport_bucket = Column(String(20), index=True, comment="视口分桶 lg(>1440)/md(768-1440)/sm(<768)")
    event_type      = Column(String(20), comment="click / move")
    x_ratio         = Column(Numeric(5, 4), comment="x / viewport_w，0~1 相对坐标")
    y_ratio         = Column(Numeric(5, 4), comment="y / viewport_h，0~1 相对坐标")
    weight          = Column(Integer, default=1, comment="聚合计数")
    day             = Column(Date, index=True, comment="按天分区清理")
    # 唯一约束：(tenant_id, page_path, viewport_bucket, event_type, x_ratio, y_ratio, day)
    #   用 INSERT ... ON CONFLICT DO UPDATE SET weight = weight + 1 实现 upsert 聚合
```

**屏幕比例问题如何被彻底解决**：
- 采集时存相对坐标 `x_ratio = clientX / viewport_w`（0~1），不存绝对像素
- 按 `viewport_bucket` 分桶，避免 1920 与 1366 的点击混到一张图
- 渲染时画布坐标 = `x_ratio × target_w`，等比换算
- 响应式布局导致的 DOM 结构差异，靠 `viewport_bucket` 天然隔离

## 六、脱敏策略（黑名单精准脱敏）

复用已有 `maskPhone/maskIdCard` 工具定位敏感字段，用 rrweb 原生机制打标：

| rrweb 原生机制 | 用法 | 覆盖场景 |
|---|---|---|
| `class="rrweb-block"` | 整块不录制 | 病历内容区、患者详情抽屉 |
| `data-rrweb-input-mask` | 只遮输入值，保留布局 | 手机号/身份证/姓名输入框 |
| `data-rrweb-mask-text` | 遮文本内容 | 患者列表里的姓名/手机列 |

**统一打标**：在共享的表格列定义 / ProDescriptions 字段配置层，给患者敏感字段统一加 `data-rrweb-mask-text`，一处改全局生效。复用 `shared/utils/format.ts` 已有脱敏字段判断逻辑做"是否需要打标"的决策。

**上线前脱敏审计**：用 Phase 4 的 Playwright 截图脚本跑核心页面（患者列表、预约详情、病历），人工确认回放无明文敏感信息。

**⚠️ 重要约束**：rrweb/Sentry 的脱敏都是 **on-ingest（采集时执行），不可回溯**。已录制的明文事后改不掉。因此脱敏策略必须在首次上线前定死，不能"先录后收紧"。

## 七、分阶段实施

### Phase 1：埋点补全（✅ 已核实 — 可跳过，埋点已完整接入）

核实结论（2026-06-17）：
- `initApp.ts:12` 已 `initTracker`（platform='admin'，batchSize 10/5s，dev 已开）
- `app.tsx:222` 在 Umi `onRouteChange` 自动调 `trackPageView` → **PV 自动采集已接**
- Tracker 构造函数自动采集 JS 错误 + Promise rejection（`initErrorCapture`）
- `utils/analytics.ts` 有完整手动埋点 helper（click/search/custom）
- **session_id** 走 sessionStorage（`__tracker_session_id__`，每 tab 一会话）

→ Phase 2 的 rrweb 直接复用 `getTracker()?.getSessionId()`，与 `behavior_log` 同 session 串联。无需补全工作。

### Phase 2：rrweb 会话回放（5-7 天，核心）
1. **前端**：admin 装 `rrweb`，在 `initApp.ts` 加 `initRrweb()`（仿 `initTracker` 批量队列 + sendBeacon）
2. **前端上报器**：复制 `tracker.ts` 的 `flush` 机制，改目标为 `/api/v1/session-events/batch`
3. **后端 router**：仿 `analytics/router.py /batch`，接收后 `batch_save_session_events.delay()`
4. **后端 Celery 任务**：仿 `behavior_log_task.py`，批量落库；rrweb 事件 JSON 落 `infrastructure/storage/`，DB 存 `storage_url`
5. **脱敏打标**：按第六节给敏感组件加 rrweb 属性
6. **回放前端**：admin 后台加「会话回放」页，用 `rrweb-player` 播放（从 storage_url 拉事件）
7. **清理任务**：仿 `behavior-log-cleanup` 加 `session-events-cleanup`（建议 30-90 天，rrweb 数据大）

### Phase 3：热力图（3-4 天）
1. **采集**：rrweb record 时，对 `IncrementalSnapshot` 类型为 `mousemove/click` 的事件，**额外提取相对坐标**写入 `heatmap_points`
2. **聚合**：Postgres `ON CONFLICT DO UPDATE` upsert，天然聚合计数
3. **渲染**：admin 后台「热力图分析」页，按 page_path + viewport_bucket 查询，前端装 `heatmap.js`（纯渲染），坐标按 `x_ratio × 画布宽` 换算

### Phase 4：定期截图（2-3 天）
**后端 Celery 路线**（贴合现有架构）：
1. `apps/server` 装 Python `playwright` + `playwright install chromium`（**Docker 固定环境，消除渲染漂移**）
2. 新增 `tasks/screenshot_task.py`：`sync_playwright()` 启 chromium → 登录 admin（测试账号 token）→ 遍历核心页面 → `page.screenshot({full_page: True})` → 落 `infrastructure/storage/`
3. `celery_app.py` 注册：`beat_schedule` 加 `admin-periodic-screenshot`（如每天 02:00），`task_routes` 加 `screenshot_task.* → scheduled`，`autodiscover_tasks` 登记
4. **关键**：截图脚本必须在 Docker 固定环境跑（OS/字体/硬件一致），否则像素 diff 噪声
5. 截图完成通过 `ws_manager` 通知（需扩展 admin 维度连接：加 `connect_admin`/`_admin_connections`/`ws:admin:` 通道前缀）

## 八、关键技术决策

| 决策 | 推荐 | 理由 |
|---|---|---|
| rrweb 事件存哪 | 对象存储 + DB 索引 | Postgres 扛不住 rrweb 事件量，对象存储便宜且已有抽象 |
| 热力图坐标计算时机 | 采集时算相对坐标（前端），后端只 upsert | 避免后端解析整个 rrweb 流 |
| 截图跑前端 E2E 还是后端 Celery | 后端 Celery + Python playwright | 与 beat 架构一致，可调度、可通知、环境可控 |
| 热力图渲染依赖 | heatmap.js（纯渲染） | 成熟稳定，6KB+，不采集只画图 |
| 实时 vs 事后 | 事后分析为主 | admin 内部场景，实时意义不大 |

## 九、数据量与清理

- rrweb 单次会话事件 JSON：典型几百 KB ~ 几 MB（取决于操作时长）
- admin 内部员工量级可控，但**必须配 TTL 清理**
- 建议会话回放保留 30-90 天（比 behavior_log 的 90 天短，体积大）
- `heatmap_points` 是聚合数据，体积小，可保留更久（180 天）

## 十、合规边界

- 操作者侧：PIPL Art.13(2)"为履行人力资源管理所必需"为合法基础，无需单独同意
- **患者数据侧是硬约束**：admin 显示的患者姓名/手机号/身份证/病历属 Art.28 敏感个人信息，必须脱敏
- 脱敏 on-ingest 不可回溯 → 首次上线前必须锁定脱敏策略
- 若 rrweb 事件落对象存储涉及跨境，需评估 PIPL Art.38-40（取决于 storage 后端部署位置）

## 十一、已确认决策

1. **rrweb 事件存储后端 = MinIO 自建**（分阶段）
   - Phase 2 开发验证：复用现有 `local`（已在用、零新基础设施、当天跑通回放链路）
   - 生产上线前：切到 MinIO（加进 docker-compose 单容器 ~50MB，数据自主、无按量计费、S3 兼容、部署在腾讯云国内无跨境合规）
   - 不选 cos（rrweb 量大计费线性增长）、不选 local 上生产（无副本易满盘）
2. **回放保留期 = 30 天**
   - `session_events`（rrweb 回放，重量）保留 30 天
   - `behavior_log`（轻量）维持现状 90 天
   - `heatmap_points`（聚合，轻量）保留 180 天
   - 理由：内部员工操作回放实际查询窗口不超一个月，rrweb 体积大需控制清理压力
3. **Phase 1 立即启动**（只读核实埋点现状）

## 十二、执行清单（顺序）

1. ✅ 读 `initApp.ts` + `analytics/router.py` + `app.tsx` — 埋点已完整接入，Phase 1 跳过
2. ✅ Phase 1：补全埋点（无需，session_id 由 Tracker 管理，rrweb 复用）
3. ✅ 新建 `session_events` + `heatmap_points` 模型 + Alembic 迁移（`123_create_session_events`，down_revision='122'）
4. ✅ Phase 2：前端 rrweb record + 上报器 + 后端 router/Celery 任务 + 存储接入（workflow 落地）
5. ✅ 脱敏打标（5 个核心页面：patient/index、patient/detail、appointment/detail、medical-record/index、AppointmentDetailModal）
6. ✅ Phase 2：admin 回放页（rrweb-player）+ 路由 + service
7. ✅ Phase 2：会话清理 Celery beat 任务（session-events-cleanup 03:25 / heatmap-points-cleanup 03:30）
8. ✅ Phase 3：热力图查询端点（`/heatmap`）+ 前端渲染页（pages/heatmap，heatmap.js 纯渲染，xRatio/yRatio→canvas 换算，视口分桶）
9. ✅ Phase 4：Python playwright + 截图任务（tasks/screenshot_task.py，token 注入 admin localStorage）+ beat 注册（admin-periodic-screenshot 02:15）+ Docker（playwright install chromium --with-deps）
10. ☐ 上线前脱敏审计 + 像素环境验证（需运行环境：alembic upgrade + pnpm install + pip install playwright 后人工跑一遍核心页面）

### Phase 3/4 落地后的遗留项（终审结论）

**已修复（本轮）**
- [Critical] screenshot_task S310（Request 构造）+ B905（zip strict=True）→ ruff 全通过
- [High] tenant_id 注入格式不一致（JSON.stringify 多余引号）→ 统一为原始字符串，对齐 admin setStorage 字符串分支
- [Low] session_event_task day 时区统一 UTC（naive 视为 UTC）+ cleanup asyncio 批量化（单次 run 顺序删）
- [Low] 脱敏补覆盖 8 个页面（appointment/list、appointment/queue、user/detail、user/index、DayDetailDrawer、CreateAppointmentModal、waitlist、follow-up/records）

**需手动执行（部署前）**
- `cd apps/server && alembic upgrade head`（→ 123）
- `cd apps/admin && pnpm install`（rrweb / rrweb-player / @types/rrweb-player / heatmap.js）
- `cd apps/server && pip install -r requirements.txt && playwright install chromium --with-deps`
- 配置环境变量：`SCREENSHOT_ADMIN_BASE_URL` / `SCREENSHOT_TOKEN`（或 `SCREENSHOT_ACCOUNT`/`SCREENSHOT_PASSWORD`）/ 截图目标页面（建议专用只读全权限账号）
- 服务器 storage 后端切 MinIO 前先验证 local 跑通回放链路

**建议跟进（非阻断）**
- [Info] heatmap v1 在空白画布渲染，未来可叠加真实页面截图作背景提升定位精度
- [Info] CreateAppointmentModal 的患者搜索 Select option label 为明文姓名+手机，antd Select option 字符串无法内嵌 data-* 属性做单元格级遮蔽，展开下拉时仍可能录制（建议改 optionRender 自定义渲染或后端脱敏 label）
- [Info] 截图任务默认页面含 /schedule/calendar 等需 access 权限，截图账号需相应权限否则截到 403/空白
- [Info] rrweb 2.x alpha，建议锁版固化

### Phase 2 落地后的遗留项（终审结论）

**已修复**
- [High] 热力图唯一约束 NULL tenant_id 不聚合 → 迁移改为 `NULLS NOT DISTINCT`（PG16 支持，`ON CONFLICT ON CONSTRAINT` 正常命中）

**需手动执行（部署前）**
- [Medium] `cd apps/server && alembic upgrade head`（→ 123，建 session_events/heatmap_points 表）
- [Medium] `pnpm install`（admin 新增 rrweb ^2.0.0-alpha.18 / rrweb-player ^2.0.0-alpha.4 / @types/rrweb-player）

**建议跟进（非阻断）**
- [Low] session_event_task 里 day 计算时区不一致（router 用 naive isoformat，task 用 utcnow 补默认，东八区可能跨天偏 8h）→ 统一 UTC 算 day
- [Low] cleanup_session_events 每文件一次 `asyncio.run()` → 改单次循环批量 delete
- [Info] rrweb 2.x alpha，建议锁版并在 lockfile 固化
- [Info] 脱敏仅覆盖 5 个核心页面，其余含敏感字段页面（appointment/list、user/detail、DayDetailDrawer、waitlist、follow-up/records 等）需后续补打标

## 附：关键复用路径速查

| 步骤 | 复用文件 |
|---|---|
| 前端 rrweb 录制启动 | `apps/admin/src/utils/initApp.ts`（仿 `initTracker` 加 `initRrweb`） |
| 前端事件批量上报器 | `packages/shared/src/analytics/tracker.ts`（复制改 flush 目标 URL） |
| 前端脱敏 DOM | rrweb 原生 `rrweb-block`/`data-rrweb-mask-text`；文本掩码用 `packages/shared/src/utils/format.ts` |
| 后端接收 router | `apps/server/app/modules/analytics/router.py` 的 `/batch` |
| 后端落库 Celery 任务 | `apps/server/app/tasks/behavior_log_task.py` 的 `batch_save_behavior_logs` |
| 新建模型 | 仿 `apps/server/app/models/behavior_log.py`（`UserBehaviorLog`） |
| 新建迁移 | `apps/server/migrations/versions/`，`down_revision='122'` |
| 定时任务注册 | `apps/server/app/celery_app.py` 的 `beat_schedule` + `autodiscover_tasks` + `task_routes` |
| 截图任务 | Playwright test 已就绪；Python 侧截图需新增 `playwright` 依赖 |
| 实时通知 | `apps/server/app/core/websocket.py` 的 `ws_manager`（需扩展 admin 维度） |
