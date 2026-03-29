# 医生/科室/门店管理功能 -- 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-03-29
> 审查目标：医生/科室/门店管理功能的逻辑流程、页面布局、文字描述、操作合理性

---

## Phase 0：模式选择

选定 **集中调度模式**。理由：三个模块属于同一业务域（医疗机构基础数据），边界清晰，适合 Team Lead 统一收集事实后集中裁决。

---

## Phase 1：Round 1 -- 事实收集

### 1.1 PM Agent 事实清单（产品视角）

#### 医生管理模块

**前端页面清单：**
- `doctor/list.tsx` -- 医生列表页（614行），功能包括：表格展示、搜索筛选（门店/科室/姓名/状态）、推荐开关、推荐排序弹窗（DnD 拖拽）、诊费设置弹窗、导入导出、操作（编辑/删除/详情/诊费设置）
- `doctor/form.tsx` -- 医生表单页（500行），包含 5 个 Card：基础信息、资质信息、坐诊设置、展示设置、其他设置
- `doctor/detail.tsx` -- 医生详情页（135行），Tabs 结构：基本信息、排班管理（ScheduleCalendar）、预约记录（ProTable + 统计卡片）
- `doctor/booking-setting.tsx` -- 预约设置列表页（130行）
- `doctor/booking-setting-form.tsx` -- 预约设置表单页（250行）
- `doctor/consultation-fee-modal.tsx` -- 诊费管理弹窗（423行），支持按门店+科室分组配置诊费，支持全局模板一键带入
- `doctor/components/DoctorScheduleTab.tsx` -- 排班管理 Tab（188行），含日历视图和"从模板生成"功能
- `doctor/components/DoctorAppointmentTab.tsx` -- 预约记录 Tab（246行），含统计卡片 + 预约列表

**后端 API 端点（`doctors/router.py`）：**
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| POST | /login | 无 | 医生登录 |
| GET | /me | doctor token | 获取当前医生信息 |
| GET | / | admin | 医生列表（分页） |
| GET | /all | admin | 所有医生 |
| GET | /recommended | 无 | 推荐医生（公开） |
| GET | /by-department/{id} | 无 | 科室医生（公开） |
| GET | /public/{id} | 无 | 医生详情（公开） |
| GET | /{id} | admin | 医生详情（管理端） |
| POST | / | admin+permission | 创建医生 |
| PUT | /{id} | admin+permission | 更新医生 |
| DELETE | /{id} | admin+permission | 删除医生 |
| PUT | /batch-sort | admin+permission | 批量排序 |
| POST | /check-username | admin | 检查账号唯一性 |
| POST | /generate-username | admin | 生成唯一账号 |

**前后端接口对应情况：**
- `doctorApi.getList` -> `GET /doctors` -- 正常
- `doctorApi.getDetailAdmin` -> `GET /doctors/{id}` -- 正常
- `doctorApi.create` -> `POST /doctors` -- 正常，前端手动 toSnakeCaseKeys 转换
- `doctorApi.update` -> `PUT /doctors/{id}` -- 正常，前端手动 toSnakeCaseKeys 转换
- `doctorApi.getRecommended` -> `GET /doctors/recommended` -- 正常
- `doctorApi.batchUpdateSort` -> `PUT /doctors/batch-sort` -- 正常
- `doctorApi.getByStore` -> `GET /doctors` (store_id 参数) -- 正常
- `doctorApi.checkUsername` -> `POST /doctors/check-username` -- 正常
- `doctorApi.generateUsername` -> `POST /doctors/generate-username` -- 正常

**业务逻辑流程：**
1. 医生列表 -> 新增/编辑 -> 表单提交 -> 跳转列表
2. 医生列表 -> 详情 -> Tab 切换（基本信息/排班/预约记录）
3. 医生列表 -> 诊费设置 -> 弹窗配置 -> 保存
4. 医生列表 -> 推荐排序 -> DnD 弹窗 -> 保存排序
5. 预约设置列表 -> 新增/编辑 -> 表单提交 -> 跳转列表

**文字描述/文案问题：**
- 列表页 `headerTitle` 为"医生列表"
- 表单页标题动态："编辑医生"/"新增医生"
- 详情页标题动态："{name} - 医生详情"
- 预约设置列表 `headerTitle` 为"医生预约设置"
- 预约设置表单标题动态："编辑医生预约设置"/"添加医生预约管理" -- **不一致**：列表叫"医生预约设置"，创建按钮叫"添加医生预约管理"
- 预约设置列表搜索字段 `bookingStartOffset` 的 render 中 `offset === 1` 显示"第2天"但 tooltip 说是"n+1天"，语义不够直观

#### 科室管理模块

**前端页面清单：**
- `department/index.tsx` -- 科室列表页（593行），功能包括：拖拽排序、门店筛选、推荐/热门/状态开关、医生绑定弹窗、导入导出
- `department/form.tsx` -- 科室表单页（375行），包含 5 个 Card：基础信息、图片设置、详情内容、联系信息、开关设置

**后端 API 端点（`departments/router.py`）：**
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | / | admin | 科室列表（分页） |
| GET | /tree | 无 | 科室树（公开） |
| GET | /hot | 无 | 热门科室（公开） |
| GET | /all | admin | 所有启用科室 |
| PUT | /batch-sort | admin+permission | 批量排序 |
| GET | /{id} | admin | 科室详情 |
| POST | / | admin+permission | 创建科室 |
| PUT | /{id} | admin+permission | 更新科室 |
| DELETE | /{id} | admin+permission | 删除科室 |
| GET | /{id}/doctors | admin | 科室已绑定医生 |
| GET | /{id}/available-doctors | admin | 可绑定医生 |
| PUT | /{id}/doctors/batch | admin+permission | 批量绑定医生 |

**前后端接口对应：** 全部正常

**文字描述/文案问题：**
- 列表页门店筛选列标题是"门店筛选"（hideInTable:true），但在搜索栏中显示 -- 合理
- 操作列的"更多"菜单中"设为推荐/取消推荐"与列表中 Switch 推荐列功能重复 -- 功能冗余但不严重
- 科室列表第457行有 `console.log("🚀 ~ dataApi:", dataApi , dataApi.getExportDepartmentsUrl())` -- **遗留调试日志**

#### 门店管理模块

**前端页面清单：**
- `store/index.tsx` -- 门店列表页（515行），功能包括：门店 CRUD、科室绑定弹窗（Tree）、用户分配弹窗（Transfer）、签到二维码弹窗、导入导出、启用/禁用
- `store/form.tsx` -- 门店表单页（383行），包含 5 个 Card：基础信息、地址信息、展示设置、营业设置、就诊卡配置、其他信息
- `store/visit-type-config.tsx` -- 复诊规则配置页（201行）
- `store/fee-templates.tsx` -- 诊费模板配置页（258行）
- `store/fee-types.tsx` -- 诊费类型管理页（267行）

**后端 API 端点（`stores/router.py`）：**
| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /by-code/{code} | 无 | 编码获取门店（公开） |
| GET | /check-unique | admin | 名称/编码唯一性检查 |
| GET | / | admin | 门店列表 |
| GET | /all | admin | 所有营业中门店 |
| GET | /{id} | admin | 门店详情 |
| POST | / | super_admin | 创建门店 |
| PUT | /{id} | admin+permission | 更新门店 |
| DELETE | /{id} | super_admin | 删除门店 |
| PATCH | /{id}/status | admin | 状态更新 |
| GET | /{id}/departments | admin | 门店科室列表 |
| PUT | /{id}/departments/batch | admin | 批量绑定科室 |
| GET | /{id}/admins | super_admin | 门店管理员列表 |
| PUT | /{id}/admins/batch | super_admin | 批量绑定管理员 |
| GET | /{id}/wechat-config | admin | 微信配置 |
| PUT | /{id}/wechat-config | admin | 更新微信配置 |
| GET | /{id}/checkin-qrcode | admin | 签到二维码 |

**文字描述/文案问题：**
- 门店列表 `headerTitle` 为"门店列表"
- 操作列"签到"按钮图标为 `QrcodeOutlined`，标签为"签到" -- 清晰
- 门店表单中风格选项使用了 emoji 前缀 -- 对于管理端 UI 略显不正式

### 1.2 Designer Agent 事实清单（用户视角）

#### 页面结构与布局

**医生列表页：**
- 布局：PageContainer > ProTable，标准管理列表模式
- 搜索栏：门店（下拉，单门店隐藏）/ 科室（下拉）/ 姓名（文本）/ 状态（下拉）
- 表格列：头像 | 所属门店 | 所属科室 | 医生姓名 | 性别 | 职称 | 标签 | 号源状态 | 推荐（Switch） | 状态 | 操作
- 操作栏：导入导出组件 | 推荐排序按钮 | 新增医生按钮
- 操作列：编辑 | 删除 | 更多（详情、诊费设置）
- 弹窗：推荐医生排序弹窗（Modal + DnD）、诊费设置弹窗（Modal 800px 宽）
- scroll={{ x: 1200 }} -- 12列含操作列，基本合理

**医生表单页：**
- 布局：FormPage > 5 个 Card
- Card 1 基础信息：姓名 + 性别 + 门店（单行）| 账号（带唯一性验证和建议）| 密码（仅新增）| 头像上传 | Banner 上传 | 科室 + 职称 + 医龄 | 手机号
- Card 2 资质信息：学历 + 毕业院校 | 执业证书编号 | 执业证书图片 | 所获荣誉
- Card 3 坐诊设置：坐诊时间说明 | 每日最大接诊量 | 在线问诊开关 + 费用
- Card 4 展示设置：页面风格（3选1）| 宣传视频 | 标签 | 擅长 | 医生介绍（富文本）
- Card 5 其他设置：排序 | 推荐开关 | 启用开关
- 使用基础设施：FormPage、ImageUploadCard、SwitchGroup、PasswordField

**医生详情页：**
- 布局：PageContainer > Tabs（基本信息 | 排班管理 | 预约记录）
- Tab URL 参数同步：`?tab=basic|schedule|appointment`
- 基本信息Tab：Avatar + 姓名 + 职称 + Tags + ProDescriptions（科室/手机/排序/专长/简介/时间）
- 排班管理Tab：Card > Alert + ScheduleCalendar + ScheduleEditModal + 从模板生成弹窗
- 预约记录Tab：统计卡片（4个 StatisticCard）+ ProTable

**科室列表页：**
- 布局：PageContainer > DndContext > ProTable（支持行拖拽排序）
- 搜索栏：门店筛选（单门店隐藏）/ 科室名称
- 表格列：拖拽手柄 | 门店筛选（仅搜索）| 科室名称 | 所属门店 | 科室标签 | 排序（hidden）| 终极科室 | 推荐（Switch）| 热门（Switch）| 状态（Switch）| 创建时间 | 操作
- 操作列：医生（仅终极科室）| 编辑 | 删除 | 更多（推荐/热门切换）
- 弹窗：医生绑定弹窗（Modal + List + Checkbox）

**科室表单页：**
- 布局：FormPage > 5 个 Card
- Card 1 基础信息：门店选择 + 父级分类 | 科室名称 + 科室标签 | 排序 | 描述
- Card 2 图片设置：3 列 Row/Col（图标 1:1 | Banner 16:9 | 简介图 free）
- Card 3 详情内容：科室简介（富文本）| 科室特色 | 预约须知
- Card 4 联系信息：科室电话 + 位置/楼层 | 工作时间
- Card 5 开关设置：6 个 Switch（启用状态、终极科室、是否推荐、是否热门、开放Banner、开放简介）
- 响应式支持：使用 useBreakpoint + useResponsive hooks

**门店列表页：**
- 布局：PageContainer > ProTable
- 表格列：Logo | 门店名称 | 门店编码 | 城市 | 地址 | 联系电话 | 风格 | 状态 | 操作
- 操作列：编辑 | 签到 | 删除 | 禁用/启用 | 更多（绑定科室、诊费模板、复诊配置、分配用户）
- 弹窗：科室绑定弹窗（Tree）| 用户分配弹窗（Transfer）| 签到二维码弹窗
- **注意：操作列固定宽度 240px，按钮众多**

**门店表单页：**
- 布局：FormPage > 5 个 Card
- Card 1 基础信息：门店名称（唯一性验证）+ 门店编码（自动生成+唯一性验证）| 联系人 + 联系方式 | 邮箱
- Card 2 地址信息：地址（必填）
- Card 3 展示设置：Logo 上传 | 风格选择 + 排序
- Card 4 营业设置：开始营业时间 + 结束营业时间 | 营业状态开关
- Card 5 就诊卡配置：每用户可建就诊卡数量上限
- Card 6 其他信息：门店简介（15行高度）

**交互模式统计：**
| 模块 | 操作按钮数量 | 弹窗数量 | 特殊交互 |
|------|------------|---------|---------|
| 医生列表 | 工具栏 3 + 操作列 4~5 | 2（排序、诊费） | DnD 排序、导入导出 |
| 科室列表 | 工具栏 2 + 操作列 4~5 | 1（医生绑定） | DnD 行排序、导入导出 |
| 门店列表 | 工具栏 2 + 操作列 6~7 | 3（科室、用户、二维码） | Tree 勾选、Transfer、导入导出 |

### 1.3 Engineer Agent 事实清单（技术视角）

#### 数据模型

**Doctor 模型（`models/doctor.py`）：**
- 字段：id, user_id, tenant_id, store_id, department_id, name, username, phone, password_hash, gender, avatar, banner, title, years_of_experience, education, graduate_school, license_number, license_image, honors, schedule_desc, max_daily_appointments, online_consult_enabled, online_consult_fee, page_style, promo_video, tags, specialty, introduction, is_recommended, sort_order, status, last_login_at, last_login_ip, use_fee_template
- 关联：tenant(N:1), store(N:1), department(N:1), schedules(1:N), consultation_fees(1:N)
- 约束：UniqueConstraint('tenant_id', 'username'), UniqueConstraint('tenant_id', 'phone')
- 多租户：所有查询均通过 `get_current_tenant_id()` 过滤

**Department 模型（`models/department.py`）：**
- 字段：id, name, parent_id, description, sort_order, is_hot, status, tenant_id, store_id, tag, enable_banner, enable_intro, is_final, is_recommended, banner_image, icon, intro_images, intro_content, features, appointment_notice, phone, location, working_hours
- 关联：tenant(N:1), children(1:N self-ref), doctors(1:N), store(N:1)
- 树形结构：通过 parent_id 自引用

**Store 模型（`models/store.py`）：**
- 字段：id, tenant_id, name, code, address, province, city, district, latitude, longitude, phone, contact_person, description, opening_time, closing_time, working_days, business_hours, image, logo, password, email, theme_style, sort_order, status, wechat_*, max_cards_per_user
- 约束：UniqueConstraint('tenant_id', 'code')
- 微信配置字段：wechat_app_id, wechat_app_secret, wechat_mch_id, wechat_api_key, wechat_notify_url

#### Schema 层

- Doctor schemas（`schemas/doctor.py`）：DoctorBase(24字段) -> DoctorCreate(+password), DoctorUpdate(全Optional), DoctorResponse(28字段+时间), DoctorListResponse(16字段)
- Doctor 模块 schemas（`modules/doctors/schemas.py`）：登录请求/响应、排序请求、账号检查请求/响应、账号生成请求/响应
- Department schemas（`schemas/department.py`）：DepartmentBase(18字段) -> Create/Update/Response/TreeNode
- Store schemas（`schemas/store.py`）：StoreBase(21字段) -> Create/Update/Response/ListResponse/Info/Query/WechatConfig

#### Service 层

**DoctorService（Mixin 组合模式）：**
- DoctorQueryMixin：get_by_phone, get_by_username, authenticate, update_login_info, get_by_id, get_list, get_recommended, get_by_department, get_all_active, get_doctors_availability
- DoctorMutationMixin：create（配额检查+自动建User+默认密码）, update, delete, check_username_exists, name_to_pinyin, generate_username, suggest_usernames, batch_update_sort_order

**DepartmentService（单文件）：**
- 查询：get_by_id, get_list, get_tree, get_hot, get_all_active, get_doctors, get_all_doctors
- 变更：create, update, delete（检查子科室）, batch_bind_doctors, batch_update_sort_order
- **注意：DepartmentService 没有使用多租户过滤（没有 tenant_id 过滤）** -- 但 Department 模型有 tenant_id 字段

**StoreService（Mixin 组合模式）：**
- StoreQueryMixin：get_by_id, get_by_code, get_by_name, check_name_exists, check_code_exists, get_list, get_all_active, get_department_count, get_departments, get_admins, get_wechat_config
- StoreMutationMixin：create（配额检查+默认密码+设置tenant_id）, update, delete（检查关联科室）, update_status, batch_bind_departments, batch_bind_admins, update_wechat_config

#### 安全机制

- 医生 CRUD：get_current_admin 依赖 + require_permission + get_store_filter + check_store_access
- 科室 CRUD：get_current_admin 依赖 + require_permission + check_store_access
- 门店 CRUD：get_current_admin 依赖 + require_permission + super_admin 检查（创建/删除）
- 医生登录：账号或密码错误统一返回"账号或密码错误"
- 微信配置：敏感字段掩码返回（'******'）
- 密码：默认 123456，前端不展示编辑密码入口

#### 多租户处理

- Doctor：所有查询都有 tenant_id 过滤
- Store：所有查询都有 tenant_id 过滤
- Department：模型有 tenant_id 字段但 **service 层查询未过滤 tenant_id**

---

## Phase 2：Round 2 -- 交叉辩论

### 2.1 交叉验证矩阵

| 维度 | 医生管理 | 科室管理 | 门店管理 |
|------|---------|---------|---------|
| 前后端接口完整度 | 完整 | 完整 | 完整 |
| CRUD 闭环 | 完整 | 完整 | 完整 |
| 多租户隔离 | Service 层全部过滤 | **Service 层未过滤 tenant_id** | Service 层全部过滤 |
| 权限控制 | 完善（admin+permission+store_filter） | 完善（admin+permission+store_access） | 完善（super_admin 区分） |
| 门店权限隔离 | 前端+后端双重过滤 | 前端+后端双重过滤 | 前端+后端双重过滤 |
| 导入导出 | 有 | 有 | 有 |
| 拖拽排序 | 推荐（弹窗内） | 列表行拖拽 | 无 |
| 诊费体系 | 医生级+门店模板+全局三级 | N/A | 门店模板+全局 |
| 文案一致性 | 基本一致 | 基本一致 | 基本一致 |

### 2.2 Critic Agent 质询

**Q1：Department Service 缺少 tenant_id 过滤是否为安全漏洞？**
- 事实：Department 模型有 `tenant_id` 字段且 ForeignKey 到 tenants 表
- 事实：`DepartmentService.get_list()` 没有 tenant_id 过滤
- 事实：Router 层通过 `get_store_filter` 间接做了门店级隔离（如果门店本身有 tenant_id 过滤）
- 结论：**这是一个真实的数据隔离缺陷**。虽然通过 store_id 间接隔离，但如果没有 store_id 参数的请求（如 store_id=None），将返回所有租户的科室数据。风险等级：高。

**Q2：医生表单提交时 boolean -> number 转换是否有双重转换风险？**
- 事实：前端 SwitchGroup 组件已自动处理 boolean -> 0/1
- 事实：`handleSubmit` 中又手动做了 `values.isRecommended ? 1 : 0` 转换
- 事实：后端 Schema 接受 int 类型（0/1）
- 结论：双重转换不会导致错误（true -> 1 -> 1），但注释已说明"为了兼容现有逻辑"。属于冗余代码，不构成 bug。

**Q3：门店列表接口 get_stores 对门店管理员的实现方式是否合理？**
- 事实：对于门店管理员，循环 `get_by_id` 逐个获取门店（N+1 查询）
- 事实：对于超级管理员，调用 `get_list`（单次分页查询）
- 结论：**性能问题**。当门店管理员绑定了多个门店时（如10个），会产生10次独立的数据库查询。应改为一次 `WHERE id IN (...)` 查询。

**Q4：医生预约设置页的文案是否一致？**
- 事实：列表页 `headerTitle` 为"医生预约设置"
- 事实：创建按钮文案为"添加医生预约管理"
- 事实：表单页标题为"编辑医生预约设置" / "添加医生预约管理"
- 结论：**文案不一致**。"预约设置"vs"预约管理"混用。

**Q5：科室列表页遗留的 console.log 是否应该清理？**
- 事实：`department/index.tsx` 第457行有 `console.log("🚀 ~ dataApi:", dataApi , dataApi.getExportDepartmentsUrl())`
- 结论：**遗留调试代码**，应清理。

**Q6：门店列表操作列按钮是否过多？**
- 事实：操作列包含 编辑、签到、删除、禁用/启用、更多（绑定科室、诊费模板、复诊配置、分配用户）
- 事实：列宽固定 240px
- 结论：操作项多达 7-8 个，在 240px 内排列较拥挤。但已使用"更多"下拉收纳了 4 项，算是合理的折中。

**Q7：门店表单的时间字段使用纯文本输入而非 TimePicker 是否合理？**
- 事实：`store/form.tsx` 的 openingTime/closingTime 使用 `ProFormText` + `timeRules.pattern`
- 事实：`doctor/booking-setting-form.tsx` 的 releaseTime 使用 `ProFormTimePicker`
- 结论：**不一致**。门店营业时间应使用 TimePicker 以提供更好的用户体验和时间格式保障。

### 2.3 投票矩阵

| 发现 | PM | Designer | Engineer | 投票结果 |
|------|-----|----------|----------|---------|
| Department Service 缺 tenant_id 过滤 | -- | -- | 确认 | **通过（高优先级）** |
| 门店列表 N+1 查询问题 | -- | -- | 确认 | **通过（中优先级）** |
| 预约设置文案不一致 | 确认 | -- | -- | **通过（低优先级）** |
| 科室列表 console.log | -- | -- | 确认 | **通过（低优先级）** |
| 门店时间输入方式不一致 | -- | 确认 | -- | **通过（低优先级）** |
| 医生表单 boolean 双重转换 | -- | -- | 确认 | 通过但为冗余代码 |
| 门店操作列按钮过多 | -- | 确认 | -- | 已通过"更多"收纳，现状可接受 |

### 2.4 独到发现

1. **医生删除为硬删除**：`DoctorMutationMixin.delete()` 直接 `db.delete()`，没有检查关联的排班/预约数据。如果医生有待进行的预约，删除后预约将成为孤儿数据。
2. **科室绑定医生时隐式修改门店**：`DepartmentService.batch_bind_doctors()` 在绑定医生时会把医生的 `store_id` 改为科室的门店ID，这是一个隐式的副作用操作，前端没有提示。
3. **门店创建默认密码明文存储**：`StoreMutationMixin.create()` 中 `store_data["password"] = "123456"`，密码以明文存入数据库（Store.password 列是 String(100)，非 hash）。
4. **医生创建同时创建 User 记录**：`DoctorMutationMixin.create()` 中有条件地创建 User 记录（需要 phone），但医生和 User 之间的关联通过 `user_id` 字段维护。如果医生没有手机号则不创建 User，导致无法通过 User 系统登录。
5. **Department 的 tree 接口缺少 tenant_id 过滤**：`get_tree()` 方法是公开接口（无需登录），且没有 tenant_id 过滤，任何人都可获取所有科室树数据。

---

## Phase 3：Round 3 -- 共识收敛

### Team Lead 裁决

经三智能体交叉验证，以下问题按优先级排列并确认行动计划。

---

## 行动计划

### P0 -- 必须修复（数据安全/正确性）

#### P0-1：Department Service 添加 tenant_id 过滤
- **问题**：DepartmentService 所有查询方法都没有 tenant_id 过滤，包括公开的 `get_tree()` 接口
- **影响**：跨租户数据泄露风险；公开接口可获取全量科室数据
- **修复范围**：`apps/server/app/modules/departments/service.py` 所有查询方法
- **修复方案**：在所有 select 查询中添加 `Department.tenant_id == get_current_tenant_id()` 过滤（公开接口需要从请求上下文或其他方式获取 tenant_id）
- **成本估算**：2小时
- **负责角色**：Engineer

#### P0-2：医生删除前检查关联数据
- **问题**：删除医生时不检查是否有未完成的排班或预约
- **影响**：删除后产生孤儿数据，预约记录失去医生信息
- **修复范围**：`apps/server/app/modules/doctors/service_mutation.py` 的 `delete()` 方法
- **修复方案**：删除前检查关联的 Schedule 和 Appointment，如有活跃数据则拒绝删除或提示先转移
- **成本估算**：3小时
- **负责角色**：Engineer

#### P0-3：科室绑定医生的隐式门店变更需提示
- **问题**：`batch_bind_doctors()` 隐式修改医生的 store_id
- **影响**：管理员在绑定医生到科室时，不知不觉改变了医生的门店归属
- **修复范围**：`apps/server/app/modules/departments/service.py` 的 `batch_bind_doctors()`
- **修复方案**：(a) 后端在绑定前检查医生的 store_id 是否与科室的 store_id 一致，不一致则返回提示；或 (b) 前端在绑定时弹出确认框说明门店也会变更
- **成本估算**：2小时
- **负责角色**：Engineer + PM

### P1 -- 建议修复（性能/一致性）

#### P1-1：门店列表接口消除 N+1 查询
- **问题**：门店管理员获取列表时逐个 `get_by_id`，N+1 查询
- **影响**：绑定门店数多时性能下降
- **修复范围**：`apps/server/app/modules/stores/router.py` 的 `get_stores()`
- **修复方案**：改为 `WHERE id IN (store_ids)` 一次性查询，同时在循环外批量获取 department_count
- **成本估算**：2小时
- **负责角色**：Engineer

#### P1-2：门店营业时间改用 TimePicker
- **问题**：门店表单的 openingTime/closingTime 使用纯文本输入
- **影响**：用户体验差，时间格式不可控
- **修复范围**：`apps/admin/src/pages/store/form.tsx`
- **修复方案**：将两个 ProFormText 改为 ProFormTimePicker，参考 booking-setting-form.tsx 的实现
- **成本估算**：0.5小时
- **负责角色**：Designer

#### P1-3：门店密码加密存储
- **问题**：门店密码明文存储在数据库
- **影响**：安全风险
- **修复范围**：`apps/server/app/modules/stores/service_mutation.py` 的 `create()` 和 `update()`
- **修复方案**：使用 `get_password_hash()` 对密码进行哈希存储
- **成本估算**：1小时
- **负责角色**：Engineer

### P2 -- 优化项（文案/代码质量）

#### P2-1：统一预约设置文案
- **问题**："医生预约设置"和"医生预约管理"混用
- **修复范围**：`apps/admin/src/pages/doctor/booking-setting.tsx` 第120行按钮文案
- **修复方案**：统一为"医生预约设置"，按钮改为"添加预约设置"
- **成本估算**：10分钟
- **负责角色**：PM

#### P2-2：清理科室列表调试日志
- **问题**：`department/index.tsx` 第457行遗留 `console.log`
- **修复范围**：`apps/admin/src/pages/department/index.tsx`
- **修复方案**：删除该行
- **成本估算**：5分钟
- **负责角色**：Engineer

#### P2-3：清理 department API 模块调试日志
- **问题**：`packages/api/src/modules/department.ts` 第47行和第61行有 `console.log`
- **修复范围**：`packages/api/src/modules/department.ts`
- **修复方案**：删除两行 console.log
- **成本估算**：5分钟
- **负责角色**：Engineer

#### P2-4：门店表单风格选项移除 emoji
- **问题**：管理端 UI 中使用 emoji 作为风格选项前缀不够正式
- **修复范围**：`apps/admin/src/pages/store/form.tsx` THEME_STYLE_OPTIONS
- **修复方案**：移除 emoji 前缀或改为色块标记
- **成本估算**：15分钟
- **负责角色**：Designer

#### P2-5：医生表单 boolean 转换代码清理
- **问题**：SwitchGroup 已自动处理转换，手动转换冗余
- **修复范围**：`apps/admin/src/pages/doctor/form.tsx` handleSubmit 函数
- **修复方案**：移除手动转换代码，统一依赖 SwitchGroup 的自动处理
- **成本估算**：15分钟
- **负责角色**：Engineer

---

## 摘要

本次评审通过集中调度模式，对医生/科室/门店三大基础管理模块进行了全面的事实收集和交叉验证。

**总体评价**：三个模块的功能完成度高，前后端接口一一对应，CRUD 闭环完整，权限控制层级合理（super_admin/admin/门店管理员三级），门店权限隔离在前后端均有实现。前端组件化程度良好，使用了 FormPage、ImageUploadCard、SwitchGroup 等基础设施组件。

**关键发现**：
1. **P0 级**：Department Service 缺少 tenant_id 过滤（安全风险）、医生删除无关联数据检查（数据完整性）、科室绑定医生隐式修改门店归属（逻辑合理性）
2. **P1 级**：门店列表 N+1 查询（性能）、门店营业时间输入方式不一致（体验）、门店密码明文存储（安全）
3. **P2 级**：文案不一致、遗留调试日志、风格选项 emoji 等代码质量问题

**建议优先处理 P0 级的 3 个问题**，特别是 Department 的 tenant_id 过滤缺失，这直接影响多租户数据隔离的安全性。

**总成本估算**：P0 约 7 小时，P1 约 3.5 小时，P2 约 50 分钟。全部修复约 11.5 人时。
