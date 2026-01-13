# API 接口文档

本文档详细说明了小程序端需要调用的所有后端 API 接口。

## 接口规范

### 基础信息

**Base URL**: `https://api.example.com/api/v1`

**请求头**:
```
Content-Type: application/json
Authorization: Bearer {accessToken}  // 需要认证的接口
```

**门店 ID**: 所有请求会自动添加 `storeId` 参数到 URL 查询字符串中。

### 响应格式

成功响应：
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

错误响应：
```json
{
  "code": 400,
  "message": "错误信息",
  "data": null
}
```

### 状态码说明

| 状态码 | 说明 |
|--------|------|
| 0/200 | 请求成功 |
| 400 | 请求参数错误 |
| 401 | 未授权，需要登录 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 500 | 服务器错误 |

## 一、认证模块

### 1.1 微信登录

**接口**: `POST /auth/wechat/login`

**说明**: 使用微信登录凭证进行登录

**请求参数**:
```json
{
  "code": "string",        // 微信登录凭证
  "storeId": "string"      // 门店ID（可选）
}
```

**响应数据**:
```json
{
  "isNewUser": true,
  "needBindPhone": true,
  "openid": "string",
  "accessToken": "string",
  "refreshToken": "string",
  "expiresIn": 7200
}
```

**字段说明**:
- `isNewUser`: 是否为新用户
- `needBindPhone`: 是否需要绑定手机号
- `openid`: 用户的 openid
- `accessToken`: 访问令牌（已绑定手机号时返回）
- `refreshToken`: 刷新令牌（已绑定手机号时返回）
- `expiresIn`: 令牌过期时间（秒）

### 1.2 微信获取手机号并登录

**接口**: `POST /auth/wechat/phone`

**说明**: 通过微信手机号授权完成登录

**请求参数**:
```json
{
  "code": "string",        // 手机号获取凭证
  "openid": "string",      // 用户 openid
  "storeId": "string"      // 门店ID（可选）
}
```

**响应数据**:
```json
{
  "accessToken": "string",
  "refreshToken": "string",
  "expiresIn": 7200,
  "user": {
    "id": "string",
    "openid": "string",
    "nickname": "string",
    "avatar": "string",
    "phone": "string",
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

### 1.3 微信绑定手机号（手动输入）

**接口**: `POST /auth/wechat/bind-phone`

**说明**: 手动输入手机号进行绑定

**请求参数**:
```json
{
  "openid": "string",
  "phone": "string"
}
```

**响应数据**:
```json
{
  "success": true
}
```

### 1.4 微信绑定用户信息

**接口**: `POST /auth/wechat/bind-userinfo`

**说明**: 绑定用户昵称和头像

**请求参数**:
```json
{
  "openid": "string",
  "nickname": "string",
  "avatar": "string"
}
```

**响应数据**:
```json
{
  "success": true
}
```

### 1.5 刷新 Token

**接口**: `POST /auth/refresh`

**说明**: 使用刷新令牌获取新的访问令牌

**请求参数**:
```json
{
  "refresh_token": "string"
}
```

**响应数据**:
```json
{
  "accessToken": "string",
  "refreshToken": "string",
  "expiresIn": 7200,
  "user": {}
}
```

## 二、预约模块

### 2.1 获取预约列表

**接口**: `GET /appointments`

**说明**: 获取当前用户的预约列表

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | number | 否 | 预约状态 |
| page | number | 否 | 页码，默认 1 |
| pageSize | number | 否 | 每页数量，默认 10 |

**响应数据**:
```json
{
  "data": [
    {
      "id": "string",
      "appointmentNo": "string",
      "patientId": "string",
      "patientName": "string",
      "scheduleId": "string",
      "doctorId": "string",
      "doctorName": "string",
      "doctorTitle": "string",
      "departmentId": "string",
      "departmentName": "string",
      "scheduleDate": "2024-01-01",
      "timeSlot": "morning",
      "startTime": "09:00",
      "endTime": "12:00",
      "status": 1,
      "queueNumber": 10,
      "symptomDescription": "string",
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "pageSize": 10
}
```

**预约状态说明**:
| 状态值 | 说明 |
|--------|------|
| 1 | 已预约 |
| 2 | 已签到 |
| 3 | 就诊中 |
| 4 | 已完成 |
| 5 | 已取消 |
| 6 | 爽约 |
| 7 | 已过号 |

### 2.2 获取预约详情

**接口**: `GET /appointments/:id`

**说明**: 根据预约 ID 获取详情

**路径参数**:
- `id`: 预约 ID

**响应数据**: 同预约列表中的单个预约对象

### 2.3 按预约号获取详情

**接口**: `GET /appointments/by-no/:appointmentNo`

**说明**: 根据预约号获取详情

**路径参数**:
- `appointmentNo`: 预约号

**响应数据**: 同预约列表中的单个预约对象

### 2.4 创建预约

**接口**: `POST /appointments`

**说明**: 创建新的预约

**请求参数**:
```json
{
  "scheduleId": "string",
  "patientId": "string",
  "symptomDescription": "string"
}
```

**响应数据**: 创建成功的预约对象

### 2.5 检查重复预约

**接口**: `GET /appointments/check-duplicate`

**说明**: 检查是否存在重复预约

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| schedule_id | string | 是 | 排班 ID |
| patient_id | string | 是 | 就诊人 ID |

**响应数据**:
```json
{
  "hasDuplicate": true,
  "appointments": [
    {
      "id": "string",
      "appointmentNo": "string",
      "scheduleDate": "2024-01-01",
      "timeSlot": "morning",
      "status": 1
    }
  ]
}
```

### 2.6 取消预约

**接口**: `PUT /appointments/:id/cancel`

**说明**: 取消指定的预约

**路径参数**:
- `id`: 预约 ID

**请求参数**:
```json
{
  "reason": "string"  // 取消原因（可选）
}
```

**响应数据**:
```json
{
  "success": true
}
```

### 2.7 签到

**接口**: `PUT /appointments/:id/sign-in`

**说明**: 对预约进行签到

**路径参数**:
- `id`: 预约 ID

**响应数据**:
```json
{
  "message": "签到成功",
  "queueNumber": 10
}
```

### 2.8 获取今日待签到预约

**接口**: `GET /appointments/today-pending`

**说明**: 获取今日待签到的预约列表

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| store_id | string | 是 | 门店 ID |

**响应数据**:
```json
[
  {
    "id": "string",
    "appointmentNo": "string",
    "patientName": "string",
    "doctorName": "string",
    "scheduleDate": "2024-01-01",
    "timeSlot": "morning",
    "signInStatus": "available",
    "signInMessage": "可以签到",
    "checkinOpenAt": "08:30",
    "checkinCloseAt": "09:30",
    "minutesUntilOpen": 0,
    "minutesUntilClose": 30
  }
]
```

**签到状态说明**:
| 状态 | 说明 |
|------|------|
| early | 签到时间未到 |
| available | 可以签到 |
| late | 已超过签到时间 |

## 三、排班模块

### 3.1 获取医生可预约排班

**接口**: `GET /schedules/available/:doctorId`

**说明**: 获取指定医生的可预约排班

**路径参数**:
- `doctorId`: 医生 ID

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| days | number | 否 | 查询天数，默认根据门店配置 |

**响应数据**:
```json
[
  {
    "id": "string",
    "scheduleDate": "2024-01-01",
    "timeSlot": "morning",
    "availableSlots": 10,
    "totalSlots": 20,
    "startTime": "09:00",
    "endTime": "12:00",
    "bookingStatus": "available",
    "bookingOpenAt": "2024-01-01 00:00:00",
    "bookingCloseAt": "2024-01-01 11:30:00",
    "capacityPercent": 50,
    "urgencyLevel": "normal"
  }
]
```

**号源状态说明**:
| 状态 | 说明 |
|------|------|
| not_open | 未开放 |
| available | 可预约 |
| closing_soon | 即将截止 |
| full | 已约满 |
| closed | 已截止 |

**紧急程度说明**:
| 级别 | 说明 |
|------|------|
| normal | 正常 |
| medium | 紧张 |
| high | 很紧张 |
| critical | 非常紧张 |

## 四、医生模块

### 4.1 获取推荐医生

**接口**: `GET /doctors/recommended`

**说明**: 获取推荐医生列表

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | number | 否 | 返回数量限制 |

**响应数据**:
```json
[
  {
    "id": "string",
    "name": "string",
    "title": "主任医师",
    "departmentId": "string",
    "departmentName": "内科",
    "avatar": "string",
    "introduction": "string",
    "specialty": "string",
    "isRecommended": true,
    "sortOrder": 1
  }
]
```

### 4.2 按科室获取医生

**接口**: `GET /doctors/by-department/:departmentId`

**说明**: 获取指定科室的医生列表

**路径参数**:
- `departmentId`: 科室 ID

**响应数据**: 同推荐医生列表

### 4.3 获取医生详情（公开）

**接口**: `GET /doctors/public/:id`

**说明**: 获取医生详细信息（无需登录）

**路径参数**:
- `id`: 医生 ID

**响应数据**: 同推荐医生列表中的单个医生对象

### 4.4 搜索医生

**接口**: `GET /doctors`

**说明**: 根据姓名搜索医生

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 医生姓名 |
| page | number | 否 | 页码，默认 1 |
| pageSize | number | 否 | 每页数量，默认 10 |

**响应数据**: 分页的医生列表

## 五、科室模块

### 5.1 获取科室树

**接口**: `GET /departments/tree`

**说明**: 获取科室树形结构

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| status | number | 否 | 状态筛选，1-启用 |

**响应数据**:
```json
[
  {
    "id": "string",
    "name": "内科",
    "parentId": null,
    "isFinal": false,
    "icon": "string",
    "description": "string",
    "isHot": true,
    "sortOrder": 1,
    "children": [
      {
        "id": "string",
        "name": "心内科",
        "parentId": "string",
        "isFinal": true,
        "icon": "string",
        "description": "string",
        "isHot": false,
        "sortOrder": 1,
        "children": []
      }
    ]
  }
]
```

### 5.2 获取热门科室

**接口**: `GET /departments/hot`

**说明**: 获取热门科室列表

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | number | 否 | 返回数量限制 |

**响应数据**: 科室列表（不含 children）

### 5.3 搜索科室

**接口**: `GET /departments`

**说明**: 根据名称搜索科室

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 科室名称 |
| page | number | 否 | 页码，默认 1 |
| pageSize | number | 否 | 每页数量，默认 10 |

**响应数据**: 分页的科室列表

## 六、用户/就诊人模块

### 6.1 获取用户信息

**接口**: `GET /users/profile`

**说明**: 获取当前登录用户的信息

**响应数据**:
```json
{
  "id": "string",
  "openid": "string",
  "nickname": "string",
  "avatar": "string",
  "phone": "string",
  "createdAt": "2024-01-01T00:00:00Z",
  "updatedAt": "2024-01-01T00:00:00Z"
}
```

### 6.2 更新用户信息

**接口**: `PUT /users/profile`

**说明**: 更新用户信息

**请求参数**:
```json
{
  "nickname": "string",
  "avatar": "string"
}
```

**响应数据**: 更新后的用户信息

### 6.3 获取就诊人列表

**接口**: `GET /users/patients`

**说明**: 获取当前用户的就诊人列表

**响应数据**:
```json
[
  {
    "id": "string",
    "userId": "string",
    "name": "string",
    "phone": "string",
    "idCard": "string",
    "gender": 1,
    "birthday": "1990-01-01",
    "relationship": "self",
    "isDefault": true,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
]
```

**性别说明**:
- 1: 男
- 2: 女

**关系说明**:
- self: 本人
- parent: 父母
- child: 子女
- spouse: 配偶
- other: 其他

### 6.4 获取就诊人详情

**接口**: `GET /users/patients/:id`

**说明**: 获取指定就诊人的详情

**路径参数**:
- `id`: 就诊人 ID

**响应数据**: 同就诊人列表中的单个对象

### 6.5 添加就诊人

**接口**: `POST /users/patients`

**说明**: 添加新的就诊人

**请求参数**:
```json
{
  "name": "string",
  "phone": "string",
  "idCard": "string",
  "gender": 1,
  "birthday": "1990-01-01",
  "relationship": "self",
  "isDefault": false
}
```

**响应数据**: 创建成功的就诊人对象

### 6.6 更新就诊人

**接口**: `PUT /users/patients/:id`

**说明**: 更新就诊人信息

**路径参数**:
- `id`: 就诊人 ID

**请求参数**: 同添加就诊人

**响应数据**: 更新后的就诊人对象

### 6.7 删除就诊人

**接口**: `DELETE /users/patients/:id`

**说明**: 删除指定的就诊人

**路径参数**:
- `id`: 就诊人 ID

**响应数据**:
```json
{
  "success": true
}
```

### 6.8 上传头像

**接口**: `POST /users/avatar`

**说明**: 上传用户头像

**请求参数**: `multipart/form-data`
- file: 图片文件

**响应数据**:
```json
{
  "url": "https://example.com/avatar.jpg"
}
```

## 七、收藏模块

### 7.1 检查是否已收藏

**接口**: `GET /favorites/check`

**说明**: 检查指定对象是否已收藏

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| targetType | string | 是 | 收藏类型：doctor/department |
| targetId | string | 是 | 目标 ID |

**响应数据**:
```json
{
  "isFavorited": true,
  "favoriteId": "string"
}
```

### 7.2 添加收藏

**接口**: `POST /favorites`

**说明**: 添加收藏

**请求参数**:
```json
{
  "targetType": "doctor",
  "targetId": "string"
}
```

**响应数据**:
```json
{
  "id": "string",
  "userId": "string",
  "targetType": "doctor",
  "targetId": "string",
  "createdAt": "2024-01-01T00:00:00Z"
}
```

### 7.3 取消收藏（通过收藏ID）

**接口**: `DELETE /favorites/:favoriteId`

**说明**: 根据收藏 ID 取消收藏

**路径参数**:
- `favoriteId`: 收藏 ID

**响应数据**:
```json
{
  "success": true
}
```

### 7.4 取消收藏（通过目标）

**接口**: `DELETE /favorites/target/:targetType/:targetId`

**说明**: 根据目标类型和 ID 取消收藏

**路径参数**:
- `targetType`: 收藏类型
- `targetId`: 目标 ID

**响应数据**:
```json
{
  "success": true
}
```

### 7.5 获取收藏列表

**接口**: `GET /favorites`

**说明**: 获取用户的收藏列表

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| targetType | string | 否 | 收藏类型筛选 |
| page | number | 否 | 页码，默认 1 |
| pageSize | number | 否 | 每页数量，默认 10 |

**响应数据**: 分页的收藏列表

## 八、内容模块

### 8.1 获取活跃轮播图

**接口**: `GET /content/banners/active`

**说明**: 获取当前活跃的轮播图（无需登录）

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| position | string | 否 | 位置：home/department/doctor |

**响应数据**:
```json
[
  {
    "id": "string",
    "title": "string",
    "imageUrl": "string",
    "linkType": 1,
    "linkUrl": "string"
  }
]
```

**链接类型说明**:
- 0: 无链接
- 1: 小程序内部页面
- 2: 外部链接

### 8.2 获取已发布公告

**接口**: `GET /content/notices/published`

**说明**: 获取已发布的公告列表（无需登录）

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | number | 否 | 返回数量限制 |

**响应数据**:
```json
[
  {
    "id": "string",
    "title": "string",
    "content": "string",
    "publishedAt": "2024-01-01T00:00:00Z"
  }
]
```

## 九、设置模块

### 9.1 获取预约规则（公开）

**接口**: `GET /settings/booking/rules`

**说明**: 获取预约规则配置（无需登录）

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| storeId | string | 否 | 门店 ID |

**响应数据**:
```json
{
  "advanceDays": 7,
  "sameDayBooking": true,
  "cancelHours": 2,
  "perDayLimit": 3,
  "advanceBookingMinutes": 30,
  "signInAdvanceMinutes": 30,
  "signInLateMinutes": 15
}
```

**字段说明**:
- `advanceDays`: 可提前预约天数
- `sameDayBooking`: 是否支持当天预约
- `cancelHours`: 取消预约提前小时数
- `perDayLimit`: 每日预约上限
- `advanceBookingMinutes`: 提前预约截止分钟数
- `signInAdvanceMinutes`: 提前签到分钟数
- `signInLateMinutes`: 迟到签到分钟数

### 9.2 获取医院信息

**接口**: `GET /settings/hospital`

**说明**: 获取医院基本信息（无需登录）

**响应数据**:
```json
{
  "hospitalName": "XX医院",
  "hospitalLevel": "三级甲等",
  "address": "XX市XX区XX路XX号",
  "phone": "0123-12345678",
  "workTime": "周一至周日 8:00-17:00",
  "introduction": "医院简介",
  "logo": "string"
}
```

### 9.3 获取时段配置

**接口**: `GET /settings/time-periods`

**说明**: 获取时段配置（无需登录）

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| storeId | string | 否 | 门店 ID |

**响应数据**:
```json
{
  "periods": [
    {
      "key": "morning",
      "name": "上午",
      "startTime": "08:00",
      "endTime": "12:00"
    },
    {
      "key": "afternoon",
      "name": "下午",
      "startTime": "14:00",
      "endTime": "17:00"
    }
  ],
  "isCustom": false
}
```

## 十、门店模块

### 10.1 通过编码获取门店信息（公开）

**接口**: `GET /stores/by-code/:code`

**说明**: 根据门店编码获取门店信息（无需登录）

**路径参数**:
- `code`: 门店编码

**响应数据**:
```json
{
  "id": "string",
  "code": "string",
  "name": "XX门店",
  "address": "XX市XX区XX路XX号",
  "phone": "0123-12345678",
  "status": 1
}
```

### 10.2 获取门店签到二维码

**接口**: `GET /stores/:storeId/checkin-qrcode`

**说明**: 获取门店的签到二维码信息

**路径参数**:
- `storeId`: 门店 ID

**响应数据**:
```json
{
  "storeId": "string",
  "storeName": "XX门店",
  "qrcodeContent": "store-checkin:xxx",
  "description": "请扫描此二维码进行签到"
}
```

## 十一、反馈模块

### 11.1 提交反馈

**接口**: `POST /feedbacks`

**说明**: 提交用户反馈

**请求参数**:
```json
{
  "userId": "string",
  "userType": "string",
  "feedbackType": "bug",
  "title": "string",
  "content": "string",
  "images": ["string"],
  "contact": "string"
}
```

**响应数据**:
```json
{
  "id": "string",
  "userId": "string",
  "userType": "string",
  "feedbackType": "bug",
  "title": "string",
  "content": "string",
  "images": ["string"],
  "contact": "string",
  "status": 1,
  "createdAt": "2024-01-01T00:00:00Z"
}
```

### 11.2 获取我的反馈列表

**接口**: `GET /feedbacks/my`

**说明**: 获取当前用户的反馈列表

**请求参数**:
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户 ID |

**响应数据**: 反馈列表

## 错误码说明

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| 0/200 | 成功 | - |
| 400 | 请求参数错误 | 检查请求参数 |
| 401 | 未授权 | 跳转登录页 |
| 403 | 无权限 | 提示用户无权限 |
| 404 | 资源不存在 | 提示资源不存在 |
| 500 | 服务器错误 | 提示稍后重试 |
| 1001 | 重复预约 | 提示用户已有预约 |
| 1002 | 号源已满 | 提示选择其他时段 |
| 1003 | 超过预约限制 | 提示超过每日预约上限 |
| 1004 | 签到时间未到 | 提示签到时间 |
| 1005 | 签到已超时 | 提示已超时 |

---

**文档版本**: v1.0  
**最后更新**: 2026-01-08  
**维护者**: Manus AI
