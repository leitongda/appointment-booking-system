# Celery 异步任务服务

Celery 用于处理系统中的异步任务，包括：
- 操作日志记录
- 用户行为日志
- 预约提醒通知
- 黑名单自动解禁
- 排班自动生成
- 数据清理任务

## 前置条件

确保 Redis 服务已启动：
```bash
redis-cli ping
# 应返回 PONG
```

## 启动命令

```bash
# 进入服务端目录
cd apps/server

# 前台启动（可以看到实时日志，Ctrl+C 停止）
celery -A app.celery_app worker --loglevel=info

# 后台启动（守护进程模式）
celery -A app.celery_app worker --loglevel=info --detach \
  --pidfile=/tmp/celery_worker.pid \
  --logfile=/tmp/celery_worker.log

# 启动定时任务调度器（Beat）- 用于处理定时任务
celery -A app.celery_app beat --loglevel=info --detach \
  --pidfile=/tmp/celery_beat.pid \
  --logfile=/tmp/celery_beat.log
```

## 关闭命令

```bash
# 方式1：使用 PID 文件关闭（后台模式启动时）
kill $(cat /tmp/celery_worker.pid)
kill $(cat /tmp/celery_beat.pid)

# 方式2：通过进程名关闭所有 Celery 进程
pkill -f "celery -A app.celery_app"

# 方式3：优雅关闭（等待当前任务完成）
pkill -TERM -f "celery -A app.celery_app"

# 方式4：强制关闭
pkill -9 -f "celery -A app.celery_app"
```

## 查看状态

```bash
# 查看是否在运行
ps aux | grep "celery" | grep -v grep

# 查看 Worker 状态
celery -A app.celery_app inspect active

# 查看队列中的任务数量
redis-cli LLEN celery
```

## 任务列表

| 任务名称 | 说明 | 队列 |
|---------|------|------|
| `operation_log_task.save_operation_log` | 保存操作日志 | default |
| `behavior_log_task.save_behavior_log` | 保存用户行为日志 | default |
| `notification_task.send_appointment_reminder` | 发送预约提醒 | notification |
| `blacklist_task.auto_release_blacklist_task` | 黑名单自动解禁 | scheduled |
| `blacklist_task.mark_no_show_appointments_task` | 爽约自动标记 | scheduled |
| `schedule_task.auto_generate_schedules_task` | 排班自动生成 | scheduled |
| `cleanup_task.cleanup_expired_data_task` | 数据清理 | scheduled |
| `wechat_task.refresh_wechat_token_task` | 微信 Token 刷新 | default |

## 定时任务配置

定时任务在 `app/celery_app.py` 中配置：

| 任务 | 执行时间 |
|------|---------|
| 黑名单自动解禁 | 每小时整点 |
| 预约提醒 | 每 30 分钟 |
| 爽约自动检测 | 每 30 分钟 |
| 排班自动生成 | 每天凌晨 2:00 |
| 微信 Token 刷新 | 每 2 小时 |
| 数据清理 | 每天凌晨 3:00 |

## 常见问题

### 1. 操作日志查询不到数据

**原因：** Celery Worker 没有启动，操作日志任务无法执行。

**解决：** 启动 Celery Worker：
```bash
cd apps/server
celery -A app.celery_app worker --loglevel=info
```

### 2. Redis 连接失败

**原因：** Redis 服务未启动或配置错误。

**解决：**
```bash
# 检查 Redis 是否运行
redis-cli ping

# 启动 Redis（macOS）
brew services start redis

# 检查 .env 中的 REDIS_URL 配置
```

### 3. 任务堆积

**原因：** Worker 处理速度跟不上任务产生速度。

**解决：** 增加 Worker 并发数：
```bash
celery -A app.celery_app worker --loglevel=info --concurrency=16
```

## 生产环境部署

### 使用 Supervisor 管理

创建 `/etc/supervisor/conf.d/celery.conf`：

```ini
[program:celery-worker]
command=celery -A app.celery_app worker --loglevel=info
directory=/path/to/apps/server
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/worker.log
stderr_logfile=/var/log/celery/worker_error.log

[program:celery-beat]
command=celery -A app.celery_app beat --loglevel=info
directory=/path/to/apps/server
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/beat.log
stderr_logfile=/var/log/celery/beat_error.log
```

### 使用 Docker Compose

在 `docker-compose.yml` 中添加：

```yaml
celery-worker:
  build: ./apps/server
  command: celery -A app.celery_app worker --loglevel=info
  depends_on:
    - redis
    - postgres
  env_file:
    - ./apps/server/.env

celery-beat:
  build: ./apps/server
  command: celery -A app.celery_app beat --loglevel=info
  depends_on:
    - redis
    - postgres
  env_file:
    - ./apps/server/.env
```

