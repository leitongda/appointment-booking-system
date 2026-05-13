# Admin E2E Test Coverage Audit

**Audit Date**: 2026-05-13
**Auditor**: Automated Analysis
**Codebase**: `apps/admin` (SaaS Hospital Appointment Booking System)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total routes (with component) | 111 |
| Routes covered by E2E tests | 91 (82%) |
| Total interactive operations found | 233 |
| Operations covered by tests | 156 (67%) |
| Operations NOT covered by tests | 77 (33%) |
| Total E2E spec files | 31 |
| Total test cases | 288 |

---

## 1. Module-by-Module Coverage Matrix

### 1.1 Platform Management (ping tai guan li)

| Route | Visible? | Operations in Source | Covered | Uncovered |
|-------|----------|---------------------|---------|-----------|
| `/platform/tenant/list` | Yes | List, Create, Edit, Delete, Status Switch, View Detail, Usage | List, Create, Edit, Delete, Status Switch | View Detail (Drawer), Usage Page |
| `/platform/tenant/create` | Hidden | Form Submit | Form Submit | - |
| `/platform/tenant/:id` | Hidden | Detail View | Detail View (basic) | Detail Page Operations (suspend/activate) |
| `/platform/tenant/:id/edit` | Hidden | Form Submit | Form Submit | - |
| `/platform/tenant/plans` | Yes | List, Create, Edit, Drawer Detail | List, Edit | Create Plan, Drawer Detail View |
| `/platform/tenant/plans/create` | Hidden | Form Submit | - | Form Submit (Plan Create) |
| `/platform/tenant/plans/:id/edit` | Hidden | Form Submit | Form Submit | - |
| `/platform/miniapp-platform/company` | Yes | List, Create, Edit, View Detail | List, Create, Edit, Detail | Delete Company |
| `/platform/miniapp-platform/company/create` | Hidden | Form Submit | Form Submit | - |
| `/platform/miniapp-platform/company/:id/edit` | Hidden | Form Submit | Form Submit | - |
| `/platform/miniapp-platform/payment-profile` | Yes | List, Create, Edit, View Detail | List, Create, Edit, Detail | Delete Payment Profile |
| `/platform/miniapp-platform/instance` | Yes | List, Create, Edit, View Detail | List, Create, Edit, Detail | Delete Instance |
| `/platform/miniapp-platform/template` | Yes | List View | Page Load | Template CRUD Operations |
| `/platform/miniapp-platform/build` | Yes | List View | Page Load | Build Trigger/Cancel |
| `/platform/miniapp-platform/release` | Yes | List View | Page Load | Release CRUD |

**Module Stats**: 15 routes, 13 tested (87%), 35 operations, 24 covered (69%), 11 uncovered

---

### 1.2 Medical Services (yi liao fu wu) - Doctor Management

| Route | Visible? | Operations in Source | Covered | Uncovered |
|-------|----------|---------------------|---------|-----------|
| `/medical-services/doctor/list` | Yes | List, Create, Edit, Delete, Status Switch, Recommend Switch, Import/Export | List, Create, Edit, Delete, Status Switch, Import/Export | Recommend Switch (list), Dropdown Actions |
| `/medical-services/doctor/create` | Hidden | Form Submit, Avatar Upload, Banner Upload, Certificate Upload | Form Submit | Image Uploads (Avatar/Banner/Certificate) |
| `/medical-services/doctor/:id/edit` | Hidden | Form Submit | Form Submit | Image Uploads |
| `/medical-services/doctor/:id` | Hidden | Detail Tabs (Schedule/Appointment/Info), Consultation Fee Modal | Detail View (basic) | Consultation Fee Modal (Switch/Delete), Appointment Tab Actions |
| `/medical-services/doctor/booking-setting` | Yes | List, Add, Edit, Delete | List, Add, Edit | Delete Booking Setting |
| `/medical-services/doctor/booking-setting/create` | Hidden | Form Submit | Form Submit | - |
| `/medical-services/doctor/booking-setting/:id/edit` | Hidden | Form Submit | Form Submit | - |

**Module Stats**: 7 routes, 7 tested (100%), 28 operations, 20 covered (71%), 8 uncovered

---

### 1.3 Medical Services - Schedule Management

| Route | Visible? | Operations in Source | Covered | Uncovered |
|-------|----------|---------------------|---------|-----------|
| `/medical-services/schedule/rule` | Yes | List, Create, Edit, Delete, Batch Enable/Disable, Copy Rule, Generate, History | List, Create, Edit, Batch Enable/Disable | Copy Rule Modal, Generate Schedule, History Logs Modal, Delete Single Rule |
| `/medical-services/schedule/rule/create` | Hidden | Step Form Submit | Step Form Submit | - |
| `/medical-services/schedule/rule/:id/edit` | Hidden | Step Form Submit | Step Form Submit | - |
| `/medical-services/schedule/list` | Yes | List, Suspend, Resume | List (basic) | Suspend/Resume from List |
| `/medical-services/schedule/calendar` | Yes | Calendar View, Month/Week Toggle, Day Detail Drawer, Create Appointment | Calendar View, Month/Week Toggle | Day Detail Drawer, Create Appointment from Calendar |
| `/medical-services/schedule/gantt` | Yes | Gantt View, Drawer Detail | Gantt View | Drawer Detail Interaction |
| `/medical-services/schedule/custom` | Yes | List, Add, Delete | List, Add | Delete Custom Schedule |
| `/medical-services/schedule/custom/create` | Hidden | Form Submit | Form Submit | - |
| `/medical-services/schedule/rest-day` | Yes | List, Add, Delete, Batch Delete | List, Add | Delete Single, Batch Delete |
| `/medical-services/schedule/rest-day/create` | Hidden | Form Submit | Form Submit | - |
| `/medical-services/schedule/suspension` | Yes | List, Add Suspension (ModalForm), Cancel Suspension | Page Load, Add Modal | Cancel Suspension, Delete Suspension |
| `/medical-services/schedule/leave-request` | Yes | List, Approve, Reject, View Detail | List, Approve, Reject, View Detail | - |
| `/medical-services/schedule/statistics` | Yes | Query Form, Chart | Query Form | Chart Interaction |

**Module Stats**: 13 routes, 13 tested (100%), 38 operations, 26 covered (68%), 12 uncovered

---

### 1.4 Medical Services - Appointment Management

| Route | Visible? | Operations in Source | Covered | Uncovered |
|-------|----------|---------------------|---------|-----------|
| `/medical-services/appointment/list` | Yes | List, Cancel, Mark NoShow, Cancel SignIn, Import/Export, Filter/Search, Pagination | List, Cancel, Mark NoShow, Cancel SignIn, Import/Export, Filter, Pagination | Modal.confirm Cancel with Reason |
| `/medical-services/appointment/queue` | Yes | Queue List, Call (叫号), Complete, Pass (过号), Recall, Auto-refresh Switch, Store/Doctor/Date Filter | - (only covered via API-level in appointment-state-flows) | ALL Queue Page UI Operations: Call/Complete/Pass/Recall Buttons, Auto-refresh Switch, Filters |
| `/medical-services/appointment/statistics` | Yes | Query Form, Summary Cards, Trend Chart, Status Distribution | - | ALL Statistics Page Operations: Query, Date Range, Store Filter |
| `/medical-services/appointment/:id` | Hidden | Detail View, Cancel (Popconfirm), Refund (Drawer), Refund Submit, Refund Cancel | Detail View, Refund Drawer Open/Submit/Cancel | Cancel from Detail Page, Detail Timeline Interaction |

**Module Stats**: 4 routes, 3 tested via direct page (75%), 25 operations, 16 covered (64%), 9 uncovered

---

### 1.5 Medical Services - Patient Management

| Route | Visible? | Operations in Source | Covered | Uncovered |
|-------|----------|---------------------|---------|-----------|
| `/medical-services/patient/list` | Yes | List, Search/Filter, Pagination | List, Search, Pagination | - |
| `/medical-services/patient/:id` | Hidden | Detail View, Add Medical Card (ModalForm), Edit Card (ModalForm), Delete Card (Popconfirm) | Detail View (basic) | Add Medical Card Modal, Edit Card Modal, Delete Card |
| `/medical-services/patient/card/list` | Yes | List | Page Load | Card CRUD Operations |
| `/medical-services/patient/card/:id` | Hidden | Detail View | Detail View (basic) | - |
| `/medical-services/medical-record` | Yes | List, View | Page Load | View Record Detail |
| `/medical-services/consultation-fee/types` | Yes | List, Create, Edit | List, Create, Edit | Delete Fee Type |
| `/medical-services/consultation-fee/types/create` | Hidden | Form Submit | Form Submit | - |
| `/medical-services/consultation-fee/types/:id/edit` | Hidden | Form Submit | Form Submit | - |
| `/medical-services/consultation-fee/templates` | Yes | List | Page Load | Template CRUD |

**Module Stats**: 9 routes, 9 tested (100%), 18 operations, 12 covered (67%), 6 uncovered

---

### 1.6 Organization Structure (zu zhi jia gou)

| Route | Visible? | Operations in Source | Covered | Uncovered |
|-------|----------|---------------------|---------|-----------|
| `/organization/store/list` | Yes | List, Create, Edit, Delete, Import/Export | List, Create, Edit, Delete, Import/Export | - |
| `/organization/store/create` | Hidden | Form Submit | Form Submit | - |
| `/organization/store/:id/edit` | Hidden | Form Submit | Form Submit | - |
| `/organization/store/:storeId/visit-type-config` | Hidden | Config Save | Config Save | - |
| `/organization/department/list` | Yes | List, Create, Edit, Delete, Status Switch, Recommend/Hot Switch, Import/Export | List, Create, Edit, Delete, Status Switch, Recommend/Hot Switch, Import/Export | - |
| `/organization/department/create` | Hidden | Form Submit, Image Upload | Form Submit | Image Uploads (Icon/Cover/Banner) |
| `/organization/department/:id/edit` | Hidden | Form Submit | Form Submit | Image Uploads |
| `/organization/medical-config/booking-rules` | Yes | Settings Form | Page Load | Save Settings Form |
| `/organization/medical-config/booking-fields` | Yes | Settings Form | Page Load | Save Settings Form |
| `/organization/medical-config/booking-notice` | Yes | Form, Switch | Page Load | Save Notice, Toggle Switch |
| `/organization/medical-config/patient-card` | Yes | Settings Form | Page Load | Save Config |
| `/organization/medical-config/shift-types` | Yes | List, Create | List, Create | Delete Shift Type |
| `/organization/medical-config/shift-types/create` | Hidden | Form Submit | Form Submit | - |
| `/organization/medical-config/shift-types/:id/edit` | Hidden | Form Submit | - | Edit Shift Type |
| `/organization/medical-config/rule-sets` | Yes | List, Create, Delete, Copy, Preview, Import/Export | List, Create | Delete Rule Set, Copy Rule Set, Preview Drawer, Import/Export |
| `/organization/medical-config/rule-sets/create` | Hidden | Form Submit | Form Submit | - |
| `/organization/medical-config/rule-sets/:id/edit` | Hidden | Form Submit | - | Edit Rule Set |
| `/organization/medical-config/rule-sets/:id/audit` | Hidden | History View | - | Audit History Page |
| `/organization/staff` | Yes | List, Create, Edit, Reset Password, Import/Export | List, Create, Edit, Reset Password | Import/Export |
| `/organization/staff/create` | Hidden | Form Submit | Form Submit | - |
| `/organization/staff/:id/edit` | Hidden | Form Submit | Form Submit (basic) | - |

**Module Stats**: 21 routes, 19 tested (90%), 40 operations, 26 covered (65%), 14 uncovered

---

### 1.7 Content Center (yun ying zhong xin)

| Route | Visible? | Operations in Source | Covered | Uncovered |
|-------|----------|---------------------|---------|-----------|
| `/content-center/content/news` | Yes | List, Create, Edit, Delete, Status Switch, Import/Export, Batch Delete | List, Create, Edit, Delete, Import/Export, Batch | Status Switch |
| `/content-center/content/news/create` | Hidden | Form Submit, Image Upload | Form Submit | Image Upload |
| `/content-center/content/news/:id/edit` | Hidden | Form Submit | Form Submit | Image Upload |
| `/content-center/content/notice` | Yes | List, Create, Edit, Delete, Status Switch | List, Create, Edit, Delete | Status Switch |
| `/content-center/content/notice/create` | Hidden | Form Submit | Form Submit | - |
| `/content-center/content/notice/:id/edit` | Hidden | Form Submit | Form Submit | - |
| `/content-center/content/banner` | Yes | List, Create, Edit, Delete, Status Switch | List, Create, Edit, Delete, Status Switch | - |
| `/content-center/content/banner/create` | Hidden | Form Submit, Image Upload | Form Submit | Image Upload |
| `/content-center/content/banner/:id/edit` | Hidden | Form Submit | Form Submit | Image Upload |
| `/content-center/message/list` | Yes | List, Create | List, Create | - |
| `/content-center/message/create` | Hidden | Form Submit | Form Submit | - |
| `/content-center/feedback` | Yes | List, View Detail (Drawer), Reply (ModalForm), Import/Export | List, View Detail, Reply | Import/Export |
| `/content-center/statistics` | Yes | Dashboard/Charts | Page Load | Chart Interactions |

**Module Stats**: 13 routes, 13 tested (100%), 23 operations, 18 covered (78%), 5 uncovered

---

### 1.8 System Management (xi tong guan li)

| Route | Visible? | Operations in Source | Covered | Uncovered |
|-------|----------|---------------------|---------|-----------|
| `/system/role` | Yes | List, Create, Edit, Delete, Assign Permissions | List, Create, Edit, Delete, Assign Permissions | - |
| `/system/role/create` | Hidden | Form Submit | Form Submit | - |
| `/system/role/:id/edit` | Hidden | Form Submit | Form Submit | - |
| `/system/role/:id/permissions` | Hidden | Permission Tree, Save | Permission Tree, Save | - |
| `/system/config/hospital-info` | Yes | Settings Form | Page Load | Save Hospital Info |
| `/system/config/wechat` | Yes | Settings Form | Page Load | Save Wechat Config |
| `/system/config/email-config` | Yes | Settings Form | Page Load | Save Email Config |
| `/system/config/image-config` | Yes | Settings Form, Save | Page Load, Save | - |
| `/system/config/email-templates` | Yes | List, Create, Edit, Delete | List, Create, Edit | Delete Email Template |
| `/system/config/email-templates/create` | Hidden | Form Submit | Form Submit | - |
| `/system/config/email-templates/:id/edit` | Hidden | Form Submit | - | Edit Email Template |
| `/system/config/email-recipients` | Yes | List, Create, Delete | List, Create, Delete | - |
| `/system/blacklist` | Yes | List, Add, Remove | List, Add, Remove | - |
| `/system/monitoring/log` | Yes | List, Filter | List, Filter | - |
| `/system/monitoring/notification-logs` | Yes | List | Page Load | - |
| `/system/monitoring/checkin-audit-logs` | Yes | List | Page Load | - |
| `/system/monitoring/online-users` | Yes | List, Kick User | List, Kick User | - |

**Module Stats**: 17 routes, 17 tested (100%), 28 operations, 21 covered (75%), 7 uncovered

---

### 1.9 Authentication & Utility

| Route | Visible? | Operations in Source | Covered | Uncovered |
|-------|----------|---------------------|---------|-----------|
| `/login` | Yes | Tab Switch (WeChat/Phone/Account), Login Form Submit | Page Load, Tab Verify, Account Login | Phone Login, WeChat Login |
| `/tenant-suspended` | Yes | Info Display | Page Load (via settings) | - |
| `/account/settings` | Hidden | Settings Form | Page Load | Save Settings |
| `/dashboard` | Yes | Stats Display | Page Load | Dashboard Card Interactions |
| `/404` | Wildcard | Error Display | 404 Page Test | - |

**Module Stats**: 5 routes, 5 tested (100%), 8 operations, 5 covered (63%), 3 uncovered

---

## 2. Uncovered Operations List

### P0 - Critical Business Operations (直接影响核心业务流程)

| # | Page Route | Operation Name | Interaction Type | Notes |
|---|-----------|---------------|-----------------|-------|
| 1 | `/medical-services/appointment/queue` | 叫号 (Call Patient) | click | Queue page has dedicated Call/Complete/Pass/Recall buttons - only tested via API-level |
| 2 | `/medical-services/appointment/queue` | 完成就诊 (Complete Visit) | click | Queue page operation |
| 3 | `/medical-services/appointment/queue` | 过号 (Pass Patient) | click | Queue page operation |
| 4 | `/medical-services/appointment/queue` | 重新叫号 (Recall) | click | Queue page operation |
| 5 | `/medical-services/appointment/queue` | 自动刷新开关 (Auto-refresh Switch) | switch | Queue page auto-polling toggle |
| 6 | `/medical-services/appointment/queue` | 门店/医生/日期筛选 (Queue Filters) | select | Queue page filter controls |
| 7 | `/medical-services/appointment/statistics` | 查询条件表单 (Statistics Query) | fill + click | Entire appointment statistics page untested |
| 8 | `/medical-services/appointment/list` | 取消预约带原因 (Cancel with Modal.confirm) | fill + click | Modal.confirm with reason textarea |
| 9 | `/medical-services/doctor/:id` | 诊金设置弹窗 (Consultation Fee Modal) | click + switch + delete | Doctor detail fee management |
| 10 | `/medical-services/doctor/:id` | 医生预约Tab取消/爽约 (Appointment Tab Actions) | click | Doctor detail appointment tab actions |

### P1 - Important Operations (影响管理效率)

| # | Page Route | Operation Name | Interaction Type | Notes |
|---|-----------|---------------|-----------------|-------|
| 11 | `/medical-services/patient/:id` | 添加就诊卡 (Add Medical Card) | modal + fill | ModalForm on patient detail |
| 12 | `/medical-services/patient/:id` | 编辑就诊卡 (Edit Medical Card) | modal + fill | ModalForm on patient detail |
| 13 | `/medical-services/patient/:id` | 删除就诊卡 (Delete Medical Card) | click + confirm | Popconfirm on patient detail |
| 14 | `/medical-services/medical-record` | 查看病历详情 (View Record Detail) | click | Medical record detail view |
| 15 | `/medical-services/consultation-fee/templates` | 诊费模板管理 (Fee Template CRUD) | click | Entire fee template page untested |
| 16 | `/medical-services/consultation-fee/types` | 删除诊费类型 (Delete Fee Type) | click + confirm | Missing delete operation |
| 17 | `/organization/medical-config/booking-rules` | 保存预约规则 (Save Booking Rules) | fill + click | Settings form save |
| 18 | `/organization/medical-config/booking-notice` | 保存预约须知 (Save Booking Notice) | fill + click + switch | Notice form with switch |
| 19 | `/organization/medical-config/shift-types` | 编辑班次类型 (Edit Shift Type) | fill + click | Edit form untested |
| 20 | `/organization/medical-config/shift-types` | 删除班次类型 (Delete Shift Type) | click + confirm | Missing delete operation |
| 21 | `/organization/medical-config/rule-sets` | 删除规则组 (Delete Rule Set) | click + confirm | Modal.confirm delete |
| 22 | `/organization/medical-config/rule-sets` | 复制规则 (Copy Rule Set) | click + modal | CopyRuleModal component |
| 23 | `/organization/medical-config/rule-sets` | 规则组预览 (Preview Drawer) | click + drawer | RuleSetPreviewDrawer component |
| 24 | `/organization/medical-config/rule-sets/:id/edit` | 编辑规则组 (Edit Rule Set) | fill + click | Edit form page |
| 25 | `/system/config/hospital-info` | 保存医院信息 (Save Hospital Info) | fill + click | Settings form save |
| 26 | `/system/config/wechat` | 保存微信配置 (Save Wechat Config) | fill + click | Settings form save |
| 27 | `/system/config/email-config` | 保存邮件配置 (Save Email Config) | fill + click | Settings form save |
| 28 | `/system/config/email-templates` | 删除邮件模板 (Delete Email Template) | click + confirm | Missing delete |
| 29 | `/system/config/email-templates/:id/edit` | 编辑邮件模板 (Edit Email Template) | fill + click | Edit form page |
| 30 | `/account/settings` | 保存个人设置 (Save Account Settings) | fill + click | Account settings form |
| 31 | `/login` | 手机号登录 (Phone Login Tab) | fill + click | Second login tab |
| 32 | `/login` | 微信登录 (WeChat Login Tab) | click | Third login tab (QR code) |

### P2 - Nice-to-Have Operations (完善性测试)

| # | Page Route | Operation Name | Interaction Type | Notes |
|---|-----------|---------------|-----------------|-------|
| 33 | `/medical-services/doctor/create` | 头像上传 (Avatar Upload) | upload | ImageUploadCard component |
| 34 | `/medical-services/doctor/create` | Banner上传 (Banner Upload) | upload | ImageUploadCard component |
| 35 | `/medical-services/doctor/create` | 执业证书上传 (Certificate Upload) | upload | ImageUploadCard component |
| 36 | `/organization/department/create` | 科室图标上传 (Icon Upload) | upload | ImageUploadCard component |
| 37 | `/organization/department/create` | 科室封面上传 (Cover Upload) | upload | ImageUploadCard component |
| 38 | `/organization/department/create` | 科室Banner上传 (Banner Upload) | upload | ImageUploadCard component |
| 39 | `/content-center/content/news/create` | 新闻封面图上传 (News Cover Upload) | upload | ImageUploadCard component |
| 40 | `/content-center/content/banner/create` | 轮播图上传 (Banner Image Upload) | upload | ImageUploadCard component |
| 41 | `/medical-services/schedule/rule` | 复制规则弹窗 (Copy Rule Modal) | click + modal | CopyRuleModal component |
| 42 | `/medical-services/schedule/rule` | 生成排班弹窗 (Generate Modal) | click + modal | GenerateScheduleModal component |
| 43 | `/medical-services/schedule/rule` | 历史日志弹窗 (History Logs) | click + modal | HistoryLogsModal component |
| 44 | `/medical-services/schedule/calendar` | 日详情抽屉 (Day Detail Drawer) | click + drawer | DayDetailDrawer component |
| 45 | `/medical-services/schedule/calendar` | 从日历创建预约 (Create from Calendar) | click + modal | CreateAppointmentModal |
| 46 | `/medical-services/schedule/gantt` | 甘特图详情抽屉 (Gantt Drawer) | click + drawer | Drawer detail view |
| 47 | `/medical-services/schedule/custom` | 删除自定义排班 (Delete Custom) | click + confirm | Popconfirm delete |
| 48 | `/medical-services/schedule/rest-day` | 删除休息日 (Delete Rest Day) | click + confirm | Popconfirm delete |
| 49 | `/medical-services/schedule/rest-day` | 批量删除休息日 (Batch Delete) | click + confirm | Batch operation |
| 50 | `/medical-services/schedule/suspension` | 取消停诊 (Cancel Suspension) | click + confirm | Popconfirm cancel |
| 51 | `/medical-services/schedule/list` | 从列表停诊/恢复 (Suspend/Resume) | click + confirm | modal.confirm operations |
| 52 | `/platform/tenant/:id` | 租户详情操作 (Detail Page Actions) | click | Tenant detail page full operations |
| 53 | `/platform/tenant/plans/create` | 创建订阅计划 (Create Plan) | fill + click | Plan form submit |
| 54 | `/platform/miniapp-platform/company` | 删除公司 (Delete Company) | click + confirm | Missing delete |
| 55 | `/platform/miniapp-platform/template` | 模板管理操作 (Template CRUD) | click | Template page operations |
| 56 | `/platform/miniapp-platform/build` | 构建触发/取消 (Build Trigger/Cancel) | click | Build management operations |
| 57 | `/platform/miniapp-platform/release` | 发布管理操作 (Release CRUD) | click | Release page operations |
| 58 | `/content-center/content/news` | 新闻状态切换 (News Status Switch) | click | Status toggle in list |
| 59 | `/content-center/content/notice` | 公告状态切换 (Notice Status Switch) | click | Status toggle in list |
| 60 | `/organization/medical-config/rule-sets` | 规则组导入导出 (Import/Export) | click | ImportExport component |
| 61 | `/organization/medical-config/rule-sets/:id/audit` | 变更历史查看 (Audit History) | click | Audit page |
| 62 | `/organization/medical-config/patient-card` | 就诊卡配置保存 (Save Card Config) | fill + click | Settings form |
| 63 | `/organization/staff` | 员工导入导出 (Staff Import/Export) | click | ImportExport component |
| 64 | `/content-center/feedback` | 反馈导入导出 (Feedback Import/Export) | click | ImportExport component |
| 65 | `/content-center/statistics` | 数据统计交互 (Analytics Interactions) | click | Chart interactions |
| 66 | `/medical-services/doctor/booking-setting` | 删除预约设置 (Delete Booking Setting) | click + confirm | Popconfirm delete |
| 67 | `/medical-services/doctor/list` | 医生推荐开关 (Recommend Switch in List) | switch | Separate from detail page |
| 68 | `/medical-services/doctor/list` | 更多操作下拉 (Dropdown Actions) | click | Dropdown menu for additional actions |
| 69 | `/system/config/email-templates/:id/edit` | 编辑邮件模板表单 (Edit Template Form) | fill + click | Edit form page |

---

## 3. Statistics

### Route Coverage

| Category | Count | Percentage |
|----------|-------|-----------|
| Total routes (with component) | 111 | 100% |
| Routes with any E2E test | 91 | 82% |
| Routes with smoke test only (page load) | 14 | 13% |
| Routes with zero test coverage | 6 | 5% |

**Routes with zero test coverage**:
1. `/medical-services/appointment/queue` (only API-level, not UI)
2. `/medical-services/appointment/statistics` (no dedicated test)
3. `/organization/medical-config/booking-fields` (only smoke)
4. `/organization/medical-config/patient-card` (only smoke)
5. `/organization/medical-config/rule-sets/:id/edit` (not tested)
6. `/system/config/email-templates/:id/edit` (not tested)

### Operation Coverage by Module

| Module | Total Ops | Covered | Uncovered | Coverage % |
|--------|-----------|---------|-----------|-----------|
| Platform Management | 35 | 24 | 11 | 69% |
| Doctor Management | 28 | 20 | 8 | 71% |
| Schedule Management | 38 | 26 | 12 | 68% |
| Appointment Management | 25 | 16 | 9 | 64% |
| Patient Management | 18 | 12 | 6 | 67% |
| Organization Structure | 40 | 26 | 14 | 65% |
| Content Center | 23 | 18 | 5 | 78% |
| System Management | 28 | 21 | 7 | 75% |
| Auth & Utility | 8 | 5 | 3 | 63% |
| **Total** | **233** | **156** | **77** | **67%** |

### Test Case Distribution by Category

| Test Category | Spec Files | Test Cases |
|--------------|-----------|-----------|
| Route Smoke Tests | 6 | ~56 |
| CRUD Operations | 4 | 42 |
| Form Validation | 3 | 30 |
| Error Handling | 2 | 21 |
| State Transitions | 3 | 25 |
| Permission Testing | 2 | 25 |
| Search & Filter | 1 | 18 |
| Schedule Operations | 2 | 22 |
| Batch Operations | 1 | 12 |
| Login Flow | 1 | 2 |
| Appointment State Flows | 1 | 9 |
| Async Validation | 1 | 12 |
| Miniapp Platform | 1 | 12 |
| Detail Pages | 1 | 7 |
| **Total** | **31** | **288** |

### Test Quality Observations

1. **Strong areas**: CRUD operations, form validation, permission boundaries, error handling
2. **Weak areas**: File uploads, settings form saves, queue page operations, calendar interactions, statistics pages
3. **Pattern**: Most tests use mock API responses via `page.route()` - good for isolation
4. **Skip rate**: Many tests have conditional `test.skip()` when elements aren't found - this can mask real failures

### Priority Recommendations

**Immediate (P0) - 10 operations**: Focus on the appointment queue page (operations 1-6) and appointment statistics (7). These are core business flows with zero UI-level E2E coverage.

**Short-term (P1) - 22 operations**: Patient detail card management, settings form saves, and missing delete operations across modules. These represent admin productivity gaps.

**Medium-term (P2) - 37 operations**: Image uploads, modal interactions, drawer details, and platform-specific operations (template/build/release management).
