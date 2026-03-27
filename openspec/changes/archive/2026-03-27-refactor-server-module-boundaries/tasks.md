## 1. 基线与约束

- [x] 1.1 盘点现有 Server 端模块映射、超大文件和边界违规点
- [x] 1.2 为关键接口补充特征测试，覆盖 `admin`、`appointments`、`schedules`、`content`
- [x] 1.3 新增架构约束测试，禁止 Router 内定义业务 DTO
- [x] 1.4 新增架构约束测试，禁止 Router 直接执行 ORM 查询

## 2. 新结构骨架

- [x] 2.1 创建 `app/modules`、`app/common`、`app/infrastructure` 目录骨架
- [x] 2.2 抽离通用依赖到 `app/common/deps`
- [x] 2.3 抽离统一响应与错误处理辅助到 `app/common`
- [x] 2.4 调整 `main.py` 和 API 聚合方式以支持新模块注册

## 3. 低风险样板迁移

- [x] 3.1 迁移 `content` 模块到新结构
- [x] 3.2 迁移 `booking_notices` 模块到新结构
- [x] 3.3 迁移 `store_email_recipients` 模块到新结构
- [x] 3.4 保持旧 API 行为不变并补充回归测试

## 4. 超大文件拆分

- [x] 4.1 拆分 `api/v1/admin.py` 为认证、管理员、角色权限、审计日志等子模块
- [x] 4.2 拆分 `api/v1/import_export.py` 为按领域组织的导入导出模块
- [x] 4.3 拆分 `api/v1/doctor_portal.py` 为日程、候诊、病历、随访子模块
- [x] 4.4 拆分 `services/appointment_service.py` 为预约创建、签到、叫号、状态流转子服务
- [x] 4.5 拆分 `services/patient_service.py` 为患者档案、家庭成员、后台患者管理子服务

## 5. 基础设施与运行期数据

- [x] 5.1 将存储、邮件、微信、Excel 等适配层整理到 `app/infrastructure`
- [x] 5.2 为日志与上传目录引入明确的运行期目录配置
- [x] 5.3 更新 `.gitignore`、部署文档和本地开发说明

## 6. 收尾

- [x] 6.1 删除完成迁移模块的兼容导入
- [x] 6.2 更新 `docs/server` 架构文档
- [x] 6.3 运行测试并修复回归
- [x] 6.4 复核所有任务并更新状态
