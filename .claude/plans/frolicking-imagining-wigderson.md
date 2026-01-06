# 规则系统增强功能实现计划

## 概述

本计划包含三个功能的实现：规则预览、规则导入/导出、签到审计日志完善。

---

## 功能1：规则预览功能

### 实现方案
在规则组表单页面添加预览功能，通过 Modal 展示规则效果。

### 关键文件
- **新建** `/apps/admin/src/pages/system/components/RulePreviewModal.tsx` - 预览Modal组件
- **修改** `/apps/admin/src/pages/system/rule-set-form.tsx` - 集成预览按钮

### 实现步骤

#### 步骤1：创建预览Modal组件
```tsx
// RulePreviewModal.tsx
- 表单字段：班次类型、排班日期、开始时间、结束时间、当前时间(可选)
- 调用 ruleSetApi.preview() 获取预览结果
- 展示三个窗口结果：预约窗口、签到窗口、取消窗口
- 使用 Tag 显示允许/不允许状态
- 使用 Statistic 展示开放/截止时间
```

#### 步骤2：集成到规则组表单
```tsx
// rule-set-form.tsx
- 添加状态：const [previewModalOpen, setPreviewModalOpen] = useState(false);
- 在 FooterToolbar 添加"预览规则效果"按钮
- 渲染 RulePreviewModal 组件
```

### API
- 后端已实现：`POST /api/v1/rule-sets/preview`
- 前端已封装：`ruleSetApi.preview(data)`

---

## 功能2：规则导入/导出

### 实现方案
参考医生模块，为规则组添加批量导入导出功能。

### 关键文件
- **新建** `/apps/server/app/api/v1/rule_set_import_export.py` - 导入导出路由
- **新建** `/apps/server/app/services/rule_set_import_service.py` - 导入服务
- **修改** `/apps/server/app/main.py` - 注册路由
- **修改** `/packages/api/src/modules/data.ts` - 添加URL生成函数
- **修改** `/apps/admin/src/pages/system/rule-sets.tsx` - 集成ImportExport组件

### Excel结构（5个工作表）
1. **规则组** - 基础信息（名称、优先级、班次类型、时间来源等）
2. **时间窗** - 各动作窗口配置
3. **预约策略** - 预约相关策略
4. **签到策略** - 签到相关策略
5. **容量策略** - 容量相关策略

### 实现步骤

#### 后端
1. 创建 `rule_set_import_export.py`，添加三个路由：
   - `GET /export/rule-sets` - 导出规则组
   - `GET /template/rule-sets` - 下载导入模板
   - `POST /import/rule-sets` - 导入规则组

2. 创建 `rule_set_import_service.py`，实现：
   - `parse_excel()` - 解析多工作表Excel
   - `import_rule_sets()` - 导入逻辑
   - 数据验证和错误收集

3. 在 `main.py` 注册路由：
   ```python
   app.include_router(rule_set_import_export.router, prefix="/api/v1", tags=["rule-sets"])
   ```

#### 前端
4. 在 `data.ts` 添加URL函数：
   ```typescript
   getExportRuleSetsUrl: (params?) => string
   getImportRuleSetsUrl: () => string
   getRuleSetTemplateUrl: () => string
   ```

5. 在 `rule-sets.tsx` 集成ImportExport组件：
   ```tsx
   <ImportExport
     moduleName="规则组"
     exportUrl={dataApi.getExportRuleSetsUrl()}
     importUrl={dataApi.getImportRuleSetsUrl()}
     templateUrl={dataApi.getRuleSetTemplateUrl()}
     onImportSuccess={() => actionRef.current?.reload()}
   />
   ```

### 可复用组件
- 后端：`ExcelExportService`, `ExcelImportService`
- 前端：`<ImportExport />` 组件

---

## 功能3：签到审计日志

### 实现方案
在签到时记录详细审计日志，包括成功和失败的签到。

### 关键文件
- **修改** `/apps/server/app/services/appointment_service.py` - 添加审计日志记录
- **修改** `/apps/server/app/api/v1/appointments.py` - 添加设备信息参数
- **新建** `/apps/server/app/api/v1/audit_logs.py` - 审计日志查询API
- **新建** `/apps/admin/src/pages/system/checkin-audit-logs.tsx` - 日志列表页
- **新建** `/packages/api/src/modules/audit-log.ts` - 前端API模块

### 数据库表
- `appointment_checkins` - 已定义，包含完整字段

### 实现步骤

#### 后端

1. **修改签到服务** (`appointment_service.py`)

   ```python
   async def sign_in(
       self,
       appointment_id: str,
       checkin_method: str = 'MANUAL',
       device_info: Optional[str] = None,
       location_info: Optional[str] = None,
       operator_id: Optional[str] = None,
       operator_type: Optional[str] = None
   ):
       # ... 原有验证逻辑 ...

       try:
           # 验证通过后记录成功日志
           await self._create_checkin_log(
               appointment_id=appointment.id,
               checkin_method=checkin_method,
               device_info=device_info,
               location_info=location_info,
               operator_id=operator_id,
               operator_type=operator_type,
               status='SUCCESS',
               fail_reason=None
           )
       except Exception as e:
           # 失败时记录失败日志
           await self._create_checkin_log(
               appointment_id=appointment.id,
               checkin_method=checkin_method,
               device_info=device_info,
               location_info=location_info,
               operator_id=operator_id,
               operator_type=operator_type,
               status='FAILED',
               fail_reason=str(e)
           )
           raise
   ```

2. **添加私有方法** (`appointment_service.py`)

   ```python
   async def _create_checkin_log(self, ...):
       """创建签到审计日志"""
       checkin_log = AppointmentCheckin(...)
       self.db.add(checkin_log)
       await self.db.flush()
   ```

3. **修改签到API** (`appointments.py`)

   ```python
   @router.post("/{appointment_id}/sign-in")
   async def sign_in_appointment(
       appointment_id: str,
       checkin_method: Optional[str] = Body(None),
       device_info: Optional[str] = Body(None),
       location_info: Optional[str] = Body(None),
       ...
   ):
   ```

4. **创建审计日志查询API** (`audit_logs.py`)

   ```python
   @router.get("/checkin-logs")
   async def get_checkin_logs(
       appointment_id: Optional[str] = None,
       patient_id: Optional[str] = None,
       status: Optional[str] = None,
       ...
   ):
   ```

#### 前端

5. **创建审计日志API模块** (`audit-log.ts`)

   ```typescript
   export const auditLogApi = {
     async getCheckinLogs(params?): Promise<{data, total}>
   }
   ```

6. **创建审计日志页面** (`checkin-audit-logs.tsx`)

   - ProTable展示日志列表
   - 支持按状态、方式、时间筛选
   - 显示患者姓名、电话、设备信息等

7. **配置路由** (`config/routes.ts`)

   ```typescript
   { path: '/system/checkin-audit-logs', name: '签到审计日志', component: './system/checkin-audit-logs' }
   ```

### 记录的信息

#### 成功签到
- `appointment_id`, `checkin_time`
- `checkin_method`: QR_CODE/MANUAL/PHONE
- `device_info`: 用户代理、设备类型
- `location_info`: IP地址、地理位置
- `operator_id`, `operator_type`: USER/ADMIN/DOCTOR
- `status`: SUCCESS

#### 失败签到
- 同上，但 `status`: FAILED
- `fail_reason`: 失败原因

---

## 关键文件清单

### 后端
- `/apps/server/app/services/appointment_service.py` - 签到服务（添加审计日志）
- `/apps/server/app/api/v1/appointments.py` - 签到API（添加参数）
- `/apps/server/app/api/v1/rule_set_import_export.py` - **新建**规则组导入导出
- `/apps/server/app/services/rule_set_import_service.py` - **新建**导入服务
- `/apps/server/app/api/v1/audit_logs.py` - **新建**审计日志查询
- `/apps/server/app/main.py` - 注册新路由

### 前端
- `/apps/admin/src/pages/system/components/RulePreviewModal.tsx` - **新建**预览Modal
- `/apps/admin/src/pages/system/rule-set-form.tsx` - 集成预览功能
- `/apps/admin/src/pages/system/rule-sets.tsx` - 集成导入导出
- `/apps/admin/src/pages/system/checkin-audit-logs.tsx` - **新建**审计日志页面
- `/packages/api/src/modules/data.ts` - 添加规则组URL
- `/packages/api/src/modules/audit-log.ts` - **新建**审计日志API
- `/apps/admin/config/routes.ts` - 添加审计日志路由

---

## 技术要点

### 功能依赖
- 规则预览：复用现有API，无需后端修改
- 导入导出：复用 `ExcelExportService` 和 `ImportExport` 组件
- 审计日志：数据库表已存在，只需添加业务逻辑

### 潜在难点
1. **导入导出**：多工作表Excel的关联数据处理
2. **审计日志**：确保失败时也记录日志（使用try-catch）

### 解决方案
- 使用"规则名称"作为关联键
- 在事务中同时记录日志和更新状态
- 提供详细的导入模板和示例数据

---

## 实施顺序建议

1. **功能1**（规则预览）- 独立，无依赖，约2小时
2. **功能3**（审计日志）- 核心功能，约3小时
3. **功能2**（导入导出）- 复杂度最高，约4小时

**总计约9小时**
