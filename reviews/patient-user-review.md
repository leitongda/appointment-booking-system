# 患者/用户管理功能 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-03-29
> 审查目标：患者管理和用户管理功能的逻辑流程、页面布局、操作合理性

---

## 模式选择

**选定模式：** 集中调度 -- Team Lead 统一调度 3 个 Explore agent 和 1 个 Critic agent

**选择理由：** 患者管理 + 用户管理横跨 admin 端、患者端 H5、小程序、Server 端，涉及数据模型、业务逻辑、前后端接口对应、UI/UX 等多维度。集中调度可确保跨端一致性审查。

---

## Round 1：事实层（只写事实，不评价）

### PM agent -- 产品视角

**功能覆盖范围：**

| 功能 | Admin 端 | 患者 H5 | 小程序 | Server API |
|------|---------|---------|--------|------------|
| 患者列表（用户维度） | user/index.tsx -> `/medical-services/user/list` | - | - | `/user-manage` (GET) |
| 患者详情（用户维度） | user/detail.tsx -> `/medical-services/user/:id` | - | - | `/user-manage/:id` (GET) |
| 就诊卡列表 | patient/index.tsx -> `/medical-services/medical-card/list` | - | - | `/patients` (GET) |
| 就诊卡详情 | patient/detail.tsx -> `/medical-services/medical-card/:id` | - | - | `/patients/:id` (GET) |
| 用户禁用/启用 | user/detail.tsx | - | - | `/user-manage/:id/status` (PUT) |
| 用户积分调整 | user/detail.tsx | - | - | `/user-manage/:id/points` (POST) |
| 就诊卡增删改 | patient/index.tsx + detail.tsx | - | - | `/patients` (POST/PUT/DELETE) |
| 添加家庭成员 | patient/detail.tsx | - | - | `/patients/:id/family-members` (POST) |
| 黑名单管理 | patient/index.tsx | - | - | `/patients/:id/blacklist` (PUT/DELETE) |
| 就诊人管理（C 端） | - | profile/patient/index + edit | packageProfile/patient/index + edit | `/users/patients` (CRUD) |
| 个人资料编辑 | - | profile/edit | packageProfile/profile/edit | `/users/profile` (PUT) |
| 头像上传 | - | profile/edit | packageProfile/profile/edit | `/users/avatar` (POST) |
| 手机号绑定 | - | - | packageProfile/profile/edit | `/users/bind-phone` (POST) |
| 登录（手机+密码） | - | login/index | - | `/auth/login` (POST) |
| 注册（手机+密码） | - | register/index | - | `/auth/register` (POST) |
| 微信登录 | - | - | profile/index | `/auth/wechat/login` (POST) |
| 微信获取手机号 | - | - | 已注释代码 | `/auth/wechat/phone` (POST) |
| 微信绑定用户信息 | - | - | profile/index | `/auth/wechat/bind-userinfo` (POST) |
| 预约记录查看 | patient/detail.tsx | appointment/index | packageBooking/pages/appointment | `/patients/:id/appointments` (GET) |
| 积分流水 | patient/detail.tsx | - | - | `/patients/:id/points` (GET) |
| 消费记录 | patient/detail.tsx | - | - | `/patients/:id/consumption-records` (GET) |
| 数据导入导出 | patient/index.tsx (ImportExport) | - | - | `/data` 相关接口 |

**业务模型关系：**
- User（用户/账号） -> 1:N -> Patient（就诊卡/就诊人）
- User 模型字段: id, tenant_id, phone, password_hash, nickname, avatar, gender, openid, status, points, unionid, wechat_nickname, wechat_avatar, wechat_synced_at
- Patient 模型字段: id, user_id, tenant_id, store_id, name, phone, id_card, gender, age, birthday, relationship, is_default, card_no, province, city, district, street, id_card_type, ethnicity, address, source, total_consumption
- 数据库约束: User 表 tenant_id+phone 唯一, tenant_id+openid 唯一, tenant_id+unionid 唯一; Patient 表 tenant_id+card_no 唯一

**Admin 端页面结构：**
- 路由: `/medical-services/user` -> 患者管理（用户维度）; `/medical-services/medical-card` -> 就诊卡管理（就诊卡维度）
- user/index.tsx: ProTable 列表页，搜索参数 keyword (phone/nickname)，列含头像/昵称/手机号/就诊卡数量/预约次数/积分/状态/注册时间/操作
- user/detail.tsx: 详情页，含头部统计卡片 + 基本信息 + 就诊卡列表，支持编辑用户信息/调整积分/禁用启用/删除用户/添加/编辑/删除就诊卡
- patient/index.tsx: ProTable 列表页，搜索参数 keyword (name/phone/cardNo)，列含卡号/姓名/性别/年龄/手机号/默认/所属患者/来源/预约次数/爽约次数/黑名单/创建时间/操作，含新增就诊卡 ModalForm
- patient/detail.tsx: 详情页，Tab 含档案详情/预约记录/项目记录/积分，家庭成员卡片，支持编辑/删除当前患者/添加/编辑/删除家庭成员/调整积分

**前后端接口对应：**

| 前端 API (packages/api) | 后端路由 | 匹配状态 |
|-------------------------|---------|---------|
| patientApi.getList -> GET /patients | router_manage.get_patients | 匹配 |
| patientApi.getDetail -> GET /patients/:id | router_manage.get_patient_detail | 匹配 |
| patientApi.create -> POST /patients | router_manage.create_patient | 匹配 |
| patientApi.update -> PUT /patients/:id | router_manage.update_patient | 匹配 |
| patientApi.delete -> DELETE /patients/:id | router_manage.delete_patient | 匹配 |
| patientApi.getAppointments -> GET /patients/:id/appointments | router_manage.get_patient_appointments | 匹配 |
| patientApi.getConsumptionRecords -> GET /patients/:id/consumption-records | router_manage.get_consumption_records | 匹配 |
| patientApi.getPointLogs -> GET /patients/:id/points | router_manage.get_point_logs | 匹配 |
| patientApi.adjustPoints -> POST /patients/:id/points | router_manage.adjust_points | 匹配 |
| patientApi.addToBlacklist -> PUT /patients/:id/blacklist | router_manage.add_to_blacklist | 匹配 |
| patientApi.removeFromBlacklist -> DELETE /patients/:id/blacklist | router_manage.remove_from_blacklist | 匹配 |
| patientApi.addFamilyMember -> POST /patients/:id/family-members | router_manage.add_family_member | 匹配 |
| patientApi.updateFamilyMember -> PUT /patients/:id/family-members/:mid | router_manage.update_family_member | 匹配 |
| patientApi.deleteFamilyMember -> DELETE /patients/:id/family-members/:mid | router_manage.delete_family_member | 匹配 |
| userManageApi.getList -> GET /user-manage | router_users.get_users | 匹配 |
| userManageApi.getDetail -> GET /user-manage/:id | router_users.get_user_detail | 匹配 |
| userManageApi.updateStatus -> PUT /user-manage/:id/status | router_users.update_user_status | 匹配 |
| userManageApi.adjustPoints -> POST /user-manage/:id/points | router_users.adjust_user_points | 匹配 |
| userManageApi.deleteUser -> DELETE /user-manage/:id | router_users.delete_user | 匹配 |
| userManageApi.updateUser -> PUT /user-manage/:id | router_users.update_user | 匹配 |
| userManageApi.createCard -> POST /user-manage/:id/cards | router_users.create_card | 匹配 |
| userManageApi.updateCard -> PUT /user-manage/:id/cards/:cid | router_users.update_card | 匹配 |
| userManageApi.deleteCard -> DELETE /user-manage/:id/cards/:cid | router_users.delete_card | 匹配 |
| userApi.getProfile -> GET /users/profile | users.router.get_profile | 匹配 |
| userApi.updateProfile -> PUT /users/profile | users.router.update_profile | 匹配 |
| userApi.getPatients -> GET /users/patients | users.router.get_patients | 匹配 |
| userApi.addPatient -> POST /users/patients | users.router.add_patient | 匹配 |
| userApi.updatePatient -> PUT /users/patients/:id | users.router.update_patient | 匹配 |
| userApi.deletePatient -> DELETE /users/patients/:id | users.router.delete_patient | 匹配 |

**文字描述相关：**
- Admin 患者列表页标题: "患者列表"（user/index.tsx:136 headerTitle）
- Admin 就诊卡列表页标题: "就诊卡列表"（patient/index.tsx:222 headerTitle）
- Admin 患者详情页标题: "患者详情"（user/detail.tsx:321, patient/detail.tsx:629 均为 "患者详情"）
- Admin 患者详情页返回按钮目标: user/detail.tsx:322 -> `/medical-services/user/list`; patient/detail.tsx:630 -> `/medical-services/user/list`（注：就诊卡详情页也返回用户列表）
- Admin 删除患者确认文本: "确定删除该就诊卡吗？删除后不可恢复"（patient/index.tsx:199, patient/detail.tsx:671）
- Admin 删除用户确认文本: "确定删除该用户吗？删除后用户的所有就诊卡将被一并删除，此操作不可恢复"（user/index.tsx:125）
- H5 注册页标题: "医院挂号系统"，副标题 "便捷预约，健康生活"
- H5 登录页忘记密码: "请联系医院客服重置密码：400-xxx-xxxx"
- 小程序登录提示: "点击登录"
- 小程序用户信息弹窗标题: "完善个人信息"

---

### Designer agent -- 用户视角

**Admin 端页面布局：**

| 页面 | 布局模式 | 组件使用 | 宽度 |
|------|---------|---------|------|
| user/index | PageContainer + ProTable | 头像 Avatar、Tag、OperationGroup | scroll x:1000 |
| user/detail | PageContainer + 多 Card | Avatar/Statistic/ProDescriptions/Table/ModalForm | 自适应 |
| patient/index | PageContainer + ProTable | ModalForm(新增/编辑)、ImportExport、Dropdown | scroll x:1300 |
| patient/detail | PageContainer + 多 Card + Tabs | Avatar/Statistic/ProDescriptions/ProTable/Table/ModalForm | 自适应 |

**user/detail.tsx 页面结构：**
- 头部卡片: Avatar(80px) + 昵称/性别图标/手机号/状态标签 + 统计数据(就诊卡/预约次数/爽约次数/积分) + 操作按钮(编辑/调整积分/禁用启用/删除)
- 基本信息 Card: ProDescriptions 3列，含用户ID/手机号/昵称/性别/OpenID/积分/状态/注册时间/更新时间
- 就诊卡列表 Card: Table 含添加按钮，列含卡号/姓名/性别/年龄/手机号/关系/默认/来源/预约次数/爽约次数/操作
- 弹窗: 积分调整 Modal、编辑用户信息 ModalForm、添加就诊卡 ModalForm、编辑就诊卡 ModalForm

**patient/detail.tsx 页面结构：**
- 头部卡片: Avatar(80px) + 姓名/性别/手机号/来源标签/黑名单标签 + 累计消费/最近就诊 + 操作按钮(编辑/删除)
- Tab 内容 Card: Tabs 包含"档案详情/预约记录/项目记录/积分"四个 Tab
- 家庭成员 Card: Table 含"添加亲友"按钮，显示家庭成员总消费（当前实现为 reduce 返回 sum=0 的空计算）
- 弹窗: 积分调整 Modal、添加家庭成员 ModalForm、编辑家庭成员 ModalForm、编辑当前患者信息 ModalForm

**表单设计（Admin）：**
- 新增就诊卡: 姓名*(必填) + 手机号*(必填, 正则 ^1\d{10}$) + 性别 + 出生日期 + 身份证号(正则) + 证件类型(默认居民身份证) + 与本人关系(默认"本人") + 民族(默认"汉族") + 省/市 + 区/街道 + 详细地址
- 编辑就诊卡: 同新增，但无默认值（不加载 birthday/relationship 以外的初始值）
- 编辑用户信息: 昵称 + 手机号 + 性别（仅 3 个字段）
- 积分调整: 积分数量(InputNumber, 提示"正数为增加，负数为减少") + 调整原因(TextArea, 必填, 最大200字)

**H5 端页面布局：**
- login/index: 居中卡片布局，渐变背景装饰，logo + 标题 + 表单(手机号/密码) + 忘记密码/注册链接
- register/index: NavBar 返回 + 表单(姓名/手机号/验证码/密码/确认密码) + 注册按钮 + 已有账号链接
- profile/index: 渐变头部(头像72px+昵称+手机号脱敏) + 菜单组(就诊人管理/就诊记录/消息通知 + 意见反馈/设置) + 退出登录
- profile/edit: NavBar + 头像上传(ImageUploader) + 表单(昵称/邮箱/手机号只读) + 底部固定保存按钮
- profile/patient/index: NavBar + 就诊人列表(SwipeAction 含设为默认/删除) + 底部固定添加按钮
- profile/patient/edit: NavBar + 表单(姓名/手机号/身份证号/性别Picker/关系Picker/设为默认Switch) + 删除/保存按钮

**小程序端页面布局：**
- profile/index (packageProfile): 头像+昵称区 + 统计卡片(预约次数/就诊人/消息) + 菜单列表(就诊人管理/我的收藏/就诊记录/消息通知/意见反馈/联系我们/关于我们/用户协议/隐私政策) + 退出登录 + 用户信息弹窗(头像选择/昵称输入)
- patient/index (packageProfile): 就诊人列表(Swipe 含删除) + 底部添加按钮 + LoginPopup
- patient/edit (packageProfile): 基本信息卡片(姓名*/性别/身份证号/手机号*) + 附加设置(与本人关系/设为默认Switch) + 提示信息
- profile/edit (packageProfile): 头像区(微信头像/从相册选择) + 表单(昵称nickname input/性别/手机号可编辑) + 保存按钮

**交互模式差异：**
- Admin: ProTable 搜索栏 + ModalForm 编辑 + Popconfirm 删除确认
- H5: antd-mobile NavBar + Form + SwipeAction + Dialog/Toast 反馈
- 小程序: NutUI Button/Form/Swipe + Taro.showModal/Toast 反馈 + LoginPopup 登录保护

**移动端适配：**
- H5: Tailwind CSS 类名布局，framer-motion 动画，响应式类名（min-h-screen bg-background）
- 小程序: Less 样式文件，PageContainer 包装，适配微信小程序交互模式

---

### Engineer agent -- 技术视角

**数据模型分析：**

| 模型 | 表名 | 关键约束 | 索引 |
|------|------|---------|------|
| User | users | tenant_id+phone 唯一, tenant_id+openid 唯一, tenant_id+unionid 唯一 | tenant_id, phone, openid, unionid |
| Patient | patients | tenant_id+card_no 唯一 | tenant_id, store_id, card_no |
| PointLog | point_logs | user_id FK | user_id |
| Blacklist | blacklists | user_id FK(可选), store_id FK(可选) | - |

**API 端点分析（共 35+ 个端点）：**

认证模块 (`/auth`):
- POST /auth/login, /auth/register, /auth/refresh, /auth/change-password
- POST /auth/wechat/login, /auth/wechat/phone, /auth/wechat/bind-phone, /auth/wechat/bind-userinfo
- POST /auth/send-code

用户自服务模块 (`/users`):
- GET/PUT /users/profile, POST /users/change-password, POST /users/bind-phone, POST /users/avatar
- GET /users/patients, GET /users/patients/:id, POST /users/patients, PUT /users/patients/:id, DELETE /users/patients/:id

管理员-就诊卡管理 (`/patients`):
- GET /patients, POST /patients, GET /patients/blacklist
- GET/PUT/DELETE /patients/:id
- GET /patients/:id/appointments, /consumption-records, /points, /points/summary
- POST /patients/:id/points
- PUT/DELETE /patients/:id/blacklist
- POST/PUT/DELETE /patients/:id/family-members, /family-members/:mid

管理员-用户管理 (`/user-manage`):
- GET /user-manage, GET /user-manage/:id
- PUT /user-manage/:id/status, POST /user-manage/:id/points
- DELETE /user-manage/:id, PUT /user-manage/:id
- POST /user-manage/:id/cards, PUT /user-manage/:id/cards/:cid, DELETE /user-manage/:id/cards/:cid

**认证/授权机制：**
- Admin 端: get_current_admin (JWT) + require_permission 权限检查
- 患者端: get_current_user (JWT)
- 权限标识: patient:create, patient:detail, patient:update, patient:delete, user:update, user:delete
- 多租户: 所有 service 层通过 _current_tenant_id() + ContextVar 过滤数据

**黑名单实现分析：**
- 系统存在两套黑名单机制:
  1. Blacklist 独立模型（blacklists 表）: 含 user_id/store_id/keyword/reason/no_show_count/source/expire_at/released_at/status
  2. User.status=0 状态禁用: service_manage.py 中 add_to_blacklist/remove_from_blacklist 直接操作 User.status
- patient/detail.tsx 中 `isBlacklist` 字段实际上映射的是 `user.status == 0`（service_manage.py:73, 203）
- Blacklist 模型未被患者管理模块使用

**家庭成员逻辑：**
- 概念: 同一 User 下的多个 Patient 记录，每个 Patient 是一张就诊卡/一个就诊人
- "家庭成员"和"就诊卡"在数据库层面是同一张表（patients 表），通过 user_id 关联
- 添加家庭成员: 创建新的 Patient 记录，继承 user_id 和 tenant_id
- 防止重复: 同一 user_id 下 name 不能重复

**积分系统：**
- 积分存储在 User.points 字段
- 积分流水存储在 PointLog 表，含 change_amount/balance/type(1消费/2充值/3赠送/4手动调整)/remark/operator_id
- 两套积分调整入口:
  1. `/user-manage/:id/points` (UserManageService.adjust_points) -- 直接操作 User 表 + 写 PointLog
  2. `/patients/:id/points` (PointService.adjust_points) -- 通过独立 PointService

**数据安全：**
- Admin 创建患者时默认密码 "123456"（service_manage.py:424 get_password_hash("123456")）
- 手机号脱敏: H5 端 `phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')`；小程序同样
- 身份证号脱敏: H5 就诊人列表 `idCard.replace(/(\d{4})\d{10}(\d{4})/, '$1**********$2')`
- Admin 端手机号/身份证号均未脱敏（符合后台管理需求）
- OpenID 在用户详情页可复制（user/detail.tsx:403 copyable）

**C 端用户创建患者差异：**
- C 端 PatientService.create: 只创建 Patient 记录，不创建 User
- Admin PatientManageService.create_patient: 先查找或创建 User，再创建 Patient
- Admin UserManageService.create_card: 只创建 Patient（User 必须已存在）

**性能相关：**
- patient 列表查询: 每个 patient 单独执行 2 次子查询（appointment_count + no_show_count），N+1 问题
- user 列表查询: 每个 user 单独执行 2 次子查询（card_count + appointment_count），N+1 问题
- patient 详情: 加载时同时加载全部医生列表（fetchAllData doctorApi.getList）用于预约记录筛选下拉

---

## Round 2：交叉辩论

### Critic agent 质询

**质询 1: "患者" vs "就诊卡" vs "就诊人" 术语混乱**
- Admin 端路由: `/medical-services/user` 叫"患者管理"，`/medical-services/medical-card` 叫"就诊卡管理"
- 但 patient/index.tsx 的 headerTitle 是"就诊卡列表"
- user/index.tsx 的 headerTitle 是"患者列表"
- 两者的详情页标题都叫"患者详情"
- C 端 (H5/小程序) 统一叫"就诊人"
- 服务器端代码: Patient 模型对应 "patients" 表，router_manage 是 "就诊卡管理"，router_users 是 "患者管理"
- **判定：术语确实混乱，User/Patient/就诊卡/就诊人/患者 在不同端含义不一致**

**质询 2: 黑名单机制冲突**
- Blacklist 模型（blacklists 表）设计了完整的黑名单功能: reason, no_show_count, expire_at, released_at, status, source(手动/自动)
- 但实际使用的黑名单操作只是把 User.status 设为 0（禁用）
- admin 端加黑名单时硬编码 reason='多次爽约'（patient/index.tsx:55）
- 黑名单列表页的筛选 is_blacklist 映射的是 user.status==0
- **判定：Blacklist 表未被使用，黑名单功能与用户禁用功能混淆**

**质询 3: 就诊卡详情页返回路径指向错误**
- patient/detail.tsx:630 返回按钮: `history.push('/medical-services/user/list')`
- 但就诊卡详情页应该返回就诊卡列表 `/medical-services/medical-card/list`
- 从就诊卡列表进入详情: patient/index.tsx:188 -> `/medical-services/medical-card/${record.id}`
- **判定：确认存在返回路径错误**

**质询 4: user/detail 中就诊卡的查看跳转路径**
- user/detail.tsx:220 就诊卡列表中的"查看"链接: `history.push(`/medical-services/medical-card/${record.id}`)`
- 这会跳转到就诊卡详情页（patient/detail.tsx），而不是用户维度的详情
- 但就诊卡详情页的返回按钮又指向 `/medical-services/user/list`
- **判定：跳转链路混乱**

**质询 5: 积分系统两套入口可能不一致**
- `/user-manage/:id/points` 通过 UserManageService 直接操作 User.points + 写 PointLog
- `/patients/:id/points` 通过独立 PointService 调整
- 两者操作同一个 User.points 字段，但 service 层实现不同
- **判定：存在数据一致性风险**

**质询 6: 家庭成员总消费计算无效**
- patient/detail.tsx:395 `familyTotalConsumption = patient?.familyMembers?.reduce((sum, m) => sum, 0) || 0`
- reduce 回调只返回 sum，不累加任何值，永远返回 0
- **判定：确认存在逻辑 Bug**

**质询 7: H5 端注册页提交了 confirmPassword 但后端不接收**
- register/index.tsx:49 校验 `values.password !== form.getFieldValue('confirmPassword')`
- 但 register API 只提交 phone/password/code/name，confirmPassword 不提交
- 后端 RegisterRequest schema 不含 confirmPassword 字段
- **判定：前端逻辑正确（前端校验不提交），但 register 中调用 `form.getFieldValue('confirmPassword')` 而非从 values 获取**

**质询 8: user-manage 的 updateUser 接口使用 Body(...) 但未做字段白名单校验**
- router_users.py:115 `data: dict = Body(...)` 直接传入 service.update_user
- service_users.py:248 `allowed_fields = ["nickname", "avatar", "gender", "phone"]` 有白名单
- **判定：service 层有白名单保护，但 API 层缺少 schema 验证**

**质询 9: C 端就诊人编辑缺少 birthday/地址等字段**
- H5 profile/patient/edit: 只有 name/phone/idCard/gender/relationship/isDefault
- 小程序 patient/edit: 只有 name/gender/idCard/phone/relationship/isDefault
- Admin 端就诊卡编辑: 含 birthday/province/city/district/street/idCardType/ethnicity/address 等完整字段
- 后端 PatientCreate schema 支持 birthday 等字段
- **判定：C 端就诊人表单字段比 Admin 端少很多，但这是产品设计选择而非 Bug**

**质询 10: 微信获取手机号功能已注释**
- 小程序 profile/index.tsx:315-371 大段注释代码: handleGetPhoneNumber, handleBindPhone
- 当前流程: 微信登录 -> 设置头像昵称（可跳过）-> 直接进入
- 不要求绑定手机号
- 后端 auth/wechat/bind-userinfo 支持无手机号创建用户
- **判定：手机号非必填是刻意的产品设计，但可能导致后续通知/找回密码困难**

### 投票矩阵

| # | 发现 | PM 投票 | Designer 投票 | Engineer 投票 | 最终裁决 |
|---|------|---------|-------------|-------------|---------|
| 1 | 术语混乱（患者/就诊卡/就诊人） | P1 | P1 | P2 | P1 |
| 2 | 黑名单与用户禁用混淆 | P1 | P2 | P0 | P1 |
| 3 | 就诊卡详情返回路径错误 | P0 | P2 | P1 | P0 |
| 4 | 跳转链路混乱 | P1 | P1 | P2 | P1 |
| 5 | 积分两套入口一致性风险 | P2 | -- | P1 | P2 |
| 6 | 家庭成员总消费永远为 0 | P0 | P2 | P0 | P0 |
| 7 | H5 注册校验写法不规范 | -- | -- | P2 | P2 |
| 8 | user-manage 更新接口缺 schema | -- | -- | P1 | P1 |
| 9 | C 端就诊人表单字段不完整 | P1 | P2 | -- | P2 |
| 10 | 微信登录不要求手机号 | P1 | -- | P2 | P1 |
| 11 | N+1 查询性能问题 | -- | -- | P1 | P1 |
| 12 | Admin 创建患者默认密码硬编码 | -- | -- | P1 | P1 |
| 13 | 预约状态映射不一致 (detail vs index) | P1 | -- | P2 | P1 |

### 独到发现

1. **patient/detail.tsx 的预约状态映射与全局不一致**: 页面内 `APPOINTMENT_STATUS_MAP` 定义了 9 种状态(0-8)，但 `valueEnum` 只映射了 5 种(0/1/4/6/7)，且 7 在 MAP 中是"已过期"而在 valueEnum 中是"退款中"。这会导致状态显示不一致。

2. **Admin 端就诊卡编辑不加载全部初始值**: patient/index.tsx:360 的 editModal initialValues 只包含 name/phone/gender/idCard/birthday/relationship 6 个字段，但编辑表单有 province/city/district/street/idCardType/ethnicity/address 等字段。编辑时这些字段会显示为空。

3. **C 端 PatientService.create 缺少 tenant_id**: users/service.py:193 创建 Patient 时没有设置 tenant_id，而 Admin 端的 service_manage.py:441 设置了。这可能导致 C 端创建的就诊人在多租户场景下无法被正确过滤。

4. **user/detail.tsx 的 OpenID 展示**: 在基本信息中展示 OpenID 并允许复制，但这属于敏感信息，普通管理员可能不应该看到。

5. **H5 端 profile/edit 引用了 User.name 和 User.email 字段**: 但 User 模型没有 name 和 email 字段（只有 nickname）。`form.setFieldsValue({ nickname: data.nickname || data.name, email: data.email })` 中 data.name 和 data.email 会是 undefined。

---

## Round 3：共识收敛

### Team Lead 裁决

**P0 -- 必须立即修复（影响功能正确性或数据完整性）：**

1. **就诊卡详情页返回路径错误** (发现 #3)
   - patient/detail.tsx:630 返回按钮指向 `/medical-services/user/list`，应指向 `/medical-services/medical-card/list`

2. **家庭成员总消费永远为 0** (发现 #6)
   - patient/detail.tsx:395 reduce 回调未累加成员消费值

3. **C 端创建就诊人缺少 tenant_id** (独到发现 #3)
   - users/service.py PatientService.create 未设置 tenant_id

**P1 -- 应尽快修复（影响用户体验或系统安全）：**

4. **术语统一** (发现 #1)
   - 需要统一"患者"/"就诊卡"/"就诊人"在不同端的使用

5. **黑名单机制与用户禁用混淆** (发现 #2)
   - Blacklist 表未被使用，需要明确黑名单的业务定义

6. **Admin 端跳转链路混乱** (发现 #4)
   - user/detail -> 就诊卡查看 -> 就诊卡详情 -> 返回用户列表（不合理）

7. **预约状态映射不一致** (独到发现 #1)
   - patient/detail.tsx 中 APPOINTMENT_STATUS_MAP 与 valueEnum 不匹配

8. **Admin 就诊卡编辑初始值不全** (独到发现 #2)
   - 编辑弹窗未加载 province/city 等地址字段初始值

9. **user-manage 更新接口缺 schema 验证** (发现 #8)
   - 应使用 Pydantic schema 替代 dict = Body(...)

10. **N+1 查询性能问题** (发现 #11)
    - 列表页每个记录单独查询统计信息

11. **Admin 创建患者默认密码硬编码** (发现 #12)
    - "123456" 硬编码在代码中

12. **微信登录不要求手机号** (发现 #10)
    - 需要评估是否需要引导绑定

13. **H5 profile/edit 引用不存在的字段** (独到发现 #5)
    - data.name 和 data.email 在 User 类型上不存在

**P2 -- 可排期修复（改进建议）：**

14. **积分系统两套入口** (发现 #5)
    - 统一积分调整入口

15. **H5 注册校验写法** (发现 #7)
    - 应从 values 获取 confirmPassword 而非 getFieldValue

16. **C 端就诊人表单字段不完整** (发现 #9)
    - 可逐步补齐

17. **OpenID 敏感信息展示** (独到发现 #4)
    - 考虑权限控制或脱敏

---

## 行动计划

### P0 行动项

| # | 行动 | 影响文件 | 成本估算 | 负责角色 |
|---|------|---------|---------|---------|
| P0-1 | 修复就诊卡详情页返回路径: `/medical-services/user/list` -> `/medical-services/medical-card/list` | `apps/admin/src/pages/patient/detail.tsx:630` | 0.5h | 前端 |
| P0-2 | 修复家庭成员总消费 reduce 逻辑: 累加 totalConsumption | `apps/admin/src/pages/patient/detail.tsx:395` | 0.5h | 前端 |
| P0-3 | C 端 PatientService.create 添加 tenant_id 字段 | `apps/server/app/modules/users/service.py:193-206` | 1h | 后端 |

### P1 行动项

| # | 行动 | 影响文件 | 成本估算 | 负责角色 |
|---|------|---------|---------|---------|
| P1-1 | 统一术语：Admin"患者管理"管理 User 维度，"就诊卡管理"管理 Patient 维度；C 端统一"就诊人"；修正所有页面标题和按钮文字 | `apps/admin/src/pages/user/index.tsx`, `apps/admin/src/pages/patient/index.tsx`, `apps/admin/src/pages/patient/detail.tsx` 等 | 2h | 前端 |
| P1-2 | 明确黑名单业务定义：Blacklist 表 vs User.status 禁用的关系；修复硬编码 reason；关联 Blacklist 表或移除冗余模型 | `apps/server/app/modules/patients/service_manage.py`, `apps/admin/src/pages/patient/index.tsx:55`, `apps/server/app/models/blacklist.py` | 4h | 后端+前端 |
| P1-3 | 修复跳转链路：用户详情 -> 就诊卡查看应停留在用户维度或明确告知用户已跳转到就诊卡管理 | `apps/admin/src/pages/user/detail.tsx:220` | 1h | 前端 |
| P1-4 | 统一预约状态映射：patient/detail.tsx 中 APPOINTMENT_STATUS_MAP 与 valueEnum 对齐 | `apps/admin/src/pages/patient/detail.tsx:57-67 vs 275-280` | 1h | 前端 |
| P1-5 | 修复就诊卡编辑初始值：补全 province/city/district/street/idCardType/ethnicity/address 字段 | `apps/admin/src/pages/patient/index.tsx:360` | 0.5h | 前端 |
| P1-6 | user-manage 更新接口添加 Pydantic schema 替代 dict = Body(...) | `apps/server/app/modules/patients/router_users.py:115` | 1h | 后端 |
| P1-7 | 优化列表查询 N+1：使用子查询或 JOIN 批量获取统计信息 | `apps/server/app/modules/patients/service_manage.py:62-71`, `apps/server/app/modules/patients/service_users.py:51-76` | 4h | 后端 |
| P1-8 | 管理员创建患者默认密码改为可配置或移除硬编码 | `apps/server/app/modules/patients/service_manage.py:424` | 1h | 后端 |
| P1-9 | 评估微信登录后手机号绑定引导策略，如首次预约时提示绑定 | `apps/patient-miniapp/src/pages/profile/index.tsx`, 后端相关逻辑 | 4h | 产品+前端 |
| P1-10 | H5 profile/edit 修复：移除对 User.name/User.email 的引用 | `apps/patient-h5/src/pages/profile/edit.tsx:28` | 0.5h | 前端 |

### P2 行动项

| # | 行动 | 影响文件 | 成本估算 | 负责角色 |
|---|------|---------|---------|---------|
| P2-1 | 统一积分调整入口：移除 UserManageService.adjust_points，统一使用 PointService | `apps/server/app/modules/patients/service_users.py:178-206`, `apps/server/app/modules/patients/router_users.py:71-92` | 2h | 后端 |
| P2-2 | H5 注册校验改用 values.confirmPassword | `apps/patient-h5/src/pages/register/index.tsx:49` | 0.5h | 前端 |
| P2-3 | C 端就诊人表单逐步补齐 birthday/地址等字段 | H5 `profile/patient/edit.tsx`, 小程序 `packageProfile/pages/patient/edit.tsx` | 2h | 前端 |
| P2-4 | OpenID 展示添加权限控制或脱敏处理 | `apps/admin/src/pages/user/detail.tsx:403` | 0.5h | 前端 |

---

## 摘要

本次评审对"患者管理+用户管理"模块进行了全链路审查，覆盖 Admin 端 4 个页面、患者端 H5 6 个页面、小程序 4 个页面、Server 端 35+ 个 API 端点。发现 3 个 P0 级问题、10 个 P1 级问题、4 个 P2 级建议。

**关键发现：**
1. 核心概念"用户(User)"与"就诊卡(Patient)"在不同端名称混乱（患者/就诊卡/就诊人），需要统一术语
2. 黑名单功能存在两套机制（Blacklist 表 vs User.status），Blacklist 表实际未被使用
3. 存在 2 个明确的 Bug：就诊卡详情返回路径错误、家庭成员总消费永远为 0
4. C 端创建就诊人缺少 tenant_id，在多租户场景下可能导致数据隔离问题
5. 列表查询存在 N+1 性能问题

**总修复成本估算：** P0 约 2h，P1 约 19h，P2 约 5h，合计约 26h。
