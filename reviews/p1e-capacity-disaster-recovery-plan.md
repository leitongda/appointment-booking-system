# P1-E: 容量压测+灾备评估方案

> 状态：待审批
> 日期：2026-06-30
> 优先级：P1（Critic🚨关键，SaaS 医疗系统致命盲区）

---

## 1. 问题陈述

**现状**（R1/R2 调研）：
- 压测：`locustfile.py` 默认仅 50 用户，无 CI 容量门禁
- 灾备：仅有 `/backup` JSON 导出导入（应用层 dump），无数据库级备份
- 一致性：双连接池（异步 + Celery 同步），无跨池事务/崩溃恢复验证
- 备份：无 PITR/RPO/RTO，无 streaming replication

**风险**：
- 高并发挂号场景（如大促/集中挂号）可能耗尽连接池
- 数据库故障无法恢复（仅应用层 JSON dump，无增量备份）
- 多租户场景下，单租户故障可能影响全局

---

## 2. 评估范围

### 2.1 容量评估

| 指标 | 当前值 | 目标值 | 来源 |
|---|---|---|---|
| 压测用户数 | 50 | 待定 | `locustfile.py` |
| DB 连接池（异步） | pool_size=10, overflow=20 | 待定 | `db/session.py:15-23` |
| DB 连接池（同步） | pool_size=5, overflow=10 | 待定 | `db/session.py:47-55` |
| 限流 | 300 rpm / 50 rps | 已配置 | `middleware/rate_limit.py` |
| Celery 任务超时 | 软 300s / 硬 600s | 已配置 | `celery_app.py:42-43` |

### 2.2 灾备评估

| 维度 | 当前状态 | 缺失 |
|---|---|---|
| 数据库备份 | 应用层 JSON dump | 无 pg_dump / WAL 归档 / PITR |
| 复制 | 无 | 无 streaming replication |
| RPO | 未知（无增量备份） | 需定义 |
| RTO | 未知（无恢复演练） | 需定义 |
| 容器 | Docker read_only + no-new-privileges | 已配置 |

### 2.3 一致性评估

| 场景 | 当前状态 | 风险 |
|---|---|---|
| 跨池事务 | 异步 + Celery 同步双池 | 可能出现脏读 |
| 租户隔离 | 中间件级（Header/子域名） | 崩溃恢复时是否泄露 |
| 迁移 | 147 个 Alembic 迁移 | 回滚能力未知 |

---

## 3. 执行计划

### 阶段 1：容量压测（8h）
- [ ] 更新 `locustfile.py`：模拟真实场景（挂号/签到/叫号/取消）
- [ ] 压测目标：100/500/1000 并发用户
- [ ] 记录：响应时间、错误率、连接池使用率、CPU/内存
- [ ] 识别瓶颈：DB 连接 / API 响应 / Celery 任务

### 阶段 2：灾备调研（4h）
- [ ] 调研 PostgreSQL 备份方案（pg_dump / WAL 归档 / pgBackRest）
- [ ] 调研 RPO/RTO 目标（医疗行业标准：RPO<1h, RTO<4h）
- [ ] 调研 Docker 部署的备份策略（宝塔 + Docker 混合部署）

### 阶段 3：一致性验证（4h）
- [ ] 验证跨池事务场景（异步写 + Celery 读）
- [ ] 验证租户隔离在崩溃恢复时的表现
- [ ] 验证 Alembic 迁移回滚能力

### 阶段 4：方案输出（4h）
- [ ] 输出容量评估报告（瓶颈 + 建议）
- [ ] 输出灾备方案（备份策略 + RPO/RTO 目标）
- [ ] 输出一致性改进建议
- [ ] CI 容量门禁建议

**总成本：约 20h**

---

## 4. 待确认问题

1. **压测目标**：预期峰值并发用户数？（100/500/1000？）
2. **RPO/RTO 目标**：医疗行业标准 RPO<1h, RTO<4h，是否接受？
3. **备份策略**：是否接入 PostgreSQL WAL 归档？（需 DBA 支持）
4. **CI 门禁**：是否在 CI 中加容量压测门禁？（如响应时间 >500ms 则 fail）

---

## 5. 交付物

- `reviews/p1e-capacity-report.md`：容量压测报告（瓶颈 + 建议）
- `reviews/p1e-disaster-recovery-plan.md`：灾备方案（备份策略 + RPO/RTO）
- `reviews/p1e-consistency-report.md`：一致性验证报告
- CI 配置更新：容量门禁（可选）
