# 支付上线检查清单 + 执行顺序

> 版本: 1.0 | 更新: 2026-04-16
> 范围: 待支付 -> 支付回调 -> 退款 -> 后台操作 -> 历史修复

---

## 一、上线前环境检查 (前置条件)

按顺序执行，全部通过后才可进入支付流程。

### 1.1 基础设施

| # | 检查项 | 验证方式 | 状态 |
|---|--------|----------|------|
| 1 | PostgreSQL 16 运行正常 | `docker-compose ps postgres` 或 `pg_isready` | |
| 2 | Redis 7 运行正常 | `docker-compose ps redis` 或 `redis-cli ping` | |
| 3 | Celery worker 已启动 | `celery -A app.celery_app inspect active` | |
| 4 | Celery beat 已启动 (支付超时任务依赖) | `celery -A app.celery_app inspect scheduled` | |

### 1.2 环境变量

| # | 变量 | 说明 | 状态 |
|---|------|------|------|
| 1 | `DATABASE_URL` | PostgreSQL 异步连接串 | |
| 2 | `REDIS_URL` | Redis 连接串 | |
| 3 | `SECRET_KEY` | JWT 签名密钥 | |
| 4 | `WX_API_V3_KEY` | 微信支付 API v3 密钥 (被 PaymentProfile 的 `api_v3_key_ref` 引用) | |
| 5 | `WX_PRIVATE_KEY` | 商户私钥 PEM 内容 (被 `private_key_ref` 引用) | |

验证: `env | grep -E 'DATABASE_URL|REDIS_URL|SECRET_KEY|WX_API_V3_KEY|WX_PRIVATE_KEY'`

### 1.3 数据库配置 (PaymentProfile / PaymentRoute)

```sql
-- 1) 检查租户是否已创建 PaymentProfile
SELECT id, tenant_id, name, code, mode, app_id, mch_id,
       is_default, status, notify_url, cert_serial_no,
       api_v3_key_ref, private_key_ref
FROM payment_profiles
WHERE tenant_id = '<tenant_id>';

-- 预期:
--   mode = 'direct' 或 'service_provider'
--   status = 1 (启用)
--   notify_url = 'https://<域名>/api/v1/payments/wechat/callback' (必须 HTTPS、外网可达)
--   api_v3_key_ref = 'env:WX_API_V3_KEY' (env: 前缀指向环境变量)
--   private_key_ref = 'env:WX_PRIVATE_KEY' 或直接 PEM
--   is_default = true (至少一个默认配置)
```

```sql
-- 2) 如需门店级路由，检查 PaymentRoute
SELECT id, tenant_id, store_id, miniapp_instance_id,
       payment_profile_id, priority, status
FROM payment_routes
WHERE tenant_id = '<tenant_id>';

-- 预期: status = 1, priority 合理
```

```sql
-- 3) 检查迁移是否执行
SELECT * FROM alembic_version;
-- 确认版本号 >= 053 (包含 refund_records 表)
```

### 1.4 网络可达性

| # | 检查项 | 验证方式 | 状态 |
|---|--------|----------|------|
| 1 | 微信支付回调 URL 外网可达 | `curl -I https://<域名>/api/v1/payments/wechat/callback` 返回非网络错误 | |
| 2 | 退款回调 URL 外网可达 | `curl -I https://<域名>/api/v1/refunds/wechat/callback` | |
| 3 | 服务器出网可访问微信 API | `curl https://api.mch.weixin.qq.com` 非超时 | |

### 1.5 微信商户平台配置

| # | 检查项 | 说明 | 状态 |
|---|--------|------|------|
| 1 | 商户号已开通 JSAPI 支付 | 微信商户后台 -> 产品中心 | |
| 2 | API v3 密钥已设置 | 账户中心 -> API安全 | |
| 3 | 商户 API 证书已申请 | 下载后 cert_serial_no 填入 PaymentProfile | |
| 4 | 回调 URL 已在商户后台白名单 (如需) | 部分商户号有此限制 | |
| 5 | 关联 AppID 已绑定 | 关联小程序的 AppID | |

---

## 二、支付链路执行顺序 (核心流程)

### 流程 A: 创建预约 + 待支付

```
用户选择排班 -> 提交预约 -> 系统判断是否需要支付
```

**关键代码路径:**

```
POST /api/v1/appointments
  -> router_booking.py: create_appointment()
  -> service_booking.py: AppointmentBookingService.create()
      -> _get_consultation_fee()         # 获取问诊费 (医生级 > 门店级 > 全局默认)
      -> status = 0 (待支付) 或 1 (已确认, fee=0)
      -> _prepare_payment_params()       # 如需支付，调用 PaymentService
          -> PaymentConfigResolver.resolve()  # 解析支付配置
          -> WeChatPayService.create_order()  # 调用微信统一下单
          -> 返回小程序支付参数 (timeStamp, nonceStr, package, signType, paySign)
```

**检查清单:**

| # | 检查项 | 验证方式 | 状态 |
|---|--------|----------|------|
| 1 | 问诊费金额正确 | 创建预约后查 `appointments.payment_amount` | |
| 2 | 支付配置解析成功 | 日志无 "无法获取支付配置" 错误 | |
| 3 | 微信统一下单成功 | 返回 `prepay_id` 非空 | |
| 4 | 预约状态 = 0 (待支付) | `SELECT status FROM appointments WHERE id = ?` | |
| 5 | 支付快照已写入 | `payment_profile_id`, `payment_mch_id`, `payment_notify_url` 等字段非空 | |
| 6 | 号源已扣减 | `schedules.booked_slots` +1 | |

**支付配置解析优先级 (ConfigResolver):**

```
1. appointment.payment_profile_id (预约快照，最高优先)
2. miniapp_instance_id (请求参数传入)
3. appointment.payment_miniapp_instance_id (预约关联的小程序实例)
4. schedule.store_id -> PaymentRoute (门店路由)
5. PaymentProfile.is_default = true (租户默认)
```

### 流程 B: 小程序端调起支付

```
前端拿到支付参数 -> wx.requestPayment() -> 用户完成支付 -> 微信回调后端
```

**前端关键参数:**

```javascript
// 小程序端调用
wx.requestPayment({
  timeStamp: response.time_stamp,
  nonceStr: response.nonce_str,
  package: response.package,       // "prepay_id=xxx"
  signType: "RSA",
  paySign: response.pay_sign,
  success(res) { /* 跳转结果页 */ },
  fail(err) { /* 提示支付失败，保留待支付状态 */ },
});
```

**检查清单:**

| # | 检查项 | 验证方式 | 状态 |
|---|--------|----------|------|
| 1 | AppID 与 PaymentProfile 中的 app_id 一致 | 前端 config 中的 appId | |
| 2 | 签名类型 = RSA | signType 字段 | |
| 3 | 支付参数未过期 (prepay_id 有效期 2h) | 及时调起，不缓存 | |

### 流程 C: 微信支付回调

```
微信服务器 -> POST /api/v1/payments/wechat/callback (无需认证)
  -> PaymentService.handle_payment_callback()
      -> 通过 Wechatpay-Serial header 找到 PaymentProfile
      -> WeChatPayService.verify_callback() 验签解密
      -> 解析 out_trade_no 反查预约 (格式: APPT{appointment_id})
      -> 条件更新: status 0 -> 1 (CONFIRMED)
      -> 写入 payment_transaction_id, paid_at
```

**幂等处理:**

```
场景 1: 首次回调，status=0
  -> 条件更新成功，status -> 1 (CONFIRMED)

场景 2: 重复回调，status 已是 1/2/4/5
  -> 幂等成功，补齐缺失的 transaction_id / paid_at

场景 3: 超时后晚到的回调，status=7 (EXPIRED)
  -> 忽略状态变更，不恢复预约 (防止号源二次占用)
  -> 日志警告: "支付成功回调到达时预约已过期"
```

**检查清单:**

| # | 检查项 | 验证方式 | 状态 |
|---|--------|----------|------|
| 1 | 回调 URL 外网可访问 | 微信商户后台 -> API安全 -> 回调测试 | |
| 2 | 验签成功 | 日志无 "验签失败" 错误 | |
| 3 | PaymentProfile 能通过 cert_serial_no 找到 | 回调 header 中的 Wechatpay-Serial 与数据库匹配 | |
| 4 | 预约状态正确更新 0 -> 1 | `SELECT status, payment_transaction_id, paid_at FROM appointments` | |
| 5 | 重复回调不产生错误 | 模拟第二次回调，返回 `{"code": "SUCCESS"}` | |
| 6 | 回调返回格式正确 | 必须返回 `{"code": "SUCCESS", "message": "成功"}`，否则微信会重试 | |

### 流程 D: 支付超时自动取消

```
Celery Beat (每 5 分钟) -> payment.cancel_expired_pending
  -> 扫描所有活跃租户
  -> 查找 status=0 且 created_at < (now - 30min) 的预约
  -> 条件更新 status -> 7 (EXPIRED)
  -> 恢复号源: schedules.booked_slots - 1
```

**关键参数:**
- 超时阈值: `PAYMENT_TIMEOUT_MINUTES = 30`
- 执行频率: 每 5 分钟 (Celery Beat 配置)
- 并发安全: 使用 `WHERE status = 0` 条件更新防止竞态

**检查清单:**

| # | 检查项 | 验证方式 | 状态 |
|---|--------|----------|------|
| 1 | Celery Beat 正常运行 | `celery -A app.celery_app inspect scheduled` | |
| 2 | 超时任务已注册 | 日志中可见 "开始扫描超时未支付预约" | |
| 3 | 超时预约被正确取消 | 创建测试预约，等待 30 分钟后检查状态 | |
| 4 | 号源正确恢复 | 检查 `schedules.booked_slots` 值 | |
| 5 | 条件更新防竞态 | 同一预约不会被取消两次 | |

---

## 三、退款链路

### 流程 E: 管理员发起退款

```
管理员后台 -> POST /api/v1/refunds
  -> router.py: create_refund()
  -> RefundService.create_refund()
      -> 校验预约状态 (1=已预约, 5=已完成)
      -> 校验退款金额 <= 可退金额
      -> 商户一致性检查 (快照中的 mch_id)
      -> 创建 RefundRecord (status=pending)
      -> WeChatPayService.create_refund() 调用微信退款 API
      -> RefundRecord.status -> processing
  -> 微信异步回调 -> POST /api/v1/refunds/wechat/callback
      -> RefundService.process_refund_callback()
      -> 更新 RefundRecord.status -> success/failed
      -> sync_appointment_refund_state() 聚合到 Appointment
```

**退款安全机制:**

```
1. 累计退款校验: sum(已退) + 本次退款 <= payment_amount
2. 商户一致性: 退款必须退到原收款商户 (基于支付快照)
3. 幂等: refund_no 唯一约束
4. 状态保护: terminal status (success/failed) 不会被覆盖
```

**退款状态流转:**

```
pending -> processing -> success
                     -> failed
```

**Appointment 退款状态聚合:**

```
refund_status:
  "none"             -- 未退款
  "partial_refunded" -- 部分退款 (累计 < payment_amount)
  "refunded"         -- 全额退款 (累计 >= payment_amount)
```

**检查清单:**

| # | 检查项 | 验证方式 | 状态 |
|---|--------|----------|------|
| 1 | 权限校验: 需要 `appointment:refund` 权限 | 用无权限账号测试，应返回 403 | |
| 2 | 管理员门店访问控制 | 管理员只能退所属门店的预约 | |
| 3 | 退款金额校验 | 超额退款应被拒绝 | |
| 4 | 累计退款正确 | 多次部分退款后总额不超标 | |
| 5 | 微信退款 API 调用成功 | RefundRecord.wx_refund_id 非空 | |
| 6 | 退款回调正确更新状态 | 检查 RefundRecord.status = success | |
| 7 | Appointment 退款状态聚合正确 | refund_status 和 refund_amount 同步更新 | |
| 8 | transaction_id 优先使用 | 微信退款优先用 transaction_id，无则降级 out_trade_no | |

### 流程 F: 查询可退款金额

```
GET /api/v1/refunds/refundable-amount/{appointment_id}
  -> RefundService.get_refundable_amount()
  -> 返回: { payment_amount, refunded_amount, refundable_amount }
```

---

## 四、后台管理操作

### 流程 G: 预约列表 + 支付状态查看

```
GET /api/v1/payments/orders/{appointment_id}
  -> 返回: status, payment_amount, payment_transaction_id, paid_at,
           refund_status, refund_amount
```

**权限:**
- 患者: 只能查看自己的预约 (`_ensure_user_owns_appointment`)
- 管理员: 需要 `appointment:detail` 权限 + 门店访问控制

### 流程 H: 退款记录查询

```
GET /api/v1/refunds?appointment_id=xxx       # 按预约筛选
GET /api/v1/refunds?status=success           # 按状态筛选
GET /api/v1/refunds/{refund_id}              # 退款详情
```

**权限:** 需要 `appointment:refund` 权限

---

## 五、历史数据修复

### 场景 I: RefundRecord 缺失支付引用

**问题:** 早期退款记录可能缺少 `out_trade_no` 或 `wx_transaction_id`，导致无法关联微信侧。

**修复工具:**

```python
# RefundService.backfill_refund_payment_references()
# 批量修复: 根据 appointment_id 反查 Appointment 补全 RefundRecord 的支付引用

# 调用方式 (管理脚本或 shell):
from app.modules.refunds.service import RefundService
service = RefundService(db)
await service.backfill_refund_payment_references()
```

**单条修复:**

```python
# RefundService.ensure_refund_payment_reference(refund_record)
# 从关联的 Appointment 补全 out_trade_no 和 wx_transaction_id
```

### 场景 J: Appointment 缺少支付快照

**问题:** 预约创建时未保存支付配置快照 (`payment_profile_id`, `payment_mch_id` 等)。

**修复 SQL:**

```sql
-- 检查缺少快照的已支付预约
SELECT id, appointment_no, status, payment_amount, payment_profile_id
FROM appointments
WHERE status IN (1, 2, 4, 5)
  AND payment_amount > 0
  AND payment_profile_id IS NULL;

-- 修复: 根据租户默认 PaymentProfile 补全 (需逐条确认)
UPDATE appointments
SET payment_profile_id = '<default_profile_id>',
    payment_mode = 'direct',
    payment_mch_id = '<mch_id>',
    payment_app_id = '<app_id>'
WHERE id = '<appointment_id>'
  AND payment_profile_id IS NULL;
```

### 场景 K: 回调丢失导致支付成功但状态未更新

**问题:** 微信回调网络异常，用户已付款但预约状态仍为 0。

**修复步骤:**

```
1. 登录微信商户后台，查到对应的 transaction_id 和 out_trade_no
2. out_trade_no 格式: APPT{appointment_id}，可反查预约
3. 手动更新:
   UPDATE appointments
   SET status = 1,
       payment_transaction_id = '<transaction_id>',
       paid_at = NOW()
   WHERE id = '<appointment_id>'
     AND status = 0;
4. 如果已超时变为 7 (EXPIRED)，需同时恢复号源:
   UPDATE schedules
   SET booked_slots = booked_slots + 1
   WHERE id = '<schedule_id>';
```

**主动查询工具 (代码层面):**

```python
# 可通过 WeChatPayService.query_order() 主动查询支付状态
# out_trade_no = f"APPT{appointment_id}"
wx_service = WeChatPayService(payment_profile)
result = await wx_service.query_order(out_trade_no=out_trade_no)
# result.trade_state: SUCCESS / NOTPAY / CLOSED / REFUND
```

---

## 六、上线验证测试用例

按以下顺序执行端到端验证:

### 测试 1: 免费预约 (问诊费 = 0)

```
前置: 医生/门店/全局问诊费均设为 0
步骤: 创建预约
预期: status = 1 (直接确认)，无需支付
```

### 测试 2: 付费预约 - 完整流程

```
前置: 设置问诊费 > 0
步骤:
  1. 创建预约 -> 返回 payment_required=true + 支付参数
  2. 小程序完成支付
  3. 等待回调
  4. 查询预约状态
预期:
  - 预约状态 0 -> 1
  - payment_transaction_id 非空
  - paid_at 非空
  - 支付快照字段完整
```

### 测试 3: 支付超时

```
前置: 设置问诊费 > 0
步骤:
  1. 创建预约 (不支付)
  2. 等待 30 分钟 + Celery Beat 周期
预期:
  - 预约状态 0 -> 7 (EXPIRED)
  - 号源恢复 (booked_slots - 1)
  - cancel_reason = "支付超时自动取消"
```

### 测试 4: 超时后补支付

```
前置: 测试 3 完成后
步骤:
  1. 手动对已 EXPIRED 的预约模拟支付回调
预期:
  - 预约状态不恢复 (仍为 7)
  - 日志: "支付成功回调到达时预约已过期"
```

### 测试 5: 全额退款

```
前置: 测试 2 完成
步骤:
  1. 管理员发起全额退款
  2. 等待退款回调
预期:
  - RefundRecord.status = success
  - Appointment.refund_status = refunded
  - Appointment.refund_amount = payment_amount
```

### 测试 6: 部分退款 + 累计超额拦截

```
前置: 测试 2 完成，payment_amount = 100
步骤:
  1. 退款 60 -> 成功
  2. 退款 50 -> 被拒绝 (累计 110 > 100)
预期:
  - 第一次: refund_status = partial_refunded, refund_amount = 60
  - 第二次: 返回错误 "累计退款金额不能超过支付金额"
```

### 测试 7: 权限校验

```
步骤:
  1. 患者尝试创建退款 -> 应被拒绝 (403)
  2. 无 appointment:refund 权限的管理员 -> 应被拒绝 (403)
  3. 管理员查询其他门店的退款 -> 应被拒绝 (403)
```

### 测试 8: 重复回调幂等

```
步骤:
  1. 对已支付预约模拟第二次支付回调
预期:
  - 返回 {"code": "SUCCESS"}
  - 预约状态不变
  - 如缺 transaction_id / paid_at 则补齐
```

---

## 七、监控告警建议

| 指标 | 告警阈值 | 监控方式 |
|------|----------|----------|
| 支付回调验签失败次数 | > 0 立即告警 | 日志 "验签失败" 计数 |
| 超时后收到支付回调 | > 0 告警 | 日志 "支付成功回调到达时预约已过期" |
| 退款失败 | > 0 告警 | RefundRecord.status = failed |
| 待支付预约积压 | > 正常水平 | `SELECT count(*) FROM appointments WHERE status = 0` |
| Celery 任务失败 | > 0 告警 | Celery 事件监控 |
| 微信 API 调用失败 | > 0 告警 | 日志 "微信统一下单失败" / "微信退款调用失败" |

---

## 八、紧急预案

### 支付回调大面积失败

```
1. 检查服务器出网是否正常
2. 检查微信商户平台是否有变更/维护
3. 临时方案: 用 WeChatPayService.query_order() 批量主动查询补单
4. 补单脚本伪代码:
   for appointment in unpaid_appointments:
       result = wx_service.query_order(out_trade_no=f"APPT{appointment.id}")
       if result.trade_state == "SUCCESS":
           appointment.status = 1
           appointment.payment_transaction_id = result.transaction_id
           appointment.paid_at = NOW()
```

### Celery Beat 宕机 (超时任务不执行)

```
1. 重启 Celery Beat
2. 检查积压的超时预约:
   SELECT count(*) FROM appointments
   WHERE status = 0 AND created_at < NOW() - INTERVAL '30 minutes';
3. 如有积压，手动触发任务:
   celery -A app.celery_app call payment.cancel_expired_pending
```

### 微信退款 API 故障

```
1. 退款记录状态停留在 processing
2. 等微信恢复后，用 WeChatPayService.query_refund() 主动查询
3. 根据 query_refund 结果更新 RefundRecord 状态
```

---

## 九、关键代码索引

| 模块 | 文件路径 |
|------|----------|
| 支付配置模型 | `apps/server/app/models/miniapp_platform.py` (PaymentProfile, PaymentRoute) |
| 预约支付快照字段 | `apps/server/app/models/appointment.py` (payment_* 字段) |
| 退款记录模型 | `apps/server/app/models/refund.py` (RefundRecord) |
| 微信支付服务 | `apps/server/app/infrastructure/payments/wechat_pay_service.py` |
| 支付配置解析 | `apps/server/app/infrastructure/payments/config_resolver.py` |
| 支付 Schema | `apps/server/app/infrastructure/payments/schemas.py` |
| 密钥引用解析 | `apps/server/app/common/secret_refs.py` |
| 支付服务 (创建/回调/退款) | `apps/server/app/modules/payments/service.py` |
| 退款服务 | `apps/server/app/modules/refunds/service.py` |
| 支付路由 | `apps/server/app/modules/payments/router.py` |
| 退款路由 | `apps/server/app/modules/refunds/router.py` |
| 预约挂号 (含支付) | `apps/server/app/modules/appointments/service_booking.py` |
| 支付超时任务 | `apps/server/app/tasks/payment_task.py` |
| 预约状态常量 | `apps/server/app/modules/appointments/common.py` |
| 单元测试 (支付退款) | `apps/server/tests/unit/test_payment_refund.py` |
| 单元测试 (超时) | `apps/server/tests/unit/test_payment_timeout.py` |
| 集成测试 (支付端点) | `apps/server/tests/integration/test_payments_router_endpoints.py` |
