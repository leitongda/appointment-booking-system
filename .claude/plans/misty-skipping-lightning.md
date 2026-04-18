# 小程序挂号支付流程分析报告

## Context

分析小程序端挂号预约的完整支付流程，包括：支付成功如何确认挂号、支付失败的各种场景处理、以及系统保障机制。本报告是纯研究性质，不涉及代码修改。

---

## 一、完整支付流程

```
用户选号 → 创建预约(status=0 待支付) → 拉起微信支付 → 支付成功 → 回调确认(status=1 已预约)
                                              ↓ 失败/取消
                                         保留订单，可重新支付
```

### 1.1 预约创建（后端决策）

**文件**: `apps/server/app/modules/appointments/service_booking.py:224-233`

后端根据诊费决定初始状态：
- 诊费 > 0 → `status=0`（待支付），同时生成微信支付参数
- 诊费 = 0 或无诊费 → `status=1`（直接确认，跳过支付）

### 1.2 前端发起支付

**文件**: `apps/patient-miniapp/src/packageBooking/pages/booking/index.tsx:193-213`

```typescript
if (paymentRequired && paymentParams) {
  // 调用微信支付
  await Taro.requestPayment(paymentParams);
  // 成功 → 跳转结果页 (status=success)
} else if (paymentRequired) {
  // 需要支付但无法拉起 → 跳转结果页 (status=unavailable)
} else {
  // 无需支付 → 跳转结果页 (status=confirmed)
}
```

### 1.3 支付成功确认（后端回调）

**文件**: `apps/server/app/modules/payments/service.py:241-262`

微信回调 → 验签 → 金额校验 → 条件更新 `status=0 → 1`（CONFIRMED）

---

## 二、支付失败场景分析

### 场景 1: 用户主动取消支付

**前端处理**: `apps/patient-miniapp/src/utils/payment.ts:30-36`

通过匹配错误消息中的取消关键词（如 `requestPayment:fail cancel`）识别用户取消。

**结果**: 跳转到结果页，显示"支付已取消"，提供"重新支付"和"返回首页"按钮。订单保留为 `status=0`。

### 场景 2: 支付网络异常/微信返回失败

**前端处理**: `apps/patient-miniapp/src/utils/payment.ts:67-79`

不匹配取消关键词的错误统一视为"支付失败"。

**结果**: 跳转到结果页，显示"支付失败"，同样提供"重新支付"按钮。订单保留为 `status=0`。

### 场景 3: 创建预约成功但支付参数获取失败（无 openid 等）

**前端处理**: `apps/patient-miniapp/src/packageBooking/pages/booking/index.tsx:214-221`

```typescript
else if (paymentRequired) {
  // paymentParams 为 null，但需要支付
  getPaymentPreparationFailure(null, '订单已创建，但当前无法直接拉起支付...');
}
```

**结果**: 跳转结果页（status=unavailable），提示用户去预约详情页稍后重试。

### 场景 4: 支付超时（30 分钟未支付）

**后端处理**: `apps/server/app/tasks/payment_task.py`

Celery 定时任务每 5 分钟扫描，将创建超过 30 分钟的待支付预约自动过期：
- `status=0 → 7`（EXPIRED）
- 释放排班号源（`booked_slots - 1`）
- 使用条件 UPDATE 防止并发

### 场景 5: 支付回调晚到（用户支付成功但回调延迟）

**后端处理**: `apps/server/app/modules/payments/service.py:285-298`

- 预约已过期 → 自动全额退款
- 预约已取消 → 自动全额退款
- 已是成功状态 → 幂等处理，补齐缺失元数据

**保障机制**: `apps/server/app/tasks/payment_reconciliation.py`
- 每 15 分钟主动对账
- 扫描 5~60 分钟内仍为待支付的预约
- 调微信查询接口确认实际支付状态
- 若微信侧已支付但本地未更新 → 补齐状态

### 场景 6: 支付回调与取消操作并发

**后端处理**: `apps/server/app/modules/payments/service.py:240-262`

使用条件 UPDATE（WHERE status=0）保证原子性：
- 如果取消先执行成功 → status 变为 CANCELLED → 回调发现非 0 → 触发自动退款
- 如果回调先执行成功 → status 变为 CONFIRMED → 取消时走已预约取消+退款流程

---

## 三、重新支付机制

### 3.1 入口

1. **结果页**: 支付失败/取消后，"重新支付"按钮跳转到预约详情页
2. **预约详情页**: status=0 时显示"去支付"按钮
3. **预约列表页**: status=0 的条目提供支付操作

**文件**: `apps/patient-miniapp/src/packageBooking/pages/appointment/detail.tsx:100-136`

### 3.2 重新支付流程

```typescript
const handlePay = async () => {
  // 1. 获取新的支付参数
  paymentParams = await appointmentApi.getPaymentParams(appointment.id);
  // 2. 拉起微信支付
  await Taro.requestPayment(paymentParams);
  // 3. 成功/失败跳转结果页
};
```

每次重新支付都会调用后端 `GET /api/v1/appointments/:id/payment-params` 生成新的微信预支付订单。

---

## 四、发现的问题与潜在风险

### 问题 1: 前端无支付结果轮询机制

**现状**: 前端完全依赖 `Taro.requestPayment` 的 Promise resolve/reject 判断支付结果，没有额外轮询后端确认支付状态。

**风险**:
- 极端情况下，微信支付成功但小程序端 Promise reject（如网络闪断），用户会看到"支付失败"页面
- 用户需要手动去预约详情页查看实际状态或重新支付
- 虽然后端有主动对账任务（15 分钟间隔）兜底，但中间存在时间窗口

**建议**: 在 `Taro.requestPayment` reject 后，增加一次后端支付状态查询（延迟 2-3 秒），确认实际支付结果后再决定跳转哪个结果页。

### 问题 2: 预约创建后无「待支付」列表筛选引导

**现状**: 支付失败后跳转结果页，用户点"重新支付"跳到预约详情页。但如果用户直接返回首页，待支付订单没有明显的入口提醒。

**建议**: 首页或预约列表页对待支付订单增加红点/未读提示。

### 问题 3: 支付参数获取失败时的错误信息不够明确

**现状**: `getPaymentPreparationFailure` 的 fallback 消息是通用文案，用户不清楚为什么无法支付（如缺少 openid、支付配置异常等）。

**建议**: 后端返回更具体的错误码，前端根据错误码展示不同的提示。

---

## 五、流程评价总结

**设计完善的地方**:
1. 后端状态机严格，条件 UPDATE 防并发
2. 回调晚到 + 过期/取消的竞态场景有自动退款兜底
3. 主动对账任务补充回调遗漏
4. 幂等设计贯穿全链路（回调去重、退款去重）
5. 多租户隔离完整

**可以改进的地方**:
1. 前端缺少支付结果二次确认（轮询后端状态）
2. 待支付订单的用户触达不够主动
3. 支付参数获取失败的错误信息粒度不够
