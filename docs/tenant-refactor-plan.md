# 多租户隔离改造总体实施方案

> 版本：v1.2（2026-10-22，二轮评审修订：消解 resolve_actor_tenant_anchor 错误码分歧与 LEGACY_USER_ADMIN_FALLBACK 初值表述；首轮修订已落实 blockers 1-7 与 gaps 1-4）
> 来源：七份期度方案整合（第1期安全核心、第2期预约支付流 A、第2期患者数据流 B、第2期资源与消息 C、第3期数据模型、第4期生命周期、测试基建）。
> 说明：文中 file:line 均为规划阶段实读源码核实所得；方案中个别对早期审计行号的修正已在对应工作项内注明（如 `tests/conftest.py` 的数据工厂实际类名为 `TestDataFactory`（:832），全仓库不存在 `MultiTenantDataFactory`；alembic 迁移文件实测 150 个）。
> **执行环境前提（修订时实跑核实）**：`apps/server/.venv/bin/python` 是指向 `~/.pyenv/versions/3.12.13/bin/python` 的断链（本机 pyenv 仅有 3.11.13），各验收门的 `python -m pytest` 须先重建虚拟环境或以系统 `python3 -m pytest` 执行——修订时以系统 python3 两轮实测同命令 → 16 passed in 2.04s / 2.14s（约 2s 级）。批次6/批次8 的门含需 `TEST_DATABASE_URL`（PG）的 integration/alembic 测试（`.github/workflows/test.yml` PG 批次已具备该变量），本地无 PG 时对应部分记 not run、以 CI 为准。

---

## 一、背景与目标

### 1.1 审计结论摘要

对 `apps/server` 全仓逐文件实读审计后，多租户隔离现状可归纳为六类问题：

1. **租户过滤大面积 fail-open**。管理端查询普遍采用 `get_current_tenant_id() + if tenant_id:` 模式（租户上下文来自请求头 `X-Tenant-ID`，见 `app/middleware/tenant_context.py:47-49`），上下文缺失即不过滤、看全平台数据。涉及模块：appointments（11 处 fail-open + 3 处完全无过滤）、waitlist、payments、refunds、patients（manage/users 共 26 处）、medical_records、examination_reports、follow_up、schedules、doctors、stores（11 个查询方法）、messages、analytics、CMS 等。
2. **管理员身份判定可被伪造提权**。`app/common/auth_unified.py:373-376` 的 `is_super_admin` 判定仅看角色编码 `SUPER_ADMIN`/角色名「超级管理员」，不看角色租户归属——租户管理员若绑定一个 `tenant_id=本租户、code=SUPER_ADMIN` 的自建角色即获平台权限；且 `service_roles.py:73-93` 建角色无保留字校验、`service_admins.py:254` 指派 `role_id` 无租户归属校验，构成「建角色→换角色」两步自我提权链路（T-4 已核实）。另有遗留 fallback（`auth_unified.py:327-361`）：Admin 表查不到时按 id 查 User 表即授予超管。
3. **管理端锚点语义不统一**。唯一正确的既有范式是 `app/modules/audit_logs/router.py:178-185`：非平台管理员取 `current_admin["tenant_id"]`、缺失即 403；平台管理员必须显式传 `tenant_id` 查询参数否则 400。该范式仅 audit_logs 等少数模块采用，其余模块依赖请求头。
4. **个例越权五处**：analytics 三接口依赖请求头且缺失时统计全平台；CMS 写路径（update/delete/restore/版本历史）无租户校验；WebSocket `/ws/poll` 完全匿名可拉任意医生未确认消息；Celery 黑名单任务无租户上下文时向全平台管理员扇出通知；租户上下文中间件只解析 code 不回填 id，使管理端一致性校验对只带 `X-Tenant-Code` 的请求失效（换头绕过）。
5. **数据模型缺口**：news/notices/banners/content_versions 等表缺 `tenant_id` 列；`admins.username`、`roles.code`、四类业务单号、三类配置编码为全局唯一（跨租户误判/无法同码共存）；12 列裸 `tenant_id` 无外键；`system_settings` 无租户维度。
6. **生命周期与测试空白**：患者/医生 token 不校验租户状态（停服可写）；自助注册密码无策略校验；租户开通非原子（中途失败留半开通）；迁移「部分成功静默提交」；订阅 payment_status 全库无回写、auto_renew 零消费；软删租户 code 永久占用、无 90 天物理删除任务；DataScope/role_permissions/branding_config 等死代码未处置；测试侧无多租户夹具工厂、无隔离矩阵、存在弱断言（`tests/tenants/test_tenant_isolation.py:277-282` 条件放行）。

### 1.2 目标

1. 管理端所有查询以**管理员账号的 `tenant_id`** 为唯一锚点，fail-close（无租户即 403/400，而非放行全量）；
2. 堵死「租户管理员伪造平台角色→自我提权」链路，平台管理员经 `require_platform_admin`（`app/common/tenant_deps.py:223-238`）守卫；
3. 公开端走租户上下文中间件并补齐强制校验路径，患者端入口叠加 owner 水平越权校验；
4. 数据模型补齐租户列、租户内唯一约束、外键与索引，为租户级配置拆分打好列基础；
5. 打通租户开通/订阅/配额/删除闭环，处置死代码；
6. 以可批量执行、可独立回滚的测试基建（多租户夹具 + 隔离矩阵 + fail-close 负向用例）支撑上述全部改造并固化验收门。

### 1.3 范围边界：departments 纳入本期处置，其余同模式模块显式标注「本期不处置」

首轮方案 §1.1 审计仅覆盖约 14 个模块；评审以 `grep -c get_current_tenant_id` 全仓实测（修订时复跑核实，数字一致）显示同一 fail-open 模式还分布于大量未覆盖模块。为使隔离矩阵可解释、批次5 验收门可兑现，特此划定范围：

1. **departments 纳入本期处置**：`app/modules/departments/service.py` 实测 11 处 fail-open（:20/:44/:74/:103/:134/:150/:225/:241/:254/:289/:316，均为 `get_current_tenant_id() + if tenant_id:` 模式），路由全部仅挂 `get_current_admin`（router.py:42 等）无租户校验。以新增工作项 **P2C-7**（修订新增）纳入批次5，与其余资源模块同法锚点化；T-2 矩阵的 departments 条目在 P2C-7 落地后启用。
2. **其余模块本期不处置**（实测 `get_current_tenant_id` 计数，含 service/router 全部文件）：freelance_fees(22)、rule_sets(13)、approval_flows(13)、schedule_suspensions(11)、attendance_leave(11)、users(11)、blacklists(8)、schedule_templates(8)、rest_days(7)、leave_requests(7)、dictionaries(6)、attendance_shifts(6)、session_events/rule_engine/points/schedule_rooms/miniapp_platform/doctor_reviews(各 5)、support_tickets/notification_logs/integration/feedbacks/email_templates/common_services/attendance_rules(各 4)、user_favorites/notification_preferences/booking_notices/appointment_satisfactions(各 3)、performance/doctor_booking_settings/attendance_groups(各 2)。
   - 结论：**本期（批次1-8）不改这些模块的过滤行为**，统一标注「本期不处置」，作为已知 fail-open 遗留登记（新增风险 R15）。其中 users 仅由 P4-1 补患者写守卫、blacklists 仅由 P1-8 收敛 Celery 通知、freelance_fees 仅由 P3-3 改单号生成，均不等价于查询锚点改造，不改变本结论。
   - 对验收门的影响：T-2 十二模块矩阵只含本方案已处置模块，批次5 门「12 模块全启用且全绿」以本清单为界成立；未处置模块不入矩阵，其 fail-open 面留待后续立项按批次5 同法收口。

---

## 二、总体策略

整体采用 **fail-close + 管理员租户锚点 + 渐进分期** 三原则：管理端一律以管理员账号 `tenant_id` 为唯一锚点显式传参（对齐 `audit_logs/router.py:178-185` 既有正确范式），上下文头仅作为公开端语义保留；公开端继续走租户上下文中间件，并对可预约/医生/门店等路径补强制校验；所有行为收紧项均配灰度开关（`LEGACY_USER_ADMIN_FALLBACK`、`TENANT_FILTER_FAIL_CLOSE`、`TENANT_CONSISTENCY_FAIL_CLOSE`，以及修订新增的 `TENANT_CODE_TO_ID_RESOLVE`、`PATIENT_ANCHOR_FAIL_CLOSE` 与公开路径配置项 `PUBLIC_TENANT_REQUIRED_EXTRA_PATHS`，默认关/空），先观察日志再翻转，确保「关开关即回滚到旧行为」——该承诺对批次1-5 的管理端与患者端/公开端收紧均成立（见 R1）。**不做大爆炸重构**，理由有三：其一，fail-close 直接改变现网请求可见数据面（无头管理端请求从「看全量」变 403），一次性切换无法归因回归来源，必须按模块灰度观察；其二，全仓 fail-open 点位分布在 15+ 模块、约 80 处，签名式改造（service 显式收 `tenant_id` 入参）会波及跨模块调用链，必须逐模块「service→router→既有单测」闭环交付、独立 revert；其三，数据模型迁移（全局唯一改租户内唯一、补外键）依赖生产库冲突扫描结果，属不可完全预演的运维动作，必须线性串联迁移并以「先扫描中止、后执行约束」的防御式写法隔离风险。因此按「测试地基先行→安全核心→三组业务模块→数据模型→生命周期→死代码收尾」排成 8 个批次，每批有独立验收门与回滚方式（详见第四节）。

---

## 三、各期详细工作项

> 每项格式：编号 ｜ 标题 ｜ 规模（S/M/L）｜ 依赖 ｜ 改动点（file:line）｜ 测试清单 ｜ 风险与回滚。

### 第1期 安全核心（P1，8 项）

**期目标**：堵死「租户管理员伪造平台角色→自我提权」链路，把租户隔离从 fail-open 改为 fail-close，并修复 analytics/CMS/WebSocket/uploads/黑名单任务五处个例越权。全部以「管理员账号的 tenant_id」为管理端唯一锚点，平台管理员经 `require_platform_admin` 守卫，公开端继续走租户上下文中间件。

#### P1-1 超管/平台管理员判定锚定平台角色（role.tenant_id IS NULL），并收紧遗留 User fallback
- **规模**：M ｜ **依赖**：无
- **改动点**：`app/common/auth_unified.py:373-376`：`is_super_admin`/`is_platform_admin` 判定追加前提 `admin.role` 非空且 `admin.role.tenant_id IS NULL`（平台角色），即 `is_super_admin = bool(admin.role) and admin.role.tenant_id is None and (role_code == "SUPER_ADMIN" or role_name == "超级管理员")`；`is_platform_admin` 同样加租户前提。`Role.tenant_id` 已核实存在（`app/models/admin.py:58`，NULL=平台角色）；`scripts/init_roles.py:22-28` 建的平台 SUPER_ADMIN 角色 tenant_id 为 NULL，现网平台超管不受影响。`auth_unified.py:327-361`：Admin 查不到时按 id 查 User 即授予 `is_super_admin=True/is_platform_admin=True/permissions=["*"]` 的遗留 fallback，用新配置 `settings.LEGACY_USER_ADMIN_FALLBACK`（`app/core/config.py`，仿 :126 `RATE_LIMIT_ENABLED` 布尔开关写法）包裹：False（关闭）时直接走既有 401「账号不存在」分支。**开关初值随决策点 D1 拍板（D1 已标【阻断 P1-1 开关默认值】）：按 D1 建议方向默认 True 上线（True=保留旧行为，部署即零行为变更），观察日志确认无真实命中后翻 False 收紧——本项「风险与回滚」、D1、R1、D2 已统一按此路径表述，实施者不得在 D1 拍板前自选初值（次轮修订裁决：消除首轮正文「默认 False」与 D1「建议 True」的矛盾）。**实现顺序：先加判定前提，再加开关，最后补测试；`tenant_deps.py`、`permission_deps.py` 无需改（其读取的 `is_super_admin` 字段源自本函数，`auth_types.py:84` dict 透传）。④ **既有测试夹具迁移（评审指出的批次2 必红点，归属本项、随本项同批交付）**：`tests/conftest.py:543-560` 的 `test_super_admin_role` 实为 `code=SUPER_ADMIN + tenant_id=test_tenant.id`（实读核实），本项新判定下不再是超管——消费 `super_admin_token` 的 `tests/unit/test_rule_set_permissions.py` 与 integration 测试（test_import_export/test_lowcode/test_refunds 三个 endpoint 测试，grep 实测共 5 文件含 conftest 定义），以及直接消费 `test_super_admin` 夹具的 `tests/unit/test_tenant_services.py:340/:449`、`tests/security/test_token_blacklist_all_roles.py:36`、`tests/unit/test_permission_deps.py`（is_super_admin=True 构造）等将全部受语义漂移影响，若不迁移批次2 门跑 `tests/security tests/tenants` 全量必红。处置：T-1 先行提供新平台管理员夹具（同批次1），P1-1 在本提交内将上述消费面迁移到新夹具（SUPER_ADMIN 码 + 角色 tenant_id=NULL）——T-1「只增不改」不覆盖存量夹具迁移，本迁移由 P1-1 归属（见 R8）。
- **测试清单**：
  - 正向：tenant_id 为 NULL 的平台 SUPER_ADMIN 角色管理员登录后 `/admin/me` 返回 `is_super_admin=true`（回归现网超管）；
  - 负向：租户 A 管理员绑定 code=SUPER_ADMIN 但 tenant_id=A 的角色后，`is_super_admin/is_platform_admin` 均为 false、permissions 为角色自身权限；
  - 负向：仅存在于 User 表的 id 调 admin 接口，开关关闭时返回 401；
  - 负向：伪造 token type=admin 指向 User 表 id，开关关闭时 401（越权应被拒）；
  - 正向：开关置 True 时遗留 User 管理员恢复旧行为（灰度开关可独立验证）；
  - 夹具迁移回归：P1-1 合入后 `pytest tests/unit/test_permission_deps.py tests/unit/test_rule_set_permissions.py tests/unit/test_tenant_services.py tests/security/test_token_blacklist_all_roles.py` 及消费 super_admin_token 的 integration 测试全绿（夹具已随本项迁移，批次2 全量门不再因此变红）。
- **风险与回滚**：兼容性——若现网存在 Admin.role 为空或 role.tenant_id 非空但 code 恰为 SUPER_ADMIN 的存量账号，将失去超管身份，上线前跑只读 SQL 核对（`select admin join role where role.tenant_id is not null and role.code='SUPER_ADMIN'`）。遗留 fallback 关闭可能影响仅存在于 User 表的旧管理员，用开关灰度（初值随 D1 拍板，建议方向与本路径一致）：先置 True 观察日志确认无真实命中，再置 False。回滚：revert 本提交即可，无数据变更。

#### P1-2 角色保留字黑名单 + 管理员 role_id 指派的租户校验（堵死建角色+换角色提权两步）
- **规模**：M ｜ **依赖**：P1-1
- **改动点**：两处堵点合成一个工作项。① `app/modules/admin/service_roles.py:73-93` create：在 `get_by_code` 租户内查重（:75-77）之后加保留字黑名单——新增模块级常量 `RESERVED_ROLE_CODES = {"SUPER_ADMIN", "PLATFORM_ADMIN", "TENANT_ADMIN", "STORE_ADMIN", "STORE_USER", "OPERATOR", "ADMIN"}`，`data["code"].strip().upper()` 命中即 `raise ValueError("该角色编码为系统保留，禁止使用")`（含 "admin" 小写变体：租户默认角色 code="admin" 由 `service_tenant.py:196` 直建，普通创建路径不应再造）。② `service_roles.py:95-118` update：现仅保护 `role.code=="SUPER_ADMIN"` 的角色（:101-107），租户自建角色可把 code 改成保留字——在 :109 setattr 循环前对 `data.get("code")` 做同一黑名单校验。③ `app/modules/admin/service_admins.py:209-280` create：`role_id=data.get("role_id")` 直落（:254），且 :244 `tenant_id = data.get("tenant_id") or get_current_tenant_id()` 存在「载荷 tenant_id 锚点」歧义（实读核实）——若以载荷 tenant_id 为目标租户，租户管理员可借载荷跨租户建号；若以自身租户校验则平台管理员建号被堵。消解规则（先消解目标租户、再做角色校验）：**非平台管理员**——载荷 `data.get("tenant_id")` 非空且 ≠ 自身 tenant_id 时 raise 403「禁止跨租户建号」（`router_admins.py:59-80` create 实读仅有 get_store_filter 门店校验、无租户校验，由本服务层规则统一收口），消解后目标租户恒为自身 tenant_id（载荷合法值忽略，防借载荷换锚）；**平台管理员**——必须显式传载荷 tenant_id 否则 400（对齐 audit_logs :182-185 语义），以其为目标租户。随后调用新增私有方法 `_validate_role_assignment(role_id, 消解后目标租户)`（校验角色存在、`role.tenant_id` 非空时必须等于目标租户、`role.tenant_id` 为 NULL 的平台角色一律拒绝在本接口指派，否则 raise ValueError）。④ `service_admins.py:282-344` update：:320-324 对 `data.items()` 任意字段 setattr（含 role_id），循环前若 `"role_id" in data` 调用同一校验方法（目标租户取 `admin.tenant_id`）。`router_admins.py:98-101` 已有目标 admin 租户校验，不动；`router_roles.py:74/92` 经 tenant_filter 传参，服务层堵点对两条入口同时生效。
- **测试清单**：
  - 负向：租户管理员 POST /admin/roles code=SUPER_ADMIN 返回 400；
  - 负向：租户管理员 PUT /admin/roles/{自建角色} 把 code 改为 PLATFORM_ADMIN 返回 400；
  - 负向：租户管理员 POST /admin/admins 携带平台角色 role_id 返回 400；
  - 负向：租户管理员 POST /admin/admins 携带 tenant_id=租户B 的载荷 → 403（载荷不能换锚，堵跨租户建号）；
  - 负向：平台管理员不带 tenant_id 载荷建号 → 400（请指定 tenant_id）；正向：平台管理员带 tenant_id 指定租户建号 → 200；
  - 负向：租户管理员 PUT /admin/admins/{本租户成员} 把 role_id 改为租户 B 的角色返回 400；
  - 正向：PUT /admin/admins/{本租户成员} 把 role_id 改为本租户合法角色返回 200；
  - 正向：平台管理员创建/更新非保留字的自定义角色不受影响。
- **风险与回滚**：平台角色指派收口后，租户侧无法再为成员挂平台角色（本就不该允许）；存在租户管理员自定义角色撞保留字的极小概率，上线前跑只读 SQL 核对 `select code,count(*) from roles where tenant_id is not null group by code`。回滚：revert 本提交，已创建的合法数据不受影响。合入后须移除 T-4 对应用例的 xfail 标记（见 T-4）。

#### P1-3 get_tenant_filter fail-close 化：非超管且无 tenant_id 时拒绝而非放行
- **规模**：M ｜ **依赖**：P1-1
- **改动点**：`app/common/tenant_deps.py:120-134`：`get_tenant_filter` 现为「is_super_admin→None，否则 return `current_admin.get("tenant_id")`」，非超管 tenant_id 为空时返回 None 等于不过滤。改为：**平台管理员判定扩为 `is_super_admin or is_platform_admin` 任一为真**（实读核实：`auth_unified.py:376` 存在独立 `is_platform_admin` 判定——PLATFORM_ADMIN 角色码 + tenant_id=NULL；`scripts/migrate_tenant_data.py:164-181` 会创建该角色——若仅认 `is_super_admin`（`tenant_deps.py:129` 现状），开关翻转后 PLATFORM_ADMIN 账号管理端全线 403）→None（平台管理员锚定语义保留）；非平台管理员且 tenant_id 为空时按灰度开关二选一——`settings.TENANT_FILTER_FAIL_CLOSE` 为 True 时 `raise HTTPException(403, "未关联租户")`（写法参照同文件 :212-216 `require_tenant_admin` 既有 403），为 False 时保留旧行为并 `logger.warning` 记录 tenant_id 缺失的管理员 id（灰度观察用）。已核实调用面：`admin/router_roles.py`（8 处）、`admin/router_admins.py:99/135/159`、`import_export/router_export.py`（9 处）、`export/router.py`（3 处）、`attendance_records/router.py:227` 等均按「None=不过滤」消费，函数语义不变，仅把非法输入（非超管无租户）收口。
- **测试清单**：
  - 负向：tenant_id 为 NULL 的非超管调 GET /admin/roles，开关开启时返回 403；
  - 正向：同一账号开关关闭时返回 200 且日志出现 warning（灰度路径）；
  - 正向：平台管理员（is_super_admin）开关开启时 GET /admin/roles 返回全量角色；
  - 正向：PLATFORM_ADMIN 角色（tenant_id=NULL）账号开关开启时 GET /admin/roles 返回全量角色（防误伤该平台角色，scripts/migrate_tenant_data.py 所建账号不受影响）；
  - 正向：租户 A 管理员开关开启时 GET /admin/roles 仅返回租户 A 角色；
  - 负向：GET /admin/roles/{租户B角色id} 开关开启时租户管理员收到 404（服务层租户过滤生效）。
- **风险与回滚**：现网前端若存在「无租户上下文头的管理端请求」且账号 tenant_id 为 NULL，会从「看全量」变成 403——这正是修复目标，但需灰度：开关默认 False 上线，观察 warning 日志 1-2 个发布周期确认无存量账号依赖，再翻 True；翻 True 后如出现误伤，关开关即回滚到旧行为（不需 revert 代码）。管理端查询的推荐写法仍是 `audit_logs/router.py:177-187` 的既有范式（实测该段在 :177-187），本项是兜底而非替代。

#### P1-4 租户上下文 code 解析为 id + 管理端一致性校验补 code 分支（堵换头绕过）
- **规模**：M ｜ **依赖**：P1-1
- **改动点**：① `app/middleware/tenant_context.py:167-198` `_extract_tenant`：X-Tenant-Code/子域名/路径目前只返回 `(None, tenant_code)`（:181-196）不解析成 id，导致 `auth_unified.py:440-446` 的一致性校验（仅比对 current_tenant_id）对只带 code 头的请求完全失效。改法：dispatch（:117-158）在 `_extract_tenant` 返回后、`set_tenant_context`（:132）前，受新配置 `TENANT_CODE_TO_ID_RESOLVE`（`app/core/config.py` 新增，默认 False——回填子步骤的独立回滚开关）控制，开启后当 tenant_code 非空且 tenant_id 为空时，用 `async_session_maker` 查询 `select(Tenant.id).where(Tenant.tenant_code==code, Tenant.deleted_at.is_(None))` 回填 id（查不到保持 None，不影响公开端 `validate_public_tenant_context` 既有行为）；解析结果按 tenant_code 做 RedisCache 缓存（`app/core/redis.py` 既有缓存设施），TTL ≤10 分钟。② `auth_unified.py:439-446`：管理端一致性校验补齐 code 分支——current_tenant_id 为空但 current_tenant_code 非空时，比对 `admin.tenant.tenant_code`，不一致抛同一 403（中间件解析失败或开关关闭时的兜底）；触发条件从「current_tenant_id 有值」扩为「current_tenant_id 或 current_tenant_code 有值」，用 `settings.TENANT_CONSISTENCY_FAIL_CLOSE` 开关（默认 False 灰度）控制新分支。③ 同一函数族 user（`auth_unified.py:124-134`）/doctor（:234-244）的校验在中间件回填 id 后自动生效，无需改动。
- **测试清单**：
  - 负向：租户 A 管理员带 `X-Tenant-Code: 租户B` 的 code 头调管理端接口，开关开启时返回 403；
  - 负向：租户 A 管理员带无效 X-Tenant-Code 头，开关开启时返回 403（解析失败兜底）；
  - 正向：租户 A 管理员带正确 X-Tenant-Code 返回 200，且中间件回填后 `request.state.tenant_id` 等于租户 A id；
  - 正向：公开端 /api/v1/public/* 带正确 code 头仍正常返回；
  - 负向：公开端带无效 code 头仍按既有 `validate_public_tenant_context` 行为返回（不因解析失败产生新异常）；
  - 正向：平台管理员（无租户）带任意 code 头不触发一致性 403（is_super_admin 分支）。
- **风险与回滚**：现有前端若以「只带 X-Tenant-Code 头」调管理端接口，fail-close 后将与账号租户不符时收到 403（此前静默放行）。灰度：开关默认 False，先上线中间件 id 回填（对现网只是让既有校验真正生效，属修复非破坏），观察日志；确认前端统一带 X-Tenant-ID 或 code 与账号一致后翻 True。回滚：关开关；中间件回填可单独 revert 不影响②。子域名解析（`tenant_context.py:200-221`）对 www/api 等已排除，生产管理端直连域名无子域名场景不受影响。本项先行为 P3-2 的「同名多租户带 X-Tenant-Code 登录」提供校验基础。

#### P1-5 analytics /logs、/overview、/tenant-activity 三接口按管理员 tenant_id 锚点过滤
- **规模**：M ｜ **依赖**：P1-1
- **改动点**：`app/modules/analytics/router.py`，管理端三接口一律以「管理员账号的 tenant_id」为锚点，参照 `audit_logs/router.py:177-187` 既有写法（非超管 tid=`current_admin.get("tenant_id")`，为空即 403；超管可用平台视角）。① /logs（:253-302）：query 与 count_query 目前仅有 platform/event_type/page_path/时间条件，加 base tenant 条件——非超管 append `UserBehaviorLog.tenant_id == tid`。② /overview（:305-480）：base_conditions（:315-317）同样追加租户条件，所有子查询（PV/UV/点击/搜索/Top10/每日聚合）均复用 base_conditions，一处追加全量生效。③ /tenant-activity（:483-495）：现为 `tenant_id = get_current_tenant_id(); if tenant_id: base_conditions.append(...)` 的 fail-open（依赖请求头而非账号归属，且缺失时统计全平台），改为锚定 `current_admin["tenant_id"]`：非超管强制过滤、缺失抛 403；超管未指定时维持全量。路由挂载于 /api/v1/analytics（`app/api/v1/__init__.py:99`）。
- **测试清单**：
  - 正向：租户 A 管理员 GET /analytics/logs 仅返回 tenant_id=A 的日志；
  - 正向：租户 A 管理员 GET /analytics/overview 的 PV/UV 与只插入 A 租户埋点数据的期望一致；
  - 正向：租户 A 管理员 GET /analytics/tenant-activity 的 DAU 与 A 租户数据一致；
  - 负向：tenant_id 为 NULL 的非超管调三个接口返回 403；
  - 正向：平台管理员 GET /analytics/overview 返回全平台聚合。
- **风险与回滚**：/tenant-activity 响应中的 tenant_id 字段对平台管理员（无租户）会变为 None——响应模型 `TenantActivityStats` 已是可空语义，需前端确认展示。超管视角全量统计行为不变。回滚：revert 本提交，接口无 schema 变化。

#### P1-6 CMS 写路径与版本历史补租户校验（service 层锚点 + router 层传参）
- **规模**：M ｜ **依赖**：无
- **改动点**：读有校验、写无校验的个例集中修复，参照 `unified_message/service_rules.py:48` 既有写法（`if not obj or obj.tenant_id != tenant_id: return None`）。① `app/modules/cms/service.py` 三个 get_by_id 保持 db.get 不动（:90-91 CmsSite、:214-215 CmsCategory、:349-350 CmsArticle），为其后的写方法统一增加必填 tenant_id 参数并在取数后校验 `obj.tenant_id != tenant_id → 返回 None/False`：`CmsSiteService.update/delete/restore/permanent_delete`（:114-157）、`CmsCategoryService.update/delete/batch_sort`（:236-268，batch_sort 逐条校验、不匹配的跳过）、`CmsArticleService.update/delete/restore/permanent_delete/batch_delete`（:382-460，batch_delete 逐条校验）。② 路由层把 `tenant_id=current_admin["tenant_id"]` 传入：`router_articles.py:177-247`（更新/删除/恢复/永久删除/批量删除）、`router_sites.py:93-166`（同五类写操作及批量）、`router_categories.py:99-141`（更新/删除/批量排序）。③ `router_articles.py:134-158` 版本历史：先按 :128-130 既有判定取文章并校验租户（不匹配 404），再以 `ContentVersion.content_id == 该文章 id` 查询，杜绝按任意 content_id 枚举其他租户版本快照。实现顺序：service 写方法签名变更会让既有调用点报错，service 与 router 必须同一提交内改完；/published、/{id}/view 等公开接口不经认证，保持现状（get_published 已按 site_id 圈定，本期不动）。
- **测试清单**：
  - 负向：租户 A 管理员 PUT /cms/articles/{B租户文章id} 返回 404；
  - 负向：租户 A 管理员 DELETE /cms/articles/{B文章id}、DELETE /{id}/permanent、POST /{id}/restore、POST /batch-delete 混入 B 租户 id 均不生效（B 文章计数不变）；
  - 负向：租户 A 管理员 GET /cms/articles/{B文章id}/versions 返回 404；
  - 负向：租户 A 管理员对 B 租户站点/栏目执行更新/删除/永久删除/批量删除/排序均 404 或跳过；
  - 正向：租户 A 管理员对本租户文章/站点/栏目的全套写操作返回 200；
  - 正向：更新文章后 content_versions 新增一条快照（版本机制不受影响）。
- **风险与回滚**：service 写方法签名变更属内部 API，已核实调用方仅本模块三个 router（无脚本/任务引用，grep 核实）。超管（tenant_id 为 None）调写接口将因 tenant_id 不匹配收到 404——与既有读路径 `get_article`（`router_articles.py:129`）行为一致，属现状语义延续。回滚：revert 本提交即可，无数据变更。

#### P1-7 WebSocket /ws/poll 加医生认证 + admin 兜底分支租户校验
- **规模**：S ｜ **依赖**：无
- **改动点**：① `app/modules/websocket/router.py:224-237` /ws/poll 现完全无认证（已复核：签名直取 `doctor_id/tenant_id` Query 参数），doctor_id 可枚举拉取任意医生未确认消息（含患者隐私内容）。加认证：复用同文件 /ack 已用的 `Depends(get_current_doctor_by_token)`（`app/common/auth_deps.py:101`，认证内部已做租户一致性校验），签名改为 `doctor: Doctor = Depends(get_current_doctor_by_token)` 且 doctor_id 参数删除，查询固定用 `doctor.id`；无 token/无效 token 由该依赖返回 401/403。② :85-89 admin 兜底分支：token_doctor_id/sub 均不匹配 doctor_id 时，只要 payload 带 admin_id 即放行且不校验租户——收紧为：取 `payload.get("tenant_id")` 与目标 `Doctor.tenant_id` 比对（按 doctor_id 查 Doctor 表），payload 无 tenant_id 或不一致时 `close(4003)`；仅平台级 token（payload 含 `is_platform_admin` 且 tenant_id 为空）保留直连。③ 轮询客户端兼容：现有前端改为携带医生自身 token（与 /ack 一致），若存在「管理端代轮询」场景走②收紧分支。
- **测试清单**：
  - 负向：不带 token GET /ws/poll?doctor_id=X 返回 401；
  - 负向：医生 A 的 token 无法拉取医生 B 的未确认消息；
  - 负向：租户 A 的 admin token 经 WS /ws/doctor/{B租户医生id} 连接返回 close 4003；
  - 负向：无 admin_id 的任意有效 user token 冒充 doctor_id 连接 /ws/doctor/{id} 返回 close 4003；
  - 正向：医生本人 token 调 /ws/poll 返回自己的未确认消息，/ack 确认后消息消失。
- **风险与回滚**：/ws/poll 从匿名可用变为必须医生 token——现网若有依赖匿名轮询的降级客户端会开始收到 401/403。灰度：先只上②（admin 兜底租户校验，对合法医生客户端零影响），观察一段时间无「admin 兜底被拒」告警后，再上①；回滚即 revert。隐私收益：未确认消息补发接口不再可枚举 doctor_id 拉取。

#### P1-8 blacklist_task 管理员通知按黑名单记录租户收敛，杜绝无上下文全平台扇出
- **规模**：S ｜ **依赖**：无
- **改动点**：`app/tasks/blacklist_task.py:131-177` `_notify_admins_sync`：Celery 无租户上下文时（`auto_release_blacklist_task` :181-246 从未 `set_tenant_context`，current_tenant_id 为 None）查询 Account/Admin 不带租户条件（:150-151、:160-161 的 where 仅在有租户时追加），向全平台管理员扇出且 Message 不写 tenant_id（:167-175，`Message.tenant_id` 已核实存在：`app/models/message.py:15`）。改法：① `_notify_admins_sync` 增加必填参数 tenant_id，函数内恒定 `where(Account.tenant_id == tenant_id)` / `where(Admin.tenant_id == tenant_id)`，Message 落库带 tenant_id；tenant_id 为空时 logger.warning 并直接 return（fail-close，不扇出）。② 三处调用点按业务对象租户收敛：`auto_release_blacklist_task` 的调用（:229-233）传 `record.tenant_id`（`Blacklist.tenant_id` 已核实存在：`app/models/blacklist.py:15`；为 NULL 的历史记录跳过通知并记日志）；`mark_no_show_appointments_task` 内两处调用（:384-389）传 `tenant.id`（其上下文本已按租户设置，:296）；`check_and_add_blacklist`（:485-490）传上下文里的 tenant_id（:432 已判空，语义不变）。
- **测试清单**：
  - 负向：无租户上下文执行 auto_release_blacklist_task，产出 Message 的 tenant_id 与黑名单记录租户一致，其他租户管理员收不到；
  - 负向：黑名单记录 tenant_id 为 NULL 时任务完成且不发消息、日志出现 warning；
  - 正向：mark_no_show 场景下租户 A 管理员收到本租户黑名单通知且 Message.tenant_id=A；
  - 正向：check_and_add_blacklist 场景通知仍限定本租户。
- **风险与回滚**：历史 Blacklist 记录 tenant_id 为 NULL 的解禁将不再发管理员通知（仅日志）——落地时先跑只读 SQL 统计 NULL 占比，必要时补一次性数据修复脚本（tenant_id 可由 record.user_id 反查 User.tenant_id 回填），该脚本作为独立提交便于回滚。回滚：revert 本提交。

### 第2期A 预约支付流（P2A，6 项）

**期目标**：把预约/候补/支付/退款四个模块的租户过滤从「`get_current_tenant_id() + if tenant_id:`」的 fail-open 模式统一改为：管理端以管理员账号 tenant_id（`get_tenant_filter`）为唯一锚点、公开端走租户上下文中间件且 fail-closed、平台管理员用 `require_platform_admin`/`get_tenant_filter` 既有守卫；service 与 router 分层显式传参，四模块各自独立测试、独立回滚。

#### P2A-1 新增统一租户锚点解析函数 resolve_actor_tenant_anchor
- **规模**：S ｜ **依赖**：无
- **改动点**：在 `app/common/tenant_deps.py` 新增纯函数 `resolve_actor_tenant_anchor(actor: dict) -> str | None`，作为四模块统一替换模式的核心：1) actor 含 `is_super_admin=True` 时返回 None（平台管理员全平台视图，语义与 `get_tenant_filter` 现状一致，`tenant_deps.py:120-134`）；2) actor 含 `is_admin=True` 但非平台管理员时返回 `actor['tenant_id']`，缺失则抛 `HTTPException(403,'未关联租户')`（完全复刻 `audit_logs/router.py:177-185` 既有写法）；3) 普通用户（患者/医生）返回 `get_current_tenant_id()`（tenant_deps.py 已 import，:14-17），为空时受新配置 `PATIENT_ANCHOR_FAIL_CLOSE`（`app/core/config.py` 新增，默认 False）控制：True 抛 `HTTPException(400,'缺少租户上下文')`（fail-closed，语义对齐已有 `require_tenant_context`，`tenant_deps.py:347-361`）；False 时 logger.warning 并返回 None（保持现网「无头不过滤」行为）——**评审指出的「患者端无头 400 无灰度开关、批次3 上线即生效、只能 revert 回滚」据此消除，R1 的「关开关即回滚」对批次3-5 成立**。同时在 `app/common/deps.py` 导出列表（:45-47、:72-76 一带）追加该符号。不改任何业务行为，本工作项只交付函数与单测。**合并约束**：P2B-1、P2C-1 将新增同名/近义函数，三者必须收敛为同一函数族（见六、风险登记簿 R2），P2A-1 先落地者为准，后续批次扩展而非重复定义。**错误码裁决（次轮修订补，消解 P2A-1 与 P2B-1 的规格分歧）**：单一实现内按受众分派两个语义分支——管理员型 actor（is_admin/is_super_admin/is_platform_admin 任一为真）tenant_id 缺失 → 403「未关联租户」（audit_logs 语义，覆盖本项分支 2 与 P2B-1② 的平台管理员输入）；患者/医生型 actor 无租户锚点 → 开关开启后 400「缺少租户上下文」（require_tenant_context 语义，本项分支 3）。两码作用于不同输入、并存不冲突，R2 收敛后本项与 P2B-1 两套测试清单的期望据此同时成立。
- **测试清单**：
  - 单测（可放 `tests/unit/test_tenant_anchor.py` 新建）：平台管理员 `{'is_super_admin':True}` 返回 None；租户管理员 `{'is_admin':True,'tenant_id':'t1'}` 返回 't1'；租户管理员无 tenant_id 抛 403；普通用户在 `set_tenant_context('t1')` 后返回 't1'；普通用户 `clear_tenant_context()` 后（无头场景）在开关 True 时抛 400、开关 False 时返回 None 并 warning（两态都测——负向用例：开关开启后无头必须被拒；本组 P2A-2~6 测试清单中的全部「无头 400」用例均在 PATIENT_ANCHOR_FAIL_CLOSE=True 态执行）；
  - 纯函数不触库，不需要 DB 夹具；用 `tests/security/test_tenant_isolation.py:293` 的 `set_tenant_context` 模式设置/清理上下文。
- **风险与回滚**：纯新增，不影响现有请求；回滚 = revert 单个 commit 删除该函数。后续 P2A-2~P2A-5 依赖它，但它自身零风险可先行合入。

#### P2A-2 appointments：查询与写守卫统一租户锚点
- **规模**：M ｜ **依赖**：P2A-1
- **改动点**：service 层 `app/modules/appointments/common.py` 共 11 处 fail-open + 3 处完全无过滤，全部改为显式 tenant_id 入参、不再内部调用 `get_current_tenant_id()`（:15 的 import 与 :65/:77/:99/:183/:196/:228/:393/:416/:436 九处调用点随之删除）：1) get_by_id :63-69（审计所引 :65-67 实为 get_by_id 的租户段，列表 get_list 的租户段在 :99-105，行号以本次核实为准）；2) get_by_appointment_no :71-81；3) get_list :83-162（query 与 count_query 双处）；4) get_today_by_doctor :164-187；5) get_statistics :189-224；6) get_queue_info :226-308（:228、:241-242、:258-259、:275-276 三段查询统一用入参）；7) get_today_pending_by_user_and_store :310-332——完全无租户过滤，补 tenant_id where；8) get_checkin_queue :334-370——同样完全无过滤，补 tenant_id where；9) check_duplicate_same_day :372-397；10) _count_user_store_daily_appointments :399-422；11) _count_user_doctor_active_appointments :424-440；12) _check_rest_day :442-469——RestDay 查询（:449）补 `RestDay.tenant_id` 过滤（字段已核实存在：`app/models/rest_day.py:14`，nullable，anchor 为 None 时跳过）。替换模式统一为 `if tenant_id: query = query.where(Appointment.tenant_id == tenant_id)`，anchor 由调用方传入而非上下文自取。同模块 service_booking.py / service_flow.py 内部调用上述方法的传参同步补 tenant_id。router 层 `router_query.py`：get_appointments :76-156（:128 管理员分支用 resolve_actor_tenant_anchor 解析锚点，:136 调用传入）、get_appointment :666-680、get_appointment_by_no :631-645、get_today_appointments :175-244、get_today_pending_appointments :265-349（患者端无头在 PATIENT_ANCHOR_FAIL_CLOSE=True 时由 P2A-1 抛 400，默认 False 保持现网行为）、get_checkin_queue :371-439、get_appointment_statistics :488-533（:514、:528 两处）、check_duplicate_appointment :553-613、get_queue_info :697-707。`router.py`：get_payment_params :149-222，把 :163-166 与 :201-203 两处 fail-open 改为显式锚点（患者端无头 400）。公开端创建路径不动：service_booking.py:60/:115/:125 的租户一致性校验保持为正面参照。
- **测试清单**：
  - 矩阵（pytest 参数化，夹具用 `tests/conftest.py:832` TestDataFactory 造租户A/B 各一套 appointment，参照 `tests/security/test_tenant_isolation.py` 的 tenant_a/tenant_b + set_tenant_context 模式）：租户A管理员（is_admin=True,tenant_id=A）查列表仅见 A 的记录、total 正确；
  - 负向：患者端接口无 X-Tenant-ID 头（clear_tenant_context）调 get_appointments / get_payment_params / today-pending → 400 被拒，且不返回全平台数据；
  - 负向：租户A管理员用 B 的 appointment_id 取详情 → 404，不泄露存在性；
  - 平台管理员列表返回两租户合计；伪造 X-Tenant-ID=B 的租户A管理员仍只看到 A（锚点是账号 tenant_id 而非头）；
  - 回归：患者带正确租户头创建→列表→详情主链路不回归；statistics 与 checkin_queue 数量与改造前同租户一致。
- **风险与回滚**：管理后台此前无头请求可看全平台数据，改造后租户管理员只见本租户——属预期安全收紧；若有管理端页面依赖「无头全平台视图」需确认前端为租户管理员下发的是本租户数据展示。get_list 签名变化会波及同模块 service_booking/service_flow 内部调用与潜在测试直接调用，需全量 grep AppointmentService 方法调用点同步。患者端无头收紧受 PATIENT_ANCHOR_FAIL_CLOSE 灰度（P2A-1），误伤时关开关即回滚，不需 revert。回滚：revert 本工作项 commit 即恢复 fail-open 原行为，无数据迁移。

#### P2A-3 waitlist：管理端锚定 admin.tenant_id，写路径 fail-closed，修复跨租户取消漏洞
- **规模**：M ｜ **依赖**：P2A-1
- **改动点**：router 层 `app/modules/waitlist/router.py`：审计所引 :135-137（/my 患者端列表）、:246-248（/stats）、:298（管理端列表）核实准确；另发现两处审计未列：:377-380（管理端递补取 entry）与 :466-469（详情）。改法：管理端三处（/stats :226-264、列表 :267-360、递补 :363-401）删除 get_current_tenant_id 上下文读取，改用 `resolve_actor_tenant_anchor(current_admin)`（current_admin 已由 :232/:279/:367 的 `Depends(get_current_admin)` 注入）；患者端两处（/my :108-197、详情 :433-514）在 :135-137/:466-469 改为无头即 400（fail-closed）。审计未列的高危写漏洞：管理端取消 :404-430 直接调 `service.cancel_waitlist`，而 `service_mutation.py:149-152` 按 entry_id 查询时无任何租户条件——跨租户管理员可取消他租户候补。service 层 `service_mutation.py`：1) add_to_waitlist :21-129——:40-47 重复候补检查补 `WaitlistEntry.tenant_id` 条件；:60-65 Schedule 加载后补租户一致性校验（照抄正面参照 `appointments/service_booking.py:60` 的 `if current_tenant_id and schedule.tenant_id != current_tenant_id: raise` 模式）；:111 `tenant_id=get_current_tenant_id()` 改为先取后判空、为空抛 BusinessError（fail-closed 写入，杜绝 tenant_id=None 脏数据）；2) cancel_waitlist :131-178——:149-152 查询加显式 tenant_id 入参过滤，router 管理端取消 :414 调用处传入锚点；3) service_query.py `_tenant_filter` :12-17 改为接收 anchor 参数（保持 mixin 结构）；4) service_promotion.py promote_next :20-45——:33-40 首条 WAITING 查询补租户过滤（router 递补 :389 调用前已按锚点校验过 entry，但 service 层自身必须闭环），auto_promote :47 起同段查询同步；5) **递补建单一致性校验衔接（评审指出的必返工点，显式列入改动清单）**：管理端递补成功后经 AppointmentService.create 建单，`appointments/service_booking.py:60` 一致性校验依赖上下文头而管理端递补请求通常无 X-Tenant-ID——采用**显式传参**方案：AppointmentService.create 增加可选 keyword-only 参数 tenant_id，传入时以其替代上下文头执行 :60 校验（与 P2A-4 payments create_payment_order 的过渡参数同款）；router 递补 :389 调用处传管理员锚点。不采用 set_tenant_context 注入（try/finally 恢复易漏、与患者端上下文交叉）。
- **测试清单**：
  - 矩阵：租户A管理员查管理端列表与 /stats 仅见 A 的候补；B 管理员仅见 B；
  - 负向（重点回归本次修复的写漏洞）：租户A管理员 POST /{B的entry_id}/cancel → 404；POST /{B的entry_id}/promote → 404，且 B 的候补状态不变；
  - 负向：患者端 /my 与 /{entry_id} 无 X-Tenant-ID 头 → 400 被拒；
  - 患者带 A 头访问 B 的 entry_id 详情 → 404（租户过滤先行，不进入 user_id 归属判断即已隔离）；
  - 写入 fail-closed：clear_tenant_context 后调 add_to_waitlist → BusinessError，库中不产生 tenant_id=NULL 的 WaitlistEntry；带 A 头正常入队且 tenant_id=A、position 计算仅统计 A 同排班队列；
  - 管理员递补成功建单且新预约 tenant_id=A（改动点⑤显式传参路径，一致性校验不依赖请求头）。
- **风险与回滚**：递补建单路径的衔接已列入改动点⑤（显式传参方案），照单执行即可，不再是风险悬置项；create 新增 keyword-only 参数对既有调用方零影响（默认不传走上下文）。cancel_waitlist 签名变化影响 router.py 两处调用（:83 患者端传患者锚点、:414 管理端传管理员锚点）与既有单测直接调用。回滚：revert 单 commit 恢复原状，无迁移。

#### P2A-4 payments：预约加载与配置解析显式锚点，回调改锚定已验签 profile.tenant_id
- **规模**：M ｜ **依赖**：P2A-1
- **改动点**：router 层 `app/modules/payments/router.py`：_get_appointment_or_404 :43-58（:50-52 fail-open）改为接收 anchor 入参、无条件 where（anchor 为 None 即 404，删掉上下文自取）；_ensure_admin_can_access_appointment :102-109 在门店校验前补租户校验 `appointment.tenant_id != actor.tenant_id → 403`（:107 的 store_id 校验保留作为门店级二级控制）；:117 写守卫 `require_tenant_active_for_write` 保留不动。create_payment_order :112-141 在 :124 调用前用 `resolve_actor_tenant_anchor(current_user)` 解析患者端锚点（无头 400）；get_payment_order_status :181-206 在 :191 前解析（管理员→账号 tenant_id，患者→上下文头）。service 层 `app/modules/payments/service.py` 四处 fail-open 改显式入参：create_payment_order 加载预约 :64-66 与 PaymentProfile :94-95；_resolve_payment_config 快照查询 :420-422；_get_appointment_by_out_trade_no :458-462 与 legacy 分支 :468-474。回调加固：handle_payment_callback :157 起——:179-182 已 fail-closed（保留），但 :218/:264 的预约查找不再依赖请求头租户，改传 :190 已按 tenant_id+cert_serial_no 验签反查得到的 `payment_profile.tenant_id` 作为锚点（公资安全等价加固：回调上下文本就来自微信而非请求方可信租户）。
- **测试清单**：
  - 矩阵：租户A管理员 GET /payments/orders/{A的appointment_id} → 200；同管理员查 B 的 appointment_id → 404；B 管理员访问 A 的预约 → 403（新增租户校验生效，此前 :102-109 仅靠 store 近似）；
  - 负向：患者端无 X-Tenant-ID 头 POST /payments/orders → 400 被拒，且不触达任何预约记录；
  - 患者带 A 头对 B 的 appointment_id 创建支付单 → 404；带伪造 X-Tenant-ID=B 头的患者查自己（A）的预约 → 按 B 锚定查不到 → 404，不能借头越权；
  - 回调：用 A 租户 PaymentProfile 证书构造合法签名回调命中 A 的预约 → 正常结算；构造 out_trade_no 指向 B 租户预约但用 A 证书验签 → 因锚定 profile.tenant_id=A 查不到 B 预约而拒收（负向资损用例）；
  - 回归：带正确租户头的患者创建支付单→签名参数返回正常；重复回调幂等路径 :267-283 不回归。
- **风险与回滚**：回调锚定改为 profile.tenant_id 后，历史脏数据（appointment.tenant_id 为 NULL 或与 profile 不一致）的预约回调会拒收——上线前需 SQL 抽查 Appointment.tenant_id 与其 payment_profile.tenant_id 的一致性；拒收时微信会重试，可在日志（:193-195 已有 detail）观测。_get_appointment_or_404 签名变化影响本文件两处调用；payments/service.py 的 create_payment_order 对外签名加 keyword-only tenant_id 参数并给默认 None 时回退上下文（过渡兼容 `appointments/router.py:218` 的跨模块调用）。回滚：revert 单 commit；回调锚定如出问题可单独还原 :218 处传参（独立小提交便于拆分回滚）。

#### P2A-5 refunds：列表/详情/创建统一 admin.tenant_id 锚点
- **规模**：M ｜ **依赖**：P2A-1
- **改动点**：router 层 `app/modules/refunds/router.py`：_get_appointment_or_404 :37-39、_get_refund_or_404 :54-56 fail-open（审计引 :31-62/:65-71/:156-183 核实准确），两个 helper 改为接收 anchor 入参（删 :16 import 与上下文自取），anchor 为 None 的非平台管理员在调用前已由锚点解析抛 403；_ensure_admin_can_access_appointment :65-71 在门店校验前补 `appointment.tenant_id != current_admin['tenant_id'] → 403`（super_admin 跳过，沿用 :66-67 既有分支）；get_refundable_amount :74-87（:82 传锚点）、create_refund :90-153（:105 传锚点）、get_refund_records :156-183（:172 后追加 `resolve_actor_tenant_anchor(current_admin)` 传入 service，:172 的 get_store_filter 保留为门店级二级过滤）、get_refund_detail :186-198。退款回调 :201-292 已 fail-closed（:228-230）且按 tenant_id+cert_serial_no 反查（:234-243），保持不动。service 层 `app/modules/refunds/service.py`：get_refund_records :409-453（:418-424）核实准确，另发现三处审计未列的 fail-open：get_refundable_amount :224-257（:226-231 两段查询）、create_refund :259 起（:276-281 预约加载，:304-309 in_flight 去重同用该 tenant_id 变量随签名一并覆盖）、get_refund_by_id :455-462。统一改为显式 tenant_id 入参。正面参照确认：sync_appointment_refund_state :206-207 已按 appointment.tenant_id 锚定，无需改动。
- **测试清单**：
  - 矩阵：租户A管理员 GET /refunds 仅见 A 的退款记录（total 正确）；B 管理员仅见 B；
  - 负向：租户A管理员用 B 的 refund_id 取详情 → 404；用 B 的 appointment_id 查 refundable-amount / 创建退款 → 404，且不产生任何 RefundRecord；
  - 负向：租户A管理员（有门店权限）对 B 租户门店的预约创建退款 → 403（新增租户校验优先于门店校验触发）；
  - 无租户上下文不适用本模块（全管理端），等价负向为：无 tenant_id 的非平台管理员账号 → 403 未关联租户；
  - 平台管理员查列表可见全平台记录；带 appointment_id 筛选时仅返回该租户数据；
  - 回归：A 管理员对 A 预约正常创建退款（金额校验/并发去重 :304-309 行为不变）；微信退款回调成功后 refund_status 同步不回归。
- **风险与回滚**：create_refund / get_refundable_amount 签名变化影响本 router 三处调用与既有单测直接调用。平台管理员全平台视图沿用 `get_tenant_filter` 既有语义（`tenant_deps.py:126-131`），若运营端依赖全平台列表页面不受影响。回滚：revert 单 commit 恢复 fail-open，无数据迁移。

#### P2A-6 四模块参数化矩阵回归测试汇总
- **规模**：M ｜ **依赖**：P2A-2、P2A-3、P2A-4、P2A-5
- **改动点**：新建 `apps/server/tests/security/test_p2a_tenant_matrix.py`（挂 `pytestmark = [pytest.mark.security]`，与 `tests/security/test_tenant_isolation.py` 同层）：用 `tests/conftest.py:832` 的 TestDataFactory 分别实例化租户A、租户B 全链路数据（create_tenant/create_store/create_schedule/create_appointment，:851-:1088），候补/退款记录直接构造 ORM 补齐（WaitlistEntry/RefundRecord 模型在 `app/models/waitlist.py`、`app/models/refund.py`）；管理员鉴权复用 `tests/conftest.py:586-:632` 的 test_super_admin/test_store_admin 夹具模式再造第二租户管理员。测试体全部 @pytest.mark.parametrize 参数化四模块 × 五场景：1) 租户A管理员只见A；2) 跨租户 id 访问被拒（404/403）；3) 患者端无头被拒（400，仅 appointments/waitlist 有患者端点）；4) 平台管理员全平台视图；5) 伪造租户头不能借头越权。本工作项只写测试不改业务代码；若前序工作项行为正确则本文件应全绿，作为第2期模块组A的统一验收门。
- **测试清单**：执行 `pytest apps/server/tests/security/test_p2a_tenant_matrix.py` 全绿；负向断言嵌入上述每个参数化用例（越权 404/403、无头 400、伪头隔离），并断言响应体不含他租户字段（如 patient_phone）；汇总回归：`pytest apps/server/tests/tenants/` 与 `apps/server/tests/security/` 既有隔离套件不因签名变化而破坏（先跑一遍记录基线，改造后对比）。
- **风险与回滚**：若 P2A-2~P2A-5 任一项实施偏差，本文件会集中暴露——这正是其价值；测试文件独立成 commit，回滚不影响业务代码。

### 第2期B 患者数据流（P2B，8 项）

**期目标**：将患者/病历/检查报告/随访四个模块从「租户上下文缺失即放行」的 fail-open 模式改造为 fail-closed：管理端以管理员账号 tenant_id 为唯一锚点显式传参过滤，混合受众端点以 token 内 tenant_id 锚定并拒绝平台管理员无租户请求，病历等患者端入口叠加 owner 水平越权校验。上述 fail-closed 行为（含「平台管理员无租户 403」）统一受 `PATIENT_ANCHOR_FAIL_CLOSE` 开关灰度（默认 False，见 P2B-1 与 R1）——开关 False 时各路由保持旧构造（`Service(db)` 上下文回退），True 时才切换为锚点构造，避免批次4 上线即全系 403。

#### P2B-1 管理端租户锚点解析器（fail-closed 公共函数）
- **规模**：S ｜ **依赖**：无
- **改动点**：新增于 `app/common/tenant_deps.py`（`require_platform_admin` 定义于 :223-238，同文件追加）。实现两个纯函数（照抄既有正确写法，不引入新抽象）：① `resolve_admin_tenant_anchor(current_admin: dict, tenant_id_override: str | None = None) -> str`，语义照抄 `audit_logs/router.py:177-185`——非平台/超级管理员取 `current_admin.get("tenant_id")`，为空抛 HTTPException 403「未关联租户」；平台/超级管理员必须显式传 tenant_id_override，否则 400「请指定 tenant_id」。② `resolve_actor_tenant_anchor(current_user: dict) -> str`，用于 medical_records/examination_reports/follow_up 这类 `get_current_user_or_admin` 混合受众端点——取 `current_user.get("tenant_id")`（患者/医生/租户管理员 token 均带该字段，见 `auth_types.py:210` 与 `auth_unified.py:169`），为空（平台管理员或历史遗留超管账号，`auth_unified.py:344-361` 返回无 tenant_id）时受 `PATIENT_ANCHOR_FAIL_CLOSE` 开关（同 P2A-1，默认 False）控制：True 抛 403（限管理员型输入；错误码裁决见 P2A-1 合并约束——管理员型 403、患者/医生型 400，本项 403 期望仅针对平台管理员/遗留超管这类无租户管理员输入，患者/医生型输入归 P2A-1 分支 3 的 400 语义）；False 时 logger.warning 返回 None，且 P2B-2~P2B-7 的路由接线按开关二态构造——True 时 `Service(db, anchor)` 锚点构造、False 时保持 `Service(db)` 旧构造（内部上下文回退），保证批次4 上线即生效的只有灰度开启后的收紧（评审指出的「P2B 全系 403 不受开关控制」据此消除）。不修改任何现有函数。**合并约束**：② 与 P2A-1 同名函数签名存在差异（P2A-1 版本含上下文回退），两批合入时必须收敛为单一实现（以 P2A-1 先落地版本为基、扩展 admin 分支），不得重复定义（见 R2）。
- **测试清单**：租户管理员（tenant_id 非空）调用 resolve_admin_tenant_anchor 返回其 tenant_id；负向：非平台管理员 tenant_id 为空 → 403（对齐 `audit_logs/router.py:181`）；负向：平台管理员未传 override → 400（对齐 :185）；单测：患者/医生/管理员 token dict（is_admin=True / is_doctor=True / 两者皆 False）经 resolve_actor_tenant_anchor 均返回 token 内 tenant_id；负向：current_user 无 tenant_id（平台管理员）在开关 True 时 → 抛 403，开关 False 时返回 None 并 warning（两态都测；P2B-2~7 测试清单中的全部无头/平台管理员 403 用例均在 PATIENT_ANCHOR_FAIL_CLOSE=True 态执行）；负向：患者/医生型 dict（is_admin/is_super_admin 均假）无租户锚点在开关 True 时 → 400（按 P2A-1 合并约束的受众分支裁决，与本项 403 期望分属不同输入，收敛后两套测试期望同时成立）。
- **风险与回滚**：纯新增代码，无行为变更；revert 单 commit 即回滚。后续工作项若暂缓，本项可独立合并。

#### P2B-2 患者模块管理端租户锚点加固（service_manage + service_users）
- **规模**：M ｜ **依赖**：P2B-1
- **改动点**：① `app/modules/patients/common.py:14-15`：保留 `_current_tenant_id()` 但 `PatientsServiceBase.__init__`（common.py:11-12）增加必传参数 `tenant_id: str` 并存为 `self.tenant_id`（不删旧方法，避免影响未迁移调用）。② `app/modules/patients/service_manage.py` 全部 14 处 fail-open 改为无条件 `self.tenant_id` 硬过滤：get_list（40、43-44）、get_detail（154-157）、update_patient（281-284）、get_patient_store_id（147-149）、get_appointments（310-314）、get_consumption_records（369-372）、add_to_blacklist（401-404）、remove_from_blacklist（414-417）、get_blacklist（432-435）、create_patient（471-474，且 :487 `User(tenant_id=tenant_id)` 与 :511 `Patient(tenant_id=tenant_id or user.tenant_id)` 改为固定 `self.tenant_id`）、add_family_member（537-540）、update_family_member（618-621）、delete_family_member（658-661）、delete_patient（687-690）。③ 同模式覆盖审计未列出的 `app/modules/patients/service_users.py` 11 处（修订实测 `_current_tenant_id` 计数为 11，首轮写 12 有误；行段：22-24、30-32、43-45、57 起、136 起、235 起、255 起、291 起、317 起、392 起、450 起）。④ 接线：`router_manage.py` 与 `router_users.py` 全部 `PatientManageService(db)/UserManageService(db)` 构造点改为 `PatientManageService(db, resolve_admin_tenant_anchor(current_admin))`（两文件均已是 `Depends(get_current_admin)`，`router_manage.py:35` 等）。实现顺序：先改 common.py 基类签名 → 改两个 service → 改路由构造点 → 修既有单测。
- **测试清单**：租户 A 管理员查患者列表仅见租户 A 数据（get_list，service_manage.py:32）；负向：构造 service 时租户锚点缺失（平台管理员未传）→ 403，不返回任何跨租户数据；负向：租户 A 管理员对租户 B 患者 id 调 get_detail/update_patient/add_to_blacklist/delete_patient → 返回 None/False（最终 404），数据不变；负向：租户 A 管理员 create_patient 写入时 tenant_id 恒为 A，即使内部回退路径（service_manage.py:511 的 `or user.tenant_id`）也不落入 B；跨租户家庭成员隔离：get_detail 返回的 familyMembers 仅含本租户成员（service_manage.py:187-189）；service_users.py 同矩阵：update_status/delete_user/update_card/delete_card 对跨租户 user_id 全部拒绝。
- **风险与回滚**：平台管理员从此不能无参跨租户管理患者（须显式指定租户，返回 400）；若前端有平台管理员直连患者列表的场景需同步传 tenant_id 参数。回滚：revert 本项单 commit 即恢复 contextvar fail-open 行为。存量 tenant_id 为 NULL 的患者行在锚点过滤后不可见（列 nullable=True），如需数据修复另立任务。

#### P2B-3 病历服务层租户锚点 fail-closed（含 update/delete 写路径）
- **规模**：M ｜ **依赖**：P2B-1
- **改动点**：① `app/modules/medical_records/service.py:24-25` __init__ 增加必传 `tenant_id: str`。② create（27-103）：:29 get_current_tenant_id() 改为 self.tenant_id；:32 `appointment = await self.db.get(...)` 后追加校验 `appointment.tenant_id != self.tenant_id` 则 raise ValueError("预约不存在")（不泄露跨租户存在性）；:42-47 查重条件追加 `MedicalRecord.tenant_id == self.tenant_id`。③ get_by_id（105-120）：116-118 的 if tenant_id 条件过滤改为无条件 where。④ get_by_appointment（122-137）：133-135 同上。⑤ get_list（139-197）：159-161 改为 conditions 初始即含 `MedicalRecord.tenant_id == self.tenant_id`（覆盖 get_patient_records 199-206 与 /my 医生路径）。⑥ update（208-222）与 delete（224-233）：:210、:226 的 `self.db.get(MedicalRecord, record_id)` 无租户过滤（审计未列、本次核实追加的写路径 fail-open）改为 `select().where(MedicalRecord.id==record_id, MedicalRecord.tenant_id==self.tenant_id, deleted_at 条件)`，查不到返回 None/False。⑦ 路由接线 `app/modules/medical_records/router.py`：:81、:106、:119、:130、:151、:175、:191、:206 共 8 处 `MedicalRecordService(db)` 构造改为 `MedicalRecordService(db, resolve_actor_tenant_anchor(current_user))`。实现顺序：service 签名与函数体 → 路由构造点 → 同步既有单测 `tests/unit/test_medical_record_service.py` 的构造方式。
- **测试清单**：租户 A 医生 create（挂租户 A 预约）→ 病历 tenant_id=A，get_by_id/get_by_appointment/get_list 可见；负向：租户 B 医生 get_by_id(租户A病历id) → None→404；get_list 不含租户 A 数据；负向：租户 B 医生对租户 A 病历调 update/delete → None/False→404，库中数据不变（service.py:210、226 写路径）；负向：租户 B 医生 create 时传租户 A 的 appointment_id → ValueError→400「预约不存在」；负向：锚点缺失（平台管理员 token）→ 路由层 403，service 不执行任何无租户查询；负向：无租户上下文请求（平台管理员 token 且不带 X-Tenant-ID）→ 403 而非返回全库病历列表。
- **风险与回滚**：平台管理员 token（tenant_id=None）访问病历接口将 403——平台侧如需跨租户审计病历须走显式租户参数（P2B-1 语义）；Celery/后台任务若有经 MedicalRecordService 的调用需核对传入锚点（已核实 tasks/ 下无直接调用，仅 follow_up 生成在 P2B-6 处理）。回滚：revert 单 commit。

#### P2B-4 病历患者端 owner 水平越权校验（第二层防护）
- **规模**：M ｜ **依赖**：P2B-1、P2B-3
- **改动点**：① `app/modules/medical_records/router.py` 新增模块级辅助 `_ensure_patient_own_access(db, current_user, patient_id)`：当 `current_user.get("is_admin")` 或 `current_user.get("is_doctor")` 为真直接放行（租户锚点已在 P2B-3 保证隔离）；否则按 `follow_up/router.py:47-66` `_resolve_patient` 既有模式查询 `Patient.user_id == current_user["id"]`（加 tenant_id 条件）校验目标 patient_id 归属，不属→404（防枚举）。② 应用于三个患者可达读端点：get_patient_records（111-121，直接传 path patient_id）、get_record_by_appointment（124-142，先查 Appointment 比对 appointment.tenant_id 与 appointment.patient_id）、get_medical_record（145-163，经 record.patient_id）。③ 写路径收紧：update_medical_record（184-196）当前患者 token 可改任意病历（核实追加），在 :190 前加 is_admin/is_doctor 判定，患者一律 403；delete_medical_record（199-220）已有 210-214 校验保持不变；create（166-181）已有医生强制（172-174）保持。实现顺序：先加辅助函数与单测 → 逐端点接线。
- **测试清单**：患者 token 查自己就诊人 /patient/{id} 病历列表 → 200 仅含本人数据；负向：患者 token 传同租户他人 patient_id 查 /patient/{id} → 404；负向：患者 token GET /{record_id} 他人病历详情 → 404；GET /appointment/{他人appointment_id} → 404；负向：患者 token PUT /{record_id} 改他人或自己病历 → 403（病历修改仅医生/管理员）；负向：患者 token DELETE /{record_id} → 403；医生 token 跨就诊人查询本租户患者病历 → 200（租户内工作场景不受影响）；负向：患者 token 传不存在 patient_id 与他人 patient_id 返回一致（404），不可枚举。
- **风险与回滚**：患者端若存在「代家人查看病历」合法场景，须经本人 user_id 名下就诊人（Patient.user_id 关系），与小程序现有 family 交互一致；家庭外代查将被拒——属预期收紧。回滚：revert 单 commit 后患者端恢复（越权窗口回归，故回滚需评估）。

#### P2B-5 检查报告租户锚点 + 患者端 owner 校验
- **规模**：M ｜ **依赖**：P2B-1
- **改动点**：① `app/modules/examination_reports/service.py:14-15` __init__ 增加必传 tenant_id。② create（17-53）：:19 上下文取值改 self.tenant_id；:22 `appointment = self.db.get(...)` 追加 tenant_id 比对（不匹配 raise ValueError("预约不存在")）。③ 五处查询 fail-open 改无条件锚点：get_by_id（58-60）、get_by_appointment（73-75）、get_by_patient（87-89）、get_by_record（116-118）、get_list（136-138）。④ delete（184-194）经 get_by_id 自动获得锚点保护。⑤ 路由接线 `app/modules/examination_reports/router.py`：:38、:137、:158、:168、:181、:201、:212、:235 共 8 处构造点传 `resolve_actor_tenant_anchor(current_user)`。⑥ 患者端 owner 层：新增与 P2B-4 同构的归属校验，应用于 get_reports_by_appointment（162-170）、get_reports_by_patient（173-192）、get_reports_by_record（195-203）、get_report（206-219）；delete_report（222-249）已有医生强制（228-233）保持。实现顺序：service → 路由锚点 → owner 层 → 既有单测同步；辅助函数与 P2B-4 共用（若 P2B-4 先落地则复用其实现）。
- **测试清单**：租户 A 医生上传报告（挂 A 租户预约）→ tenant_id=A，列表/详情可见；负向：租户 B 医生 get_by_id/get_by_appointment/get_by_record（租户 A 报告）→ 空/404；负向：租户 B 医生 create 传租户 A appointment_id → ValueError→400；负向：患者 token 查他人 /patient/{id}、/record/{id}、/{report_id} → 404；负向：患者 token DELETE /{report_id} → 403（228-233 保持）；医生/管理员本租户内多条件 get_list（keyword/日期/门店筛选）正常返回（service.py:122-182）。
- **风险与回滚**：file_url 为外链，租户隔离仅防元数据与列表泄露，文件本体访问控制依赖存储层（`build_tenant_storage_folder` 已按租户分目录，router.py:120）——本期不改存储。平台管理员 403 与存量 NULL tenant_id 行不可见，同 P2B-3。回滚：revert 单 commit。

#### P2B-6 随访统计接口 fail-open 修复 + 服务层写路径 fail-closed
- **规模**：M ｜ **依赖**：P2B-1、P2B-3
- **改动点**：① `app/modules/follow_up/router.py` get_statistics（607-676，审计引 605-660，实际范围 607-676）：:615-617 if tenant_id 条件改为经 `resolve_actor_tenant_anchor(current_user)` 取锚点后无条件 `where(FollowUpTask.tenant_id == anchor)`，status_query（624-631）与 doctor_query（642-654，join Doctor）共用 conditions 自动收敛。② `app/modules/follow_up/service.py` 三个服务 __init__（FollowUpPlanService:27-28、FollowUpTaskService:158-159、FollowUpRecordService:370-371）增加必传 tenant_id；SelfReportService（508-509）同加（其 get_by_id 537-543 现无任何租户过滤、get_list 554-557 fail-open，为核实追加）。③ 写路径 fail-closed（现均 self.db.get 无租户校验）：plan update（106）/delete（145）；generate_from_plan :192 plan 取数加租户校验、:210 上下文取值改 self.tenant_id；task complete_task（310）/skip_task（325）/delete（358）；record update（476）/delete（496）——统一改为 select 带 tenant_id 条件或取数后 `if obj.tenant_id != self.tenant_id: return None`（照抄 `unified_message/service_rules.py:47-49`）。④ 调用点接线：router.py 中四个 Service 全部构造点传锚点；跨模块调用点 `app/modules/medical_records/service.py:89` `FollowUpTaskService(self.db)` 改为 `FollowUpTaskService(self.db, self.tenant_id)`（依赖 P2B-3 已有 self.tenant_id）。⑤ `tasks/follow_up_task.py` 对 mark_overdue（service.py:338-355，显式 tenant_id 参数）的调用保持显式传参模式，实施时核对逐租户循环调用齐全。
- **测试清单**：租户 A 管理员 GET /follow-up/statistics 仅聚合租户 A 任务与医生排行；负向：平台管理员（无租户锚点）调 /statistics → 403；负向：租户 B 医生对租户 A 的 plan/task/record 调 update/delete/complete/skip → None→404，数据不变（service.py:106、145、192、310、325、358、476、496）；负向：租户 B 上下文 generate_from_plan 传租户 A plan_id → ValueError→400；负向：SelfReportService.get_by_id 跨租户 report_id → None（537-543 修复后）；租户 A 医生创建病历（P2B-3 后）自动生成的随访任务 tenant_id=A；Celery mark_overdue 按租户显式传参逐租户标记，不越租户。
- **风险与回滚**：病历创建自动生成随访任务（`medical_records/service.py:86-101`）依赖 P2B-3 先行；Celery 逾期任务 mark_overdue 为后台无请求上下文路径，保持显式 tenant_id 不纳入锚点改造（若存量调用未按租户循环则逾期标记失效——实施时必须核对）。回滚：revert 单 commit（含 medical_records/service.py:89 一行，需同 commit 回滚）。

#### P2B-7 随访患者端 owner 水平越权校验
- **规模**：S ｜ **依赖**：P2B-1、P2B-6
- **改动点**：① `app/modules/follow_up/router.py`：复用既有 `_resolve_patient`（47-66）。get_patient_tasks（361-371）与 get_patient_records（502-512）：患者 token（非 is_admin 且非 is_doctor）时校验 path patient_id 经 `_resolve_patient` 归属 `current_user["id"]`，不属→404（防枚举）；医生/管理员放行（租户锚点已在 P2B-6 收敛）。② get_task（374-384）、get_task_records（538-546）、get_record（549-559）：患者 token 时取 task.patient_id / record.patient_id 做同上归属校验（内部查一次该用户就诊人归属集合）。③ 写路径 owner 约束：complete_task（424-438）、skip_task（441-456）、delete_task（459-470）、create_record（562-572）、update_record（575-588）、delete_record（591-602）——患者 token 仅允许操作自己就诊人的任务/记录（data.patient_id / 目标对象 patient_id 归属校验），否则 404；实现为模块级辅助 `_ensure_task_owner/_ensure_record_owner` 共用。my-patient 两端点（309-346、515-535）与自报告端点（712 起）已有归属解析，保持不变。
- **测试清单**：患者 token GET /tasks/patient/{自己} 与 /records/patient/{自己} → 200；负向：患者 token GET /tasks/patient/{同租户他人} → 404；负向：患者 token GET /tasks/{他人task_id}、/records/{他人record_id}、/records/task/{他人task_id} → 404；负向：患者 token PATCH /tasks/{他人task_id}/complete、/skip，DELETE /tasks/{他人task_id} → 404；负向：患者 token POST/PUT/DELETE /records 指定他人 patient_id/task_id → 404；医生 token 本租户内跨患者操作任务/记录 → 正常。
- **风险与回滚**：患者自助完成/跳过随访任务的业务语义需产品确认（见决策点 D8）；若确认患者端不应可写，将 owner 校验收紧为一律 403 即可（单点改动）。回滚：revert 单 commit。

#### P2B-8 四模块租户隔离回归矩阵测试
- **规模**：M ｜ **依赖**：P2B-2、P2B-3、P2B-4、P2B-5、P2B-6、P2B-7
- **改动点**：新增 `tests/security/test_patient_data_flow_tenant_isolation.py`（`pytestmark=[pytest.mark.security]`，参照 `tests/security/test_tenant_isolation.py:33` 起的双租户夹具风格；数据构造用 `tests/conftest.py:832` 的 TestDataFactory——注意实际类名，`MultiTenantDataFactory` 在仓库中不存在）。测试矩阵（模块 × 场景，全部为负向断言 403/404/400）：患者列表/详情/更新/拉黑、病历列表/详情/更新/删除、检查报告列表/详情/上传创建/删除、随访统计/任务/记录/自报告；场景含：①租户 A 管理员访问租户 B 资源；②无租户上下文（平台管理员 token）访问各列表；③患者 token 跨就诊人（同租户水平越权）读/写；④租户锚点缺失时 service 层抛错而非静默全查。并加一条正名冒烟：租户内正常读写路径全绿（防过度收紧）。实现顺序：P2B-2~P2B-7 各自的单测先行落地后，本项做汇总矩阵与回归（全量跑 tests/security 与 tests/tenants 确认无回归）。
- **测试清单**：矩阵断言：4 模块 × 跨租户读（列表+详情）全部 404/空集；4 模块 × 跨租户写（更新/删除/创建挂他租户实体）全部 404/400 且库数据不变；负向：平台管理员 token（tenant_id=None）访问 4 模块列表 → 403；负向：患者 token 跨就诊人读病历/报告/随访 → 404；正名：租户 A 管理员+医生+患者全链路读写冒烟通过；回归：`pytest tests/security tests/tenants` 全量通过（规划阶段未运行测试，实施期执行）。
- **风险与回滚**：仅新增测试文件，无业务影响；若先于部分改造项合并会红——须在 P2B-7 之后合并或按项启用 skip 标记。回滚：revert 单 commit。

### 第2期C 资源与消息（P2C，7 项）

**期目标**：将排班/医生/门店/消息四个模块的管理端查询从「header 租户上下文 fail-open（tenant_id 为空即不过滤）」改为「管理员账号 tenant_id 显式锚点」，公开端维持租户上下文中间件并补齐强制校验路径；医生登录查询与普通查询分离设计。

#### P2C-1 新增管理端租户锚点依赖 resolve_admin_tenant_anchor（共享底座）
- **规模**：S ｜ **依赖**：无
- **改动点**：在 `app/common/tenant_deps.py`（`require_platform_admin` 位于 :223-238）之后新增依赖工厂 resolve_admin_tenant_anchor：内部 `Depends(get_current_admin)` + `tenant_id: str | None = Query(None)`；非超管返回 `current_admin["tenant_id"]`，缺失抛 403「未关联租户」（逐字对齐 `audit_logs/router.py:178-181` 既有写法）；超管必须显式传 tenant_id 查询参数，否则抛 400「请指定 tenant_id」（对齐 :182-185）。并在 `app/common/deps.py:39-52` 的 tenant_deps 导入块与 :55-92 的 `__all__` 中追加导出。四个模块的 P2C-2~P2C-5 均以该依赖为唯一锚点来源，替代对 X-Tenant-ID header 上下文的依赖。**合并约束**：与 P2B-1 的 resolve_admin_tenant_anchor 同名——P2C-1 为 FastAPI Depends 工厂（含 Query 参数）、P2B-1 为纯函数（含 override 参数），合入时收敛为「一个纯函数 + 一个薄 Depends 包装」，不重复实现语义（见 R2）。
- **测试清单**：租户管理员（token 含 tenant_id）→ 依赖返回该 tenant_id，无论请求是否带 X-Tenant-ID；租户管理员账号 tenant_id 为空 → 403（负向）；super admin 带 tenant_id 查询参数 → 返回该值；super admin 不带 tenant_id → 400（负向）；普通用户/医生 token 访问 → 401/403（负向）。
- **风险与回滚**：纯新增依赖函数，未接线前无任何行为变更；回滚=revert tenant_deps.py 与 deps.py 两个文件的追加。「超管必须显式传参」的行为变化只在各模块接入（P2C-2~5）后逐模块生效，可逐模块独立回退。

#### P2C-2 schedules 模块查询锚点：5 处 fail-open + 1 处内联 RestDay 泄漏 + 公开路径强制校验
- **规模**：M ｜ **依赖**：P2C-1
- **改动点**：① `app/modules/schedules/service_query.py` 五处核实无误：get_by_id（:45-55，上下文读取 :46、条件过滤 :52-53）、get_list（:57-112，:68、:74-76）、_compute_effective_status（:114-146，:127 独立读上下文、:141-142 过滤自定义排班子查询）、_get_rest_days_cached（:212-228，:219-221）、_get_booking_setting（:256-274，:270-272）、get_available（:295-363，:301、:328-329）：全部增加关键字参数 `tenant_id: str | None = None`，语义为「显式传入即唯一锚点（直接 where，优先于上下文）；未传时保持现状回退 get_current_tenant_id()（公开端兼容）」；_compute_effective_status 的 tenant 改为由 get_list 显式下传，避免 :127 与锚点不一致。② `schedules/router.py` 管理端：get_schedules（:104-128 服务调用 :124）与 get_schedule（:456 起，服务调用 :464）挂 `Depends(resolve_admin_tenant_anchor)` 显式传参；get_schedules 内联 RestDay 查询（:135-144，当前完全无租户过滤，休息日标记跨租户泄漏）补 `RestDay.tenant_id == anchor`。③ `doctor_portal/router_schedules.py` 两处 get_list（:66-74、:118 起）显式传 `tenant_id=doctor.tenant_id`（医生 token 认证对象自带租户，`auth_deps.py:142-155` 已按 id 加载 Doctor）。④ 公开路径强制校验改为**配置驱动灰度**：`app/core/config.py` 新增 `PUBLIC_TENANT_REQUIRED_EXTRA_PATHS`（默认空列表），`tenant_context.py:33-44` 的强制名单在静态 `PUBLIC_TENANT_REQUIRED_PATHS` 之外逐请求并入该配置；灰度期配置为空即保持现状，翻转时配置为 `["/api/v1/schedules/available"]`（患者端可预约接口 `router.py:309-428` 当前不在强制名单，无 header 时会跨租户返回号源）——**若直接写死进静态名单，批次3 上线即生效且只能 revert 回滚（评审指出的批次顺序冲突之一），故改为配置项**。注：`router_extra_quota.py:213-214` 已是显式锚点写法，无需改动；Celery 自动生成路径 `tasks/schedule_task.py:306` 已 set_tenant_context、:334 clear，且生成写入不经 ScheduleQueryMixin 读查询，不受影响。
- **测试清单**：租户A管理员不带 X-Tenant-ID 调 GET /schedules → 仅返回A租户排班；租户A管理员以B租户 schedule_id 调 GET /schedules/{id} → 404（负向）；super admin 不带 tenant_id → 400；带 tenant_id → 仅该租户数据；公开 GET /schedules/available/{doctor_id} 无租户上下文 → 400（负向）；带 X-Tenant-ID → 正常返回该租户号源；doctor_portal 医生 token 查排班仅见本院本租户；管理端列表 is_rest_day 标记不再引用其他租户 RestDay。
- **风险与回滚**：患者端/医生端小程序若从未发送 X-Tenant-ID，新增强制校验会 400——上线前需确认客户端已携带（现有 /doctors/recommended、/stores/by-code 已强制，说明客户端具备此能力）。涉及模型 Schedule.tenant_id 可空（`models/schedule.py:31`、RestDay :14），历史 NULL 行在锚点过滤后不可见，必要时先做数据订正（本期只读不改数据）。测试清单中「公开 /schedules/available 无租户上下文 → 400」用例在 `PUBLIC_TENANT_REQUIRED_EXTRA_PATHS` 配置包含该路径时执行。回滚=revert schedules/service_query.py、schedules/router.py、doctor_portal/router_schedules.py 三个文件；公开路径强制校验误伤时从 `PUBLIC_TENANT_REQUIRED_EXTRA_PATHS` 配置移除对应路径即回退（不需 revert 代码）。

#### P2C-3 doctors 模块查询锚点 + 登录查询与普通查询分离
- **规模**：M ｜ **依赖**：P2C-1
- **改动点**：① 普通查询（加显式 tenant_id 参数，语义同 P2C-2）：`service_query.py` get_by_id（:100-110）、get_list（:112-149，:121/:129-131）、get_recommended（:151-164）、get_by_department（:166-181）、get_all_active（:183-194）、get_doctors_availability（:196-253，其中 :219-224 RestDay 查询当前无租户过滤，一并补齐）。管理端路由 `router.py`：get_doctors（:478-507）、get_all_doctors（:523-538）挂 resolve_admin_tenant_anchor；管理员更新/删除等 get_by_id 调用点（:699、:776、:816）显式传锚点。② 登录查询分离（决策敏感，见决策点 D5）：get_by_phone（:17-41）/get_by_username（:43-67）的 `strict_tenant: bool = False` 默认值（:20、:46）翻转为 True——已核实当前唯一调用方是 authenticate（:69-77，:70/:72 显式 strict_tenant=True），翻转对现有登录零影响，仅消除未来调用方的危险默认；无租户上下文且多租户命中时维持现状抛 ValueError → 登录端点 `router.py:184-186` 转 400 引导带 X-Tenant-ID。③ refresh 端点 router.py:277 的 get_by_id 改为显式传 `tenant_id=token_tenant_id`（该端点 :281-282 已有 token 租户一致性校验，锚点显式化后语义不变）；医生 token 端点 get_by_id 调用点（:748）显式传 doctor.tenant_id。④ 公开端 recommended（:559-575）、by-department（:595-611）、public/{id}（:629-647）保持上下文回退——三路径已在 `tenant_context.py:40-42` PUBLIC_TENANT_REQUIRED_PATHS 强制校验。
- **测试清单**：租户A管理员医生列表/详情不含B租户医生；跨租户 doctor_id 详情 → 404（负向）；手机号在 A/B 双租户存在：无 X-Tenant-ID 登录 → 400 提示指定租户；带A的 header → 登录A租户账号；get_by_phone 默认参数（翻转后 strict=True）在无上下文+单租户命中 → 返回；多租户命中 → ValueError（负向）；公开 /doctors/recommended、/doctors/by-department、/doctors/public/{id} 无租户上下文 → 400（负向）；refresh token 携带他人租户 tenant_id → 401（负向）；get_doctors_availability 的 RestDay 子查询过滤后，B租户休息日不影响A医生可约状态。
- **风险与回滚**：若存在本审计未覆盖的 get_by_phone/get_by_username 未来调用方依赖旧默认，行为收窄属预期防护（已全仓 grep 核实当前无其他调用方）。医生端登录必须带 X-Tenant-ID 或接受「唯一命中即登录」语义——需产品拍板（决策点 D5）。Doctor.tenant_id 可空（`models/doctor.py:15`），历史 NULL 行锚点过滤后不可见。回滚=revert doctors/service_query.py 与 doctors/router.py 两个文件。

#### P2C-4 stores 模块查询锚点：11 个查询方法全量显式化
- **规模**：M ｜ **依赖**：P2C-1
- **改动点**：① `service_query.py` 全部 11 个方法（任务书 :16-140 修正为实际 :14-144）增加显式 tenant_id 参数：get_by_id（:14-20）、get_by_code（:22-28）、get_by_name（:30-36）、check_name_exists（:38-46）、check_code_exists（:48-56）、get_list（:58-85，:62/:65-67）、get_all_active（:87-93）、get_department_count（:95-101）、get_department_counts_batch（:103-122）、get_departments（:124-132）、get_admins（:134-144），语义同 P2C-2。门店 code 为租户内唯一（`models/store.py:60` uq_stores_tenant_code），唯一性校验 fail-open 会跨租户误判。② 管理端 `router.py`：get_stores（:135-213）、get_all（:216 起）、check_unique（:84-110）及详情/更新/删除/科室/管理员子端点挂 resolve_admin_tenant_anchor；门店管理员 store_ids 白名单分支（:154-183）保留叠加。③ `service_mutation.py` 内部校验调用点显式传锚点：create 的 get_by_code（:19）、update 的 get_by_id/get_by_code（:46、:52）——注意 create 的 tenant_id 写入（:26、:34）仍依赖上下文，Mutation 侧整体锚点改造列入下期（本期仅保证校验查询与路由查询锚点一致，避免「A 管理员无 header 时建店被 B 租户同名编码拦截/放行」的错乱）。④ 公开 by-code（`router.py:43-66`）保持上下文回退（路径已在 PUBLIC_TENANT_REQUIRED_PATHS :43）。
- **测试清单**：租户A管理员门店列表/详情/科室/绑定管理员查询不含B门店；跨租户 store_id 详情 → 404（负向）；check_unique：A 管理员校验与B租户重复的 code → exists=false；与本租户重复 → true（修正跨租户误报）；super admin 不带 tenant_id → 400（负向）；带 → 仅该租户；公开 /stores/by-code/{code} 无租户上下文 → 400（负向）；A 管理员创建与本租户重复 code → 400；与B租户重复 → 允许（租户内唯一语义）；NULL 租户的平台级门店（store.py:15 注释）对租户管理员不可见（现状语义保持）。
- **风险与回滚**：super admin 视角行为收窄（原无 header 可全量总览，改后须传参）；平台级 NULL 租户门店语义需与业务确认（决策点 D3/D10）。回滚=revert stores/service_query.py、stores/router.py、stores/service_mutation.py 三个文件。

#### P2C-5 messages 管理端消息列表锚点（get_all_messages）
- **规模**：S ｜ **依赖**：P2C-1
- **改动点**：① `app/modules/messages/service_messages.py` get_all_messages（:231-274，fail-open 在 :242-245）签名增加必填参数 tenant_id，删除函数内 get_current_tenant_id() 读取，写法与 `unified_message/service_rules.py:24`（get_rules 按 tenant_id 参数 where）、:48（update_rule 校验 `rule.tenant_id != tenant_id` 即拒）同构；get_by_id（:197-203）同步增加可选显式参数。② `router.py` get_all_messages（:265-304）挂 resolve_admin_tenant_anchor 显式传参；现有 store_filter 逻辑（:280-282 get_store_filter(current_admin)）保留叠加（门店管理员再收窄到本店）。本模块已整体标记 deprecated（`api/v1/__init__.py:74` deprecated=True，统一消息中心 unified_message 已是锚点写法），故范围严格限定在审计指出的 get_all_messages，不做全模块迁移。
- **测试清单**：租户A管理员 GET /messages 仅返回A租户消息；A 管理员传B租户 store_id 过滤 → 结果为空（锚点优先，store_id 只是叠加条件）（负向）；super admin 不带 tenant_id → 400（负向）；带 → 仅该租户；未携带管理员 token → 401（负向）。
- **风险与回滚**：deprecated 端点行为收窄影响面小；若前端仍在无 header 下使用 super admin 全量视图会看到空列表，需前端同步传参。回滚=revert messages/service_messages.py 与 messages/router.py 两个文件。

#### P2C-6 四模块租户锚点矩阵回归测试（测试清单落库）
- **规模**：M ｜ **依赖**：P2C-2、P2C-3、P2C-4、P2C-5
- **改动点**：新增 `tests/tenants/test_p2c_resource_message_anchor_matrix.py`（沿用 `tests/tenants/test_tenant_data_isolation.py` 的写法：set_tenant_context/clear_tenant_context 切换上下文 + TestDataFactory 造数；注意实际类名为 TestDataFactory）。矩阵设计：主体={A管理员带header、A管理员不带header、B管理员、super admin带tenant_id、super admin不带、医生token、公开带上下文、公开无上下文} × 资源={排班（列表/详情/available）、医生（列表/详情/登录）、门店（列表/详情/by-code/check_unique）、消息（管理列表）}；每格断言正向（本租户可见）或负向（跨租户不可见/404/400/403/401）。服务层另用直连 service + set_tenant_context 的用例验证「显式 tenant_id 参数优先于上下文」的语义。
- **测试清单**：`cd apps/server && python -m pytest tests/tenants/test_p2c_resource_message_anchor_matrix.py -v` 全绿；负向用例覆盖：跨租户详情 404、无头管理端 403/400、公开无上下文 400、未认证 401、跨租户同手机号登录 400；回归既有：`python -m pytest tests/tenants/ -v` 确认未破坏存量隔离测试。
- **风险与回滚**：依赖 P2C-2~P2C-5 全部落地后才可全绿，建议各模块合入时先带各自矩阵子集；单文件新增，回滚=删除该测试文件。

#### P2C-7 departments 模块查询锚点：11 处 fail-open 全量收口（评审指出首轮遗漏，修订新增）
- **规模**：M ｜ **依赖**：P2C-1
- **改动点**：实读核实 `app/modules/departments/service.py` 共 11 处 fail-open（:20/:44/:74/:103/:134/:150/:225/:241/:254/:289/:316，均为 `get_current_tenant_id() + if tenant_id:` 模式），路由层全部仅挂 `get_current_admin`（router.py:42 等）无任何租户校验——首轮方案未给 departments 任何 P 项却将其列入 T-2 十二模块矩阵，批次5 门对其无法兑现；本项补齐（与 §1.3 范围边界呼应）。改法：① `service.py` 查询方法 get_by_id（:18 起）、get_list（:31 起）、get_tree（:70 起）、get_hot（:99 起）、get_all_active（:115 起）、get_doctors（:238 起）、get_all_doctors（:251 起）增加显式 tenant_id 入参（语义同 P2C-2：显式传入即唯一锚点，未传回退上下文）；② 管理端路由（列表/详情/创建/更新/删除/医生绑定/排序）挂 `Depends(resolve_admin_tenant_anchor)` 显式传参；③ 写路径 create（:144 起）/update（:193 起）/delete（:218 起）/batch_bind_doctors（:264 起）/batch_update_sort_order（:307 起）在取数与写入处补租户锚点校验（父级归属不匹配 404/跳过）。实现顺序：service → router → 既有单测同步。
- **测试清单**：租户A管理员科室列表仅见 A；跨租户 department_id 详情/更新/删除 → 404（负向）；super admin 不带 tenant_id → 400、带 → 仅该租户；T-2 矩阵 departments 条目在本项落地后启用并全绿。
- **风险与回滚**：与 P2C-2~5 同法，独立 commit 独立 revert；departments 为医生/排班的上游维度，本项只改本模块查询与写校验，不触碰 P2C-2/P2C-3 已覆盖的排班/医生路径。

### 第3期 数据模型（P3，7 项）

**期目标**：补齐多租户数据模型缺口：引入 TenantMixin、为缺租户列的表加 tenant_id 并回填存量数据、将 8 处全局唯一约束改为租户内唯一、补齐缺失的约束与索引、为 12 列裸 tenant_id 补外键，全部通过串联的 Alembic 迁移（M1→M7）落地，为第4期租户级配置拆分打好列基础。

#### P3-1 TenantMixin 落地 + 内容四表补 tenant_id 列与存量回填（news/notices/banners/content_versions）
- **规模**：M ｜ **依赖**：无
- **改动点**：1) `app/db/base.py:16-19` 之后新增 TenantMixin：`tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID（NULL表示平台级/全局）")`，供后续新表复用。2) `app/models/content.py:9/29/47`——News、Notice、Banner 各显式加 tenant_id 列（写法对齐 `store.py:15`），不改变继承结构以降低风险；content.py:27/45/63 的 store relationship 不动。3) `app/models/content_version.py:13` 后加 tenant_id 列（nullable=True，本期只加列不加 FK，FK 统一在 P3-6）。4) 新增迁移 M1（down_revision='20260630_drop_plaintext'，已用脚本对 150 个迁移验证其为当前唯一 head——修订实测 versions 目录 150 个文件，首轮写 151 有误）：对 news/notices/banners/content_versions 四表 `op.add_column(tenant_id, nullable=True)` 并 `create_index('ix_<table>_tenant_id')`；PG 加可空列不重写表，可在线执行。5) 回填（同一迁移 upgrade 内 data 步骤，先于建索引）：`UPDATE news SET tenant_id = s.tenant_id FROM stores s WHERE news.store_id = s.id AND news.tenant_id IS NULL`（notices/banners 同理，Store.tenant_id 已核实存在于 store.py:15）；store_id IS NULL 的行保留 NULL，语义定为「平台级全局内容」，与现有 store_id IS NULL=全局的展示语义一致。6) 写入点配套：`app/modules/content/service.py:120-138`（News.create）、:313 附近（Notice.create）、:496 附近（Banner.create）在构造模型时补 `tenant_id=get_current_tenant_id()`（该函数已核实存在于 `app/middleware/tenant_context.py:47`）。7) downgrade：drop 新索引与新列；回填属数据变更，downgrade 无法恢复原始 NULL，迁移文件中注明需依赖升级前备份。实现顺序：先加列→再回填→最后建索引→服务层写入点与迁移同 PR 发布。
- **测试清单**：迁移测试：alembic upgrade head 与 downgrade -1 在测试库往返成功，四表出现/消失 tenant_id 列与索引；回填正确性：用 TestDataFactory 建租户A+门店+新闻，跑回填逻辑后新闻 tenant_id 等于门店租户；负向：store_id 为 NULL 的存量新闻回填后 tenant_id 保持 NULL，不被错误归入任一租户；写入点：租户上下文下调用 News.create，新行 tenant_id 非空且等于当前租户；无租户上下文（平台）创建时 tenant_id 为 NULL 不报错。
- **风险与回滚**：content 服务层读取（get_list 的 store 过滤 content/service.py:105-107、get_by_id :116-118）本期不改，存量 NULL 行为完全不变；新写入带 tenant_id 后，管理端查询尚未按租户过滤前列表行为不变（属后续收口）。回滚：alembic downgrade 掉 M1 即删列，但回填数据不可自动恢复，需在升级前对四表做备份（pg_dump 对应表）。

#### P3-2 管理员与角色编码改租户内唯一（admins.username、roles.code）+ 登录兼容 + 平台角色查重修复
- **规模**：L ｜ **依赖**：P3-1
- **改动点**：1) `app/models/admin.py:83`——Admin.username 去掉 unique=True；admin.py:78-97 类内新增 `__table_args__ = (UniqueConstraint('tenant_id','username',name='uq_admins_tenant_username'), Index('uq_admins_username_platform','username',unique=True,postgresql_where=text('tenant_id IS NULL')))`——已核实库为 PostgreSQL（alembic.ini:5），复合唯一对 tenant_id=NULL 的平台管理员行不生效，必须用 partial unique index 补平台行唯一。2) `models/admin.py:70-75`——Role.__table_args__ 补 `UniqueConstraint('tenant_id','code',name='uq_roles_tenant_code')` 与平台行 partial index（兑现 :50/:72-73 注释宣称的复合唯一）。3) 迁移 M2：第一步在迁移内执行冲突扫描（`SELECT username FROM admins GROUP BY username HAVING count(DISTINCT tenant_id)>1`，roles.code 同理；本规划环境无生产库连接，扫描结果未知），存在冲突时 RAISE 中止并列出冲突行，待决策点 D13 裁决处理后重跑；第二步 `op.drop_constraint('admins_username_key','admins')`（沿用迁移 f1a2b3c4d5e6:16-21 的 drop 范式）→ create 复合 unique + partial index。4) 查重修复：`app/modules/admin/service_roles.py:65-71`——get_by_code 条件改为：tenant_id 传值时 `where(code==code, tenant_id==tenant_id)`；tenant_id 为 None（平台管理员，来自 `app/common/tenant_deps.py:120-134`）时改为 `where(code==code, Role.tenant_id.is_(None))`，修正「平台建平台角色被任意租户同 code 角色阻塞」的反向逻辑（正确范式参照 `service_templates.py:73-81`）。5) 登录兼容（必须同 PR）：`app/modules/admin/service_admins.py:152-164`——get_by_username_global 不再假设全局唯一，改为先按租户上下文过滤（get_current_tenant_id()），无上下文时查全部同名行：唯一则返回，多行则由 authenticate（:195-197）抛 HTTPException 400「用户名在多个租户存在，请附带 X-Tenant-Code 登录」，杜绝 scalar_one_or_none 的 MultipleResultsFound 500。
- **测试清单**：TestDataFactory 建租户A、租户B，各自创建 username=admin 的管理员均成功；负向：同租户内重复 username 创建返回 400（服务层 ValueError 路径），而非 500 IntegrityError；负向：平台管理员创建 code 与某租户角色相同的平台角色成功；与既有平台角色同 code 返回 400；负向：租户管理员创建与本租户既有角色同 code 返回 400；登录负向：双租户同名 admin 且请求无租户头时登录返回 400 歧义提示而非 500；带 X-Tenant-Code 登录成功；迁移回滚：downgrade -1 成功（无冲突数据前提下恢复全局唯一）。
- **风险与回滚**：最大风险是存量跨租户同名 username/code 导致迁移中止（已内置扫描与中止，不会写坏数据）与登录体验变化（同名多租户用户必须带租户标识登录）；admins.tenant_id 可 NULL（平台管理员，admin.py:91），partial index 保证平台行仍唯一。回滚：downgrade 恢复全局唯一约束，但若已产生跨租户同名行，恢复会失败——downgrade 注释按 f1a2b3c4d5e6:32-36 写明需先清理。

#### P3-3 业务单号改租户内唯一（appointment_no/record_no/task_no/settlement_no）+ settlement_no 生成器加固
- **规模**：M ｜ **依赖**：P3-1
- **改动点**：1) 迁移 M3 对四表执行：`app/models/appointment.py:13` 的 appointment_no、`medical_record.py:16` 的 record_no、`follow_up_task.py:19` 的 task_no、`freelance.py:93` 的 settlement_no——各 drop 全局 unique 约束（约束名默认 `<table>_<col>_key`），改为 `UniqueConstraint(tenant_id, <单号列>)`，并各建 partial unique index（`<单号列> WHERE tenant_id IS NULL`）保住平台行唯一。迁移内先扫描四表同租户内重复单号（现有全局唯一理论上已排除，扫描为零成本兜底）。2) 单号生成器改造点核实结论：appointment_no 生成于 `app/modules/appointments/service_booking.py:219`（YY+秒级时间戳+uuid4[:4]，含随机段，租户内冲突概率可忽略，无需改动）；record_no 于 `app/modules/medical_records/service.py:17-20`（同理不改）；task_no 于 `app/modules/follow_up/service.py:19-21`（同理不改）；settlement_no 两处且均无随机段——`app/tasks/freelance_task.py:52-55`（FS+时间戳+freelancer_id[:6]）与 `app/modules/freelance_fees/service_mutation.py:324`（同格式）——同一租户同一秒对同一 freelancer 生成两次结算必撞，两处均追加 4 位 uuid 随机段并保持单号总长不超过 freelance.py:93 的 String(32)（freelancer_id 截断从 [:6] 收窄为 [:2] 以留位）。3) 模型层同步：四个模型文件去掉列上 unique=True、加 __table_args__ 复合唯一与 partial index（写法同 P3-2）。
- **测试清单**：双租户下用固定前缀构造相同单号写入 appointments 各自成功；负向：同租户内重复 appointment_no 被 DB 约束拒绝（IntegrityError 映射为 400）；负向：同一 freelancer 在同秒触发两次结算（直接调用 freelance_fees/service_mutation.py:324 路径），两单 settlement_no 不同且均写入成功；回归：payments/service.py:460 按 appointment_no 查单在双租户同号场景下仍命中唯一行；迁移回滚：downgrade -1 成功。
- **风险与回滚**：payments 模块按 appointment_no 查单（`app/modules/payments/service.py:460`，作 out_trade_no），单号生成器含 uuid 实际仍全局唯一，按号查询行为不变；唯一缩围反而降低跨租户撞号导致支付回调错配的概率。settlement_no 加长后注意不超 32 字符。回滚：downgrade 恢复全局唯一，若已存在跨租户同号行会失败，迁移注释写明。

#### P3-4 配置类编码改租户内唯一（shift_types.code、message_templates.code、guide_tours.code）+ 服务层配套
- **规模**：M ｜ **依赖**：P3-1
- **改动点**：1) 迁移 M4：shift_types.code（`app/models/shift_type.py:15`）、message_templates.code（`message.py:38`）、guide_tours.code（`guide_tour.py:32`）三表 drop 全局 unique，改 `UniqueConstraint(tenant_id, code)` + 平台行 partial unique index。2) 存量回填策略（已核实）：shift_types 的服务层创建（`app/modules/shift_types/service.py:141-147`）从不写 tenant_id，存量行全部为 NULL——采用保守策略：不回填，存量一律视为平台级共享类型（与现状行为一致），仅新数据开始区分；message_templates 与 guide_tours 的 tenant_id 服务层已有写入（service_templates.py:93、guide_tours/service.py:155），NULL 行同理视为平台模板/指引，与 `messages/service_templates.py:45-52` 读取时 tenant_id IS NULL 优先的既有语义吻合。3) 服务层配套（约束变更后必须同步，否则行为回归）：shift_types/service.py:99-111 get_by_code 加租户过滤、:136-147 create 写入 `tenant_id=get_current_tenant_id()`（范式照抄 service_templates.py:66-95）；guide_tours/service.py:147-162 create 增加租户内查重（当前无任何查重，仅靠 DB 兜底），平台上下文时检查 tenant_id IS NULL。message_templates 服务层已正确，不改。
- **测试清单**：双租户各创建 code=OPD 的班次类型成功；负向：同租户重复 code 返回 400 而非 500；负向：同租户重复创建 message_templates.code 返回 400（回归现有服务层查重），跨租户同 code 成功；负向：guide_tours 同租户重码返回 400（新查重生效），跨租户成功；迁移回滚：downgrade -1 成功。
- **风险与回滚**：shift_types 存量全为平台级，租户侧此前依赖「所有租户共享同一套 code」的行为，改造后新建的租户级类型不再冲突但也不再共享——与审计要求一致，属预期行为变化；若创建时无租户上下文（平台管理员），写入 tenant_id=NULL 继续走平台行约束。回滚：downgrade 恢复全局唯一，跨租户同 code 已产生时恢复失败，注释写明。

#### P3-5 TenantUsageLog 启用每日唯一约束 + 用量写入 upsert 幂等化
- **规模**：S ｜ **依赖**：P3-1
- **改动点**：1) `app/models/tenant.py:258-261`——去掉注释，启用 `UniqueConstraint('tenant_id','usage_date',name='uq_tenant_usage_date')`（tenant.py:230 该列 nullable=False，无需 partial index）。2) 迁移 M5：先扫描存量重复 (tenant_id,usage_date) 行——写入点 `app/tasks/tenant_usage_task.py:109-125` 是 check-then-insert，Celery 并发可产生重复（发现属实），重复行按「保留最新 created_at、计数列取 SUM 合并」清洗后 op.create_unique_constraint。3) 写入幂等化：tenant_usage_task.py:109-125 与 `app/modules/tenants/service_usage.py:103` 附近改为 `insert().on_conflict_do_update(constraint='uq_tenant_usage_date')`（asyncpg 方言，与 alembic.ini:5 的 PG 目标一致），消除并发窗口。4) 索引说明：该复合唯一索引的最左前缀已覆盖 tenant_id 单列查询，故 tenant.py:230 不再单列建索引（tenant.py:193/270 的索引归 P3-7）。
- **测试清单**：负向：同租户同日插入第二条 usage_log 被约束拒绝；正向：on_conflict 路径对已存在 (tenant,day) 记录执行更新而非插入，计数列累加正确；并发模拟：顺序执行两次定时任务体（tenant_usage_task.py 路径）最终仅一行且计数为两次之和；迁移测试：预置重复行时迁移打印冲突清单后中止；清洗后重跑成功；downgrade -1 成功。
- **风险与回滚**：清洗重复行是数据删改：合并逻辑按 SUM 聚合计数列，若业务侧不接受合并口径需在执行前人工核对扫描结果（迁移打印冲突清单）；on_conflict_do_update 仅 PG 可用。回滚：downgrade drop 约束即可，写入代码回退到 check-then-insert 无副作用。

#### P3-6 12 列裸 tenant_id 补外键（NOT VALID + VALIDATE 两步）
- **规模**：M ｜ **依赖**：P3-1
- **改动点**：1) 12 列清单（全部已逐一核实为裸 String 无 FK）：email_templates（`email_template.py:17`）、message_templates（`message.py:37`）、notification_logs（`notification_log.py:13`）、notification_preferences（`notification_preference.py:16`）、rule_set_audit_logs（`rule_set_audit.py:15`，nullable=False）、schedule_audit_logs（`schedule_audit.py:15`，nullable=False）、unified_templates（`unified_template.py:33`）、notification_groups（`app/modules/unified_message/models.py:39`）、notification_recipients（:61）、notification_deliveries（:86）、channel_strategies（:115）、recipient_rules（:130）；外加 P3-1 新增的 content_versions 与 news/notices/banners 的 tenant_id 一并挂 FK。2) 模型层同步给上述列加 `ForeignKey("tenants.id")`，FK 不设 ondelete（租户删除为软删，tenant.py:63，避免级联删业务数据）。3) 迁移 M6：逐表先清洗孤儿值（LEFT JOIN tenants 找 tenant_id 非空但租户不存在的行），审计日志类表孤儿行 tenant_id 置 NULL，并对 rule_set_audit.py:15 与 schedule_audit.py:15 两张 NOT NULL 表放宽为 nullable（模型层同步改 nullable=True——审计行缺租户属可接受的降级，见决策点 D14），随后 `ADD CONSTRAINT ... FOREIGN KEY (tenant_id) REFERENCES tenants(id) NOT VALID`，最后 VALIDATE CONSTRAINT（两步规避长锁）。4) VALIDATE 仅校验非 NULL 行，「NULL=平台级」语义不受影响。
- **测试清单**：负向：向 notification_groups 插入 tenant_id='nonexistent' 被外键拒绝；正向：tenant_id 指向真实租户的写入全部成功（unified_message 全链路回归）；孤儿清洗：预置孤儿行跑迁移后其 tenant_id 为 NULL，模型可读；迁移回滚：downgrade -1 逐表 drop 外键成功。
- **风险与回滚**：孤儿清洗中 NOT NULL 表放宽约束是行为放宽（可接受，审计日志本就允许缺失上下文）；VALIDATE 阶段若仍有脏值会失败但表已挂 NOT VALID 约束（新写入受保护），可修复后单独重跑 VALIDATE。回滚：downgrade 逐表 drop constraint 并恢复两表 NOT NULL，无数据损失。

#### P3-7 system_settings 租户维度预留 + tenant 子表索引补齐（标注第4期依赖）
- **规模**：S ｜ **依赖**：P3-1
- **改动点**：1) `app/models/settings.py:20` 后加 `tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID，NULL表示平台级配置")`，并在 :30-34 __table_args__ 增加 `Index('ix_system_settings_tenant_category','tenant_id','category')`；本期不新增唯一约束（现有 store_id/category/key 无唯一约束属实，等第4期定稿租户解析语义后随其一起加，避免约束与读路径脱节）。2) 读写逻辑本期零改动：`app/modules/settings/service_core.py:14-210` 的查询仍按 store_id 维度（已核实无任何 tenant 条件），tenant_id 列上线后默认全 NULL=平台级，行为不变。3) 索引补齐：`app/models/tenant.py:193`（tenant_subscriptions.tenant_id）与 :270（tenant_notifications.tenant_id）加 index=True；tenant_usage_logs.tenant_id（:230）由 P3-5 复合唯一覆盖不加单列索引。4) 迁移 M7：三处 add column/index；downgrade 对称删除。5) 第4期依赖标注（写进迁移文件 docstring 与交付说明）：SettingsService 需增加「租户覆盖 → 门店覆盖 → 平台默认」三级解析；微信/短信配置读点（`app/infrastructure/sms/service.py`、`app/tasks/wechat_task.py`、settings.py:69-89 定义的 wechat/sms category）在第4期改为按租户读取，本期列只是预留、不拆数据。
- **测试清单**：迁移往返：upgrade head / downgrade -1 成功，system_settings 出现/消失 tenant_id 与新索引；读写回归：get_by_category('booking')（service_core.py:14-38）在迁移前后返回一致，不传 tenant 时仍读平台级配置；负向：插入 tenant_id 不存在的 settings 行在 P3-6 完成后被外键拒绝（联合验证）。
- **风险与回滚**：零行为变更（新列全 NULL、读路径不动），是本期最安全的项；唯一风险是 FK 挂上后对存量 settings 行做孤儿校验——存量 tenant_id 全 NULL 不受影响。回滚：downgrade 删列删索引即可，完全无数据风险。

### 第4期 生命周期（P4，8 项）

**期目标**：先堵停服链路与注册密码两个安全缺口，再打通租户开通原子性、迁移事务与审计、订阅/配额/开关的商业化闭环与删除闭环，最后对 DataScope、role_permissions、branding_config 等死代码给出「接线 vs 删除」的处置对比与建议。所有发现均已逐条读源码核实，行号以当前代码为准。

#### P4-1 停服链路补全：患者/医生 token 校验租户状态 + 患者写入口守卫补挂
- **规模**：M ｜ **依赖**：无
- **改动点**：核实：患者/医生 token 加载器均不校验租户状态——`app/common/auth_unified.py:124-134`（_get_user_account 仅做租户一致性比对）与 :234-244（_get_doctor_account 同），而管理员路径 :391-428 有完整四态校验（status 0/2、订阅到期、试用到期）。写守卫 `require_tenant_active_for_write` 定义于 `app/common/tenant_deps.py:364-415`，实际仅挂 3 处（审计写 4 处有误）：`appointments/router_booking.py:39、:84`、`payments/router.py:117`。患者写入口仍有缺口：`appointments/router_flow.py:43`（签到，Depends(get_current_user) 无守卫）、`waitlist/router.py:15-19` 等，共约 12 个使用 get_current_user 的路由文件（waitlist/doctor_reviews/appointment_satisfactions/user_favorites/support_tickets/users/common_services 等）。改法：① auth_unified.py 新增内部辅助 `_ensure_tenant_serviceable(db, tenant_id, request_method)`，加载 Tenant（写法参照 tenant_deps.py:382-383），tenant 不存在或账号无 tenant_id 时放行（与 :127 判空语义一致）；status==0 一律 403 TENANT_DISABLED（复用 :395-400 的 raise_business_http_error 写法与 core/error_codes.py 既有错误码）；status==2 或 subscription_end_at 已过期、status==3 试用到期时仅对 POST/PUT/PATCH/DELETE 抛 TENANT_SUSPENDED_WRITE / TENANT_TRIAL_EXPIRED（区分逻辑参照 :401-428），GET 放行以保证「停服可浏览」（与 tenant_deps.py:369-371 守卫语义对齐）。在 :124-134 与 :234-244 两处租户校验块之后调用；get_current_account（:535-588）签名增加 `request: Request`（FastAPI Depends 显式传参风格）并把 request.method 传入两个 loader。② 对上述缺口写入口逐一补挂 `Depends(require_tenant_active_for_write)`（router_flow.py:43 签到、waitlist join 等患者写端点），风格与 router_booking.py:39 完全一致。
- **测试清单**：status=0 租户的患者 token：GET/POST 一律 403 TENANT_DISABLED（负向：无租户的平台管理员 token 不受影响）；status=2 租户：GET 预约列表 200、POST 创建预约 403 TENANT_SUSPENDED_WRITE；status=3 且 subscription_end_at 已过期：POST 403 TENANT_TRIAL_EXPIRED；停服租户患者调 router_flow 签到接口 403（修复前该端点无守卫可成功——回归用例）；账号 tenant_id 为 NULL 或租户行不存在：放行且不 500（防御性负向用例）。
- **风险与回滚**：每请求多一次 Tenant 查询（可与既有租户一致性查询合并）；停服租户下小程序将收到新错误码（错误码已存在，前端需兼容提示）；admin/平台账号路径不受影响。回滚：revert 单个 commit；各路由守卫挂载可逐个摘除。

#### P4-2 自助注册密码接入 PasswordPolicyValidator
- **规模**：S ｜ **依赖**：无
- **改动点**：核实：自助注册入口 `router_current_tenant.py:91-112` → `service_tenant.py:423-485` register_tenant，:468 直接 `get_password_hash(data.admin_password)`，未经过任何策略校验；schema 层 `schemas.py:628-647` 的 validate_password_strength 仅硬编码长度 6-20，未复用策略实现。策略实现在 `password_policy.py:30-113`（PasswordPolicyValidator.validate 支持 username/phone 维度），get_tenant_password_policy（:116-149）对 tenant_id=None 返回 DEFAULT_POLICY（:14-27，min 6/max 20、无复杂度要求）；该校验器已在管理端 8 处路径使用（admin/service_admins.py:225-227 等）。改法：① service_tenant.py:454-468 在 get_password_hash 之前插入 `PasswordPolicyValidator(await get_tenant_password_policy(self.db, None)).validate(data.admin_password, username=data.admin_username, phone=data.contact_phone)`，失败 raise ValueError（router_current_tenant.py:109-112 已映射 400）；注册时租户尚未建立，故取默认策略。② schemas.py:641-647 的硬编码校验改为调用 `PasswordPolicyValidator(dict(DEFAULT_POLICY)).validate`，单一事实来源，默认语义不变（min 6/max 20），保证向后兼容。
- **测试清单**：密码 "12345"（<6 位）注册 → 400（负向）；monkeypatch DEFAULT_POLICY 开启 disallow_username 后，密码包含 admin_username → 400（负向）；合法密码 "abc123" 注册成功（默认策略无复杂度要求，向后兼容正例）；既有管理端改密路径（admin/service_admins.py、auth/router.py、doctors/router.py、users/router.py、accounts/router.py）行为不变（回归）。
- **风险与回滚**：默认策略与现网行为一致，无破坏性；未来收紧 DEFAULT_POLICY 将同步约束注册——这是设计意图。回滚：revert 单 commit 即恢复硬编码校验。

#### P4-3 租户开通原子性：单事务提交（create 与 register_tenant）
- **规模**：M ｜ **依赖**：无
- **改动点**：核实：`service_tenant.py:112-154` create() 在 :145 先 commit 租户，:149 调 _init_tenant_defaults，后者在 :205 再次 commit——中途失败（如建门店/科室/角色任一步 IntegrityError）会留下有租户无默认数据的半开通状态；:156-205 默认初始化只建门店/科室/角色，不建管理员账号（对比 register_tenant:459-476 自助注册会建管理员）。改法：① :145-146 的 commit+refresh 改为 `await self.db.flush()`（Tenant.id 由模型 default lambda 生成，flush 后可用）；② _init_tenant_defaults 末尾 :205 的 commit 改为 `await self.db.flush()`（该函数同时被 register_tenant:457 复用，改后由外层统一提交）；③ create() 尾部（:149-154）统一 commit + refresh，整体包 try/except：异常时 `await self.db.rollback()` 后 raise ValueError("租户开通失败，请重试")，`tenants/router.py:236-243` 已映射 400；④ register_tenant（:454-478）去除中途提交路径后天然单事务（flush:455 → defaults → 建 admin:464-477 → :478 唯一一次 commit），同样补 rollback 保护。「默认初始化是否补建平台开通管理员账号」为产品决策（决策点 D16），本期不动 TenantCreate schema。
- **测试清单**：monkeypatch 使 Department 插入失败 → tenants 表无该 tenant_code 记录（负向：不留半开通租户）；正常 create → 门店/科室/角色全部存在且与租户同事务落库；重复 tenant_code → 400 且无任何残留行（负向）；register_tenant 初始化阶段失败 → 租户与管理员均无残留（负向）。
- **风险与回滚**：提交时点后移，调用方语义不变（仍返回已 refresh 的 Tenant）；tenant_code 数据库唯一约束（`models/tenant.py:58`）兜底并发重复。回滚：revert 即恢复两段提交行为，无 schema 变更。

#### P4-4 迁移健壮性：全有或全无事务 + preserve_ids 撞键预检 + 迁移审计
- **规模**：M ｜ **依赖**：无
- **改动点**：核实：`service_migration.py:471-476` 逐实体 except 吞异常仅记入 failures，:478 无条件 commit——部分成功静默落库且无审计；:310-311 _get_new_id 在 preserve_ids=True 时直接返回原 ID，配合 :321-331 _copy_model_instance 会在目标租户已存在同 ID 数据时撞主键（`router_migration.py:75` 文档原文「preserve_ids=true 可保留原始 ID（需谨慎使用）」），撞键异常同样被 :471 吞掉；migrate_data 全程无任何审计写入。改法：① 事务语义改为全有或全无：任一实体失败 → `await self.db.rollback()` 后 `raise ValueError(f"迁移失败: entity={entity_name}, error={exc}")`（router_migration.py:119-123 已映射 400），全部成功才执行 :478 的 commit；② preserve_ids 预检：每个实体写入循环前执行 `select(model.id).where(model.id.in_(源ID集), model.tenant_id == target_tenant_id)`（大集合分批 in 查询），命中即 raise ValueError 说明冲突，router_migration.py:75 文档同步更新为「需目标租户无同 ID 数据」；③ 审计：audit_tracker.py 仿照 track_subscription_change（:214-247）新增 `track_migration(tenant_id, source_tenant_id, copied, preserve_ids, actor_id)`，event_type/action="migrate"，在成功 commit 后调用，actor 取 router_migration.py:117 已传入的 current_admin id。迁移的权限守卫已是 require_platform_admin（router_migration.py:32、:106），符合目标模式，不动。
- **测试清单**：第二个实体强制抛错 → 整体 rollback：目标租户无任何新行，接口 400 且 body 含实体名（负向：不再部分提交）；preserve_ids=True 重放同源迁移 → 400 冲突提示且零写入（负向：撞主键被前置拦截）；成功迁移 → copied 计数正确且 TenantAuditLog 出现 action=migrate 记录（含 copied 快照与操作人）；非平台管理员调用 /migrate → 403（既有守卫负向回归）。
- **风险与回滚**：从「部分成功」变为「全有或全无」属行为变更，需知会运营；ID 预检的大列表 in 查询需分批防超长。回滚：revert 单 commit；track_migration 为新增方法可独立移除。

#### P4-5 订阅闭环：payment_status 回写端点 + auto_renew 定时续费任务
- **规模**：M ｜ **依赖**：无
- **改动点**：核实：`service_subscription.py:153-165` 构造 TenantSubscription 时不写 payment_status，模型默认恒为 "pending"（`models/tenant.py:212`），全库无任何更新 payment_status 的代码（grep 仅命中 models/tenant.py:212 与 schemas.py:384 响应字段）；auto_renew（models/tenant.py:219）仅被 :163 写入，全库零读取方；`tasks/tenant_usage_task.py` 仅在 :225 把到期租户置 status=2，无续费逻辑。改法：① service_subscription.py 新增 `mark_subscription_paid(tenant_id, subscription_id, payment_method, transaction_id, actor_id)`：置 payment_status="paid"、paid_at=utcnow，并按 :178-187 既有 tracker 模式写订阅审计；② tenants/router_plans.py（或 router.py）新增平台管理员端点 `PATCH /tenants/{tenant_id}/subscriptions/{subscription_id}/paid`，Depends(require_platform_admin())（写法参照 router_migration.py:106），作为支付状态回写入口；③ auto_renew 消费：tenant_usage_task.py 每日扫描中（:225 置欠费之前）读取租户最新订阅（复用 get_tenant_subscriptions，service_subscription.py:194-206），若最新订阅 auto_renew=True 且 payment_status="paid" 且 tenant.subscription_end_at <= now：按 billing_cycle 延长 end_at（monthly +30 天 / yearly +365 天，对齐 :144-150 算法），新建一条 TenantSubscription(payment_status="pending"，auto_renew 继承) 记录本期应收，且该租户跳过 :225 的置 2 分支（宽限期语义）；未付费（pending）或 auto_renew=False 的租户维持现有到期置 2 行为。幂等：以最新订阅的 start_at/end_at 区间判断防重。
- **测试清单**：平台管理员标记支付 → payment_status/paid_at 正确落库并出审计（负向：租户管理员调用 → 403；订阅不存在 → 404）；续费任务：auto_renew=True 且 paid 且今日到期 → end_at +30 天、生成一条 pending 新订阅、tenant 保持 status=1；auto_renew=True 但 payment_status=pending → 不续费、到期照常置 2（负向：未付费不延长）；auto_renew=False → 行为与现状完全一致（回归）；重复执行续费任务 → 不产生重复订阅记录（幂等负向）。
- **风险与回滚**：自动续费仅「延长周期 + 生成待支付账单」，无真实扣款通道——商务语义需确认（决策点 D17）；定时任务改动需验证与 :225 欠费标记的先后顺序。回滚：新端点与任务内续费分支可独立摘除，无 schema 变更。

#### P4-6 配额闭环：miniapp/storage/lowcode 三类资源检查接线
- **规模**：M ｜ **依赖**：无
- **改动点**：核实：`common/quota.py:285-290` check_methods 仅注册 stores/admins/doctors/appointments 四类；`models/tenant.py:156-162` get_effective_max_lowcode_pages 与 :164-170 get_effective_max_miniapp_instances 全库零调用方；存储维度 Tenant 上无 max_storage_mb 列也无 getter（审计「storage 有 getter」不成立，修正），仅有计划列 max_storage_mb（models/tenant.py:37）与用量字段 TenantUsageLog.storage_used_mb（:246，service_usage.py:243、:261 只读，全库无写入方）。缺口：`miniapp_platform/service_instance.py:193-205` 创建实例无任何配额检查（该文件 grep 无 quota/max_miniapp）；`upload/router.py:55` upload_image、:152 transfer_from_url 无存储配额；lowcode 页面数已有 feature_gate 门禁（`lowcode/router.py:139-140、:332-333` → feature_gate.py:84-98 按 features.lowcode_max_pages），与计划配额 max_lowcode_pages 构成双轨。改法：① QuotaChecker 新增 check_miniapp_instances_quota（用 :164-170 getter，count MiniappInstance）、check_lowcode_pages_quota（用 :156-162 getter，count LowCodePage）、check_storage_quota（max_storage_mb 对比 TenantUsageLog 最新 storage_used_mb；因计量无写入方，实现为「无用量数据时放行」，待计量任务补齐后生效）；:285-290 注册 "miniapp_instances"/"lowcode_pages"/"storage_mb"。② 接线：service_instance.py:193 前（:205 add 之前）`check_quota(tenant_id, "miniapp_instances", self.db)`；upload/router.py:55/:152 入口挂 storage 检查（无数据放行）；lowcode 创建入口（lowcode/router.py:139-140、:332-333）在既有 feature 门禁后追加计划配额检查（两道限制取更严者；单轨化决策见决策点 D19）。测试扩展 `tests/tenants/test_quota.py`。
- **测试清单**：已达 max_miniapp_instances 的租户创建实例 → 403 QuotaCheckError（负向：其他租户不受影响）；租户无订阅计划 → 使用 models/tenant.py:170 兜底值 3，行为可预期（负向：无计划不 500）；storage 用量数据存在且超 max_storage_mb → 上传 403；无用量数据 → 放行（负向：不误杀）；lowcode 计划配额 5、已建 5 页 → 创建 403；删一页后可再建（含负向）；check_quota 传未注册资源类型 → ValueError（既有负向回归）。
- **风险与回滚**：storage 计量缺失时必须「无数据即放行」防误杀；miniapp 计数是否包含已停用实例（status=2，service_instance.py:279）需产品确认口径（决策点 D20）。回滚：三类检查相互独立，注册项与接线点均可单独摘除。

#### P4-7 租户审计补全 + 软删除闭环（审计接线、get_by_code 语义、90 天物理删除任务）
- **规模**：L ｜ **依赖**：P4-3
- **改动点**：核实：`audit_tracker.py` 的 track_create（:72-101）与 track_delete（:154-183）全库零调用方（grep 仅 track_update/track_status_change 被 service_tenant.py:226/:232/:255、track_subscription_change 被 service_subscription.py:180 使用）；租户 create（service_tenant.py:112-154）、delete（:276-305）、restore（:307-335）均无审计；:276-305 delete 文档承诺「保留关联数据 90 天后物理删除」但 tasks/ 目录无任何对应任务；get_by_code（:39-46）与 check_code_exists（:415-421）不滤 deleted_at，tenant_code 又有数据库唯一约束（models/tenant.py:58），故被软删租户的 code 在物理删除前永久占用。改法：① create() 提交前调 track_create(actor_id=created_by, actor_type="platform_admin")，delete() 提交前调 track_delete(actor_id=deleted_by)，restore() 补 track_update；audit_tracker.py:24-30 的 TRACKED_MODELS["tenant"] 字段列表加入 "deleted_at" 使软删/恢复在 update 审计中可见；② get_by_code 增加 `include_deleted: bool = False` 参数：唯一性检查路径（create:115、register_tenant:430、check_code_exists:415-421、router.py:260 check-unique）显式传 include_deleted=True 保持占位语义，业务解析路径默认滤 `deleted_at.is_(None)`（过滤写法参照 contacts/service.py:102-113）；③ 新增 `tasks/tenant_lifecycle_task.py` purge_deleted_tenants_task（celery beat 每日，注册参照 celery_app.py:78、:267 既有条目）：选取 deleted_at < now-90d 的租户，逐租户单事务按外键层级删除子表（TenantNotification→TenantUsageLog→TenantSubscription→TenantAuditLog→业务表，实施时用 information_schema 枚举 tenant_id 外键表核对防孤儿）；双保险开关 config.TENANT_PURGE_ENABLED（默认 False）+ TENANT_PURGE_DRY_RUN（默认 True），首版仅 dry_run 输出将删除清单，删除前写 TenantAuditLog(action="purge") 并打结构化日志。
- **测试清单**：create/delete 后 TenantAuditLog 各新增一条 action=create/delete 记录（负向：纯查询不产生审计）；软删租户：check_code_exists 仍为 True（占位）；物理 purge 后变 False 且同 code 可重新注册（负向：未 purge 前创建同 code → 400 而非裸 IntegrityError）；purge dry_run=True → 仅输出清单不删数据（负向）；ENABLED+超 90 天 → 租户及子表清空；未满 90 天不动；ENABLED=False 全程不动；purge 中某租户子表删除失败 → 该租户事务回滚、跳过并记日志，其余租户继续；restore 后审计记录含 deleted_at 变更快照。
- **风险与回滚**：物理删除不可逆，必须 dry_run 试点并确认备份策略后才启用；子表清单遗漏会产生孤儿数据（实施时以 schema 枚举校验）；软删 code 在 purge 前保持占用是唯一性约束的必然语义，需在管理端文案说明。回滚：关闭 TENANT_PURGE_ENABLED 即停；已删数据仅能靠备份恢复（回滚方式=禁用开关+备份还原）。

#### P4-8 死代码与功能开关处置：DataScope / role_permissions / branding_config / 未消费开关（接线 vs 删除对比）
- **规模**：M ｜ **依赖**：无（建议在 P4-5/P4-6 稳定后实施，排入末批）
- **改动点**：核实：① DataScope：模型 `models/data_scope.py:10-34`，Role.data_scope_id 与 relationship 在 `models/admin.py:60、:68`；全库无任何 DataScope 的 CRUD/种子数据，管理员响应字典也不含 data_scope（admin/helpers.py:38-100 build_admin_response 未构建该键），故 `common/data_scope.py:83-89` _get_data_scope 恒为 None、一律走 :121-149 fallback（审计所指「:111-117 永远走 fallback」修正为：custom 分支在 :111-117，恒走 fallback 的入口在 :83-89）；唯一运行时消费是 `statistics/router_overview.py:45、:61、:66、:71、:83` 的 apply_data_scope（实际全走 fallback）。② role_permissions 关联表 `models/admin.py:11-16` 全库无读写（grep 命中的均为无关的 app/common/role_permissions.py 模块与路由函数名）。③ branding_config（`models/tenant.py:84`）写入口为 TenantSelfUpdateRequest（schemas.py:284-291）并经 TenantResponse（schemas.py:309）回显，但无任何运行时消费。④ 功能开关：TenantFeatures 共约 23 个布尔开关（feature_definitions.py:18-54），真正的运行时强制消费仅 lowcode_* 共 10 处 enforce_feature（lowcode/router.py:139、:332、:412、:525、:575、:627、:804、:857、router_template.py:263、:422，经 feature_gate.py:45/:84），router_current_tenant.py:191-192 仅展示；`tasks/notification_task.py:247-262` 的 _should_use_unified 检查的 beta_unified_message 已退役（feature_definitions.py:43 注释），因 feature_flags.py:61-65 只合并已定义字段而恒为 False，:435 处分支成死代码（审计将此列为「真消费」，实际为死分支，修正）。处置方案（每项附接线/删除两选项与建议）：DataScope——A 接线：auth_unified.py:315-324 查询加 selectinload(Role.data_scope)，AdminInfo/管理员字典补 data_scope（helpers.py:96 区域），另需新建 DataScope 角色管理 CRUD（M~L）；B 删除：删模型与 Role.data_scope_id（:60、:68）、common/data_scope.py 的 scope 分支（保留 _fallback_filter 为唯一路径，router_overview 调用不变）、permission_deps.py:40-52/:76-86 解析，Alembic drop data_scopes 表与 roles.data_scope_id 列。**建议 B**：与本期「tenant_id 锚点」模式重复、从未启用，接线反而扩大越权面。role_permissions——**建议直接 Alembic drop**（drop 前核对行数=0）。branding_config——A 接线：router_current_tenant /me 与公开登录配置端点返回解析后的品牌 JSON（S）；B 仅存不用。**建议 A**。功能开关——A 接线：新增 common/feature_deps.py 提供 `require_feature(name)` Depends 工厂（403 模式参照 feature_gate.py:47-63），先试点 online_payment→payments/router.py:112 与 export_data、basic_statistics 三个高价值开关；B 不接线：在 feature_definitions.py 与运营文档标注「展示型开关」。共同必做：删除 notification_task.py:247-262 死分支（改为直走统一消息路径或删除）。**建议**：B 起步 + 删死分支 + online_payment 单点试点 A。
- **测试清单**：online_payment 试点：未开通开关的租户创建支付订单 → 403 功能未启用（负向），开通后恢复 200；删除 notification_task 死分支后：预约通知发送回归（既有单测 + 触发一条通知确认走统一消息路径）；DataScope 选删除：statistics/router_overview 概览接口回归（fallback 语义不变，数值一致）；role_permissions 表 drop：角色创建/更新/登录鉴权回归（权限仍走 roles.permissions JSON，helpers.py:40-47）；branding 接线：/me 返回解析后的 branding_config（负向：未配置时返回 null 不 500）。
- **风险与回滚**：删除类操作不可逆，依赖 Alembic downgrade 重建表列，drop 前必须核实 data_scopes/role_permissions 行数为 0（决策点 D20）；接线项若开关默认 False 会立即切断现网租户功能，试点开关须先给存量租户/计划补 features 数据或临时默认 True；死分支删除涉及通知链路需与统一消息收尾工作协调。回滚：接线部分逐端点摘除；删除部分依赖 downgrade 迁移。

### 测试基建（T，7 项）

**期目标**：为租户隔离改造第1、2期提供可批量执行、可独立回滚的测试基建：多租户夹具工厂、12模块隔离矩阵参数化模板、fail-close与提权链负向用例、弱断言加固、空白区补测与CI分批跑法。实测基线：`pytest tests/security/test_tenant_isolation.py -q` → 16 passed in 3.84s。T 项与各批穿插关系见第四节批次表。

#### T-1 conftest 新增多租户夹具工厂 multi_tenant_env 与 admin_token_factory
- **规模**：M ｜ **依赖**：无
- **改动点**：`apps/server/tests/conftest.py` 新增夹具部分只增不改（存量夹具的语义迁移不在本项——`test_super_admin_role`/`super_admin_token` 消费面的迁移由 P1-1 改动点④ 归属并在批次1 完成，见 R8）：基于既有 TestDataFactory（conftest.py:832-1090，factory fixture 1087-1090；注意审计所称 MultiTenantDataFactory 实为 TestDataFactory，全库 grep 无该名）新增 (a) multi_tenant_env fixture：两个租户（A/B）+ 各自门店 + 各自租户管理员角色与账号 + 平台管理员账号；(b) admin_token_factory fixture：闭包工厂，复用 conftest.py:436-452 的 `create_access_token({"sub": admin_id, "type": "admin"})` 模式为任意 admin 生成 token。关键约束：is_super_admin 判定为 role_code=="SUPER_ADMIN"（`app/common/auth_unified.py:373`，P1-1 合入后追加 role.tenant_id IS NULL 前提），故租户管理员角色码必须避开 SUPER_ADMIN/PLATFORM_ADMIN（用 TENANT_ADMIN 或 STORE_ADMIN，参照 conftest.py:565-582 的角色构造）；平台管理员用 SUPER_ADMIN 码 + tenant_id=None 的 Admin（conftest.py:586-605 的 test_super_admin 实为带 tenant_id 的全量权限角色，不满足 require_platform_admin 语义，见 tenant_deps.py:105-117），须新建独立夹具并命名区分。实现顺序：先写 multi_tenant_env 与 admin_token_factory 并加 unit 用例，再供 T-2~T-6 消费。
- **测试清单**：`tests/unit/test_factory_fixture.py`（已存在）新增用例：multi_tenant_env 两租户 id/tenant_code 互不相同；admin_token_factory 生成的 token 经 decode_token 解出 sub 与 type=admin；平台管理员夹具的 admin.tenant_id 为 None 且角色码为 SUPER_ADMIN；负向：租户管理员 token 携带 SUPER_ADMIN 角色码时 get_tenant_filter 返回 None（tenant_deps.py:129-131）——用例显式防止该错误配置再次出现。
- **风险与回滚**：纯新增，不改任何现有 fixture，回滚=删除新增段落即可；风险点是 ContextVar 租户上下文在 async fixture 间串扰，须在 fixture 内 finally 调 `clear_tenant_context()`（`middleware/tenant_context.py:63-66`）。

#### T-2 12 模块租户隔离矩阵参数化模板（注册表 + 3类断言批量生成）
- **规模**：L ｜ **依赖**：T-1
- **改动点**：新增 `apps/server/tests/security/tenant_matrix.py`（注册表+断言库）与 `tests/tenants/test_isolation_matrix.py`（参数化用例）。注册表条目结构：(module, list_path, object_path_tpl, factory_method, item_id_extractor, cross_status∈{403,404}, requires_detail=bool)。每模块生成 3 类断言：① 租户A管理员带 X-Tenant-ID=A 调 list_path，仅见A数据（锚定目标模式：管理员查询以管理员账号 tenant_id 过滤，参照 `app/modules/contacts/service.py:101-113` 与 `audit_logs/router.py:178-187`）；② A 管理员 GET B 租户对象 id → cross_status；③ A 管理员对 B 对象执行 PUT/DELETE → 非 2xx。首批 12 模块为核心管理端路由：stores、departments、doctors、schedules、appointments、patients(router_manage)、admin/roles、tenants、audit-logs、contacts、payments、statistics；statistics 等无单对象 GET 的模块 requires_detail=False 只跑列表断言。注（修订核实）：该清单并非全部来自 `api/v1/__init__.py:22-33`——实测该区间注册的是 auth/users/stores/departments/doctors/schedules/appointments/patients/admin/settings/statistics/platform-metrics/accounts/tenants，无 audit-logs（注册于 :101）、contacts（:91-94）与 payments（:109）；各模块条目实施时以实际挂载路径为准（D23 确认口子兑现）。departments 条目在 P2C-7 落地后启用，未落地前 skip。用 pytest.mark.parametrize 展开，marker 标 security+multi_tenant（marker 注册见 T-7）。实现顺序：先抽象断言库并跑通 stores/departments/doctors 三模块试点，再扩到 12。
- **测试清单**：每模块3条：A管理员列表仅含A数据（含数量与id双重断言，禁用『不包含』单侧断言）；A管理员跨租户 GET → 404 或 403（注册表显式声明期望值，禁止 200+空体过关）；A管理员跨租户写（PUT/DELETE）→ 非 2xx 且 B 数据未被改动（改后回读校验）；负向：矩阵注册表中某模块 extractor 写错导致断言失效——试点阶段以注入伪造 B 数据的对抗用例验证断言确实会失败；B 租户数据在 A 全部请求后仍完整存在（防误删）。
- **风险与回滚**：各模块响应包裹不同（PageResponse.data vs 裸 list vs {items,total}），item_id_extractor 需逐模块适配，试点先行可控制风险；部分写接口路径不规则（如 appointments 取消在 `router_booking.py:71-99`），矩阵只覆盖标准 REST 形态，特殊端点单独补测。回滚=删除两个新文件。矩阵各模块条目按对应模块修复批次的验收门逐步启用（未修复模块先 skip/xfail，防止长期红）。

#### T-3 fail-close 行为测试（无上下文 403/400 而非全量）
- **规模**：M ｜ **依赖**：T-1
- **改动点**：新增 `apps/server/tests/security/test_fail_close.py`：(a) 模拟 tenant_id 为空的租户管理员（角色码非 SUPER_ADMIN）调用 audit-logs 导出等以 admin.tenant_id 为锚的接口 → 403（依据 `audit_logs/router.py:178-181`）；(b) 显式验证平台管理员例外路径：is_super_admin → get_tenant_filter 返回 None（tenant_deps.py:120-134），仅平台管理员可见跨租户，配 require_platform_admin 守卫接口（tenant_deps.py:223-238）对租户管理员 403；(c) 记录并测试 require_tenant_active_for_write 的组合语义：无租户上下文时直接放行（tenant_deps.py:378-380 return），因此该守卫只可与『上下文已由中间件保证』的端点组合——对 `appointments/router_booking.py:39、84` 与 `payments/router.py:117` 三处挂载点发无 X-Tenant-ID 请求，断言不得返回全量数据（依赖公开路径校验 validate_public_tenant_context 返回 400，tenant_context.py:69-89，PUBLIC_TENANT_REQUIRED_PATHS 33-44）；(d) 公开预约/医生/门店路径无任何租户头 → 400 而非 200。每用例前后调 clear_tenant_context() 防 ContextVar 污染。
- **测试清单**：非平台管理员且 admin.tenant_id 为空 → 403 而非空列表 200（fail-close 核心断言）；平台管理员跨租户查询可见全量（正向例外路径，防误伤）；租户管理员调 require_platform_admin 守卫接口（如 tenants 迁移 precheck，`tenants/router_migration.py:32`）→ 403；公开端路径无租户头 → 400（覆盖 PUBLIC_TENANT_REQUIRED_PATHS 全部 10 个前缀）；负向：删除请求头后管理端列表不得返回他租户数据（若返回 200+他租户数据即失败）。
- **风险与回滚**：『无 tenant_id 的 admin』需手工构造（现有夹具均带 tenant_id）；中间件在 TestClient 下对 X-Tenant-ID 缺失的行为与生产网关可能不同，断言以应用内 deps/中间件行为为准并在用例注释注明。回滚=删除新文件。

#### T-4 提权链负向测试（建 SUPER_ADMIN 角色/赋平台 role_id 应拒，TDD 红灯 xfail 标注）
- **规模**：M ｜ **依赖**：T-1
- **改动点**：新增 `apps/server/tests/security/test_privilege_escalation.py`。核实结论（2026-10-22 实读）：① 创建角色无保留字校验——`admin/router_roles.py:63-77` 直通 `service_roles.py:73-93`，create() 的唯一性检查 get_by_code（:75）仅限本租户范围，租户管理员可成功创建 code="SUPER_ADMIN" 或 permissions=["*"] 的角色（现有保护 :101-107/:128-129/:143-144 只覆盖对已存在 SUPER_ADMIN 角色的 update/delete）；② 创建管理员 role_id 直写——`service_admins.py:246-259` 第 :254 行 role_id=data.get("role_id") 无租户归属与保留字校验；③ 迁移守卫已存在可直接转绿——`tenants/router_migration.py:32` precheck 与 :51 附近 migrate 均挂 Depends(require_platform_admin())。用例：租户管理员 POST /api/v1/admin/roles 建 code="SUPER_ADMIN" → 期望 4xx；建 permissions=["*"] → 期望 4xx；创建 admin 时 role_id 指向他租户/平台角色 → 期望 4xx；租户管理员调 /tenants/{id}/migrate 与 /migrate/precheck → 断言 403（现状即应通过）。①②为 TDD 红灯用例：以 `pytest.mark.xfail(strict=True)` + 自定义 marker pending_fix_phase1 标注，第1期（P1-2）代码修复合入后 xpass 触发失败提示移除标记，防止红测试被静默遗忘。
- **测试清单**：租户管理员建 code=SUPER_ADMIN 角色 → 期望 4xx（xfail strict，现状会 201/200 成功）；租户管理员建 permissions=[*] 角色 → 期望 4xx（xfail strict）；租户管理员创建下级 admin 时 role_id 指向平台角色 id → 期望 4xx（xfail strict）；租户管理员调 migrate/precheck 与 migrate → 403（现状即绿，验证既有守卫不回退）；负向：平台管理员执行同样操作应成功（防把守卫收紧到误伤平台管理员）。
- **风险与回滚**：xfail(strict=True) 在 P1-2 落地时会转为 XPASS→用例失败，属预期提醒机制而非缺陷；须在提交信息与用例 docstring 注明对应第1期修复项编号（P1-2），否则移除标记时无从判断。回滚=删除新文件；xfail 用例不影响现有套件通过率。

#### T-5 弱断言加固：tests/tenants/test_tenant_isolation.py:277-282 条件放行改硬断言
- **规模**：S ｜ **依赖**：无
- **改动点**：修正 `apps/server/tests/tenants/test_tenant_isolation.py:277-282`（审计行号 281-285 有偏移，实为 test_cross_tenant_access_denied 内 :269-275 发请求、:277-282 弱断言）：把 `if response.status_code == 200:` 的条件分支改为硬断言 `assert response.status_code in (200, 403)`，且 200 分支内必须同时断言 doctor_ids 为空列表或不含 B 医生（禁止『非 200 即通过』的静默放行）。同模式全库排查（修订时实跑 `grep -rn "if response.status_code" apps/server/tests` 实测命中 6 处）：tests/tenants/test_tenant_isolation.py:279、tests/tenants/test_tenant_data_isolation.py:807、:834、tests/integration/test_permissions_403.py:178 四处为条件放行，逐处按同法加固；tests/integration/test_rule_sets_router_endpoints.py:513、:1295 两处为 ==500 分支属合法模式，不动。另加固同类弱写法：凡『断言不含 X』的单侧断言必须伴随数量/全集断言。
- **测试清单**：加固后的 test_cross_tenant_access_denied 在 200/403/500 三种 mock 响应下的行为：500 必须失败；grep 复查门（精确定义，替代首轮「无残留」表述——首轮该表述按全库实测不可能通过）：`grep -rn "if response.status_code" apps/server/tests` 仅允许命中 ==500 等非放行比较（即仅剩 test_rule_sets_router_endpoints.py:513/:1295 两处），任何 `==200` 条件放行与 if-else 静默分支均判失败；tests/tenants/test_tenant_isolation.py、tests/tenants/test_tenant_data_isolation.py、tests/integration/test_permissions_403.py 三个加固文件重跑通过。
- **风险与回滚**：低风险单文件修改，回滚=revert 该 commit；注意加固后若暴露现有接口真实 500，属测试发现缺陷而非测试问题，转交第1期代码工作项。

#### T-6 空白区补测：停服登录/密码策略/自助注册租户上下文/公开端写守卫
- **规模**：M ｜ **依赖**：T-1
- **改动点**：五处空白全部核实为无既有测试（grep password_policy/_check_tenant_status_for_login/require_tenant_active_for_write/TENANT_DISABLED 于 tests/ 均无命中；migrate 仅命中与 Alembic 无关的 tests/integration/test_alembic_migration.py）。新增四文件：(a) `tests/security/test_suspended_tenant_login.py`——管理员登录在租户 status∈{0,2,3} 时 403，依据 `admin/router_auth_login.py:67-103` _check_tenant_status_for_login（status 0→403 租户已被禁用、2→403、3→403 结构化错误码），另覆盖 :172-173 账号停用 403；(b) `tests/unit/test_password_policy.py`——PasswordPolicyValidator 全分支参数化（`app/modules/tenants/password_policy.py:30-113`：长度/大小写/数字/特殊字符/disallow_username/disallow_phone 后四位/连续重复），get_tenant_password_policy 的 tenant_id=None→DEFAULT_POLICY（:132-133）、租户不存在→默认（:138-140）、坏 JSON→默认（:142-147）；(c) `tests/tenants/test_register_tenant_scope.py`——自助注册 `auth/router.py:210-253`：无租户上下文时 tenant_id=None（:224）→ 密码策略走默认且用户落库租户归属未定，期望 fail-close 拒绝的用例以 xfail strict 标注待决策点 D22 拍板（同 T-4 机制），现状行为用例直接编写；(d) `tests/security/test_public_write_guard.py`——require_tenant_active_for_write（tenant_deps.py:364-415）对 status=0→TENANT_DISABLED 403、status=2→TENANT_SUSPENDED_WRITE 403、订阅过期→403（:399-413 区分试用/正式错误码）、无上下文放行（:378-380，组合语义由 T-3 覆盖），对挂载点 `appointments/router_booking.py:39,84` 与 `payments/router.py:117` 做 API 级验证。依赖 T-1 的 multi_tenant_env 构造双租户与状态位。
- **测试清单**：租户 status=0/2/3 时管理员登录均 403 且错误码正确；租户 status=1 时登录成功（防守卫误伤）；密码策略参数化全分支命中（含负向：含用户名/手机号后四位/超长重复字符被拒）；注册端点无租户上下文 → 期望 400（xfail strict 待拍板）+ 现状行为快照用例；公开写端点在停服/欠费/过期租户下 → 403，只读端点仍 200；无租户上下文的写请求 → 不得静默成功写入库（负向）。
- **风险与回滚**：(c) 的期望行为依赖决策点 D22，先以 xfail 标注期望、现状用例照常编写可避免阻塞；租户状态字段直接改库（status=2 等）绕过业务流转，属测试夹具惯例，注释说明。回滚=删除四个新文件。

#### T-7 CI 分批执行：注册 multi_tenant marker 并在 test.yml 增加隔离矩阵步骤
- **规模**：S ｜ **依赖**：T-2、T-4、T-6
- **改动点**：pytest.ini 现状已核实（`apps/server/pytest.ini:1-18`：asyncio_mode=auto、markers 含 unit/integration/security/slow/architecture、addopts 含 --strict-markers）。改动：(a) pytest.ini markers 追加 `multi_tenant: Multi-tenant isolation matrix tests`（--strict-markers 下未注册 marker 会报错，必须先注册）；(b) `.github/workflows/test.yml` 现有分批：64 行 pytest tests/unit（SQLite+覆盖率）、76 行 tests/integration（PG，TEST_DATABASE_URL=postgresql+asyncpg://test:test@localhost:5433/test_db）、86 行 alembic、98 行 architecture。新增一步 Run tenant isolation matrix：`pytest tests/security tests/tenants -m multi_tenant -q`（SQLite 内存库即可，实测增量成本低）；并在 PG integration 步骤以 -m multi_tenant 追加跑一遍矩阵防 SQLite/PG 方言差异（JSONB 等路径，与 conftest.py:56-59 注释一致）。分批策略：第1期合入 T-2/T-3/T-5（矩阵+fail-close+加固）后启用该步骤；第2期合入 T-4/T-6 后 xfail 项随修复逐个转绿移除标记，无需改 CI。本地按期跑法：第1期 `pytest tests/security tests/tenants -m multi_tenant`；第2期 `pytest tests/security -m privilege` 或按文件名。timeout-minutes 现 30（test.yml:23），增量预计 <2 分钟无需上调。
- **测试清单**：pytest.ini 修改后 `pytest --co -q` 无 strict-markers 报错；本地 `pytest tests/security tests/tenants -m multi_tenant -q` 全绿；负向：临时注入一个故意失败的矩阵用例，确认 CI 新步骤红且阻断（本地以 `pytest -m multi_tenant` 退出码非 0 验证）；PG 批次：TEST_DATABASE_URL=postgresql+asyncpg://test:test@localhost:5433/test_db pytest -m multi_tenant 通过（CI 环境验证，本地无 PG 则报告 not run）。
- **风险与回滚**：矩阵在 PG 下首跑可能暴露方言相关失败（历史见 conftest.py:26-29 JSONB 补丁），失败用例单独修不阻塞 SQLite 批次；不新增重跑机制，沿用 test.yml:63 注释的『flaky 必须暴露』原则。回滚=revert pytest.ini 与 test.yml 两个文件。

---

## 四、实施批次与验收门

依赖汇总（完整版见三）：T-2←T-1；T-3/T-4/T-6←T-1；T-7←T-2+T-4+T-6；P1-2~P1-5←P1-1；P2A-2~5←P2A-1；P2A-6←P2A-2~5；P2B-2/3/5←P2B-1；P2B-4←P2B-1+3；P2B-6←P2B-1+3；P2B-7←P2B-1+6；P2B-8←P2B-2~7；P2C-2~5←P2C-1；P2C-6←P2C-2~5；P2C-7←P2C-1；P3-2~7←P3-1；P4-7←P4-3。

| 批次 | 内容（工作项） | 验收门（跑哪组测试算过） |
|---|---|---|
| 批次1 测试地基与安全判定收紧 | T-1、T-5、P1-1（含既有夹具迁移）、T-4 | 环境前提：先重建 apps/server/.venv（当前 bin/python 为断链，见文首「执行环境前提」）或以系统 python3 执行。门：`cd apps/server && python -m pytest tests/unit/test_factory_fixture.py tests/tenants/test_tenant_isolation.py tests/security/test_privilege_escalation.py tests/unit/test_permission_deps.py tests/unit/test_rule_set_permissions.py tests/unit/test_tenant_services.py tests/security/test_token_blacklist_all_roles.py -q` 全绿（T-4 提权红灯用例以 xfail(strict) 计；后四个文件验证 P1-1 夹具迁移，防批次2 全量门变红）；P1-1 新增判定/开关单测全绿；`grep -rn "if response.status_code" apps/server/tests` 复查仅剩 test_rule_sets_router_endpoints.py:513/:1295 两处 ==500 合法模式（T-5 已加固其余 4 处条件放行） |
| 批次2 第1期安全核心收口 + 测试基建主体 | T-2（先试点 stores/departments/doctors）、T-3、T-6、P1-2、P1-3、P1-4、P1-5、P1-6、P1-7、P1-8 | `cd apps/server && python -m pytest tests/security tests/tenants -q` 全绿；P1-2 合入后移除 T-4 的 xfail 标记并全绿（XPASS 提醒机制兑现）；T-2 三模块试点断言全绿；灰度开关默认值核对（三个 fail-close 开关均 False） |
| 批次3 第2期A 预约支付流 + CI 接入 | T-7、P2A-1、P2A-2、P2A-3、P2A-4、P2A-5、P2A-6 | `cd apps/server && python -m pytest tests/security/test_p2a_tenant_matrix.py tests/security tests/tenants -q` 全绿；CI 新步骤 `pytest tests/security tests/tenants -m multi_tenant -q` 通过；payments 回调一致性核对 SQL 已执行并留档（决策点 D15）；**上线前置（D4 已标【阻断批次3】）**：小程序端患者/公开调用租户头核实留档完成，且 PATIENT_ANCHOR_FAIL_CLOSE=False、PUBLIC_TENANT_REQUIRED_EXTRA_PATHS=空 上线，观察核实完成后再翻转——误伤时关对应开关/清配置即回滚，不需 revert 代码 |
| 批次4 第2期B 患者数据流 | P2B-1、P2B-2、P2B-3、P2B-4、P2B-5、P2B-6、P2B-7、P2B-8 | `cd apps/server && python -m pytest tests/security/test_patient_data_flow_tenant_isolation.py tests/security tests/tenants -q` 全绿；P2B-1 与 P2A-1 的锚点函数已收敛为单一实现（grep 确认无重复定义），且 400/403 按 R2 错误码裁决的受众分支语义、两处测试清单期望同时全绿；PATIENT_ANCHOR_FAIL_CLOSE 默认 False（P2B 收紧经开关灰度，见 P2B-1） |
| 批次5 第2期C 资源与消息 + 全模块矩阵转绿 | P2C-1、P2C-2、P2C-3、P2C-4、P2C-5、P2C-6、P2C-7（departments，修订新增） | `cd apps/server && python -m pytest tests/tenants/test_p2c_resource_message_anchor_matrix.py tests/tenants tests/security -q` 全绿；T-2 注册表 12 模块（含 departments，经 P2C-7）全启用且 `pytest tests/security tests/tenants -m multi_tenant -q` 全绿（第1、2期统一验收门；矩阵范围以 §1.3「本期不处置」清单为界，未处置模块不入矩阵） |
| 批次6 第3期 数据模型迁移 | P3-1、P3-2、P3-3、P3-4、P3-5、P3-6、P3-7（M1→M7 线性串联） | `cd apps/server && python -m pytest tests/integration/test_alembic_migration.py -q` 全绿；测试库 `alembic upgrade head` 与逐个 `downgrade -1` 往返成功；P3-2 的 admins/roles 冲突扫描 SQL 在预发库执行并留档；P3 各项服务层测试全绿；`python -m pytest tests/ -q` 全量回归不劣化（批次1前先跑一次记基线）。环境前提：alembic 与 integration 测试需 TEST_DATABASE_URL 指向 PG（`.github/workflows/test.yml` PG 批次已具备；本地无 PG 时该部分记 not run，以 CI 为准），且虚拟环境可用（见文首「执行环境前提」） |
| 批次7 第4期 生命周期闭环 | P4-1、P4-2、P4-3、P4-4、P4-5、P4-6、P4-7 | P4-1~P4-7 各项新增单测全绿；`cd apps/server && python -m pytest tests/security tests/tenants -q` 回归全绿；P4-7 purge 任务 dry_run 输出清单经人工核对无误且 TENANT_PURGE_ENABLED=False |
| 批次8 收尾：死代码处置与全量验收 | P4-8 | data_scopes/role_permissions 在所有环境行数=0 的核实记录落档；notification 死分支删除后通知链路回归通过；`python -m pytest tests/ -q` 全量 + `pytest tests/security tests/tenants -m multi_tenant -q`（SQLite 与 PG 双跑）全绿（同批次6：需 TEST_DATABASE_URL 指向 PG、虚拟环境可用，本地缺失部分记 not run 以 CI 为准）；第五节标注「阻断」的决策点全部已拍板 |

批次间顺序约束：批次1→8 串行交付（批次 3/4/5 内部各工作项可并行）；三个批次均触碰 `app/common/tenant_deps.py`/`app/common/deps.py`，合入顺序必须与批次顺序一致以避免冲突。

---

## 五、决策点清单

> 标注【阻断】的决策点会阻塞对应工作项实施；其余可在对应批次内拍板。每条给出建议选项。

| # | 决策点 | 影响工作项 | 建议选项 |
|---|---|---|---|
| D1 | 遗留 User 表 fallback：现网是否仍存在仅存在于 User 表、需走该 fallback 的管理员账号？【阻断 P1-1 开关默认值】 | P1-1 | 若能提供清单先迁移到 Admin 表；无法确认时按「开关默认 True 观察日志→确认无命中后翻 False」灰度执行 |
| D2 | 全部灰度开关的翻转排期：LEGACY_USER_ADMIN_FALLBACK / TENANT_FILTER_FAIL_CLOSE / TENANT_CONSISTENCY_FAIL_CLOSE，修订新增 TENANT_CODE_TO_ID_RESOLVE（P1-4 中间件回填独立开关）、PATIENT_ANCHOR_FAIL_CLOSE（患者/公开端锚点 fail-close）、PUBLIC_TENANT_REQUIRED_EXTRA_PATHS（公开强制路径配置项），及 /ws/poll 客户端携带医生 token 的改造排期 | P1-3、P1-4、P1-7、P2A-1、P2B-1、P2C-2 | 除 LEGACY_USER_ADMIN_FALLBACK 初值随 D1 拍板（建议 True 上线、观察后翻 False，见 D1）外，其余开关/配置默认 False/空 上线，观察 1-2 个发布周期后翻转；/ws/poll 分两步（先 admin 兜底租户校验，后强制医生 token）；批次3-5 各开关/配置独立可回滚（R1） |
| D3 | 平台管理员访问租户级列表（预约/候补/退款/排班/医生/门店/患者）：沿用 get_tenant_filter 全平台视图，还是像 audit_logs 那样强制显式传 tenant_id（不传 400）？后者更严但可能影响平台运营总览页 | P2A-2~5、P2B-2、P2C-2~5 | 三期必须统一（当前 P2A 默认全平台视图、P2B/P2C 建议显式传参）；建议统一为「显式传 tenant_id 否则 400」的 audit_logs 语义，运营总览如需跨租户汇总另立 require_platform_admin 专门端点 |
| D4 | 患者端读取接口（appointments 列表/详情、waitlist /my 与详情）无 X-Tenant-ID 头时：400 拒绝还是返回空集？【阻断批次3——核实留档未完成前不得翻转 PATIENT_ANCHOR_FAIL_CLOSE / PUBLIC_TENANT_REQUIRED_EXTRA_PATHS】 | P2A-2、P2A-3、P2C-2 | 默认 400（对齐 require_tenant_context）；小程序端所有调用均已带租户头的核实留档为批次3 上线前置；核实期间开关默认 False 保持现网行为 |
| D5 | 医生登录跨租户产品语义：get_by_phone/get_by_username 的 strict_tenant 默认翻转 True（手机号+租户定位，多租户命中 400 引导），还是「跨租户统一医生账号」（需另行设计映射流程）？【阻断 P2C-3②】 | P2C-3 | 建议翻转 strict_tenant=True（当前唯一调用方 authenticate 已显式传 True，翻转零现网影响，仅消除未来危险默认） |
| D6 | 消息模板「租户模板覆盖全局模板（tenant_id IS NULL）」的管理端模板列表/CRUD 是否纳入锚点改造？ | P2C-5 | 建议本期保留全局回退语义、暂不改造，仅改 get_all_messages |
| D7 | 平台管理员跨租户查看患者/病历数据的合规场景是否存在？ | P2B-1、P2B-2 | 按 audit_logs 语义：平台管理员必须显式指定 tenant_id（否则 400）；如需跨租户汇总能力另立带 require_platform_admin 守卫的专门端点 |
| D8 | 随访任务/记录的患者端自助写操作（complete_task/skip_task、create_record）是否存在真实业务场景？ | P2B-7 | 默认按「owner 内允许」实施；产品确认患者端只读则收紧为一律 403（单点改动） |
| D9 | 四模块（患者/病历/报告/随访）及排班/医生/门店/消息的 tenant_id 列均为 nullable，存量 NULL 行在锚点过滤后将永久不可见——是否另立数据回填任务（按关联 appointment/租户推导）？ | P2B-2~7、P2C-2~5 | 建议实施前跑只读 SQL 统计各表 NULL 行占比，占比显著时另立数据订正任务；本期默认只读不改数据，仅在风险中标注 |
| D10 | content 三表 store_id 为 NULL 的存量「全局内容」行归属：保留 tenant_id=NULL 视为平台级，还是绑定指定运营租户？ | P3-1 | 建议保留 NULL=平台级（行为不变，与现有 store_id IS NULL=全局展示语义一致） |
| D11 | admins.username 改租户内唯一后，双租户同名管理员在无租户头登录时：返回 400 要求附带 X-Tenant-Code，还是自动取唯一命中/最早账号？ | P3-2 | 建议 400 + 附带 X-Tenant-Code 引导（P3-2 已按此设计；P1-4 中间件已支持 code→id 解析，体验闭环） |
| D12 | shift_types 存量 code 全部 tenant_id=NULL：不回填保持平台级共享，还是按 rule_sets 关联推导回填到具体租户？ | P3-4 | 建议不回填、保持平台级共享（与现状行为一致，仅新数据开始区分） |
| D13 | M2 冲突扫描若在生产库发现跨租户重复 username/code 存量行，改名原则：加租户前缀还是人工逐个处理？【阻断批次6 M2 执行】 | P3-2 | 需业务拍板；建议「先人工核对清单、优先人工改名」，不做自动前缀（避免破坏外部系统对账号名的引用） |
| D14 | rule_set_audit_logs 与 schedule_audit_logs 的 tenant_id 当前 NOT NULL，P3-6 放宽为 nullable 以允许历史孤儿审计行置 NULL，是否接受？ | P3-6 | 建议接受（审计行缺租户属可接受的降级，NOT VALID FK 仍保护新写入） |
| D15 | payments 回调锚点从请求头租户切换为已验签 profile.tenant_id 前的一致性核对（Appointment.tenant_id vs PaymentProfile.tenant_id 不一致的历史数据会导致回调拒收） | P2A-4 | 建议上线前必跑一致性核对 SQL 并留档；拒收时微信会重试，可在日志观测；如发现不一致先修数据再上线 |
| D16 | 平台管理员开通租户时是否需要同时创建默认管理员账号（TenantCreate 增加初始管理员+初始密码字段，还是维持现状由管理员 CRUD 单独创建）？ | P4-3 | 建议 P4-3 仅修原子性、维持现状（管理账号由管理员 CRUD 单独创建）；如需同步建号另立 schema 变更 |
| D17 | 订阅 auto_renew 无真实扣款通道，自动续费语义确认为「到期自动延长周期 + 生成 pending 应收账单 + 宽限期内不停服」？ | P4-5 | 建议确认该语义后落地；如商务需要真实扣款通道则超出本期范围 |
| D18 | 存储配额计量来源：TenantUsageLog.storage_used_mb 目前无写入方，先补每日存储统计任务再启用 storage 检查，还是对象存储实时聚合？ | P4-6 | 建议前者（每日统计任务），storage 检查在计量任务上线前保持「无数据放行」 |
| D19 | 低代码页面配额双轨（feature_gate.lowcode_max_pages 与计划 max_lowcode_pages）保留哪个作为单一事实来源？ | P4-6 | 本期按「两道限制取更严者」实施；单轨化需产品决策后另立任务 |
| D20 | DataScope 与 role_permissions 的「删除」选项需确认所有环境（含生产）两表行数为 0；miniapp 配额计数是否包含已停用实例（status=2）？【阻断批次8 drop】 | P4-6、P4-8 | drop 前以只读 SQL 逐环境核实并留档；miniapp 计数建议仅统计启用实例（status≠2），待产品确认 |
| D21 | T-4/T-6 的 xfail(strict) 红灯用例先行合入，还是「代码先合、测试后跟」？ | T-4、T-6 | 建议 xfail 先行（红灯护栏防遗忘）；若倾向代码先合则改普通 skip 待修复后启用 |
| D22 | 自助注册无租户上下文（auth/router.py:224 tenant_id=None，密码策略退化默认且用户租户归属未定）的期望行为 | T-6(c)、P4-2 | 建议 fail-close 拒绝（400 需指定租户上下文），T-6(c) 按此以 xfail 预置 |
| D23 | 12 模块隔离矩阵的模块清单确认 | T-2 | 建议核心管理端 12 模块（stores/departments/doctors/schedules/appointments/patients/admin-roles/tenants/audit-logs/contacts/payments/statistics）；注：清单并非全部来自 api/v1/__init__.py:22-33（实测该区间无 audit-logs，其注册于 :101，contacts 于 :91-94、payments 于 :109），各模块挂载路径实施时逐个核对 |
| D24 | 既有 conftest.py:586-605 的 test_super_admin 实为带 tenant_id 的全量权限角色，命名与平台管理员语义不符：是否顺带重命名？ | T-1 | 建议新增独立平台管理员夹具、不改名旧夹具以免波及存量测试 |

---

## 六、风险登记簿

| # | 风险 | 涉及工作项 | 缓解/应对 |
|---|---|---|---|
| R1 | fail-close 上线对现网前端兼容：无头管理端请求从「看全量」变 403/400；只带 X-Tenant-Code 的请求在一致性校验开启后被拒；患者端无头调用与公开端强制路径被 400/400（修订落实：后两者不再无条件生效） | P1-3、P1-4、P2A/B/C 全部患者端/公开端收紧 | 各开关「上线即旧行为、翻转才收紧、翻回即回滚」：LEGACY_USER_ADMIN_FALLBACK 初值随 D1 拍板（建议 True=保留旧行为，观察日志后翻 False 收紧），TENANT_FILTER_FAIL_CLOSE / TENANT_CONSISTENCY_FAIL_CLOSE / TENANT_CODE_TO_ID_RESOLVE / PATIENT_ANCHOR_FAIL_CLOSE 默认 False，公开路径增补走 PUBLIC_TENANT_REQUIRED_EXTRA_PATHS（默认空）；批次3-5 的患者端/公开端收紧同样受开关与配置控制，翻 True 后误伤只需关开关/清配置回滚，不需 revert 代码——『关开关即回滚』对全部批次成立；上线前核实小程序/管理端所有调用均携带租户头（D4 已标【阻断批次3】，核实留档为批次3 门前置） |
| R2 | 三个批次各自新增同名锚点函数（P2A-1 resolve_actor_tenant_anchor、P2B-1 resolve_admin_tenant_anchor + resolve_actor_tenant_anchor、P2C-1 resolve_admin_tenant_anchor 依赖工厂）签名不一致 → 重复实现与合并冲突；且同函数无租户锚点的错误码曾在 P2A-1（患者型 400）与 P2B-1（管理员型 403）两处规格分歧 | P2A-1、P2B-1、P2C-1 | 批次 3/4/5 串行交付；P2A-1 先落地为基，P2B-1/P2C-1 以「纯函数 + 薄 Depends 包装」扩展而非重复定义；**错误码裁决（次轮修订）：单一实现内按受众分派语义分支——管理员型输入 403「未关联租户」、患者/医生型输入开关开启后 400「缺少租户上下文」，裁决正文见 P2A-1 合并约束，两处测试清单期望据此同时成立**；批次4验收门含 grep 无重复定义与 400/403 分支语义一致检查 |
| R3 | admins.username / roles.code 改复合唯一的迁移顺序：生产库冲突扫描→改名→约束切换→登录引导，任一步顺序错误导致迁移中止或登录 500 | P3-2（与 P1-4 的先后关系） | M2 内置冲突扫描 RAISE 中止机制（不写坏数据）；P1-4 先行上线使 X-Tenant-Code 一致性校验与 code→id 解析真正生效，再做 P3-2 的登录兼容；改名原则先拍板（D13） |
| R4 | settings 表租户拆分与微信/短信配置改造的先后：P3-7 只加预留列，若第4期前后有人按租户读配置而无三级解析，将读到 NULL 平台配置或行为漂移 | P3-7、P4（后续租户级配置立项） | P3-7 读写逻辑零改动（已核实 service_core.py:14-210 无 tenant 条件），租户覆盖→门店覆盖→平台默认三级解析作为独立后续任务；迁移文件 docstring 标注第4期依赖；微信回调 fail-close 行为不受影响 |
| R5 | 存量 tenant_id NULL 行在锚点过滤后永久不可见（患者/病历/报告/随访/排班/医生/门店/消息等多表均 nullable） | P2B-2~7、P2C-2~5、P3-1 | 各表实施前跑只读 SQL 统计 NULL 占比；显著时另立数据订正任务（按关联 appointment/租户推导回填）；本期只读不改数据（D9） |
| R6 | 回调与异步任务锚点切换的数据前提：payments 回调改锚 profile.tenant_id 后，appointment 与 profile 租户不一致的存量单将被拒收；blacklist_task 历史记录 tenant_id 为 NULL 时不再通知 | P1-8、P2A-4 | 上线前必跑一致性核对 SQL（D15）与 Blacklist NULL 占比统计；一次性回填脚本独立提交便于回滚；拒收有微信重试兜底，日志可观测 |
| R7 | service 签名变更的跨模块波及：appointments get_list、payments create_payment_order、CMS 写方法、follow_up 服务构造（medical_records/service.py:89）、waitlist cancel_waitlist 等 | P1-6、P2A-2~5、P2B-3/5/6 | 每项实施时全量 grep 调用点（含跨模块与单测直接调用），service 与 router 同一提交内闭环；payments create_payment_order 以 keyword-only 参数 + 默认回退上下文做过渡兼容 |
| R8 | 测试夹具与判定收紧的一致性：P1-1 收紧 is_super_admin 判定后，存量 test_super_admin_role 夹具（code=SUPER_ADMIN + tenant_id=test_tenant.id，conftest.py:543-560 实读）不再是超管，super_admin_token 与 test_super_admin 的消费面（tests/unit/test_rule_set_permissions.py、test_tenant_services.py:340/:449、tests/security/test_token_blacklist_all_roles.py:36、integration 三个 endpoint 测试等 ≥5 文件）语义漂移；T-4/T-6 xfail(strict) 在修复合入时 XPASS 报错 | T-1、T-4、T-6、P1-1、P1-2 | 夹具迁移**归属 P1-1 改动点④** 并在批次1 完成（批次1 门含全部受影响文件回归，批次2 全量门不再因此变红）；T-1 平台管理员夹具显式满足新判定（SUPER_ADMIN 码 + tenant_id=None + role.tenant_id=NULL）；xfail 用例 docstring 标注对应修复项编号（P1-2/D22），合入当批移除标记并转正；负向用例防止错误夹具配置再现 |
| R9 | 迁移不可逆点：P3-2/3/4 的 downgrade 恢复全局唯一在已产生跨租户同名后失败；P3-5 清洗重复行、P3-1 回填均为数据变更；P4-7 物理删除租户不可逆 | P3-1/2/3/4/5、P4-7 | 所有数据变更迁移前 pg_dump 对应表备份；downgrade 注释写明恢复前置条件；P4-7 双保险开关（ENABLED 默认 False + DRY_RUN 默认 True），先 dry_run 试点、确认备份策略后启用 |
| R10 | 死代码删除的破坏面：data_scopes/role_permissions drop 不可逆；notification_task 死分支删除触及通知链路；online_payment 开关试点若存量租户 features 为空会立即切断支付 | P4-8 | drop 前逐环境行数=0 核实留档（D20）；试点开关先给存量租户/计划补 features 数据或临时默认 True；死分支删除与统一消息收尾协调、独立 commit |
| R11 | WS /ws/poll 收紧对降级客户端的影响：匿名轮询客户端（若有）将从 200 变 401/403 | P1-7 | 两步灰度：先只上 admin 兜底租户校验（对合法医生客户端零影响），观察告警后再强制医生 token；前端同步改为携带医生 token（D2） |
| R12 | 并行合入冲突与迁移串联：多批改 tenant_deps.py/deps.py/pytest.ini 等公共文件；M1-M7 必须 down_revision 线性串联；partial index/on_conflict 仅 PG 可用，SQLite 测试库与 PG 方言差异 | 全部批次、P3 全部 | 批次串行合入、批内可并行；M1→M7 严格顺序，每迁移独立可 downgrade；矩阵在 PG integration 批次加跑一遍（T-7），方言失败单独修不阻塞 SQLite 批次 |
| R13 | 迁移部分成功静默提交与 preserve_ids 撞键：migrate_data 现吞异常部分提交，preserve_ids=True 可撞目标租户主键 | P4-4 | 改全有或全无事务 + 写入前分批 in 查询预检；接口 400 带实体名；track_migration 审计留痕；行为变更知会运营 |
| R14 | 发布顺序耦合：T-4 xfail 在 P1-2 合入时转 XPASS 属预期；CI multi_tenant 步骤启用过早会因未修复模块长期红 | T-4、T-7、批次2/3 | 批次2移除标记转正；T-2 矩阵条目按模块修复进度逐步启用（未修复模块 skip/xfail），批次5全量转绿后才作为固定验收门 |
| R15 | 本期不处置的 fail-open 遗留面：departments 之外另有 30+ 模块仍为 `get_current_tenant_id() + if` 模式（§1.3 清单，含 freelance_fees(22)、rule_sets(13)、approval_flows(13) 等），多租户隔离在这些模块不成立 | §1.3 清单所列模块（本期不处置） | 显式标注「本期不处置」并作为 T-2 矩阵范围边界（未处置模块不入矩阵，批次5 门以此解释）；后续立项按批次5 同法逐模块锚点化；过渡期对跨租户数据访问日志保持监控 |

---

## 附：工作项总览（51 项）

- 第1期安全核心：P1-1 ~ P1-8（8 项）
- 第2期A 预约支付流：P2A-1 ~ P2A-6（6 项）
- 第2期B 患者数据流：P2B-1 ~ P2B-8（8 项）
- 第2期C 资源与消息：P2C-1 ~ P2C-7（7 项，P2C-7 为修订新增）
- 第3期数据模型：P3-1 ~ P3-7（7 项）
- 第4期生命周期：P4-1 ~ P4-8（8 项）
- 测试基建：T-1 ~ T-7（7 项）
