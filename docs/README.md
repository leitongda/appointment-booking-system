# 🏥 医院挂号系统 - 项目文档

## 文档目录

### 📋 需求文档
- [PRD产品需求文档](./PRD.md) - 完整的产品需求说明
- [系统架构设计](./architecture.md) - 技术架构与部署方案
- [系统流程图](./flowcharts.md) - 核心业务流程图

### 🗄️ 数据库设计
- [数据库ER图](./database/er-diagram.md) - 实体关系图
- [数据库表结构](./database/schema.sql) - 完整SQL DDL
- [数据字典](./database/data-dictionary.md) - 字段说明

### 🔌 API文档
- [API概览](./api/README.md) - 接口规范与约定
- [认证模块API](./api/auth.md)
- [用户模块API](./api/users.md)
- [科室模块API](./api/departments.md)
- [医生模块API](./api/doctors.md)
- [排班模块API](./api/schedules.md)
- [预约模块API](./api/appointments.md)
- [病历模块API](./api/medical-records.md)
- [内容模块API](./api/content.md)
- [系统设置API](./api/settings.md)
- [统计模块API](./api/statistics.md)

### 🖥️ 服务端开发指南
- [服务端概览](./server/README.md) - 技术栈、项目结构、快速开始
- [配置管理](./server/config.md) - 环境变量与配置项
- [Redis 缓存](./server/redis.md) - 缓存操作、验证码、Token
- [日志系统](./server/logging.md) - 日志配置与使用
- [中间件](./server/middleware.md) - 限流、请求日志、响应格式
- [异常处理](./server/exception.md) - 异常类型与错误码
- [数据库操作](./server/database.md) - ORM 使用与连接池

### 📝 模块需求文档
- [权限管理模块](./modules/permission.md)
- [门店管理模块](./modules/branch.md)
- [科室管理模块](./modules/department.md)
- [医生管理模块](./modules/doctor.md)
- [患者管理模块](./modules/patient.md)
- [排班管理模块](./modules/schedule.md)
- [预约管理模块](./modules/appointment.md)
- [内容管理模块](./modules/content.md)
- [系统设置模块](./modules/settings.md)
- [数据统计模块](./modules/statistics.md)

---

## 快速开始

### 启动服务端

```bash
# 安装依赖
cd apps/server
pip install -r requirements.txt

# 启动数据库
docker-compose up -d postgres redis

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 启动管理后台

```bash
cd apps/admin
pnpm install
pnpm dev
```

### 启动患者端 H5

```bash
cd apps/patient-h5
pnpm install
pnpm dev
```

### 启动医生端

```bash
cd apps/doctor
pnpm install
pnpm dev
```

---

**版本**: v1.0.0  
**更新日期**: 2024年  
**负责人**: 开发团队
