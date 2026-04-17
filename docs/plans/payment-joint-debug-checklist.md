# 支付/退款手工联调清单

本清单用于端到端验证支付闭环。按顺序执行，每项标注前置条件和预期结果。

---

## 前置准备

- [ ] 后端服务运行 (`pnpm dev:server`)
- [ ] PostgreSQL + Redis 运行 (`docker-compose up -d postgres redis`)
- [ ] Celery worker + beat 运行 (`celery -A app.celery_app worker -Q default,scheduled,notification --loglevel=info &; celery -A app.celery_app beat --loglevel=info &`)
- [ ] 至少一个租户已配置 PaymentProfile (is_default=True, status=1)
- [ ] PaymentProfile 的 `api_v3_key_ref` / `private_key_ref` / `cert_serial_no` 指向有效凭据
- [ ] `notify_url` 可从微信服务器访问 (公网可回调)
- [ ] 至少一个医生有排班且有余号

---

## P0: 免费预约

### T01: 创建免费预约

**前置**: 医生挂号费 = 0 (或未设置)

**步骤**:
1. 患者端: `POST /api/v1/appointments` 创建预约
2. 检查响应

**预期**:
- 响应无 `payment_required` 字段 (或为 false)
- 预约状态直接为 `CONFIRMED` (status=1)
- 无 payment_params

---

## P1: 付费预约完整流程

### T02: 创建付费预约

**前置**: 医生挂号费 > 0

**步骤**:
1. 患者端: `POST /api/v1/appointments` 创建预约

**预期**:
- 响应包含 `payment_required: true`
- 包含 `payment_amount` (元)
- 包含 `payment_params` (含 timeStamp, nonceStr, package, signType, paySign)
- 预约状态为 `PENDING` (status=0)

**验证**:
```sql
SELECT id, status, payment_amount, payment_profile_id, payment_mode
FROM appointments WHERE id = '<新预约ID>';
```

### T03: 支付成功

**前置**: T02 通过，预约处于 PENDING

**步骤**:
1. 小程序: 用 payment_params 调用 `Taro.requestPayment` 完成支付
2. 等待微信回调到达后端
3. 刷新预约详情

**预期**:
- 预约状态变为 `CONFIRMED` (status=1)
- `payment_transaction_id` 已填入微信交易流水号
- `paid_at` 已填入时间
- `booked_slots` 未变化 (已在创建时占位)

**验证**:
```sql
SELECT status, payment_transaction_id, paid_at
FROM appointments WHERE id = '<预约ID>';
```

### T04: 支付成功页面展示

**前置**: T03 通过

**步骤**:
1. 患者端: 访问 "我的预约" 列表
2. 点击刚完成的预约进入详情

**预期**:
- 列表显示预约状态为 "已预约"
- 详情页展示支付金额和支付时间

---

## P2: 重试支付

### T05: 取消支付后重试

**前置**: 完成另一个 T02 (创建付费预约)

**步骤**:
1. 小程序: 在支付弹窗点击 "取消"
2. 患者端: 进入该待支付预约详情
3. 点击 "重新支付"
4. 后端: `GET /api/v1/appointments/:id/payment-params`
5. 用返回的新 payment_params 再次调用 `Taro.requestPayment`

**预期**:
- 重试请求返回新的 payment_params (prepay_id 不同)
- 支付完成后预约变为 CONFIRMED

### T06: 未绑定 openid 的用户重试支付

**前置**: 用户无 openid 绑定

**步骤**:
1. 不传 openid 参数调用重试接口

**预期**:
- 如果后端无法从用户信息获取 openid → 返回 400 提示需要 openid
- 如果用户已绑定 openid → 正常返回 payment_params

---

## P3: 支付超时

### T07: 超时自动过期

**前置**: 创建付费预约后不支付，等待 30+ 分钟

**步骤**:
1. 等待 Celery 超时任务执行 (每 5 分钟)
2. 查看预约状态

**预期**:
- 预约状态变为 `EXPIRED` (status=7)
- `booked_slots` 减 1 (号源释放)

**验证**:
```sql
SELECT a.status, s.booked_slots, s.total_slots
FROM appointments a
JOIN schedules s ON a.schedule_id = s.id
WHERE a.id = '<超时预约ID>';
```

### T08: 晚到的支付回调 (竞态保护)

**前置**: T07 完成后，手动模拟支付成功回调

**预期**:
- 回调处理不恢复预约状态 (仍为 EXPIRED)
- 不释放号源 (booked_slots 不再减少)
- 日志输出: "支付成功回调到达时预约已过期，忽略状态变更"

---

## P4: 重复回调安全

### T09: 重复支付回调

**前置**: 一个已支付成功的预约

**步骤**:
1. 用相同的回调数据再次发送到 `POST /api/v1/payments/wechat/callback`

**预期**:
- 回调正常返回 SUCCESS
- 预约状态不变 (仍为 CONFIRMED)
- transaction_id 和 paid_at 不会被覆盖
- 不产生异常日志

---

## P5: 管理员退款

### T10: 全额退款

**前置**: 一个已支付成功的预约 (T03 完成)

**步骤**:
1. 管理端: `POST /api/v1/refunds`
   ```json
   {
     "appointment_id": "<预约ID>",
     "refund_amount": 50.00,
     "refund_reason": "患者申请全额退款"
   }
   ```
2. 等待微信退款回调

**预期**:
- RefundRecord: pending → processing → success
- 预约 refund_status = "refunded"
- 预约 refund_amount = 原支付金额

**验证**:
```sql
SELECT refund_no, status, refund_amount, original_amount
FROM refund_records WHERE appointment_id = '<预约ID>';

SELECT refund_status, refund_amount
FROM appointments WHERE id = '<预约ID>';
```

### T11: 部分退款

**前置**: 一个已支付 50 元的预约

**步骤**:
1. 管理端: `POST /api/v1/refunds` (refund_amount=30)
2. 等待回调
3. 再次 `POST /api/v1/refunds` (refund_amount=20)

**预期**:
- 第一次: refund_status = "partial_refunded", refund_amount = 30
- 第二次: refund_status = "refunded", refund_amount = 50

### T12: 超额退款拒绝

**前置**: 一个已支付 50 元且已退 30 元的预约

**步骤**:
1. 管理端: `POST /api/v1/refunds` (refund_amount=30)

**预期**:
- 返回错误: 累计退款金额超过原支付金额

### T13: 退款失败回调

**前置**: 退款请求被微信拒绝 (模拟)

**预期**:
- RefundRecord status = "failed"
- 预约 refund_amount 不增加
- 日志记录 failed_reason

---

## P6: 权限与安全

### T14: 患者越权访问

**步骤**:
1. 用户 A 尝试调用 用户 B 的预约的 `GET /appointments/:id/payment-params`

**预期**: 403 Forbidden

### T15: 非管理员退款

**步骤**:
1. 普通用户调用 `POST /api/v1/refunds`

**预期**: 403 Forbidden

### T16: 未支付预约退款

**步骤**:
1. 对 status=PENDING 的预约调用 `POST /api/v1/refunds`

**预期**: 400 错误 "当前预约状态不允许退款"

---

## P7: 配置路由

### T17: 门店级支付路由优先

**前置**:
- 租户有默认 PaymentProfile (mch_id=DEFAULT)
- 门店有 PaymentRoute 指向另一个 Profile (mch_id=STORE)

**步骤**:
1. 为该门店下的医生创建付费预约

**预期**:
- payment_mch_id = STORE (门店路由优先于租户默认)

### T18: 无支付配置时创建失败

**前置**: 租户无 PaymentProfile

**步骤**:
1. 创建付费预约

**预期**: 返回错误，提示无法解析支付配置

---

## 完成标准

全部 T01-T18 通过后，支付闭环可以视为手工联调完成。
