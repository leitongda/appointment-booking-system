# 医院预约挂号系统 — 深度探索改进实施方案

基于对项目技术栈、用途和状态的深入探索，针对发现的改进点制定的分阶段实施方案。

---

## Phase 1 — P0: 关键安全加固（28-34 小时）

### 1.1 Token 黑名单覆盖所有角色

**优先级：** P0 | **工作量：** 4h | **风险：** LOW

**现状：** `auth_unified.py` 仅 `_get_admin_account` 检查 Redis 黑名单，`_get_user_account` 和 `_get_doctor_account` 跳过检查。

**方案：**
- 从 `_get_admin_account`（行 271-280）提取黑名单检查逻辑为独立辅助函数 `_check_token_blacklist(token, tenant_id)`
- 在 `_get_user_account` 和 `_get_doctor_account` 顶部调用该辅助函数
- 更新 `get_current_account`（行 544-551）传递原始 token 到三个角色函数

**修改文件：**
- `apps/server/app/common/auth_unified.py`

**测试：** 新增 `tests/security/test_token_blacklist_all_roles.py` 验证 user/doctor 黑名单 token 返回 401

---

### 1.2 安全响应头中间件

**优先级：** P0 | **工作量：** 3h | **风险：** LOW

**方案：** 创建 `SecurityHeadersMiddleware`，添加以下响应头：
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`（非 DEBUG 时）
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`

在 `main.py` 中注册，位于中间件栈前部（CORS 之前）。通过环境变量 `SECURITY_HSTS_ENABLED` 控制。

**新建文件：**
- `apps/server/app/middleware/security_headers.py`

**修改文件：**
- `apps/server/app/main.py`
- `apps/server/app/middleware/__init__.py`

---

### 1.3 Refresh Token 轮换与黑名单

**优先级：** P0 | **工作量：** 6h | **风险：** MEDIUM

**现状：** `auth/router.py` 的 `refresh_token` 端点（行 238）创建新 token 对但不吊销旧 refresh token，存在重放攻击风险。

**方案：**
- refresh 端点成功解码旧 token 后，将其 SHA256 哈希加入 Redis 黑名单（TTL = 剩余有效期）
- 在 `redis.py` 新增 `add_refresh_token_to_blacklist` 方法
- 对所有 login 端点（admin/doctor/user）统一应用
- 区分 access_token 和 refresh_token 黑名单前缀

**修改文件：**
- `apps/server/app/modules/auth/router.py`
- `apps/server/app/core/redis.py`

**测试：** 验证 refresh 后复用旧 refresh token 返回 401

---

### 1.4 强制首次登录修改密码

**优先级：** P0 | **工作量：** 6h | **风险：** MEDIUM

**方案：**
- Admin 和 User 模型新增 `must_change_password: bool = False` 字段
- Alembic 生成迁移
- 管理员创建用户时设置 `must_change_password = True`，使用默认密码
- 登录后检查该标记，响应头添加 `X-Password-Change-Required: true`
- 前端检测该头并强制跳转密码修改页

**修改文件：**
- `apps/server/app/models/admin.py`
- `apps/server/app/models/user.py`
- `apps/server/app/modules/auth/router.py`
- `apps/server/app/common/auth_unified.py`
- `apps/server/migrations/versions/`（新迁移）

---

### 1.5 Rate Limiting 默认启用

**优先级：** P0 | **工作量：** 2h | **风险：** LOW

**现状：** `.env.example` 中 `RATE_LIMIT_ENABLED=false`，但 `config.py` 默认为 `True`。

**方案：**
- `.env.example` 改为 `RATE_LIMIT_ENABLED=true`，添加注释说明
- `main.py` 启动时检测：若 `ENVIRONMENT=production` 且 `RATE_LIMIT_ENABLED=false` 则输出警告日志
- 租户更新端点添加速率限制值范围校验（min 10, max 10000 RPM）

**修改文件：**
- `apps/server/.env.example`
- `apps/server/app/main.py`

---

### 1.6 CI 安全扫描

**优先级：** P0 | **工作量：** 4h | **风险：** LOW

**方案：**
- `test.yml` 新增 `security-scan` job：`pip-audit` 扫描 Python 依赖
- 新建 `.github/workflows/security.yml`：Trivy Docker 镜像扫描
- 新建 `.github/dependabot.yml`：pip/npm/github-actions 生态每周自动更新

**新建文件：**
- `.github/dependabot.yml`
- `.github/workflows/security.yml`

**修改文件：**
- `.github/workflows/test.yml`（新增 security-scan job）
- `.github/workflows/build-server.yml`（新增 Trivy 扫描步骤）

---

### 1.7 Dockerfile 加固

**优先级：** P0 | **工作量：** 2h | **风险：** LOW

**方案：**
- 添加非 root 用户并切换
- 添加 `HEALTHCHECK` 指令（使用 `/health` 端点）
- 精确锁定 Python 版本
- 新建 `.dockerignore` 排除 tests、__pycache__、.env、.git

**修改文件：**
- `apps/server/Dockerfile`

**新建文件：**
- `apps/server/.dockerignore`

---

## Phase 2 — P1: 可观测性与监控（24-30 小时）

### 2.1 Prometheus 指标端点

**优先级：** P1 | **工作量：** 8h | **风险：** LOW

**现状：** `prometheus_client` 已是依赖（用于通知子系统），但无 `/metrics` 端点。

**方案：** 创建 `PrometheusMetricsMiddleware`：
- `http_requests_total` 计数器（method/path/status_code/tenant_id）
- `http_request_duration_seconds` 直方图
- `http_requests_in_flight` 仪表
- 新增 `/metrics` 端点，docker-compose 暴露端口

**新建文件：**
- `apps/server/app/middleware/prometheus_metrics.py`

**修改文件：**
- `apps/server/app/main.py`
- `docker-compose.yml`
- `apps/server/Dockerfile`

---

### 2.2 结构化日志增强

**优先级：** P1 | **工作量：** 6h | **风险：** LOW

**方案：**
- `RequestLogMiddleware` 增加结构化字段：trace_id、tenant_id、user_id、duration_ms
- 确保 trace_id 从 `X-Request-ID` 传播
- `JsonFormatter` 包含请求上下文字段
- `.env.example` 生产默认 `LOG_JSON_FORMAT=true`

**修改文件：**
- `apps/server/app/core/logging.py`
- `apps/server/app/middleware/request_log.py`
- `apps/server/.env.example`

---

### 2.3 健康检查增强

**优先级：** P1 | **工作量：** 4h | **风险：** LOW

**方案：**
- `/health/detailed` 增加：Celery 状态、Redis 内存、DB 连接池统计、磁盘用量、运行时间
- 新增 `/health/live`（存活探针）和 `/health/ready`（就绪探针）
- 结构化 JSON 输出，兼容 Kubernetes 探针格式

**修改文件：**
- `apps/server/app/main.py`

---

### 2.4 Grafana + Prometheus 监控栈

**优先级：** P1 | **工作量：** 4h | **风险：** LOW

**方案：** 创建 `docker-compose.monitoring.yml` 覆盖文件：
- Prometheus 抓取 `/metrics` 端点
- Grafana 预配置仪表盘（API 请求率/延迟、错误率、通知发送率、Celery 指标）

**新建文件：**
- `docker-compose.monitoring.yml`
- `monitoring/prometheus.yml`
- `monitoring/grafana/dashboards/hospital-api.json`

---

### 2.5 Sentry APM（可选）

**优先级：** P1 | **工作量：** 2h | **风险：** LOW

**方案：** 添加 `sentry-sdk[fastapi]` 依赖，lifespan 中初始化，自动捕获异常和性能追踪。

**修改文件：**
- `apps/server/requirements.txt`
- `apps/server/app/core/config.py`
- `apps/server/app/main.py`

---

## Phase 3 — P1/P2: API 版本控制与 CI/CD（16-20 小时）

### 3.1 API 版本控制与废弃机制

**优先级：** P1 | **工作量：** 8h | **风险：** MEDIUM

**方案：**
- 新建 `DeprecationMiddleware`：废弃端点添加 `Deprecation: true` 和 `Sunset: <date>` 响应头
- `RouterRegistration` 新增 `deprecated` 和 `sunset_date` 可选字段
- `build_api_router()` 将废弃模块路由到单独的 `deprecated_router`
- 新建 `docs/API_VERSIONING.md` 文档化版本策略

**新建文件：**
- `apps/server/app/middleware/deprecation.py`
- `docs/API_VERSIONING.md`

**修改文件：**
- `apps/server/app/api/v1/__init__.py`
- `apps/server/app/main.py`

---

### 3.2 启用部署工作流自动触发

**优先级：** P1 | **工作量：** 3h | **风险：** LOW

**方案：**
- 取消注释 `build-server.yml`、`build-frontend.yml`、`deploy-admin.yml` 的 push 触发器
- 添加路径过滤器（仅对应变更触发）
- 配置 GitHub Environments 保护规则（生产部署需审批）
- develop 分支部署到 staging，main 分支部署到 production

**修改文件：**
- `.github/workflows/build-server.yml`
- `.github/workflows/build-frontend.yml`
- `.github/workflows/deploy-admin.yml`

---

### 3.3 Dependabot 配置

**优先级：** P2 | **工作量：** 2h | **风险：** LOW

**新建文件：**
- `.github/dependabot.yml`

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/apps/server"
    schedule: { interval: "weekly" }
    open-pull-requests-limit: 10
  - package-ecosystem: "npm"
    directory: "/"
    schedule: { interval: "weekly" }
    open-pull-requests-limit: 10
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule: { interval: "weekly" }
```

---

## Phase 4 — P2: 代码质量（8-12 小时）

### 4.1 Ruff 配置

**优先级：** P2 | **工作量：** 3h | **风险：** LOW

**方案：**
- 新建 `apps/server/ruff.toml`：启用 E/F/I/UP/B/S/AS/SIM 规则集，行宽 120，排除 migrations
- `test.yml` 中移除 `|| true`，`continue-on-error` 改为 `false`
- 添加 `ruff format` 检查

**新建文件：**
- `apps/server/ruff.toml`

**修改文件：**
- `.github/workflows/test.yml`

---

### 4.2 废弃 Hook 清理

**优先级：** P2 | **工作量：** 2h | **风险：** LOW

**方案：** 审计 `useUniqueValidation` 引用，替换为推荐方式。使用 ruff UP 规则集扫描其他废弃模式。

---

### 4.3 生产环境加固

**优先级：** P2 | **工作量：** 3h | **风险：** LOW

**方案：**
- `main.py` 启动校验：生产环境下 SECRET_KEY 非默认值、DATABASE_URL 非 localhost、DEBUG=False、RATE_LIMIT_ENABLED=True
- 新增 `/.well-known/security.txt` 端点
- 添加 GZip 响应压缩中间件

**修改文件：**
- `apps/server/app/main.py`

---

### 4.4 依赖版本锁定

**优先级：** P2 | **工作量：** 2h | **风险：** LOW

**方案：** `requirements.txt` 中 `>=` 改为 `==` 精确锁定。`requirements-dev.txt` 添加 `pip-audit`。

**修改文件：**
- `apps/server/requirements.txt`
- `apps/server/requirements-dev.txt`

---

## 工作量汇总

| 阶段 | 优先级 | 项目数 | 预估工时 | 累计 |
|------|--------|--------|----------|------|
| Phase 1: 关键安全 | P0 | 7 | 28-34h | 28-34h |
| Phase 2: 可观测性 | P1 | 5 | 24-30h | 52-64h |
| Phase 3: 版本控制/CI | P1/P2 | 3 | 16-20h | 68-84h |
| Phase 4: 代码质量 | P2 | 4 | 8-12h | 76-96h |
| **合计** | | **19** | **76-96h** | |

---

## 依赖关系图

```
Phase 1（内部无依赖）:
  1.1 Token 黑名单 ──┐
  1.7 Docker 加固     │ 独立
  1.6 CI 安全扫描     │ 独立
  1.2 安全头          │ 独立
  1.5 限流默认启用    │ 独立
  1.3 Refresh 轮换 ───┘ 依赖 1.1 黑名单基础设施
  1.4 密码修改         独立，但受益于 1.1

Phase 2（依赖 Phase 1 完成）:
  2.1 Prometheus ──── 2.3 健康仪表盘（使用指标）
  2.1 Prometheus ──── 2.4 Grafana（使用指标）
  2.2 结构化日志     独立
  2.5 Sentry        独立

Phase 3（独立于 Phase 2）:
  3.1 API 版本控制   独立
  3.2 部署自动触发   独立
  3.3 Dependabot     独立

Phase 4（Phase 1 之后）:
  4.1 Ruff 配置      独立
  4.2 废弃 Hook      独立
  4.3 生产加固       依赖 1.4
  4.4 依赖锁定       独立
```

---

## 风险评估

| 项目 | 风险 | 缓解措施 |
|------|------|----------|
| 1.1 Token 黑名单 | LOW | 仅增加检查，不影响有效 token |
| 1.2 安全头 | LOW | 纯增量响应头 |
| 1.3 Refresh 轮换 | MEDIUM | 改变 token 生命周期；前端需处理 401。需协调前端更新 |
| 1.4 密码修改 | MEDIUM | 新增 DB 列 + 迁移；前端需重定向 |
| 1.5 限流默认 | LOW | 仅修改示例文件 |
| 1.6 CI 扫描 | LOW | 增量 CI 步骤 |
| 1.7 Docker 加固 | LOW | 标准安全实践 |
| 2.1-2.5 可观测性 | LOW | 增量中间件和端点 |
| 3.1 API 版本控制 | MEDIUM | 改变路由结构；需仔细测试 |
| 3.2 部署触发 | LOW | 恢复此前可用的功能 |
| 3.3-4.4 代码质量 | LOW | 仅工具和配置变更 |
