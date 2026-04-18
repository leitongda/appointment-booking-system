# 支付与退款生命周期

本文档描述预约挂号系统中支付和退款的完整生命周期，包括状态流转、关键代码路径、金额约定和排障指引。

---

## 一、金额单位约定

| 层 | 单位 | 说明 |
|---|---|---|
| 数据库 (Numeric 10,2) | 元 | appointment.payment_amount, refund_record.refund_amount 等 |
| API 请求/响应 | 元 | 退款请求 refund_amount、支付金额 payment_amount 均为元 |
| WeChat Pay API | 分 | `WeChatPayService` 内部做 `yuan * 100` 转换，调用方无需关心 |
| 前端显示 | 元 | 直接使用 API 返回值，无需额外转换 |

**规则**: 后端统一用元，`WeChatPayService` 是唯一的元→分转换边界。

---

## 二、Merchant Order Number 格式

| 类型 | 格式 | 示例 | 生成位置 |
|------|------|------|---------|
| 支付订单号 | `appointment.appointment_no` | `YY20260418123045A1B2` | `PaymentService._generate_out_trade_no()` |
| 退款单号 | `RF{YYYYMMDDHHMMSS}{6位hex}` | `RF20260416143000A1B2C3` | `RefundService._generate_refund_no()` |

支付创建、支付回调、退款创建、退款回调均复用同一个 `appointment_no` 作为 `out_trade_no`。

---

## 三、支付配置路由优先级

`PaymentConfigResolver.resolve()` 按以下顺序查找:

```
1. appointment snapshot (payment_profile_id 已冻结在预约上)
2. PaymentRoute (store_id 匹配，按 priority DESC)
3. MiniappInstance.default_payment_profile_id
4. Tenant default PaymentProfile (is_default=True)
5. 返回 None → 创建失败
```

每条解析结果携带 `source` 字段用于追溯:
`payment_profile` / `store_route` / `miniapp_instance_default` / `tenant_default`

---

## 四、支付生命周期

### 4.1 状态流转

```
                 ┌─ 免费预约 ──→ CONFIRMED (status=1)
                 │
创建预约 ────────┤
                 │               支付成功回调
                 └─ 付费预约 ──→ PENDING (status=0) ────→ CONFIRMED (status=1)
                                    │
                                    │ 支付超时 (30 min)
                                    └──→ EXPIRED (status=7)
```

说明:
- 运行时主状态收口为 `0/1/2/4/5/6/7/8`
- `WAITING(3)` 不参与当前支付/就诊主流程，按历史死状态处理

### 4.2 创建预约

**入口**: `POST /api/v1/appointments`
**代码**: `modules/appointments/service_booking.py` `AppointmentBookingService.create()`

1. 查询挂号费 (`_get_consultation_fee()`): 医生级 → 门店级 → 全局默认
2. 根据费用分支:
   - **免费** (`fee <= 0`): status 直接设为 `CONFIRMED`，返回 appointment 对象
   - **付费** (`fee > 0`): status 设为 `PENDING`，冻结支付快照，调用 `_prepare_payment_params()`
3. 返回值:
   - 免费: `{"code": 200, "data": <AppointmentResponse>}`
   - 付费: `{"code": 200, "data": {"appointment": ..., "payment_required": true, "payment_amount": 50.00, "payment_params": {...}}}`

**支付快照字段** (冻结到 appointment 上):
```
payment_profile_id, payment_miniapp_instance_id, payment_mode,
payment_app_id, payment_mch_id, payment_sub_mchid, payment_notify_url,
payment_amount
```

**payment_params 格式** (与 `Taro.requestPayment` 兼容):
```json
{
  "timeStamp": "1700000000",
  "nonceStr": "...",
  "package": "prepay_id=...",
  "signType": "RSA",
  "paySign": "..."
}
```

### 4.3 支付回调

**入口**: `POST /api/v1/payments/wechat/callback` (无需认证)
**代码**: `modules/payments/service.py` `PaymentService.handle_payment_callback()`

处理流程:
1. 从 `Wechatpay-Serial` 头查找对应 `PaymentProfile`
2. 验签 + 解密回调数据
3. 解析 `out_trade_no` → 提取 appointment.id
4. 幂等处理:
   - `status=0` (PENDING): 条件更新为 CONFIRMED，写入 transaction_id 和 paid_at
   - 已是 CONFIRMED/SIGNED/... 等支付后状态: 仅补全缺失字段，返回 SUCCESS
   - `status=7` (EXPIRED): 忽略状态变更，返回 SUCCESS (避免恢复已过期的号源)

**关键**: 使用 SQL 条件更新 (`WHERE status=0`) 防止超时任务和回调的竞态。

### 4.4 支付超时任务

**入口**: Celery 定时任务 `payment.cancel_expired_pending`
**代码**: `tasks/payment_task.py`
**触发**: 每 5 分钟执行一次

处理流程:
1. 查询 `status=0` 且 `created_at < now - 30min` 的预约
2. 条件更新 `SET status=EXPIRED WHERE status=0` (原子操作，跳过已被回调处理的)
3. 条件更新 `Schedule.booked_slots -= 1 WHERE booked_slots > 0` (防止负数)

### 4.5 重试支付

**入口**: `GET /api/v1/appointments/:id/payment-params`
**代码**: `modules/appointments/router.py`

1. 验证预约归属 (`appointment.user_id == current_user.id`)
2. 验证状态为 `PENDING`
3. openid 来源 (优先级): 显式传入参数 → 当前用户绑定的 openid
4. 调用 `PaymentService.create_payment_order()` 获取新的支付参数
5. 返回与创建时相同格式的 payment_params

---

## 五、退款生命周期

### 5.1 状态流转

```
创建退款 ──→ pending ──→ WeChat API 成功 ──→ processing ──→ 回调 ──→ success
                                    │                                  │
                                    └── WeChat API 失败 ──→ failed     └── 退款异常 ──→ failed
```

### 5.2 创建退款

**入口**: `POST /api/v1/refunds`
**代码**: `modules/refunds/service.py` `RefundService.create_refund()`
**权限**: `appointment:refund`

请求体:
```json
{
  "appointment_id": "uuid",
  "refund_amount": 30.00,
  "refund_reason": "患者申请部分退款"
}
```

处理流程:
1. 验证预约状态 (CONFIRMED/SIGNED/SEEING/COMPLETED 允许退款)
2. 累计退款校验: `已有退款金额(含pending/processing/success) + 本次 <= 原支付金额`
3. 创建 RefundRecord (`status=pending`)，快照商户信息
4. 调用 `sync_appointment_refund_state()` 更新预约退款聚合字段
5. 在 router 层调用 WeChat `create_refund()` API
6. WeChat 接受: `status → processing`; 拒绝: `status → failed`

**注意**:
- 取消预约 (`PUT /appointments/:id/cancel`) 对已支付且未完成预约会同步发起退款
- 若退款调用失败，取消整体回滚，避免出现“预约取消了但钱没退”的不一致
- 已完成预约退款只保留后台管理员例外路径

### 5.3 退款回调

**入口**: `POST /api/v1/refunds/wechat/callback` (无需认证)
**代码**: `modules/refunds/router.py` + `service.py`

处理流程:
1. 验签 + 解密
2. 按 `out_refund_no` 查找 RefundRecord
3. 事件类型:
   - `REFUND.SUCCESS` → `status=success`
   - `REFUND.CLOSED` / `REFUND.ABNORMAL` → `status=failed`
4. 幂等: 已在终态 (success/failed) 的记录仅补全缺失字段
5. 调用 `sync_appointment_refund_state()` 重新计算预约退款聚合

### 5.4 预约退款聚合字段

| 字段 | 类型 | 值域 |
|------|------|------|
| `refund_status` | VARCHAR(20) | `none` / `partial_refunded` / `refunded` |
| `refund_amount` | Numeric(10,2) | 累计退款金额 (元) |

更新时机:
- 退款创建后
- 退款回调处理后

计算规则:
```python
active_refunds = SUM(refund_amount) WHERE status IN ('pending', 'processing', 'success')

if active_refunds <= 0:       → refund_status = 'none'
elif active_refunds >= fee:   → refund_status = 'refunded'
else:                          → refund_status = 'partial_refunded'
```

---

## 六、回调排障指南

### 6.1 回调 URL 配置

回调 URL 策略:

- 支付回调: `PaymentProfile.notify_url`
- 退款回调: `PaymentProfile.refund_notify_url`
- 迁移兜底: 若未配置 `refund_notify_url`，退款回退使用 `notify_url`

确认链路:
```
支付: PaymentProfile.notify_url → PaymentConfigResolver → appointment snapshot → WeChatPayService
退款: PaymentProfile.refund_notify_url || notify_url → WeChatPayService.create_refund
```

### 6.2 常见问题

| 症状 | 可能原因 | 排查步骤 |
|------|---------|---------|
| 创建付费预约返回空 payment_params | 无可用 PaymentProfile | 检查: 1) 是否有 tenant default Profile; 2) Profile status=1 |
| 支付成功但预约仍为 PENDING | 回调未到达 | 1) 检查 notify_url 是否可从外网访问; 2) 检查 PaymentProfile.cert_serial_no 是否正确 |
| 回调返回 500 | 签名验证失败 | 1) 检查 api_v3_key_ref / private_key_ref 是否正确; 2) 检查证书是否过期 |
| 超时任务未执行 | Celery worker 未运行 | 1) `celery -A app.celery_app inspect active`; 2) 检查 beat 是否调度 |
| 退款 "商户号不存在" | 快照中的商户号不正确 | 检查 appointment.payment_mch_id / payment_sub_mchid 是否正确 |
| 退款回调收不到 | refund_notify_url 未配置或不可达 | 1) 检查 `refund_notify_url`; 2) 未配置时确认 `notify_url` 是否允许接收退款回调 |
| 重复退款 | 累计校验未覆盖 pending 状态 | 确认 `active_refunds` 查询包含 `pending` |

### 6.3 日志关键字

搜索以下日志前缀定位问题:
- `[微信配置]` — WechatConfigResolver 解析结果
- `[DEPRECATION]` — Legacy store fallback 被触发
- `支付成功回调` / `支付成功回调到达时预约已过期` — 支付回调处理
- `预约在超时处理前已被其他流程更新` — 超时竞态保护
- `退款回调` — 退款回调处理

---

## 七、Legacy Store Wechat Config 兼容策略

Store 模型的 `wechat_*` 字段已采用软废弃策略:

- `WechatConfigResolver` (小程序登录/授权) 仍以 store 字段为 fallback，但会输出 `[DEPRECATION]` warning
- `PaymentConfigResolver` (支付) 完全不读取 legacy store 字段
- Store wechat-config GET/PUT API 响应头包含 `Deprecation: true`

**迁移路径**: 通过 miniapp-platform 管理 API 创建 `MiniappInstance` + `PaymentProfile` + `PaymentRoute`。

详见 `docs/api/README.md` 中的 "Legacy Store Wechat Config 兼容策略" 章节。
