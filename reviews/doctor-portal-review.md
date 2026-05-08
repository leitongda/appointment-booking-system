# 医生端功能完整性 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-08
> 审查目标：医生端（apps/doctor/）功能完整性，识别功能缺口和补充项

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 综合功能评审，无明确需要深入的单一领域，集中调度可快速收敛且输出完整度最高。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品定位

**产品定位：**
- 自述为"一套完整的医院挂号系统解决方案，包含机构端、患者端（H5 + 小程序）、医生端三个平台"（README.md:3）
- 医生端标题"医生工作台"/"医生工作站"（app.tsx:301）

**功能完成度：**

| # | 功能 | 状态 |
|---|------|------|
| 1 | 登录（手机号/用户名+密码） | 已实现 |
| 2 | 工作台（今日统计、当前患者、等待队列、待签到） | 已实现 |
| 3 | 我的排班（月历视图、停诊申请） | 已实现 |
| 4 | 停诊调班（申请、状态追踪） | 已实现 |
| 5 | 今日预约（列表、叫号、完成、过号） | 已实现 |
| 6 | 历史预约（搜索表格） | **空壳/stub** — request 硬编码返回空数组，无 API 调用 |
| 7 | 就诊管理（叫号、患者历史、复诊预约） | 已实现 |
| 8 | 病历列表 | 已实现 |
| 9 | 填写病历 | 已实现（仅创建，无编辑） |
| 10 | 数据统计 | 已实现（仅 2 维度，后端有更多） |
| 11 | 预约规则（只读） | 已实现 |
| 12 | 消息中心 | 已实现 |
| 13 | 通知设置 | 已实现 |

**重点检查结果：**
- 个人资料编辑：不存在（router_profile.py 已创建但未注册到 router）
- 排班偏好设置：不存在
- 病历模板：不存在
- 患者评价查看：不存在
- 处方管理：部分（文本字段，无结构化）
- 扫码签到：不存在（患者端有，医生端无）
- 转诊功能：不存在
- 统计维度：仅 2 个（趋势+状态分布），后端有 6+ 维度未使用

**竞品功能对比：**
- 竞品常见但本项目缺失：病历编辑/删除、病历模板、个人资料编辑、在线问诊、患者评价、电子处方（结构化）、转诊、语音录入、患者随访、收入统计
- 竞品部分有但本项目缺失：多科室排班、扫码签到（医生端）

**目标用户线索：**
- Ant Design Pro Components，企业级中后台，中文界面
- API 文档：手动维护 + FastAPI 自动生成 Swagger
- 多租户 + RBAC 权限系统
- Docker Compose + 宝塔混合部署

### Designer — 用户视角

**页面清单与结构：**
- 13 路由，1 页是空壳（history），1 个未定义路由（/medical-record/view）
- 总手写代码约 3,797 行
- 就诊管理页最复杂（551 行）

**交互模式统计：**
- 6 Modal.confirm + 4 Popconfirm
- 0 alert() 调用
- 52 loading 相关模式，全部 toast 错误处理，0 error boundary / retry
- 8 个显式空状态（Dashboard/Consultation/Message/Rules/Statistics）

**响应式设计事实：**
- 0 自定义 @media 查询
- viewport 禁止缩放（user-scalable=no）
- 今日预约页 4 统计卡固定 span={6}，无响应式断点
- 多个 Modal/Drawer 宽度超过手机视口（480px/700px）
- 通知设置页用 Tailwind CSS，其他页用 Ant Design grid（不一致）

**无障碍事实：**
- 19 个 aria-*/role 属性，全部集中在 message/index.tsx
- 其他 12 个页面 0 无障碍属性
- 2 个未关联的 <label>（schedule modal）

**组件一致性事实：**
- 100% 依赖 antd/pro-components，0 自定义组件
- 32+ 硬编码颜色值（inline style），0 CSS 变量
- 0 快捷键/热键

**输入方式事实：**
- 1 个键盘处理器（message 页 Enter/Space）
- 0 autoFocus / tabIndex / autoComplete

### Engineer — 技术视角

**存储层事实：**
- localStorage 存 3 个 key：hospital_token, hospital_refresh_token, doctor（JSON）
- leave-request 页用 localStorage.getItem('doctorId') — key 名不一致，该 key 不存在
- 核心表：doctors, appointments, medical_records, schedules, rest_days, notification_preferences
- 86 个 Alembic 迁移脚本

**核心引擎事实：**
- WebSocket：前端 25s 心跳，后端 30s 心跳，固定 3s 重连（无指数退避），最大 10 次
- 预约状态机：9 个状态，医生端涉及 5 条流转
- 队列管理：前端通过 getToday 全量获取后过滤，后端有独立队列端点但前端未用
- 重连失败后仅 console.error，无用户通知/自动刷新

**API/协议事实：**
- 医生端调用 37 个 API 端点
- doctor-portal 专属 5 个子路由（schedules, appointments, queue, patient, rules）
- router_profile.py 存在但未被 include
- 排班页调用通用 GET /schedules（管理端接口），未用 doctor-portal 排班端点
- 全局超时 30000ms

**安全机制事实：**
- JWT Bearer token，localStorage 存储
- get_current_doctor_by_token 验证 doctor type + tenant_id
- _verify_appointment_ownership 校验预约归属
- 手机号脱敏显示
- WebSocket token 通过 URL query 传递

**依赖和模块耦合事实：**
- @tanstack/react-query 和 zustand 声明但未使用
- 两套请求拦截器并存（initApiConfig + umi request config）

**其他技术发现：**
- 病历编辑 API 层已定义（update/delete），前端未接入
- 两套 401 拦截器可能导致重复弹窗
- WebSocket 断连后无 polling fallback

---

## Round 2：辩论层

### 交叉评论投票矩阵（简化版 — 集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 统计页/排班页调用 admin API | 裁决者验证：确认所有 statistics/schedules 端点均为 get_current_admin，医生 token 无法访问 | 🚨 关键：比"维度不足"更根本，页面实际不可用 | **采纳**：统计页和排班页在医生端不可用，需修复 |
| leave-request doctorId bug | 裁决者验证：确认 localStorage.getItem('doctorId') 返回 null，功能完全不可用 | 🚨 关键：停诊/调班全部不可用 | **采纳**：P0 bug，需立即修复 |
| 两套响应拦截器冲突 | 裁决者部分认同：ApiError 丢失 response 属性可能导致错误信息不准确 | 普通：错误类型被吞掉 | **部分采纳**：标记为 P2 技术债务 |
| 历史预约空壳优先级 | 裁决者认同：就诊管理的患者历史已覆盖核心场景 | 普通：独立历史列表的必要性存疑 | **部分采纳**：降为 P2，非核心缺口 |
| 竞品对比标准 | 裁决者认同：定位不同（SaaS vs 平台），对比标准需调整 | 普通：对比对象不对等 | **采纳**：修正竞品范围 |
| 项目优势被忽略 | 裁决者认同：就诊管理、邮箱管理、跨 Tab 同步等是亮点 | 普通：应纳入优势维护 | **采纳**：Round 3 纳入 |
| WebSocket 断连影响 | 裁决者部分认同：有手动降级方案，但自动恢复仍有改进空间 | 普通：影响被高估 | **部分采纳**：降为 P2 |

### 独到发现

1. **统计页和排班页使用 admin 端点** — 这不是"功能维度不足"，而是"功能完全不可用"。后端 doctor_portal 已有 `/statistics/today` 端点但前端未使用。
2. **leave-request localStorage key 错误** — `doctorId` vs `doctor` 的命名不一致导致整个停诊调班模块不可用。
3. **router_profile.py 未被注册** — 后端代码已写好但未 include，前端无个人资料编辑页面。
4. **病历编辑 API 存在但前端未接入** — API 层 update/delete 已定义，前端无入口。
5. **排班页调用通用端点而非 doctor-portal 端点** — 前端用 GET /schedules（admin），后端有 GET /doctor-portal/schedules。

### Critic 质询

[Critic -> 全体] 质询 1：统计页和排班页调用 admin API，医生 token 无法访问
  论据：所有 statistics/schedules 端点使用 get_current_admin 鉴权，医生 token type="doctor" 无法通过
  要求回应：Engineer
  级别：🚨 关键
  Team Lead 裁决：**确认属实**。统计页和排班页在医生端实际不可用，catch 块静默失败显示空状态。

[Critic -> 全体] 质询 2：leave-request doctorId 永远为空，功能完全不可用
  议据：localStorage.getItem('doctorId') 返回 null（key 应为 'doctor' + JSON.parse）
  要求回应：Engineer
  级别：🚨 关键
  Team Lead 裁决：**确认属实**。停诊申请、调班申请、取消、列表查看全部传入空 doctorId。

[Critic -> 全体] 质询 3：两套响应拦截器执行冲突
  论据：ApiError 无 response 属性，医生端拦截器误判为"网络错误"
  要求回应：Engineer
  级别：普通
  Team Lead 裁决：**部分认同**。存在但优先级低，标记为技术债务。

[Critic -> 全体] 质询 4：历史预约空壳是否真的必要
  论据：就诊管理的患者历史已覆盖核心场景，独立历史列表的使用频率存疑
  要求回应：PM
  级别：普通
  Team Lead 裁决：**认同**。降为 P2，优先级低于其他缺口。

[Critic -> 全体] 质询 5：竞品对比标准不公平
  议据：微医/好大夫是大型平台，与挂号 SaaS 定位不同
  要求回应：PM
  级别：普通
  Team Lead 裁决：**认同**。竞品应限定为同类型医院预约挂号 SaaS。

[Critic -> 全体] 质询 6：三方忽略了项目优势
  议据：就诊管理、邮箱管理、跨 Tab 同步、WebSocket 消息分发等是亮点
  要求回应：全体
  级别：普通
  Team Lead 裁决：**认同**。Round 3 纳入优势维护。

[Critic -> 全体] 质询 7：WebSocket 断连影响被高估
  议据：有手动降级方案（离线标签+刷新按钮），诊室场景网络稳定
  要求回应：Designer
  级别：普通
  Team Lead 裁决：**部分认同**。手动降级可接受，但重连失败后应有更明显的用户提示。

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | 统计页/排班页调用 admin API，医生端不可用 | Team Lead 确认：所有端点均为 get_current_admin | 是 | 纳入 P0 计划 |
| 2 | leave-request doctorId 为空，功能不可用 | Team Lead 确认：localStorage key 错误 | 是 | 纳入 P0 计划 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：leave-request doctorId bug**
   **结论：** `localStorage.getItem('doctorId')` 返回 null，应改为从 `localStorage.getItem('doctor')` 解析
   **建议行动：** 修复 leave-request/index.tsx 的 doctorId 获取逻辑，与其他页面保持一致
   **成本估算：** 0.5h
   **优先级：** P0（功能性 bug，整个模块不可用）

2. **议题：统计页和排班页使用 admin 端点**
   **结论：** 医生 token 无法访问 statistics 和 schedules 的 admin 端点，页面静默失败显示空状态
   **建议行动：** 方案 A（推荐）：前端统计页改用 doctor_portal 的 `/statistics/today` 端点 + 新增 doctor_portal 统计扩展端点；排班页改用 `/doctor-portal/schedules` 端点。方案 B：后端为 statistics/schedules 端点添加 doctor token 支持
   **成本估算：** 8-12h（方案 A）
   **优先级：** P0

3. **议题：历史预约页面空壳**
   **结论：** 后端 API 已实现（GET /doctor-portal/appointments），前端是硬编码空返回。就诊管理的患者历史已覆盖核心场景，独立历史列表优先级较低
   **建议行动：** 接入后端 API，实现搜索筛选功能
   **成本估算：** 4h
   **优先级：** P2

4. **议题：病历编辑功能缺失**
   **结论：** API 层 update/delete 已定义，前端无编辑入口。需评估是否允许医生编辑已提交的病历（合规性考虑）
   **建议行动：** 草稿状态的病历允许编辑，已提交的病历不允许（或需权限控制）
   **成本估算：** 6h
   **优先级：** P1

5. **议题：router_profile.py 未注册**
   **结论：** 后端 router_profile.py 存在但未被 include 到聚合路由，前端无个人资料编辑页面
   **建议行动：** 注册 profile 路由，新增 PUT /me 端点，前端新增个人资料编辑页
   **成本估算：** 8h（后端 2h + 前端 6h）
   **优先级：** P1

### ⚡ 分歧项

1. **议题：WebSocket 断连处理改进**
   **各方立场：**
   - PM：诊室场景有手动降级，优先级可降低
   - Designer：当前"离线"标签太小，应有更明显的 banner
   - Engineer：增加指数退避 + 重连失败后自动 polling 的成本不高
   **裁决/建议：** 增加重连失败后的 banner 提示（P2），暂不实现自动 polling
   **决策依据：** 手动降级可接受，但用户应更明显地感知断连状态

2. **议题：病历模板功能**
   **各方立场：**
   - PM：竞品有，但本项目定位为挂号 SaaS，非 HIS 系统
   - Designer：纯文本表单对医生来说填写效率低
   - Engineer：实现成本中等
   **裁决/建议：** 待定 — 需用户确认是否纳入产品范围
   **决策依据：** 取决于产品定位是"挂号工具"还是"诊所工作站"

---

## 被低估的优势

1. **就诊管理页** — 551 行的诊室核心工作流，包含叫号/过号/重呼/爽约/患者历史/复诊预约，是完整可用的功能
2. **邮箱管理** — 绑定/解绑/换绑 + 验证码流程，在 app.tsx 中隐藏实现，PRD 未提及但功能完整
3. **跨 Tab 状态同步** — 监听 storage 事件处理多标签页登录状态变更
4. **WebSocket 消息分发** — 14 种消息类型的完整分发机制，含心跳/重连/死连接清理
5. **安全设计** — 多租户隔离 + RBAC + 手机号脱敏 + 预约归属校验
6. **@hospital/api 重试拦截器** — 3 次重试 + 指数退避，网络健壮性设计

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 修复 leave-request doctorId bug | 0.5h | 高（整个停诊调班模块恢复可用） | Engineer | 待执行 |
| P0 | 统计页改用 doctor_portal 端点 | 8-12h | 高（统计页从不可用变为可用） | Engineer | 待执行 |
| P0 | 排班页改用 doctor-portal/schedules 端点 | 2h | 高（排班页从不可用变为可用） | Engineer | 待执行 |
| P1 | 注册 router_profile + 新增 PUT /me + 前端个人资料编辑页 | 8h | 中（医生可管理自己的基本资料） | PM+Engineer | 待执行 |
| P1 | 病历编辑功能（草稿可编辑） | 6h | 中（完善病历管理工作流） | Engineer | 待执行 |
| P2 | 历史预约页接入后端 API | 4h | 低（就诊管理已覆盖核心场景） | Engineer | 待执行 |
| P2 | WebSocket 断连 banner 提示 | 2h | 低（手动降级已可用） | Engineer | 待执行 |
| P2 | 请求拦截器去重 | 2h | 低（错误信息准确性） | Engineer | 待执行 |
| 待定 | 病历模板功能 | 待估 | 待定 | PM+Engineer | 需用户确认 |
| 待定 | 通知设置页 Tailwind 改为 Ant Design grid | 2h | 低（样式一致性） | Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **修复 leave-request doctorId bug** — `leave-request/index.tsx:15` 改为从 `localStorage.getItem('doctor')` 解析，0.5h
2. **排班页改用 doctor-portal 端点** — `schedule/index.tsx:30` 改为调用 `GET /doctor-portal/schedules`，2h
3. **统计页改用 doctor_portal 端点** — 需新增 doctor_portal 统计扩展端点 + 前端对接，8-12h

### P1：本轮迭代（高价值、中等成本）

1. **注册 router_profile + 个人资料编辑** — 后端注册路由 + 新增 PUT /me + 前端编辑页，8h
2. **病历编辑功能** — 草稿状态允许编辑，已提交不允许，6h

### P2：下个周期规划（中等价值、较高成本）

1. **历史预约页接入 API** — 4h
2. **WebSocket 断连 banner** — 2h
3. **请求拦截器去重** — 2h

### 待定：需用户确认

1. **病历模板功能** — 取决于产品定位（挂号工具 vs 诊所工作站）
2. **通知设置页样式统一** — Tailwind → Ant Design grid

---

## 摘要

**使用模式：** 集中调度

**关键共识：** 5 项达成共识
- leave-request bug 修复（P0）
- 统计/排班页端点修复（P0）
- 历史预约接入（P2）
- 病历编辑（P1）
- 个人资料编辑（P1）

**关键分歧：** 2 项需要决策者介入
- WebSocket 断连处理改进程度
- 病历模板是否纳入产品范围

**Top 3 P0 行动：**
1. 修复 leave-request doctorId bug（0.5h）
2. 排班页改用 doctor-portal/schedules 端点（2h）
3. 统计页改用 doctor_portal 端点（8-12h）

**Critic 关键洞察：**
- 统计页和排班页不是"维度不足"，而是"完全不可用"（admin 鉴权导致医生 token 被拒绝）
- leave-request 的 localStorage key 错误导致整个停诊调班模块不可用
- 竞品对比标准需修正（挂号 SaaS vs 互联网医疗平台）
