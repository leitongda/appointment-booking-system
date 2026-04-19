# 跨模板对比总览

## Shell 变体分配矩阵

| 页面 | modern-general | elderly-tcm | premium-specialty | family-pediatrics | womens-health |
|------|---------------|-------------|-------------------|-------------------|---------------|
| 首页 | standard | home-elderly | home-premium | home-family | home-womens |
| 科室 | sidebar | dept-large-grid | dept-minimal | dept-colorful | dept-soft |
| 医生列表 | cards | doctor-large-cards | doctor-showcase | cards | doctor-cards-soft |
| 医生详情 | standard | doctor-detail-elderly | doctor-detail-premium | doctor-detail-family | doctor-detail-womens |
| 预约列表 | tabs | appoint-simple | tabs | tabs | tabs |
| 个人中心 | standard | profile-elderly | profile-premium | profile-family | profile-womens |

## 导航结构对比

| 模板 | Tab 数 | Tab 名称 | 导航高度 |
|------|--------|---------|---------|
| 现代综合 | 3 | 首页/预约/我的 | 100px |
| 长辈友好 | 3 | 首页/挂号/我的 | 120px |
| 高端专科 | **4** | 首页/专家/预约/我的 | 100px |
| 亲子儿科 | 3 | 首页/预约/成长 | 100px |
| 女性健康 | 3 | 首页/预约/我的 | 100px |

## 首页模块对比

| 模块 | 现代综合 | 长辈友好 | 高端专科 | 亲子儿科 | 女性健康 |
|------|---------|---------|---------|---------|---------|
| Banner | 1 | - | 1 (品牌级) | 2 | 1 (柔和) |
| 快捷菜单 | 4列 | **2列大按钮** | 4列 | **3x2** | 4列 |
| 就诊人卡片 | 3 | - | - | - | - |
| 家庭切换器 | - | - | - | **1** | - |
| 明星专家 | - | - | **2** | - | - |
| 特色服务 | - | - | **3** | - | **2** |
| 通知公告 | - | 2 | - | - | - |
| 最近医生 | - | 3 | - | - | - |
| 常见服务 | - | - | - | **4** | - |
| 健康提醒 | - | - | - | - | **4** |
| 推荐医生 | 4 | - | - | 5 | 5 |
| 品牌故事 | - | - | **5** | - | - |
| **模块总数** | 4 | 3 | 5 | 5 | 5 |

## 设计 Token 差异对比

| Token | 现代综合 | 长辈友好 | 高端专科 | 亲子儿科 | 女性健康 |
|-------|---------|---------|---------|---------|---------|
| 主色 | `#4D7CB8` 蓝 | `#8B6F47` 棕 | `#8B7355` 金棕 | `#5B9BD5` 天蓝 | `#C4908D` 玫瑰 |
| body字号 | 30px | **36px** | 28px | 30px | 30px |
| 圆角中 | 16px | 24px | 12px | 20px | 20px |
| 间距倍率 | 1.0 | **1.5** | 1.1 | 1.05 | 1.0 |
| 图标风格 | outlined | **bold** | thin | **filled** | thin |
| TabBar图标 | filled | filled | outlined | filled | outlined |
| 装饰风格 | none | traditional | minimal | playful | floral |

## 文案语气对比

| 维度 | 现代综合 | 长辈友好 | 高端专科 | 亲子儿科 | 女性健康 |
|------|---------|---------|---------|---------|---------|
| 预约按钮 | 预约挂号 | 挂号 | 预约咨询 | 预约挂号 | 预约挂号 |
| 就诊人称呼 | 就诊人 | 就诊人 | 就诊人 | **宝宝** | 就诊人 |
| 预约成功 | 正式指引 | 口语引导 | 尊享确认 | 宝宝关怀 | 关怀提醒 |
| 语气 | 专业正式 | 亲切口语 | 克制精致 | 温暖鼓励 | 温暖关怀 |
| 问候语 | 无 | 无 | 无 | 无 | **有** |
| 确认弹窗 | 无 | **有** | 无 | 无 | 无 |

## 约束条件对比

| 约束 | 现代综合 | 长辈友好 | 高端专科 | 亲子儿科 | 女性健康 |
|------|---------|---------|---------|---------|---------|
| 锁定页面 | 4 | 4 | 4 | 4 | 4 |
| 强制长辈模式 | false | **true** | false | false | false |
| 操作前确认 | false | **true** | false | false | false |

## Shell 复用分析

| Shell | 使用的模板 | 复用次数 |
|-------|----------|---------|
| DoctorCards | modern-general, family-pediatrics | 2 |
| AppointTabs | modern-general, premium-specialty, family-pediatrics, womens-health | 4 |
| 其余 Shell | 各模板独立 | 1 |

**结论**: 医生列表和预约列表有较高复用度，首页/科室/医生详情/个人中心每套模板几乎都是独立 Shell。
