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
| page_size | int | 每页数量，默认10，最大100 |
| sort_by | string | 排序字段 |
| sort_order | string | 排序方向：asc/desc |

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
| GET | / | 获取排班列表 | 公开 |
| GET | /available | 获取可预约排班 | 公开 |
| POST | / | 创建排班 | 管理员 |
| POST | /batch | 批量创建排班 | 管理员 |
| POST | /generate | 根据模板生成 | 管理员 |
| PUT | /:id | 更新排班 | 管理员 |
| DELETE | /:id | 删除排班 | 管理员 |
| PUT | /:id/suspend | 停诊 | 管理员/医生 |

### 预约模块 `/api/v1/appointments`
| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | / | 获取预约列表 | 登录 |
| GET | /:id | 获取预约详情 | 登录 |
| POST | / | 创建预约 | 登录 |
| PUT | /:id/cancel | 取消预约 | 登录 |
| PUT | /:id/sign-in | 签到 | 登录 |
| PUT | /:id/call | 叫号 | 医生 |
| PUT | /:id/complete | 完成就诊 | 医生 |
| GET | /statistics | 预约统计 | 管理员 |

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

