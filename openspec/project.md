# Project Context

## Purpose

医院挂号系统 (Hospital Appointment Booking System) - 一套完整的医疗预约挂号解决方案，支持多门店管理、智能排班、在线预约挂号、就诊管理、病历管理、诊费配置等功能。

**核心目标：**
- **提升患者体验**：实现线上预约挂号，减少现场排队时间
- **优化医院管理**：智能排班、号源管理、数据统计分析
- **提高医生效率**：便捷的叫号系统、病历管理、排班查看
- **数据驱动决策**：多维度数据统计，辅助医院运营决策

**目标用户：**
| 用户角色 | 说明 | 使用平台 |
|---------|------|---------|
| 机构管理员 | 医院管理人员、运营人员 | Admin Web |
| 医生 | 各科室医生 | Doctor Web |
| 患者 | 就诊患者及家属 | Patient H5 / 微信小程序 |

## Tech Stack

### 前端
- **框架**: React 18 + TypeScript 5.x
- **路由/框架**: Umi 4 (@umijs/max)
- **UI 组件**: Ant Design 5 + ProComponents 2.x
- **状态管理**: Zustand 4.x
- **数据请求**: @tanstack/react-query 5.x
- **小程序**: Taro 3.x
- **图表**: ECharts / AntV
- **工具库**: Day.js, Lodash

### 后端
- **语言**: Python 3.12+
- **框架**: FastAPI 0.109+
- **ORM**: SQLAlchemy 2.x (async)
- **数据校验**: Pydantic 2.x
- **数据库**: PostgreSQL 16
- **缓存/会话**: Redis 7.x
- **异步任务**: Celery 5.x
- **数据库迁移**: Alembic

### 工程化
- **包管理**: pnpm 8.x (Monorepo)
- **构建工具**: Turbo 2.x
- **容器化**: Docker + Docker Compose
- **运行时**: Node.js 20+

## Project Conventions

### 代码结构

```
appointment-booking-system/
├── apps/                          # 应用目录
│   ├── admin/                     # 机构端 (React + Umi)
│   ├── patient-h5/                # 患者端 H5 (React + Umi)
│   ├── patient-miniapp/           # 患者端小程序 (Taro)
│   ├── doctor/                    # 医生端 (React + Umi)
│   └── server/                    # 后端服务 (FastAPI)
├── packages/                      # 共享包
│   ├── api/                       # API 请求封装/类型定义
│   └── shared/                    # 共享组件/工具/类型
└── docs/                          # 项目文档
```

### Code Style

**前端 (TypeScript/React):**
- 使用 TypeScript 严格模式
- 组件文件使用 PascalCase 命名 (如 `DoctorList.tsx`)
- 工具函数使用 camelCase 命名 (如 `formatDate.ts`)
- 样式文件使用 `.less` 格式，与组件同名 (如 `DoctorList.less`)
- 使用函数式组件 + Hooks
- 页面组件放置于 `pages/[module]/` 目录
- 共享类型定义放置于 `packages/shared/src/types/`
- 共享常量放置于 `packages/shared/src/constants/`

**后端 (Python/FastAPI):**
- 遵循 PEP 8 代码风格
- 文件名使用 snake_case (如 `doctor_service.py`)
- 类名使用 PascalCase (如 `DoctorService`)
- 函数名使用 snake_case (如 `get_doctor_by_id`)
- API 路由遵循 RESTful 规范
- 使用 Pydantic 进行请求/响应校验
- 使用 async/await 进行异步操作

**目录命名规范:**
- 前端页面目录使用 kebab-case (如 `leave-request/`)
- 后端模块目录使用 snake_case (如 `medical_records/`)

### Architecture Patterns

**后端分层架构:**
```
┌─────────────────────────────────────────────────────────────┐
│                        API 层 (Router)                       │
│  职责: 路由定义、请求参数校验、响应格式化、权限检查           │
├─────────────────────────────────────────────────────────────┤
│                      服务层 (Service)                        │
│  职责: 业务逻辑处理、事务管理、业务校验                       │
├─────────────────────────────────────────────────────────────┤
│                      模型层 (Model)                          │
│  职责: 数据表映射、关系定义 (SQLAlchemy)                     │
├─────────────────────────────────────────────────────────────┤
│                     Schema层 (Pydantic)                      │
│  职责: 请求/响应数据结构定义、数据校验                        │
└─────────────────────────────────────────────────────────────┘
```

**前端架构模式:**
- 页面组件负责布局和数据获取
- 使用 ProComponents 进行表格、表单等业务组件开发
- 使用 React Query 进行服务端状态管理
- 使用 Zustand 进行客户端状态管理
- API 请求封装在 `packages/api/` 中统一管理

**认证授权:**
- JWT Token 认证 (Access Token + Refresh Token)
- RBAC 权限控制 (角色-权限模型)
- 前端路由权限通过 `access.ts` 配置

### Testing Strategy

**后端测试:**
- 使用 pytest + pytest-asyncio 进行单元测试
- 测试文件放置于 `apps/server/tests/` 目录
- 测试函数命名: `test_[功能描述]`

**前端测试:**
- 当前以手动测试为主
- 可扩展使用 Jest + React Testing Library

### Git Workflow

**分支策略:**
- `main`: 生产环境分支
- `develop`: 开发环境分支
- `feature/[功能名]`: 功能开发分支
- `fix/[问题描述]`: Bug 修复分支

**提交规范:**
- `feat: 新功能`
- `fix: Bug 修复`
- `docs: 文档更新`
- `style: 代码格式调整`
- `refactor: 代码重构`
- `perf: 性能优化`
- `chore: 构建/工具变更`

## Domain Context

### 核心领域概念

| 术语 | 说明 |
|------|------|
| **号源** | 医生可预约的挂号名额，由排班生成 |
| **排班** | 医生的出诊时间安排，包含日期、时段、号源数量 |
| **排班模板** | 周期性排班规则，用于自动生成排班 |
| **签到** | 患者到院后确认到达，进入候诊队列 |
| **叫号** | 医生呼叫下一位就诊患者 |
| **爽约** | 患者预约后未到院就诊 |
| **停诊** | 医生临时取消出诊 |
| **过号** | 患者错过叫号后重新排队 |
| **就诊人** | 患者账号下管理的实际就诊人员 (本人或家属) |
| **诊费** | 医生的诊费配置，通过诊费类型和模板系统管理，支持初诊/复诊不同费用 |

### 核心数据模型

- **User / Patient** - 用户与就诊人
- **Store / StoreDepartment** - 门店与门店科室关联
- **Department** - 科室
- **Doctor / DoctorBookingSetting** - 医生与预约设置
- **Schedule / ScheduleTemplate / CustomSchedule** - 排班相关
- **RestDay / ScheduleSuspension** - 休息日与停诊
- **Appointment** - 预约
- **MedicalRecord** - 病历
- **LeaveRequest** - 停诊/调班申请
- **ConsultationFeeType / DoctorConsultationFee** - 诊费配置
- **Message / MessageTemplate** - 消息与模板
- **Admin / Role** - 权限管理

### 预约状态流转

```
待支付 → 已预约 → 已签到 → 候诊中 → 就诊中 → 已完成
           ↓         ↓
        已取消     已过期/爽约
```

## Important Constraints

### 技术约束
- **Node.js**: 需要 20.0.0+
- **Python**: 需要 3.12+
- **pnpm**: 需要 8.0.0+
- **PostgreSQL**: 需要 16+
- **Redis**: 需要 7+

### 安全约束
- 敏感数据 (身份证、密码等) 必须加密存储
- 所有 API 必须进行权限验证
- 操作日志必须记录关键操作
- 医疗数据需遵循隐私保护规范

### 业务约束
- 预约需检查号源可用性
- 同一时段同一就诊人不可重复预约
- 停诊需通知已预约患者
- 爽约次数超限需加入黑名单

### 性能约束
- API 响应时间 ≤ 500ms (P99)
- 页面加载时间 ≤ 2秒
- 系统可用性 ≥ 99.9%

## External Dependencies

### 微信生态
- **微信小程序**: 患者端小程序入口
- **微信支付**: 预约支付 (可选)
- **微信消息模板**: 预约提醒、就诊通知

### 短信服务
- **阿里云短信** / **腾讯云短信**: 预约确认、就诊提醒 (可选)

### 基础设施
- **PostgreSQL**: 主数据库
- **Redis**: 缓存、会话、任务队列
- **Celery**: 异步任务处理 (通知、定时任务)
- **MinIO / 阿里云 OSS**: 文件存储 (可选)
- **Nginx**: 反向代理、静态资源服务

## 开发端口

| 服务 | 端口 |
|------|------|
| 机构端 (Admin) | http://localhost:8001 |
| 患者端 H5 | http://localhost:8002 |
| 医生端 (Doctor) | http://localhost:8003 |
| API 服务 | http://localhost:8000 |
| API 文档 | http://localhost:8000/docs |

## 快速启动

```bash
# 安装前端依赖
pnpm install

# 安装后端依赖
cd apps/server && pip install -r requirements.txt

# 启动基础服务
docker-compose up -d postgres redis

# 启动后端
pnpm dev:server

# 启动前端 (选择需要的)
pnpm dev:admin           # 机构端
pnpm dev:patient-h5      # 患者端 H5
pnpm dev:doctor          # 医生端
pnpm dev:patient-miniapp # 患者端小程序
```
