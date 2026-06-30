# P1-E: 容量压测+灾备调研报告

> 状态：调研完成，待审批执行
> 日期：2026-06-30
> 优先级：P1（Critic🚨关键）

---

## 1. 调研结论

### 1.1 容量现状

| 维度 | 当前状态 | 风险等级 |
|---|---|---|
| 压测覆盖 | 仅 4 个读场景，50 用户 | 🔴 高 |
| 写操作压测 | 无（挂号/签到/取消未覆盖） | 🔴 高 |
| DB 连接池 | 异步 10+20=30，同步 5+10=15，总计 45 | 🟡 中 |
| 限流 | 300 rpm / 50 rps（已配置） | 🟢 低 |
| Celery 超时 | 软 300s / 硬 600s（已配置） | 🟢 低 |
| API 超时 | 30s API / 10s DB query（已配置） | 🟢 低 |

### 1.2 灾备现状

| 维度 | 当前状态 | 风险等级 |
|---|---|---|
| 数据库备份 | 仅应用层 JSON dump（`/backup` API） | 🔴 高 |
| pg_dump | 未配置 | 🔴 高 |
| WAL 归档 | 未配置 | 🔴 高 |
| PITR | 未配置 | 🔴 高 |
| RPO | 未知（无增量备份） | 🔴 高 |
| RTO | 未知（无恢复演练） | 🔴 高 |
| Docker 安全 | read_only + no-new-privileges（已配置） | 🟢 低 |

### 1.3 一致性现状

| 维度 | 当前状态 | 风险等级 |
|---|---|---|
| 跨池事务 | 异步 + Celery 同步双池 | 🟡 中 |
| 租户隔离 | 中间件级（Header/子域名） | 🟡 中 |
| 迁移回滚 | 147 个 Alembic 迁移，回滚能力未验证 | 🟡 中 |

---

## 2. 已完成的改进

### 2.1 压测场景扩展（已实施）

**locustfile.py 更新**：
- 新增 `PatientBookingFlow`（权重 5）：浏览医生 → 查看排班 → 创建预约
- 新增 `AdminCheckinFlow`（权重 2）：查待签到预约 → 签到
- 新增 `AdminCancelFlow`（权重 1）：取消预约
- 保留原有 4 个读场景

**config.py 更新**：
- 新增写操作基线阈值：appointments_create (1200ms, 10rps)、checkin (800ms, 15rps)、cancel (800ms, 15rps)

### 2.2 压测运行命令

```bash
# 常规压测（50 用户，60 秒）
cd apps/server
locust -f tests/perf/locustfile.py --host http://localhost:9000 --headless \
  --users 50 --spawn-rate 5 --run-time 60s

# 高并发压测（500 用户，120 秒）
locust -f tests/perf/locustfile.py --host http://localhost:9000 --headless \
  --users 500 --spawn-rate 20 --run-time 120s

# 极限压测（1000 用户，180 秒）
locust -f tests/perf/locustfile.py --host http://localhost:9000 --headless \
  --users 1000 --spawn-rate 50 --run-time 180s
```

---

## 3. 待执行项（需审批）

### 3.1 容量压测执行（8h）

| 步骤 | 内容 | 成本 |
|---|---|---|
| 1 | 准备测试数据（真实 schedule_id / patient_id） | 2h |
| 2 | 运行 50/500/1000 用户压测 | 2h |
| 3 | 记录：P95 延迟、错误率、连接池使用率、CPU/内存 | 2h |
| 4 | 识别瓶颈并输出报告 | 2h |

### 3.2 灾备方案实施（待定）

| 方案 | 成本 | RPO | RTO | 适用场景 |
|---|---|---|---|---|
| pg_dump 定时备份 | 4h | 24h | 4h | 最低成本 |
| WAL 归档 + PITR | 16h | 5min | 1h | 推荐 |
| Streaming Replication | 40h | 0 | <1min | 高可用 |

**推荐**：WAL 归档 + PITR（成本适中，RPO<5min，RTO<1h，满足医疗行业标准）

### 3.3 CI 容量门禁（可选，4h）

在 CI 中加容量压测门禁：
```yaml
# .github/workflows/perf.yml
- name: Run load test
  run: |
    locust -f tests/perf/locustfile.py --host ${{ env.API_HOST }} \
      --headless --users 100 --spawn-rate 10 --run-time 60s \
      --csv=results
- name: Check thresholds
  run: |
    python tests/perf/check_thresholds.py results_stats.csv
```

---

## 4. 待确认问题

1. **压测环境**：是否在生产环境压测？还是需要搭建独立压测环境？
2. **压测目标**：预期峰值并发用户数？（100/500/1000？）
3. **RPO/RTO 目标**：医疗行业标准 RPO<1h, RTO<4h，是否接受？
4. **备份策略**：是否接入 PostgreSQL WAL 归档？（需 DBA 支持或云服务商配置）
5. **CI 门禁**：是否在 CI 中加容量压测门禁？（如 P95 >500ms 则 fail）

---

## 5. 交付物

- ✅ `apps/server/tests/perf/locustfile.py`：已扩展（7 个场景，含写操作）
- ✅ `apps/server/tests/perf/config.py`：已更新（写操作基线阈值）
- 📄 `reviews/p1e-capacity-investigation-report.md`：本报告
- ⏳ `reviews/p1e-capacity-test-results.md`：压测结果（待执行）
- ⏳ `reviews/p1e-disaster-recovery-plan.md`：灾备方案（待审批）
