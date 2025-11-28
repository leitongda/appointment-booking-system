# 🏥 医院挂号系统

一套完整的医院挂号系统解决方案，包含机构端、患者端、医生端三个平台。

## 📋 项目简介

本项目是一个基于 React + FastAPI 的全栈医院挂号系统，支持在线预约挂号、智能排班、就诊管理、病历管理等功能。

### 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          医院挂号系统                                │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│    机构端       │     患者端       │          医生端                 │
│   (Admin)      │  (H5 + 小程序)   │        (Doctor)                │
├─────────────────┼─────────────────┼─────────────────────────────────┤
│ • 权限管理     │ • 用户注册登录   │ • 个人信息管理                  │
│ • 门店管理     │ • 科室/医生查询  │ • 排班管理                      │
│ • 科室管理     │ • 预约挂号       │ • 预约列表                      │
│ • 医生管理     │ • 挂号记录       │ • 就诊管理                      │
│ • 排班管理     │ • 就诊记录       │ • 病历填写                      │
│ • 预约管理     │ • 消息通知       │ • 数据统计                      │
│ • 内容管理     │ • 个人中心       │ • 消息通知                      │
│ • 系统设置     │                  │                                 │
│ • 数据统计     │                  │                                 │
└─────────────────┴─────────────────┴─────────────────────────────────┘
```

## 🛠️ 技术栈

### 前端
- **框架**: React 18 + TypeScript
- **路由/框架**: Umi 4
- **UI组件**: Ant Design 5 + ProComponents
- **状态管理**: Zustand
- **请求库**: @tanstack/react-query

### 后端
- **语言**: Python 3.12+
- **框架**: FastAPI
- **ORM**: SQLAlchemy 2.x
- **数据库**: PostgreSQL 16
- **缓存**: Redis 7
- **任务队列**: Celery

## 📁 项目结构

```
appointment-booking-system/
├── apps/                          # 应用目录
│   ├── admin/                     # 机构端 (React + Umi)
│   ├── patient-h5/                # 患者端 H5 (React + Umi)
│   ├── patient-miniapp/           # 患者端小程序
│   ├── doctor/                    # 医生端 (React + Umi)
│   └── server/                    # 后端服务 (FastAPI)
│
├── packages/                      # 共享包
│   ├── api/                       # API 请求封装/类型定义
│   └── shared/                    # 共享组件/工具
│
├── docs/                          # 项目文档
│   ├── PRD.md                     # 产品需求文档
│   ├── architecture.md            # 架构设计文档
│   ├── flowcharts.md              # 流程图文档
│   ├── database/                  # 数据库文档
│   │   ├── er-diagram.md          # ER图
│   │   └── schema.sql             # 数据库表结构
│   ├── api/                       # API文档
│   │   └── README.md              # API概览
│   └── modules/                   # 模块需求文档
│
├── docker-compose.yml             # Docker编排
├── package.json                   # 项目配置
├── pnpm-workspace.yaml            # pnpm工作空间
└── README.md                      # 项目说明
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

### 启动开发服务

```bash
# 使用 Docker Compose 启动基础服务
docker-compose up -d postgres redis

# 启动后端服务
cd apps/server
uvicorn app.main:app --reload

# 启动前端服务
pnpm dev:admin           # 机构端
pnpm dev:patient-h5      # 患者端 H5
pnpm dev:patient-miniapp # 患者端小程序
pnpm dev:doctor          # 医生端
```

### 访问地址
- 机构端: http://localhost:8001
- 患者端 H5: http://localhost:8002
- 医生端: http://localhost:8003
- API文档: http://localhost:8000/docs
- 患者端小程序: 使用微信开发者工具打开 `apps/patient-miniapp`

## 📖 文档

详细文档请查看 [docs](./docs) 目录：

- [PRD产品需求文档](./docs/PRD.md)
- [系统架构设计](./docs/architecture.md)
- [系统流程图](./docs/flowcharts.md)
- [数据库ER图](./docs/database/er-diagram.md)
- [数据库表结构](./docs/database/schema.sql)
- [API接口文档](./docs/api/README.md)

## 🔧 核心功能

### 机构端
- ✅ 权限管理（角色、管理员、操作日志）
- ✅ 门店管理（多分院支持）
- ✅ 科室管理（树形结构）
- ✅ 医生管理（信息、排班、预约设置）
- ✅ 患者管理（档案、黑名单）
- ✅ 排班管理（模板、自定义、停诊）
- ✅ 预约管理（列表、统计、签到）
- ✅ 内容管理（新闻、公告、轮播图）
- ✅ 系统设置（预约规则、微信配置）

### 患者端
- ✅ 用户注册/登录
- ✅ 科室/医生浏览
- ✅ 在线预约挂号
- ✅ 预约记录查看
- ✅ 扫码签到
- ✅ 就诊记录/病历查看
- ✅ 消息通知
- ✅ 就诊人管理

### 医生端
- ✅ 排班查看/申请
- ✅ 预约管理
- ✅ 叫号管理
- ✅ 病历填写
- ✅ 数据统计

## 🐳 Docker 部署

```bash
# 构建镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 📄 License

[MIT](LICENSE)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

