# 🔌 医院挂号系统 - API文档

## 一、API概览

### 1.1 基本信息

| 项目 | 说明 |
|------|------|
| 基础路径 | `/api/v1` |
| 协议 | HTTPS |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |
| 认证方式 | JWT Bearer Token |

### 1.2 请求规范

#### 请求头
```
Content-Type: application/json
Authorization: Bearer <token>
```

#### 通用请求参数
| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，默认1 |
| page_size | int | 每页数量，默认10，通用上限100，预约列表在条件满足时可至500 |
| sort_by | string | 排序字段 |
| sort_order | string | 排序方向：asc/desc |

**预约列表分页特殊规则：**
- 常规上限：100
- 扩展上限：500（需同时满足以下条件）
  - 请求者具有管理员权限
  - 必须提供 `start_date` 和 `end_date` 日期范围参数
- 不满足条件时请求将返回 422 错误，并提示具体原因

### 1.3 响应规范

#### 成功响应
```json
{
  "code": 200,
  "message": "success",
  "data": { ... },
  "timestamp": 1700000000000
}
```

#### 分页响应
```json
{
  "code": 200,
  "message": "success",
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total": 100,
    "total_pages": 10
  },
  "timestamp": 1700000000000
}
```

#### 错误响应
```json
{
  "code": 400,
  "message": "错误信息",
  "errors": [
    { "field": "phone", "message": "手机号格式错误" }
  ],
  "timestamp": 1700000000000
}
```

### 1.4 错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权/Token过期 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 业务逻辑错误 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

### 1.5 常用枚举值

#### 预约状态 (status)
| 值 | 说明 |
|----|------|
| 0 | 待支付 |
| 1 | 已预约 |
| 2 | 已签到 |
| 3 | 历史候诊（遗留状态，不参与当前主流程） |
| 4 | 就诊中 |
| 5 | 已完成 |
| 6 | 已取消 |
| 7 | 已过期 |
| 8 | 已爽约 |

#### 预约类型 (appointment_type)
| 值 | 说明 |
|----|------|
| normal | 普通 |
| urgent | 加急 |
| expert | 专家 |
| medical_insurance | 医保 |
| self_pay | 自费 |

#### 时段 (time_slot)
| 值 | 说明 |
|----|------|
| AM / morning | 上午 |
| PM / afternoon | 下午 |
| evening | 晚上 |

#### 性别 (gender)
| 值 | 说明 |
|----|------|
| 0 | 未知 |
| 1 | 男 |
| 2 | 女 |

#### 反馈类型 (feedback_type)
| 值 | 说明 |
|----|------|
| suggestion | 建议 |
| complaint | 投诉 |
| bug | 问题反馈 |
| other | 其他 |

#### 反馈状态 (feedback_status)
| 值 | 说明 |
|----|------|
| pending | 待处理 |
| processing | 处理中 |
| resolved | 已解决 |
| closed | 已关闭 |

#### 消息类型 (message_type)
| 值 | 说明 |
|----|------|
| appointment | 预约通知 |
| consultation | 就诊通知 |
| schedule | 排班通知 |
| system | 系统通知 |
| stop_clinic | 停诊通知 |

---

## 一点五、支付闭环完成情况（2026-04-17）

### 已完成

- `POST /appointments` 已支持免费预约与待支付预约两种返回形态
- 待支付预约支持通过 `/appointments/:id/payment-params` 重新获取支付参数
- 预约响应已透出支付金额、支付交易号、支付时间、退款状态、已退款金额
- 退款接口字段已统一为 `appointment_id`、`refund_amount`、`refund_reason`，金额单位统一为“元”
- 支付成功回调、退款回调、支付超时任务已增加幂等和竞态保护

### 已验证

- 支付创建、支付状态查询、退款创建的认证与归属校验已通过集成测试
- 重试支付成功、越权拒绝、状态错误场景已通过集成测试
- 支付回调重复通知、已过期晚到回调、超时竞争跳过场景已通过单元测试

### 仍待补齐

- _(无)_ — 支付/退款生命周期文档和手工联调清单已完成，见下方参考链接。

### Legacy Store Wechat Config 兼容策略 (2026-04-17)

Store 模型上的 `wechat_*` 字段已采用**软废弃**策略:

| 字段 | 状态 | 替代方案 |
|------|------|---------|
| `wechat_app_id` | deprecated | MiniappInstance.app_id |
| `wechat_app_secret` | deprecated | MiniappInstance.app_secret_ref |
| `wechat_mch_id` | deprecated (已死代码) | PaymentProfile.mch_id |
| `wechat_api_key` | deprecated (已死代码) | PaymentProfile (api_v3_key_ref) |
| `wechat_notify_url` | deprecated (已死代码) | PaymentProfile.notify_url |

运行时行为:
- `WechatConfigResolver` 仍以 store 字段为 fallback，但会输出 `DEPRECATION` warning
- `PaymentConfigResolver` 完全不读取 legacy store 字段
- Store wechat-config GET/PUT API 响应头包含 `Deprecation: true`

迁移路径:
1. 通过 `POST /miniapp-platform/instances` 创建小程序实例 (app_id/app_secret)
2. 通过 `POST /miniapp-platform/payment-profiles` 创建支付配置 (mch_id/cert)
3. 通过 `POST /miniapp-platform/payment-routes` 绑定门店到支付配置
4. 验证路由优先级: store_route > miniapp_instance_default > tenant_default
5. 确认不再命中 store fallback 后可安全忽略 legacy 字段

### 支付/退款文档参考

- 生命周期文档: `docs/server/payment-lifecycle.md`
- 手工联调清单: `docs/plans/payment-joint-debug-checklist.md`

---

## 二、API模块列表

### 认证模块 `/api/v1/auth`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | /login | 用户登录 | 公开 |
| POST | /register | 用户注册 | 公开 |
| POST | /logout | 退出登录 | 登录 |
| POST | /refresh | 刷新Token | 登录 |
| POST | /send-code | 发送验证码 | 公开 |
| POST | /wechat-login | 微信登录 | 公开 |

### 用户模块 `/api/v1/users`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /profile | 获取个人信息 | 登录 |
| PUT | /profile | 更新个人信息 | 登录 |
| PUT | /password | 修改密码 | 登录 |
| GET | /patients | 获取就诊人列表 | 登录 |
| POST | /patients | 添加就诊人 | 登录 |
| PUT | /patients/:id | 更新就诊人 | 登录 |
| DELETE | /patients/:id | 删除就诊人 | 登录 |

### 科室模块 `/api/v1/departments`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取科室列表 | 公开 |
| GET | /:id | 获取科室详情 | 公开 |
| GET | /tree | 获取科室树 | 公开 |
| GET | /hot | 获取热门科室 | 公开 |
| POST | / | 创建科室 | 管理员 |
| PUT | /:id | 更新科室 | 管理员 |
| DELETE | /:id | 删除科室 | 管理员 |

### 医生模块 `/api/v1/doctors`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取医生列表 | 公开 |
| GET | /:id | 获取医生详情 | 公开 |
| GET | /:id/schedules | 获取医生排班 | 公开 |
| GET | /recommended | 获取推荐医生 | 公开 |
| POST | / | 创建医生 | 管理员 |
| PUT | /:id | 更新医生 | 管理员 |
| DELETE | /:id | 删除医生 | 管理员 |

### 排班模块 `/api/v1/schedules`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取排班列表 | 管理员 |
| GET | /statistics | 获取排班统计（按门店、月份） | 管理员 |
| GET | /available/:doctor_id | 获取可预约排班 | 公开 |
| GET | /:id | 获取排班详情 | 管理员 |
| POST | / | 创建排班 | 管理员 |
| POST | /batch | 批量创建排班 | 管理员 |
| PUT | /:id | 更新排班 | 管理员 |
| POST | /batch-suspend | 批量停诊 | 管理员 |
| POST | /batch-resume | 批量恢复 | 管理员 |
| POST | /batch-delete | 批量删除 | 管理员 |

### 排班模板模块 `/api/v1/schedule-templates`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取排班模板列表 | 管理员 |
| GET | /:id | 获取模板详情 | 管理员 |
| POST | / | 创建排班模板 | 管理员 |
| PUT | /:id | 更新模板 | 管理员 |
| DELETE | /:id | 删除模板 | 管理员 |
| POST | /:id/generate | 生成排班 | 管理员 |
| POST | /preview | 预览生成排班 | 管理员 |
| POST | /:id/copy | 复制模板 | 管理员 |

### 门店模块 `/api/v1/stores`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取门店列表 | 管理员 |
| GET | /all | 获取所有门店 | 管理员 |
| GET | /:id | 获取门店详情 | 管理员 |
| POST | / | 创建门店 | 管理员 |
| PUT | /:id | 更新门店 | 管理员 |
| DELETE | /:id | 删除门店 | 管理员 |
| PATCH | /:id/status | 更新门店状态 | 管理员 |

### 规则管理模块 `/api/v1/rule-sets`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取规则集列表 | 管理员 |
| GET | /:id | 获取规则集详情 | 管理员 |
| POST | / | 创建规则集 | 管理员 |
| PUT | /:id | 更新规则集 | 管理员 |
| DELETE | /:id | 删除规则集 | 管理员 |
| POST | /:id/enable | 启用规则集 | 管理员 |
| POST | /:id/disable | 禁用规则集 | 管理员 |
| POST | /preview | 预览规则效果 | 管理员 |

### 停诊调班模块 `/api/v1/leave-requests`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取停诊调班列表 | 管理员 |
| GET | /pending-count | 获取待审核数量 | 管理员 |
| GET | /my | 获取我的申请 | 医生 |
| GET | /:id | 获取申请详情 | 管理员/医生 |
| POST | /stop-clinic | 申请停诊 | 医生 |
| POST | /schedule-change | 申请调班 | 医生 |
| POST | /:id/review | 审核申请 | 管理员 |
| POST | /:id/cancel | 取消申请 | 医生 |

### 反馈管理模块 `/api/v1/feedbacks`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取反馈列表 | 管理员 |
| GET | /pending-count | 获取待处理数量 | 管理员 |
| GET | /my | 获取我的反馈 | 登录 |
| GET | /:id | 获取反馈详情 | 管理员/本人 |
| POST | / | 提交反馈 | 登录 |
| POST | /:id/reply | 回复反馈 | 管理员 |
| PATCH | /:id/status | 更新反馈状态 | 管理员 |

### 消息中心模块 `/api/v1/messages`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /my | 获取我的消息列表 | 登录 |
| GET | /unread-count | 获取未读消息数 | 登录 |
| PUT | /:id/read | 标记已读 | 登录 |
| PUT | /batch-read | 批量标记已读 | 登录 |
| DELETE | /:id | 删除消息 | 登录 |

### 黑名单模块 `/api/v1/blacklists`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取黑名单列表 | 管理员 |
| POST | / | 添加黑名单 | 管理员 |
| DELETE | /:id | 删除黑名单 | 管理员 |
| POST | /check | 检查是否在黑名单 | 管理员 |

### 预约模块 `/api/v1/appointments`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /query | 获取预约列表 | 登录 |
| GET | /query/today | 获取今日预约（医生端） | 医生 |
| GET | /query/today-pending | 获取今日待签到预约 | 登录 |
| GET | /query/queue | 获取签到队列 | 登录/管理员 |
| GET | /query/queue/info | 获取叫号队列信息 | 医生 |
| GET | /query/statistics | 预约统计 | 管理员 |
| GET | /query/check-duplicate | 检查重复预约 | 登录 |
| GET | /query/by-no/:appointment_no | 按预约号获取详情 | 登录 |
| GET | /query/:id | 获取预约详情 | 登录 |
| POST | / | 创建预约 | 登录 |
| PUT | /:id/cancel | 取消预约 | 登录 |
| PUT | /:id/sign-in | 签到 | 登录 |
| PUT | /:id/cancel-sign-in | 取消签到 | 超级管理员 |
| PUT | /:id/call | 叫号 | 管理员 |
| PUT | /:id/complete | 完成就诊 | 管理员 |
| PUT | /:id/pass | 过号 | 管理员 |
| PUT | /:id/recall | 重新叫号 | 管理员 |
| PUT | /:id/no-show | 标记爽约 | 管理员 |

### 病历模块 `/api/v1/medical-records`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取病历列表 | 登录 |
| GET | /:id | 获取病历详情 | 登录 |
| POST | / | 创建病历 | 医生 |
| PUT | /:id | 更新病历 | 医生 |

### 内容模块 `/api/v1/content`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /banners | 获取轮播图 | 公开 |
| GET | /news | 获取新闻列表 | 公开 |
| GET | /news/:id | 获取新闻详情 | 公开 |
| GET | /notices | 获取公告列表 | 公开 |
| GET | /popups | 获取弹框 | 公开 |

### 系统设置 `/api/v1/settings`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取系统设置 | 管理员 |
| PUT | / | 更新系统设置 | 管理员 |
| GET | /booking | 获取预约设置 | 公开 |
| GET | /home-menus | 获取首页菜单 | 公开 |

### 统计模块 `/api/v1/statistics`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | /overview | 总览数据 | 管理员 |
| GET | /appointments | 预约统计 | 管理员 |
| GET | /departments | 科室统计 | 管理员 |
| GET | /doctors | 医生统计 | 管理员 |

---

## 三、详细接口文档

### 3.1 认证模块

#### 用户登录
```
POST /api/v1/auth/login
```

**请求参数**
```json
{
  "phone": "13800138000",
  "password": "123456"
}
```

**响应**
```json
{
  "code": 200,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 1800,
    "user": {
      "id": "uuid",
      "phone": "13800138000",
      "name": "张三",
      "role": "PATIENT"
    }
  }
}
```

#### 用户注册
```
POST /api/v1/auth/register
```

**请求参数**
```json
{
  "phone": "13800138000",
  "password": "123456",
  "code": "123456",
  "name": "张三"
}
```

---

### 3.2 预约模块

#### 创建预约
```
POST /api/v1/appointments
```

**请求参数**
```json
{
  "doctor_id": "uuid",
  "schedule_id": "uuid",
  "patient_id": "uuid"
}
```

**响应**
```json
{
  "code": 200,
  "data": {
    "id": "uuid",
    "appointment_no": "YY20241127001",
    "doctor": {
      "id": "uuid",
      "name": "李医生",
      "title": "主任医师",
      "department": {
        "id": "uuid",
        "name": "内科"
      }
    },
    "patient": {
      "id": "uuid",
      "name": "张三"
    },
    "appointment_date": "2024-11-28",
    "time_slot": "AM",
    "queue_number": 5,
    "fee": 50.00,
    "status": 1,
    "created_at": "2024-11-27T10:00:00Z"
  }
}
```

#### 取消预约
```
PUT /api/v1/appointments/:id/cancel
```

**请求参数**
```json
{
  "reason": "临时有事"
}
```

---

### 3.3 排班模块

#### 获取可预约排班
```
GET /api/v1/schedules/available
```

**请求参数**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| doctor_id | uuid | 是 | 医生ID |
| start_date | date | 否 | 开始日期 |
| end_date | date | 否 | 结束日期 |

**响应**
```json
{
  "code": 200,
  "data": [
    {
      "id": "uuid",
      "schedule_date": "2024-11-28",
      "time_slot": "AM",
      "start_time": "08:00",
      "end_time": "12:00",
      "total_slots": 20,
      "booked_slots": 5,
      "available_slots": 15,
      "status": 1
    }
  ]
}
```

---

## 四、Swagger文档

启动服务后访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/api/v1/openapi.json`
