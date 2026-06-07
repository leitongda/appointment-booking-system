# 患者自提交随访记录 (Patient Self-Report) 实现计划

## Context

随访模块已完成 P0~P2 基础功能（任务列表、记录列表、详情、就诊人切换）。下一步是允许患者主动上报健康数据（血压、血糖、症状），让医生能在管理端查看患者自测数据，提升随访的主动性和数据丰富度。

**设计决策：新建独立表 vs 扩展 follow_up_records**
- `follow_up_records.doctor_id` 是必填字段，患者自报告没有医生
- 自报告有结构化体征数据（血压/血糖），与医生的自由文本记录不同
- 需要独立的审核工作流（待审核→已审核）
- 结论：新建 `follow_up_self_reports` 表，不复用 records 表

## 数据模型

### follow_up_self_reports (患者自报告)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID PK | |
| tenant_id | FK tenants | 租户隔离 |
| task_id | FK follow_up_tasks, nullable | 关联随访任务（可选） |
| patient_id | FK patients, required | 报告人 |
| report_date | DateTime, default now | 测量/报告时间 |
| systolic_bp | Integer, nullable | 收缩压 (mmHg) |
| diastolic_bp | Integer, nullable | 舒张压 (mmHg) |
| blood_glucose | Numeric(5,1), nullable | 血糖 (mmol/L) |
| heart_rate | Integer, nullable | 心率 (次/分) |
| temperature | Numeric(4,1), nullable | 体温 (°C) |
| symptoms | Text, nullable | 症状描述（自由文本） |
| patient_condition | String(20), nullable | 自我感受: improved/stable/worsened |
| notes | Text, nullable | 备注 |
| attachments | Text, nullable | JSON array of URLs（照片等） |
| status | String(20), default "pending" | pending/reviewed |
| reviewed_at | DateTime, nullable | 审核时间 |
| reviewed_by | String, nullable | 审核医生 ID |
| deleted_at | DateTime, nullable | 软删除 |
| AuditMixin | | created_at, updated_at |

索引：(patient_id, report_date), (task_id)

## API 端点 `/follow-up-self-reports`

### 患者端
- `POST ""` — 创建自报告（从 token 解析 patient_id）
- `GET "/my"` — 获取当前患者的自报告列表（分页，按日期倒序）
- `GET "/{id}"` — 获取详情

### 医生/管理端
- `GET ""` — 列表（按患者/任务/状态/日期筛选）
- `GET "/task/{task_id}"` — 获取任务关联的自报告
- `PATCH "/{id}/review` — 标记已审核

## Schema 设计

```python
class SelfReportCreate(BaseModel):
    task_id: Optional[str] = None
    systolic_bp: Optional[int] = None       # 60~300
    diastolic_bp: Optional[int] = None      # 30~200
    blood_glucose: Optional[float] = None   # 1.0~50.0
    heart_rate: Optional[int] = None        # 30~300
    temperature: Optional[float] = None     # 30.0~45.0
    symptoms: Optional[str] = None
    patient_condition: Optional[str] = None # improved/stable/worsened
    notes: Optional[str] = None
    attachments: Optional[list[str]] = None
    report_date: Optional[datetime] = None

class SelfReportResponse(BaseModel):
    # 所有字段 camelCase alias
    id, tenant_id, task_id, patient_id, patient_name
    report_date, systolic_bp, diastolic_bp, blood_glucose
    heart_rate, temperature, symptoms, patient_condition
    notes, attachments, status, reviewed_at, reviewed_by
    created_at
```

## 前端页面

### H5 — 自报告表单 (`/follow-up/report`)
- NavBar + Card 布局
- 血压：两个数字 Input（收缩压 / 舒张压），同一行
- 血糖：数字 Input + 单位提示 (mmol/L)
- 心率：数字 Input
- 体温：数字 Input
- 症状：Selector（头痛/头晕/恶心/乏力/胸闷/失眠/其他）+ TextArea 自由描述
- 自我感受：Selector（好转/稳定/加重）
- 备注：TextArea
- 关联任务：若从任务详情进入，自动携带 task_id
- 使用 antd-mobile Form + Form.useForm() + manual validateFields

### H5 — 任务详情页新增自报告区域
- 在 task-detail.tsx 的关联记录下方增加"自报告数据"区域
- 展示该任务关联的 self-reports 列表（血压/血糖/症状摘要）
- 点击可查看详情

### H5 — 路由 + 入口
- 路由：`/follow-up/report` 和 `/follow-up/report/:taskId`
- 入口：任务详情页"提交自报告"按钮

### 小程序 — 自报告表单
- 使用 Taro + NutUI + 手动 state 管理（Pattern A）
- Taro Input/Textarea/Picker
- useProtectedPage + LoginPopup

### 小程序 — 路由 + 入口
- app.config.ts 注册页面
- 任务详情页添加"提交自报告"按钮

## API 客户端

在 `packages/api/src/modules/follow-up.ts` 新增：
```typescript
selfReportApi: {
  create: (data) => POST /follow-up/self-reports
  getMyList: (params?) => GET /follow-up/self-reports/my
  getDetail: (id) => GET /follow-up/self-reports/{id}
  getList: (params?) => GET /follow-up/self-reports (管理端)
  getByTask: (taskId) => GET /follow-up/self-reports/task/{taskId}
  review: (id) => PATCH /follow-up/self-reports/{id}/review
}
```

## 文件清单

### 后端新建
| 文件 | 说明 |
|------|------|
| `app/models/follow_up_self_report.py` | SelfReport 模型 |
| `migrations/versions/117_create_follow_up_self_reports.py` | 建表迁移 |

### 后端修改
| 文件 | 修改 |
|------|------|
| `app/models/__init__.py` | 添加 SelfReport import |
| `app/schemas/follow_up.py` | 添加 SelfReportCreate/Response Schema |
| `app/modules/follow_up/service.py` | 添加 SelfReportService |
| `app/modules/follow_up/router.py` | 添加 6 个端点 |
| `app/api/v1/__init__.py` | 已注册 follow_up router，无需改 |

### 前端修改
| 文件 | 修改 |
|------|------|
| `packages/api/src/modules/follow-up.ts` | 添加 selfReportApi |
| `apps/patient-h5/src/pages/follow-up/report.tsx` | 新建：自报告表单 |
| `apps/patient-h5/src/pages/follow-up/task-detail.tsx` | 添加自报告区域 + 入口按钮 |
| `apps/patient-h5/.umirc.ts` | 添加路由 |
| `apps/patient-miniapp/src/packageProfile/pages/follow-up/report.tsx` | 新建：自报告表单 |
| `apps/patient-miniapp/src/packageProfile/pages/follow-up/detail.tsx` | 添加自报告区域 + 入口按钮 |
| `apps/patient-miniapp/src/app.config.ts` | 注册页面 |

## 实现顺序

1. 后端 Model + Migration
2. Schema + Service
3. Router (6 个端点)
4. API 客户端
5. H5 自报告表单页
6. H5 任务详情页集成
7. H5 路由
8. 小程序自报告表单页
9. 小程序任务详情页集成
10. 小程序路由

## 验证方式

1. 后端: `cd apps/server && python -m uvicorn app.main:app --reload`
2. Swagger: 创建自报告 → 列表查询 → 审核
3. H5: 任务详情 → 提交自报告 → 查看列表
4. 小程序: 同上流程
