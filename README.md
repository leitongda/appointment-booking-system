# 🏥 医院挂号系统

一套完整的医院挂号系统解决方案，包含机构端、患者端（H5 + 小程序）、医生端三个平台。

## 📋 项目简介

本项目是一个基于 React + FastAPI 的全栈医院挂号系统，支持多门店管理、智能排班、在线预约挂号、就诊管理、病历管理、诊费配置等功能。

### 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             医院挂号系统                                      │
├─────────────────┬─────────────────┬─────────────────────────────────────────┤
│    机构端       │     患者端       │              医生端                      │
│   (Admin)      │  (H5 + 小程序)   │            (Doctor)                     │
├─────────────────┼─────────────────┼─────────────────────────────────────────┤
│ • 仪表盘       │ • 用户注册登录   │ • 工作台仪表盘                          │
│ • 门店管理     │ • 科室/医生查询  │ • 排班查看                              │
│ • 科室管理     │ • 预约挂号       │ • 今日预约                              │
│ • 医生管理     │ • 挂号记录       │ • 历史预约                              │
│ • 预约设置     │ • 就诊记录       │ • 叫号就诊                              │
│ • 排班管理     │ • 消息通知       │ • 病历填写                              │
│ • 预约管理     │ • 就诊人管理     │ • 停诊/调班申请                         │
│ • 患者管理     │ • 意见反馈       │ • 数据统计                              │
│ • 停诊审核     │                  │ • 消息中心                              │
│ • 消息管理     │                  │                                         │
│ • 内容管理     │                  │                                         │
│ • 统计分析     │                  │                                         │
│ • 系统设置     │                  │                                         │
└─────────────────┴─────────────────┴─────────────────────────────────────────┘
```

## 🛠️ 技术栈

### 前端
- **框架**: React 18 + TypeScript
- **路由/框架**: Umi 4
- **UI 组件**: Ant Design 5 + ProComponents
- **状态管理**: Zustand
- **请求库**: @tanstack/react-query
- **构建工具**: Turbo (Monorepo)
- **小程序**: Taro 3

### 后端
- **语言**: Python 3.12+
- **框架**: FastAPI
- **ORM**: SQLAlchemy 2.x
- **数据库**: PostgreSQL 16
- **缓存**: Redis 7
- **任务队列**: Celery
- **数据库迁移**: Alembic

## 📁 项目结构

```
appointment-booking-system/
├── apps/                          # 应用目录
│   ├── admin/                     # 机构端 (React + Umi)
│   │   ├── config/                # 配置文件
│   │   └── src/pages/             # 页面组件
│   │       ├── dashboard/         # 仪表盘
│   │       ├── store/             # 门店管理
│   │       ├── department/        # 科室管理
│   │       ├── doctor/            # 医生管理
│   │       ├── schedule/          # 排班管理
│   │       ├── appointment/       # 预约管理
│   │       ├── patient/           # 患者管理
│   │       ├── leave-request/     # 停诊审核
│   │       ├── message/           # 消息管理
│   │       ├── feedback/          # 用户反馈
│   │       ├── content/           # 内容管理
│   │       ├── statistics/        # 统计分析
│   │       └── system/            # 系统设置
│   │
│   ├── patient-h5/                # 患者端 H5 (React + Umi)
│   │   └── src/pages/
│   │       ├── home/              # 首页
│   │       ├── department/        # 科室列表/详情
│   │       ├── doctor/            # 医生列表/详情
│   │       ├── booking/           # 预约挂号
│   │       ├── appointment/       # 预约记录
│   │       ├── records/           # 就诊记录
│   │       ├── message/           # 消息中心
│   │       ├── feedback/          # 意见反馈
│   │       └── profile/           # 个人中心
│   │
│   ├── patient-miniapp/           # 患者端小程序 (Taro)
│   │   └── src/pages/             # 小程序页面
│   │
│   ├── doctor/                    # 医生端 (React + Umi)
│   │   └── src/pages/
│   │       ├── dashboard/         # 工作台
│   │       ├── schedule/          # 排班查看
│   │       ├── appointment/       # 预约管理
│   │       ├── consultation/      # 叫号就诊
│   │       ├── medical-record/    # 病历管理
│   │       ├── leave-request/     # 停诊申请
│   │       ├── statistics/        # 数据统计
│   │       └── message/           # 消息中心
│   │
│   └── server/                    # 后端服务 (FastAPI)
│       ├── app/
│       │   ├── api/v1/            # API 路由
│       │   ├── models/            # 数据模型
│       │   ├── schemas/           # 请求/响应模式
│       │   ├── services/          # 业务逻辑
│       │   ├── core/              # 核心配置
│       │   ├── db/                # 数据库配置
│       │   └── middleware/        # 中间件
│       ├── migrations/            # 数据库迁移
│       └── scripts/               # 初始化脚本
│
├── packages/                      # 共享包
│   ├── api/                       # API 请求封装/类型定义
│   │   └── src/modules/           # 各模块 API
│   └── shared/                    # 共享组件/工具/类型
│       └── src/
│           ├── constants/         # 常量定义
│           ├── types/             # TypeScript 类型
│           └── utils/             # 工具函数
│
├── docs/                          # 项目文档
├── docker-compose.yml             # Docker 编排
├── package.json                   # 项目配置
└── pnpm-workspace.yaml            # pnpm 工作空间
```

## 🚀 快速开始

### 环境要求
- Node.js 20+
- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- pnpm 8+

### 安装依赖

```bash
# 前端依赖
pnpm install

# 后端依赖
cd apps/server
pip install -r requirements.txt
```

### 环境配置

后端服务需要配置环境变量才能运行。请按以下步骤配置：

```bash
# 进入后端目录
cd apps/server

# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，根据实际情况修改配置
```

**必需配置项：**

| 变量名 | 说明 | 示例值 |
|--------|------|--------|
| `DATABASE_URL` | PostgreSQL 数据库连接 | `postgresql+asyncpg://user:pass@localhost:5432/dbname` |
| `REDIS_URL` | Redis 连接地址 | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT 签名密钥 | 使用 `openssl rand -hex 32` 生成 |

> ⚠️ **安全提示**：生产环境务必修改 `SECRET_KEY` 为强随机字符串，切勿使用默认值！

完整配置项说明请查看 `apps/server/.env.example` 文件。

### 启动开发服务

```bash
# 使用 Docker Compose 启动基础服务
docker-compose up -d postgres redis

# 启动后端服务
pnpm dev:server

# 启动前端服务（选择需要的端）
pnpm dev:admin           # 机构端
pnpm dev:patient-h5      # 患者端 H5
pnpm dev:patient-miniapp # 患者端小程序
pnpm dev:doctor          # 医生端
```

### 访问地址
| 服务 | 地址 |
|------|------|
| 机构端 | http://localhost:8001 |
| 患者端 H5 | http://localhost:8002 |
| 医生端 | http://localhost:8003 |
| API 文档 | http://localhost:8000/docs |
| 患者端小程序 | 使用微信开发者工具打开 `apps/patient-miniapp` |

## 🔧 核心功能

### 机构端 (Admin)

| 模块 | 功能 |
|------|------|
| **仪表盘** | 数据概览、预约趋势、快捷入口 |
| **门店管理** | 多分院支持、门店信息、科室关联 |
| **科室管理** | 树形结构、科室信息、排序管理 |
| **医生管理** | 医生列表、医生详情、预约设置、诊费配置 |
| **排班管理** | 排班列表、排班模板、自定义排班、休息日设置、停诊管理、排班统计 |
| **预约管理** | 预约列表、预约详情、预约签到 |
| **患者管理** | 患者列表、患者详情、黑名单管理 |
| **停诊审核** | 停诊/调班申请审核、批量处理 |
| **消息管理** | 消息模板、推送记录 |
| **用户反馈** | 反馈列表、回复管理 |
| **内容管理** | 新闻管理、公告管理、轮播图 |
| **统计分析** | 预约统计、科室统计、医生统计 |
| **系统设置** | 角色管理、管理员、系统配置、诊费类型、诊费模板、操作日志 |

### 患者端 (H5 + 小程序)

| 模块 | 功能 |
|------|------|
| **首页** | 搜索、科室导航、推荐医生、轮播图 |
| **科室浏览** | 科室列表、科室详情、科室下医生 |
| **医生浏览** | 医生列表、医生详情、出诊信息 |
| **预约挂号** | 选择时段、确认预约、支付（可扩展） |
| **预约记录** | 预约列表、预约详情、取消预约 |
| **就诊记录** | 就诊历史、病历查看 |
| **消息中心** | 预约通知、就诊提醒、系统消息 |
| **个人中心** | 个人信息、就诊人管理 |
| **意见反馈** | 提交反馈、查看回复 |

### 医生端 (Doctor)

| 模块 | 功能 |
|------|------|
| **工作台** | 今日概览、待诊数量、统计数据 |
| **排班查看** | 月视图、周视图、排班详情 |
| **今日预约** | 当日预约列表、患者信息 |
| **历史预约** | 历史预约查询、筛选 |
| **叫号就诊** | 呼叫患者、过号、重呼、爽约标记 |
| **病历管理** | 病历填写、病历列表、病历详情 |
| **停诊申请** | 申请停诊、申请调班、申请记录 |
| **数据统计** | 接诊统计、月度报表 |
| **消息中心** | 系统通知、预约提醒 |

## 📡 API 模块

后端提供以下 RESTful API 模块：

| API 路由 | 说明 |
|----------|------|
| `/api/v1/auth` | 用户认证（登录/注册/令牌刷新） |
| `/api/v1/users` | 用户管理 |
| `/api/v1/stores` | 门店管理 |
| `/api/v1/departments` | 科室管理 |
| `/api/v1/doctors` | 医生管理 |
| `/api/v1/schedules` | 排班管理 |
| `/api/v1/schedule-templates` | 排班模板 |
| `/api/v1/custom-schedules` | 自定义排班 |
| `/api/v1/rest-days` | 休息日设置 |
| `/api/v1/schedule-suspensions` | 停诊管理 |
| `/api/v1/appointments` | 预约管理 |
| `/api/v1/patients` | 患者管理 |
| `/api/v1/blacklists` | 黑名单管理 |
| `/api/v1/medical-records` | 病历管理 |
| `/api/v1/leave-requests` | 停诊/调班申请 |
| `/api/v1/messages` | 消息中心 |
| `/api/v1/feedbacks` | 用户反馈 |
| `/api/v1/content` | 内容管理 |
| `/api/v1/statistics` | 数据统计 |
| `/api/v1/admin` | 权限管理 |
| `/api/v1/settings` | 系统设置 |
| `/api/v1/consultation-fees` | 诊费管理 |
| `/api/v1/doctor-booking-settings` | 医生预约设置 |
| `/api/v1/export` | 数据导出 |

## 🗃️ 数据模型

系统包含以下核心数据模型：

- **User / Patient** - 用户与患者（就诊人）
- **Store / StoreDepartment** - 门店与门店科室关联
- **Department** - 科室
- **Doctor** - 医生
- **DoctorBookingSetting** - 医生预约设置
- **Schedule** - 排班
- **ScheduleTemplate** - 排班模板
- **CustomSchedule** - 自定义排班
- **RestDay** - 休息日
- **ScheduleSuspension** - 停诊记录
- **Appointment** - 预约
- **MedicalRecord** - 病历
- **LeaveRequest** - 停诊/调班申请
- **ConsultationFeeType / Template / DoctorConsultationFee** - 诊费配置
- **Message / MessageTemplate** - 消息与消息模板
- **News / Notice / Banner** - 内容管理
- **Admin / Role / OperationLog** - 权限与日志
- **Feedback** - 用户反馈
- **Blacklist** - 黑名单
- **PointLog** - 积分日志
- **SystemSetting** - 系统设置

## 🐳 Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 📖 文档

详细文档请查看 [docs](./docs) 目录：

- [PRD 产品需求文档](./docs/PRD.md)
- [系统架构设计](./docs/architecture.md)
- [系统流程图](./docs/flowcharts.md)
- [数据库 ER 图](./docs/database/er-diagram.md)
- [数据库表结构](./docs/database/schema.sql)
- [API 接口文档](./docs/api/README.md)

## 🛡️ 安全特性

- JWT Token 认证
- 角色权限控制 (RBAC)
- 操作日志记录
- 敏感数据加密
- 黑名单机制

## 📄 License

[MIT](LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！



# 启动 PostgreSQL
brew services start postgresql@15

# 启动 Redis
brew services start redis