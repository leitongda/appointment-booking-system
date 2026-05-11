# 账号体系问题与解决方案清单

更新时间：2026-05-11
范围：`admin` / `doctor` / `user` 认证、账号模型、租户隔离、前后端账号流程

## 执行清单（完成一项勾选一项）

本轮已完成：P0-1、P0-2、P1-1、P1-2、P1-3、P1-4、P1-6、P2-1、P2-2（见下方勾选状态）。

- [x] **P0 权限漏洞：普通用户 token 可能被识别为超级管理员**
  - 问题：`get_current_admin` 对非 `admin` token 存在“旧 User 兼容分支”，并返回 `is_super_admin=True`、`permissions=["*"]`。
  - 解决方案：
    - 删除该兼容分支，非 `admin` token 直接返回 401/403。
    - 管理后台全部改为 `get_current_account_with_role(RoleType.ADMIN)`。
    - 增加回归测试：`user token` 访问 `/admin/*` 必须失败。

- [x] **P0 多租户串租风险：用户登录关键查询未强制 tenant 过滤**
  - 问题：`get_by_phone/get_by_openid/get_by_unionid` 存在不带 `tenant_id` 查询路径，可能在同手机号/同 openid 的多租户场景串租。
  - 解决方案：
    - 所有认证查询接口强制显式传入 `tenant_id`，禁止“无 tenant 查询”。
    - 对 `X-Tenant-Code` 场景先解析租户，再查询账号。
    - 增加集成测试：跨租户同手机号登录只能命中当前租户账号。

- [x] **P1 统一头像同步未生效（异步调用缺失 await）**
  - 问题：`AccountSyncService._update_account_field(...)` 调用缺失 `await`，同步可能未执行。
  - 解决方案：
    - 修正为 `await AccountSyncService._update_account_field(...)`。
    - 失败时明确记录并返回统一错误码。
    - 增加单测：上传头像后旧表与 `accounts.avatar` 一致。

- [x] **P1 医生端邮箱管理未闭环**
  - 问题：医生端调用患者 `/auth/email/*` 逻辑，依赖 `get_current_user`，与医生 token 不匹配。
  - 解决方案：
    - 新增医生专属邮箱接口（如 `/doctors/me/email/*`）或扩展统一账号邮箱接口（`/accounts/me/email/*`）。
    - 前端医生端改调医生/统一账号接口。
    - 增加端到端用例：医生邮箱绑定、解绑、换绑全链路通过。

- [x] **P1 refresh token 体系不完整（admin/doctor）**
  - 问题：admin/doctor 登录返回 refreshToken，但刷新接口仅 `/auth/refresh` 且按 user 逻辑校验，角色链路不一致。
  - 解决方案：
    - refresh token 固定 `type=refresh`，角色信息放入 `role_type` 或单独字段。
    - 提供统一刷新接口（按角色分流）或分别提供 admin/doctor refresh。
    - 前端拦截器按角色统一接入刷新逻辑。

- [x] **P1 双写默认角色可能串租户**
  - 问题：`_get_default_role_id` 仅按 `role_type + is_default` 查询，未带 `tenant_id`。
  - 解决方案：
    - `default role` 查询必须带 `tenant_id`（平台角色和租户角色分支处理）。
    - 约束层补充唯一性策略（每租户每角色类型一个默认角色）。
    - 增加迁移校验脚本，检测历史脏数据。

- [x] **P1 管理员更新接口字段不一致**
  - 问题：路由层使用 `admin.store_id`，而模型是 `current_store_id` + `stores`。
  - 解决方案：
    - 统一为 `current_store_id/store_ids` 访问控制判定。
    - 修正门店权限判断逻辑并补测试。

- [x] **P2 注册验证码流程不完整 + SDK 参数不一致**
  - 问题：
    - 注册 schema 有 `code`，但注册逻辑未验码。
    - `authApi.sendCode` 发送 `type`，后端接收 `code_type`，导致默认行为偏移。
  - 解决方案：
    - 注册接口强制验码（`register` 场景）。
    - 前端统一发送 `code_type`；移除/废弃不一致方法签名。
    - 回归 `patient-h5` 注册验证码流程。

- [x] **P2 冗余接口与重复实现增加维护成本**
  - 问题：
    - `/auth/change-password` 与 `/users/change-password` 重叠。
    - `sendCode` 与 `sendAuthCode` 并存，行为不一致。
    - 两个小程序 `utils/auth.ts` 完全重复。
  - 解决方案：
    - 合并/下线重复接口，保留单一入口。
    - `packages/api` 统一方法签名，标注 deprecated 并迁移调用方。
    - 抽离小程序共享认证模块，单源维护。

- [x] **P2 统一账号模块尚未真正收口**
  - 问题：`/accounts` 当前仅头像上传，认证和资料管理仍以旧表与兼容逻辑为主。
  - 已完成项：
    - 已新增统一邮箱入口：`/accounts/me/email/send-code|bind|unbind|change`。
    - 医生端 SDK 邮箱/改密链路已切到 `/accounts/*`（旧 `/doctors/me/email/*` 标记兼容接口）。
    - `authApi.getAccountMe()` 已切到 `/accounts/me`（旧 `/auth/account/me` 保留兼容）。
    - 已补集成测试：统一改密（admin/doctor/user legacy 同步）+ 统一邮箱绑定（user legacy 同步）。
  - 解决方案：
    - 制定分阶段迁移：
      - Phase 1：读路径统一到 `AccountInfo`；
      - Phase 2：写路径主写 `accounts/*`，旧表镜像；
      - Phase 3：清理旧兼容分支与遗留表直读。
    - 迁移期间提供对账脚本与每日一致性检查任务。

## 建议落地顺序

1. **先做安全修复（P0）**：管理员鉴权漏洞、租户串租风险。
2. **再做链路闭环（P1）**：医生邮箱、refresh token、默认角色租户化。
3. **最后做收敛与重构（P2）**：重复接口清理、统一账号迁移收口。
