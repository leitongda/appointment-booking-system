# 多风格小程序模板系统使用指南

## 概述

多风格小程序模板系统是为 SaaS 医院预约挂号系统设计的一站式小程序实例生成方案。系统预置 5 套风格各异的视觉模板，覆盖主流医疗机构的品牌定位需求。租户可通过管理后台选择模板、配置基础信息后一键生成专属小程序实例。

### 核心特性

- **5 套预置模板**: 现代综合、高端专科、亲子儿科、女性健康、长辈友好/中医康养
- **零代码生成**: 选择模板 → 配置 AppID → 选择门店 → 构建发布
- **业务内核共享**: 所有模板共享同一套业务逻辑（预约、支付、签到等），仅视觉层差异
- **版本绑定**: 每个实例记录模板代码和版本，支持独立升级
- **可扩展架构**: 预留第二阶段"模板 + 配置混合"能力，支持首页模块排序、TabBar 自定义等

---

## 5 套模板速查表

| 模板名称 | 代码 | 主色调 | Tab 数量 | 适用场景 |
|---------|------|--------|---------|---------|
| 现代综合医疗 | `modern-general` | 医疗蓝 #1890FF | 4 | 综合医院、社区卫生中心 |
| 高端专科门诊 | `premium-specialty` | 黑金奢华 #262626 | 4 | 高端诊所、私立专科医院 |
| 亲子儿科 | `pediatric` | 温暖橙 #FFA940 | 5 | 儿童医院、儿科诊所 |
| 女性健康 | `womens-health` | 柔粉渐变 #FF69B4 | 5 | 妇科、月子中心、医美 |
| 长辈友好/中医康养 | `elderly-tcm` | 大字无障碍 #6B4C3A | 3 | 中医馆、康养中心、老年医院 |

---

## 快速开始

### 开发模式（本地调试）

```bash
# 进入实例项目目录
cd apps/miniapp-instance

# 交互式选择模板开发
pnpm dev:template

# 直接指定模板开发
TARO_APP_TEMPLATE_CODE=elderly-tcm pnpm dev:weapp

# 指定模板并打开开发者工具
TARO_APP_TEMPLATE_CODE=womens-health pnpm dev:weapp --open
```

### 生产构建

```bash
# 构建单套模板
node scripts/build-template.mjs --template modern-general

# 构建全部 5 套模板
node scripts/build-all.mjs

# 清除缓存后构建（解决样式问题）
rm -rf .taro node_modules/.cache
node scripts/build-template.mjs --template premium-specialty
```

### CI/CD 构建

```bash
# CI 环境下的严格构建脚本（无交互，失败即退出）
node scripts/ci-build-all.mjs
```

---

## 创建小程序实例流程

### 管理后台操作步骤

1. **进入小程序实例管理**
   - 路径: 系统管理 → 小程序平台 → 实例管理

2. **创建新实例**
   - 点击"新建实例"按钮
   - 填写基础信息:
     - 实例名称（如"北京协和医院小程序"）
     - 实例描述
     - 租户（自动绑定当前租户）

3. **选择模板**
   - 从 5 套预置模板中选择 1 套
   - 预览模板效果（系统提供截图/演示）
   - 确认模板版本

4. **配置微信信息**
   - 填写微信 AppID
   - 填写微信 AppSecret（加密存储）
   - 上传小程序图标

5. **绑定门店**
   - 从当前租户的门店列表中选择需接入的门店
   - 支持多选

6. **构建发布**
   - 点击"立即构建"
   - 系统后台执行:
     - 按模板代码装配页面壳层
     - 注入业务逻辑容器
     - 打包模板资源包
   - 构建完成后显示:
     - 实例版本号
     - 模板版本号
     - 生成时间
     - 下载二维码

7. **提交微信审核**
   - 下载小程序代码包
   - 登录微信小程序后台上传
   - 提交审核

---

## 模板配置结构说明

每个模板包含以下配置维度:

### 1. navSchema（导航结构）

定义底部 TabBar 的标签页数量、顺序和图标。

```typescript
{
  "tabs": [
    { "key": "home", "title": "首页", "iconPath": "assets/tabbar/home.png" },
    { "key": "appointment", "title": "预约", "iconPath": "assets/tabbar/appointment.png" },
    { "key": "profile", "title": "我的", "iconPath": "assets/tabbar/profile.png" }
  ]
}
```

### 2. homeSchema（首页模块树）

定义首页展示的功能模块及排序。

```typescript
{
  "modules": [
    { "type": "banner", "order": 1 },
    { "type": "quick-actions", "order": 2 },
    { "type": "recommended-departments", "order": 3 },
    { "type": "recommended-doctors", "order": 4 }
  ]
}
```

### 3. pageShells（页面壳层）

定义各页面的视觉壳层变体代码。

```typescript
{
  "home": "HomeShellBlue",
  "doctor-detail": "DoctorShellCard",
  "department-list": "DepartmentShellGrid"
}
```

### 4. designTokens（视觉 Token）

定义色彩、圆角、阴影等设计基础变量。

```typescript
{
  "colors": {
    "primary": "#1890FF",
    "secondary": "#52C41A",
    "background": "#F5F5F5"
  },
  "borderRadius": {
    "small": "4px",
    "medium": "8px",
    "large": "16px"
  }
}
```

### 5. tone（文案语气）

定义提示语、引导语的语气风格。

```typescript
{
  "style": "professional",  // professional / friendly / warm
  "greeting": "您好，欢迎使用预约服务",
  "confirmations": {
    "booking": "确认预约该医生吗？",
    "cancel": "取消预约后号源将释放"
  }
}
```

---

## 自定义指南（第二阶段预告）

第一阶段提供 5 套固定模板，第二阶段将开放"模板 + 配置混合"能力:

### 计划支持的自定义维度

1. **首页模块排序**: 拖拽调整 Banner、快捷入口、推荐科室等模块顺序
2. **TabBar 自定义**: 增删 Tab 标签，支持跳转 H5 页面
3. **卡片样式切换**: 单列/双列/瀑布流，带/不带阴影
4. **主色调调整**: 在模板预设色系范围内微调
5. **文案自定义**: 系统提示语、引导语支持租户级覆盖

---

## 常见问题

### 构建产物为空或页面无样式？

**症状**: 执行 `node scripts/build-template.mjs --template xxx` 后 `dist/` 目录为空或文件数 < 200。

**解决方案**:
```bash
# 清除 Taro 缓存和 node_modules 缓存
rm -rf .taro node_modules/.cache
# 重新构建
node scripts/build-template.mjs --template {模板代码}
```

**原因**: Taro 的增量编译可能在切换模板时未能正确清理旧资源。

### 切换模板后样式不生效？

**症状**: 修改 `TARO_APP_TEMPLATE_CODE` 后页面仍显示旧模板样式。

**解决方案**:
```bash
# 完整清理流程
rm -rf .taro node_modules/.cache dist
pnpm install
TARO_APP_TEMPLATE_CODE=新模板代码 pnpm dev:weapp
```

### 主包超过 2MB 限制？

**症状**: 微信开发者工具提示主包超限。

**解决方案**:
1. 检查是否有未 tree-shake 的 Shell 组件:
   ```bash
   # 查看产物分析
   pnpm analyze
   ```
2. 确保每个模板仅打包自身所需的 Shell 组件
3. 非首屏页面考虑使用分包加载

### CI 构建失败？

**症状**: GitHub Actions 或其他 CI 流水线构建失败。

**解决方案**:
1. 确认 CI 环境变量已正确设置 `TARO_APP_TEMPLATE_CODE`
2. 使用严格模式脚本:
   ```bash
   node scripts/ci-build-all.mjs
   ```
3. 查看构建日志中的错误堆栈，通常依赖未安装或缓存问题

---

## 技术支持

- 代码位置: `apps/miniapp-instance/`
- 模板定义: `apps/miniapp-instance/templates/`
- 构建脚本: `apps/miniapp-instance/scripts/`
- 文档: `docs/plans/2026-04-19-template-usage-guide.md`
