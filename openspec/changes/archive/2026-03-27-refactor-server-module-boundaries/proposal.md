# Change: 重构 Server 端模块边界与代码组织

## Why
当前 `apps/server/app` 已形成较大的扁平分层结构，路由层、Schema 层、Service 层的职责边界不稳定，多个核心文件体积过大，且运行期日志与上传目录落在源码树中，增加了维护、测试和重构成本。

## What Changes
- 为 Server 端建立明确的模块边界规范，统一路由、Schema、服务、查询和基础设施职责
- 将后端从“按技术层平铺”演进为“按领域模块组织”的模块化单体结构
- 约束 Router 不再直接定义业务 DTO 或直接执行 ORM 查询
- 拆分超大文件，降低单文件复杂度并清理命名重叠
- 将日志、上传等运行期数据从源码目录默认位置迁出
- 新增架构约束测试，防止边界回退

## Impact
- Affected specs: `server-module-boundaries` (new)
- Affected code:
  - `apps/server/app/api/v1/**`
  - `apps/server/app/services/**`
  - `apps/server/app/schemas/**`
  - `apps/server/app/core/config.py`
  - `apps/server/app/main.py`
  - `apps/server/tests/**`
  - `docs/server/**`
