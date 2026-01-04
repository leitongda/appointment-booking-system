# 🏥 医院挂号系统 - 技术栈概览

本文档提供项目各端技术栈的快速参考。

---

## 📐 整体架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           医院挂号系统 (Monorepo)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Turborepo + pnpm Workspace                                                 │
├─────────────────┬─────────────────┬─────────────────┬─────────────────────────┤
│    机构端 Admin │   患者端 H5     │  患者端小程序    │     医生端 Doctor      │
│    :8005       │    :8002        │   微信开发者工具  │        :8003          │
├─────────────────┴─────────────────┴─────────────────┴─────────────────────────┤
│                    packages/api + packages/shared (共享层)                    │
├──────────────────────────────────────────────────────────────────────────────┤
│                          FastAPI 后端服务 :8000                               │
├──────────────────────────────────────────────────────────────────────────────┤
│         PostgreSQL 16       │      Redis 7       │       MinIO             │
└─────────────────────────────┴────────────────────┴──────────────────────────┘
```

---

## 🖥️ 各端技术栈

### 1. 机构端 (Admin) - `apps/admin`

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18 | 核心框架 |
| **TypeScript** | 5.6+ | 类型安全 |
| **Umi Max** | 4.6+ | 企业级前端框架（路由、数据流、构建） |
| **Ant Design** | 5.29+ | UI 组件库 |
| **ProComponents** | 2.8+ | 高级业务组件（ProTable、ProForm 等） |
| **@ant-design/charts** | 2.6+ | 图表组件 |
| **wangEditor** | 5.1+ | 富文本编辑器（开源免费） |
| **dayjs** | 1.11+ | 日期处理 |
| **@dnd-kit** | 6.x | 拖拽排序功能 |

**功能模块**：仪表盘、门店管理、科室管理、医生管理、排班管理、预约管理、患者管理、停诊审核、消息管理、内容管理、统计分析、系统设置

---

### 2. 患者端 H5 - `apps/patient-h5`

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18.2 | 核心框架 |
| **TypeScript** | 5.3+ | 类型安全 |
| **Umi** | 4.1+ | 前端框架 |
| **Ant Design Mobile** | 5.34+ | 移动端 UI 组件库 |
| **TailwindCSS** | 3.4+ | 原子化 CSS 框架 |
| **TanStack Query** | 5.17+ | 服务端状态管理（数据请求缓存） |
| **Zustand** | 4.4+ | 客户端状态管理 |
| **Framer Motion** | 12+ | 动画库 |

**功能模块**：首页、科室浏览、医生浏览、预约挂号、预约记录、就诊记录、消息中心、个人中心、意见反馈

---

### 3. 患者端小程序 - `apps/patient-miniapp`

| 技术 | 版本 | 用途 |
|------|------|------|
| **Taro** | 3.6.38 | 跨端开发框架（主要编译为微信小程序） |
| **React** | 18.2 | 核心框架 |
| **NutUI React Taro** | 2.3 | 京东风格移动端 UI 组件库 |
| **Less** | 4.2+ | CSS 预处理器 |
| **TypeScript** | 5.3+ | 类型安全 |

**支持平台**：微信小程序（主要）、支付宝小程序、百度小程序、H5

---

### 4. 医生端 (Doctor) - `apps/doctor`

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18 | 核心框架 |
| **TypeScript** | 5+ | 类型安全 |
| **Umi** | 4+ | 前端框架 |
| **Ant Design Pro** | 同 Admin | UI 组件库 |

**功能模块**：工作台、排班查看、今日/历史预约、叫号就诊、病历管理、停诊申请、数据统计、消息中心

---

### 5. 后端服务 (Server) - `apps/server`

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.12+ | 编程语言 |
| **FastAPI** | 0.115+ | 高性能异步 Web 框架 |
| **SQLAlchemy** | 2.x (async) | ORM 框架（异步支持） |
| **Pydantic** | 2.10+ | 数据验证与序列化 |
| **PostgreSQL** | 16+ | 主数据库 |
| **Redis** | 7+ | 缓存、会话、消息队列 |
| **Celery** | 5.3+ | 分布式异步任务队列 |
| **Alembic** | 1.14+ | 数据库迁移工具 |
| **MinIO** | 7.2+ | 对象存储（图片、文件） |
| **python-jose** | 3.3+ | JWT 认证 |
| **Uvicorn** | 0.32+ | ASGI 服务器 |

**后端架构层次**：

```
app/
├── api/v1/       # API 路由层（RESTful 接口）
├── models/       # 数据模型层（SQLAlchemy ORM）
├── schemas/      # 请求/响应模式（Pydantic）
├── services/     # 业务逻辑层
├── core/         # 核心配置（认证、Redis、设置）
├── db/           # 数据库连接与会话
├── middleware/   # 中间件（日志、异常处理）
└── tasks/        # Celery 异步任务
```

---

## 📦 共享包 (Packages)

### `packages/api` (@hospital/api)

- **Axios** 封装的 HTTP 请求客户端
- 统一的 API 请求/响应类型定义
- **JSEncrypt** 用于敏感数据加密

### `packages/shared` (@hospital/shared)

- 共享 TypeScript 类型定义
- 常量定义（状态枚举、配置项）
- 工具函数（格式化、验证等）

---

## 🔧 工程化工具

| 工具 | 版本 | 用途 |
|------|------|------|
| **pnpm** | 8.15+ | 包管理器（高效、节省磁盘） |
| **Turborepo** | 2.7+ | Monorepo 构建系统（缓存、并行构建） |
| **Docker Compose** | - | 容器编排（PostgreSQL、Redis、MinIO） |
| **ESLint** | - | 代码规范检查 |
| **Vitest** | 1.2+ | 单元测试 |

---

## 🛡️ 安全特性

- **JWT Token** 认证机制
- **RBAC** 角色权限控制
- 操作日志记录
- 敏感数据加密（RSA）
- 黑名单机制

---

## 📊 架构特点总结

1. **Monorepo 架构**：使用 pnpm workspace + Turborepo 管理多个应用，共享代码和依赖
2. **前后端分离**：前端采用 React 生态，后端采用 Python FastAPI
3. **跨端统一**：患者端同时支持 H5 和微信小程序，共享业务逻辑
4. **异步优先**：后端全异步（async/await），高并发性能好
5. **类型安全**：前端 TypeScript + 后端 Pydantic，全链路类型检查

---

## 🚀 快速启动

```bash
# 安装前端依赖
pnpm install

# 安装后端依赖
cd apps/server && pip install -r requirements.txt

# 启动基础服务（Docker）
docker-compose up -d postgres redis minio

# 启动后端
pnpm dev:server          # http://localhost:8000

# 启动前端（选择需要的端）
pnpm dev:admin           # http://localhost:8005
pnpm dev:patient-h5      # http://localhost:8002
pnpm dev:doctor          # http://localhost:8003
pnpm dev:patient-miniapp # 微信开发者工具打开
```

---

## 📚 相关文档

- [系统架构设计](./architecture.md) - 详细架构设计文档
- [数据库 ER 图](./database/er-diagram.md) - 数据库关系图
- [数据库表结构](./database/schema.sql) - DDL 语句
- [API 接口文档](./api/README.md) - RESTful API 说明
- [PRD 产品需求文档](./PRD.md) - 产品需求说明

