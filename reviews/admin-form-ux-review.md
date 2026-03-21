# Admin 端表单用户体验评审画布

**项目**: appointment-booking-system
**日期**: 2026-03-17
**评审目标**: admin 端新增/编辑表单的字段划分、Tab 分块、布局优化
**协作模式**: 领域主导 (Designer Lead)

---

## Round 1 — 事实收集

### 表单清单与复杂度

| 表单名称 | 字段总数 | 复杂度 | 是否需要Tab | 当前布局 |
|---------|---------|--------|------------|---------|
| 医生表单 | 28 | 高 | 是 | 5个Card区块 |
| 科室表单 | 20 | 中 | 是 | 5个Card区块 |
| 门店表单 | 13 | 中 | 否 | 6个Card区块 |
| 排班规则表单 | 11+动态 | 中 | 否 | 左右分栏+3个Card |
| 自定义排班表单 | 8+动态 | 低 | 否 | 2个Card区块 |
| 医生预约设置表单 | 5 | 低 | 否 | 单表单 |
| 用户表单 | 7 | 低 | 否 | 3个Card区块 |
| 角色表单 | 4 | 低 | 否 | 单Card |
| 班次类型表单 | 4 | 低 | 否 | 2个Card区块 |
| 邮件模板表单 | 6 | 低 | 否 | 2个Card区块 |
| 规则组表单 | 50+ | 极高 | **已实现** | 6个Tab |
| 新闻表单 | 6 | 低 | 否 | 5个Card区块 |
| 公告表单 | 4 | 低 | 否 | 3个Card区块 |
| 轮播图表单 | 5 | 低 | 否 | 3个Card区块 |

### 新增 vs 编辑字段差异

| 表单 | 仅新增显示 | 仅编辑显示/禁用 |
|-----|-----------|----------------|
| 医生表单 | password, confirmPassword | 账号字段禁用 |
| 科室表单 | - | 父级选择排除自己 |
| 门店表单 | - | 编码标记手动编辑后不自动生成 |
| 用户表单 | password, confirmPassword | username禁用 |
| 角色表单 | - | code禁用 |
| 班次类型表单 | - | code禁用 |
| 邮件模板表单 | - | code禁用 |
| 医生预约设置 | - | storeId/doctorId禁用 |

---

## Round 2 — 交叉辩论

### Designer Lead 交叉评审

#### 1. Tab 分块方案

**医生表单（建议4个Tab）**

| Tab | 名称 | 字段列表 | 字段数 |
|-----|------|---------|--------|
| Tab1 | 核心信息（新增必填） | name, gender, storeId, username, password, avatar, banner, departmentId, title, yearsOfExperience, phone | 11 |
| Tab2 | 资质信息 | education, graduateSchool, licenseNumber, licenseImage, honors | 5 |
| Tab3 | 坐诊与展示 | scheduleDesc, maxDailyAppointments, onlineConsultEnabled, onlineConsultFee, pageStyle, promoVideo, tags, specialty, introduction | 9 |
| Tab4 | 系统设置 | sortOrder, isRecommended, status | 3 |

**科室表单（建议3个Tab）**

| Tab | 名称 | 字段列表 | 字段数 |
|-----|------|---------|--------|
| Tab1 | 基本信息 | storeId, parentId, name, tag, sortOrder, description | 6 |
| Tab2 | 图片与详情 | icon, bannerImage, introImages, introContent, features, appointmentNotice | 6 |
| Tab3 | 联系与设置 | phone, location, workingHours, status, isFinal, isRecommended, isHot, enableBanner, enableIntro | 9 |

**门店表单：保持当前Card布局（13字段，6个Card已足够清晰）**

#### 2. 新增模式简化

| 表单 | 新增必填 | 延后填写 | 简化效果 |
|-----|---------|---------|---------|
| 医生 | name, gender, storeId, username, departmentId | 其余23字段 | 核心仅5字段 |
| 科室 | storeId, name | 其余18字段 | 核心仅2字段 |
| 门店 | name, address | 其余11字段 | 核心仅2字段 |
| 用户 | username, roleId | 其余6字段 | 核心仅2字段 |

#### 3. 可复用的 UX 模式

| 模式 | 适用场景 | 推荐应用 |
|-----|---------|---------|
| Tab 完成度指示器 | 多Tab表单 | 医生、科室 |
| 核心配置完成度卡片 | 高复杂度表单 | 医生 |
| 首次访问引导卡片 | 高复杂度表单 | 医生 |

### Critic 质询

#### 质询1: Tab 分块的实际效用与适用性

- **质疑点**: 医生表单28字段与规则组表单50+字段的"复杂度"是否具有可比性？规则组的复杂度体现在"逻辑配置"（需要反复调试预览），而医生表单的复杂度可能只是"字段多"（一次性填写）。
- **潜在风险**: 如果医生表单大多是必填项，Tab 分块反而增加切换成本
- **建议验证方式**: 分析医生表单字段的必填/选填比例

#### 质询2: "新增简化"策略的数据完整性风险

- **质疑点**: "延后填写"假设用户会在后续编辑中完善信息，但实际场景中用户是否真的会回来填写？
- **潜在风险**: 数据质量下降，大量"半成品"记录
- **建议验证方式**: 统计现有医生数据的字段填充率，明确"最小可用实体"的业务定义

#### 质询3: 实现成本与收益的不对称

- **质疑点**: 医生/科室表单当前是否有明确的用户反馈表明"表单太复杂"？
- **潜在风险**: 投入大量开发资源，但用户体验提升有限
- **建议验证方式**: 收集现有用户对医生/科室表单的具体反馈

---

## Round 3 — 共识与行动计划

### Team Lead 裁决

#### Critic 质询回应

| 质询 | 裁决 | 理由 |
|-----|------|------|
| Tab效用质疑 | **部分采纳** | 医生表单必填项集中在Tab1（5个），Tab分块有实际价值。但暂不引入"引导卡片"等复杂模式，先验证Tab效果 |
| 数据完整性风险 | **采纳** | 新增模式不隐藏字段，仅通过Tab分组和完成度指示器引导。保持所有字段可见 |
| 成本收益不对称 | **采纳** | 优先级调整为：先优化医生表单，验证效果后再推广到科室 |

### 共识项

1. **医生表单需要优化**：28字段，信息密度高，用户体验有改进空间
2. **Tab 分块是合理方案**：规则组表单已验证可行，模式可复用
3. **新增/编辑差异化**：密码字段、code类字段的处理逻辑已清晰
4. **参考现有模式**：规则组表单的 Tab 实现、完成度追踪可作为模板

### 分歧项

| 分歧 | 最终决策 | 理由 |
|-----|---------|------|
| Tab 分块粒度 | 4个Tab（非5个） | 合并"坐诊设置"与"展示设置"，减少Tab数量 |
| 科室表单优先级 | P1（非P0） | 先验证医生表单效果，再推广 |
| 引导卡片 | 暂不实现 | 成本较高，先观察Tab效果 |

### 行动计划

#### P0 — 立即执行（本轮迭代）

| 序号 | 任务 | 表单 | 实现内容 | 前端成本 | 后端成本 |
|-----|------|------|---------|---------|---------|
| 1 | Tab布局重构 | 医生表单 | 5个Card → 4个Tab（核心信息、资质信息、坐诊与展示、系统设置） | 8h | 0h |
| 2 | Tab完成度指示器 | 医生表单 | Tab label显示 x/y 格式 | 2h | 0h |
| 3 | 核心配置完成度卡片 | 医生表单 | 顶部进度条显示必填项完成情况 | 2h | 0h |

**P0 总成本：12h（前端）**

#### P1 — 本轮迭代（视P0效果）

| 序号 | 任务 | 表单 | 实现内容 | 前端成本 | 后端成本 |
|-----|------|------|---------|---------|---------|
| 4 | Tab布局重构 | 科室表单 | 5个Card → 3个Tab | 6h | 0h |
| 5 | Tab完成度指示器 | 科室表单 | Tab label显示 x/y 格式 | 1h | 0h |
| 6 | 开关字段优化 | 科室表单 | 增加tooltip说明，按业务逻辑分组 | 2h | 0h |

**P1 总成本：9h（前端）**

#### P2 — 下周期

| 序号 | 任务 | 表单 | 实现内容 | 前端成本 |
|-----|------|------|---------|---------|
| 7 | 首次访问引导卡片 | 医生表单 | 3步骤引导 | 4h |
| 8 | 字段填充率统计 | 后端 | 分析现有数据的字段填充情况 | - | 3h |

**P2 总成本：7h（前端）+ 3h（后端）**

#### 待定 — 需用户确认

| 任务 | 需确认问题 |
|-----|----------|
| 引导卡片设计 | 是否需要预设模板功能？ |
| 数据完整性策略 | 新增时是否允许跳过非必填Tab？ |

### 技术实现参考

**复用规则组表单的 Tab 模式：**

```tsx
// 文件: apps/admin/src/pages/doctor/form.tsx
// 参考: apps/admin/src/pages/system/rule-set-form.tsx

// Tab 完成度指示器
const getTabLabel = (key: string, baseLabel: string): React.ReactNode => {
  const tabFields = REQUIRED_FIELDS.filter(f => f.tab === key);
  const completed = tabFields.filter(({ field }) => {
    const value = formValues[field];
    return value !== undefined && value !== null && value !== '';
  }).length;

  if (completed < tabFields.length) {
    return <Space><span>{baseLabel}</span><Tag color="orange">{completed}/{tabFields.length}</Tag></Space>;
  }
  return <Space><span>{baseLabel}</span><CheckCircleOutlined style={{ color: '#52c41a' }} /></Space>;
};

// Tab 结构
const generateTabItems = () => [
  { key: 'basic', label: getTabLabel('basic', '核心信息'), children: <BasicInfoTab /> },
  { key: 'qualification', label: getTabLabel('qualification', '资质信息'), children: <QualificationTab /> },
  { key: 'display', label: '坐诊与展示', children: <DisplayTab /> },
  { key: 'settings', label: '系统设置', children: <SettingsTab /> },
];
```

### 预期效果

| 指标 | 当前 | 优化后 | 提升 |
|-----|------|-------|------|
| 医生表单新增必填项 | 分散在5个Card | 集中在Tab1 | 认知负担降低 |
| 表单填写时间 | - | - | 预计减少30% |
| 必填项漏填率 | - | - | 预计降低（完成度指示器） |

---

## 附录：各表单字段详情

### 医生表单字段划分

| Tab | 字段 | 必填 | 新增/编辑差异 |
|-----|------|------|--------------|
| **核心信息** | name | 是 | - |
| | gender | 是 | - |
| | storeId | 是 | - |
| | username | 是 | 编辑禁用 |
| | password | 新增必填 | 仅新增显示 |
| | departmentId | 是 | - |
| | avatar | 否 | - |
| | banner | 否 | - |
| | title | 否 | - |
| | yearsOfExperience | 否 | - |
| | phone | 否 | - |
| **资质信息** | education | 否 | - |
| | graduateSchool | 否 | - |
| | licenseNumber | 否 | - |
| | licenseImage | 否 | - |
| | honors | 否 | - |
| **坐诊与展示** | scheduleDesc | 否 | - |
| | maxDailyAppointments | 否 | - |
| | onlineConsultEnabled | 否 | - |
| | onlineConsultFee | 条件必填 | 依赖onlineConsultEnabled |
| | pageStyle | 否 | - |
| | promoVideo | 否 | - |
| | tags | 否 | - |
| | specialty | 否 | - |
| | introduction | 否 | - |
| **系统设置** | sortOrder | 否 | - |
| | isRecommended | 否 | - |
| | status | 否 | - |

### 科室表单字段划分

| Tab | 字段 | 必填 |
|-----|------|------|
| **基本信息** | storeId | 是 |
| | parentId | 否 |
| | name | 是 |
| | tag | 否 |
| | sortOrder | 否 |
| | description | 否 |
| **图片与详情** | icon | 否 |
| | bannerImage | 否 |
| | introImages | 否 |
| | introContent | 否 |
| | features | 否 |
| | appointmentNotice | 否 |
| **联系与设置** | phone | 否 |
| | location | 否 |
| | workingHours | 否 |
| | status | 否 |
| | isFinal | 否 |
| | isRecommended | 否 |
| | isHot | 否 |
| | enableBanner | 否 |
| | enableIntro | 否 |
