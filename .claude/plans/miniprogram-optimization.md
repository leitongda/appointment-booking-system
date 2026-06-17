# 小程序优化实施计划

## 1. Executive Summary

当前项目包含三个 Taro 小程序应用:

| 应用 | 路径 | 定位 | UI 库 |
|------|------|------|-------|
| patient-miniapp | `apps/patient-miniapp/` | 患者端主力小程序（按门店独立发布） | NutUI |
| miniapp-instance | `apps/miniapp-instance/` | 多风格模板小程序（5 套模板自动切换） | NutUI |
| mini-appointment-miniapp | `apps/mini-appointment-miniapp/` | 临时挂号小程序（独立轻量版） | 无 |

**核心问题**: patient-miniapp 和 miniapp-instance 之间存在大量逐字重复代码（theme.ts、payment.ts、checkin.ts、url.ts、navigate.ts、store.ts、wechatAuth.ts、fontMode.ts、hooks/\*、Icons.tsx 等），维护成本高且容易分叉。mini-appointment-miniapp 则完全独立，未接入共享体系。

**目标**: 通过提取共享包 + 统一依赖 + 构建优化，消除重复代码，降低维护成本，优化包体积。

---

## 2. 现状评估

### 2.1 重复代码审计

以下文件在 patient-miniapp 和 miniapp-instance 之间 **100% 逐字相同**:

| 文件 | 行数 | 备注 |
|------|------|------|
| `utils/theme.ts` | 281 | 主题管理全套逻辑 |
| `utils/payment.ts` | 113 | 支付结果处理 |
| `utils/checkin.ts` | 48 | 扫码签到 |
| `utils/url.ts` | 114 | URL 工具函数 |
| `utils/navigate.ts` | 117 | 统一导航 |
| `utils/store.ts` | 82 | 门店上下文 |
| `utils/wechatAuth.ts` | 56 | 微信登录流程 |
| `utils/fontMode.ts` | 141 | 字体模式管理 |
| `hooks/useProtectedPage.ts` | 73 | 页面登录保护 |
| `hooks/useTenantGuard.ts` | 51 | 租户状态守卫 |
| `hooks/useSubscribeMessage.ts` | 35 | 订阅消息 |
| `packageBooking/components/CheckinSuccessModal.tsx` | 58 | 签到成功弹窗 |
| `config/theme.config.ts` | 49 | 主题配置（仅注释不同） |

**合计约 1,298 行重复代码**。

### 2.2 有差异但可统一的文件

| 文件 | 差异说明 |
|------|----------|
| `components/Icons.tsx` | patient-miniapp 多 ~120 行（TabBar 图标、更多科室图标），miniapp-instance 子集 |
| `components/LoginPopup.tsx` | 功能差异大：patient-miniapp 有头像/昵称设置流程，miniapp-instance 是简化版 |
| `components/PageContainer.tsx` | patient-miniapp 用 fontMode，miniapp-instance 用 TemplateContext |
| `utils/empty-axios.ts` | patient-miniapp 有完整 mock（77 行），miniapp-instance 仅 `export default {}` |
| `utils/empty-module.ts` | patient-miniapp 有 JSEncrypt mock（33 行），miniapp-instance 仅 `export default {}` |

### 2.3 mini-appointment-miniapp 独立问题

- 未依赖 `@hospital/api` 和 `@hospital/shared`
- 自行实现 auth、request、STORE_ID 逻辑
- 使用 SASS（其他两个用 Less）
- 代码质量较低，缺少类型安全

### 2.4 共享包现状

`@hospital/shared` 已有:
- `miniapp-auth.ts` 子路径导出（认证已统一）
- `constants/miniapp-theme.ts`（主题预设已统一）
- `utils/storage.ts`（存储常量已统一）
- `types/store.ts`（StoreContext 类型已统一）

---

## 3. 详细实施计划

### 3.1 提取共享模块到 `@hospital/shared/miniapp`

将所有重复的 Taro 小程序通用逻辑提取到 shared 包的新子路径 `@hospital/shared/miniapp` 下。

#### 3.1.1 目标结构

```
packages/shared/src/miniapp/
  index.ts              # 统一导出入口
  theme.ts              # 主题管理（从 utils/theme.ts 提取）
  payment.ts            # 支付工具（从 utils/payment.ts 提取）
  checkin.ts            # 扫码签到（从 utils/checkin.ts 提取）
  url.ts                # URL 工具（从 utils/url.ts 提取）
  navigate.ts           # 导航工具（从 utils/navigate.ts 提取）
  store.ts              # 门店上下文（从 utils/store.ts 提取）
  wechatAuth.ts         # 微信登录（从 utils/wechatAuth.ts 提取）
  fontMode.ts           # 字体模式（从 utils/fontMode.ts 提取）
  icons.tsx             # 图标组件（合并两个版本的 Icons.tsx）
  hooks/
    index.ts
    useProtectedPage.ts # 页面登录保护
    useTenantGuard.ts   # 租户守卫
    useSubscribeMessage.ts # 订阅消息
  components/
    index.ts
    CheckinSuccessModal.tsx  # 签到成功弹窗
  stubs/
    empty-axios.ts      # axios 空模块 mock
    empty-module.ts     # jsencrypt 空模块 mock
```

#### 3.1.2 提取步骤（每个文件）

1. 在 `packages/shared/src/miniapp/` 下创建对应文件
2. 将 patient-miniapp 中的代码移入（优先选择更完整的版本）
3. 调整 import 路径（`@tarojs/taro` → 保持，`@hospital/shared` → 相对路径）
4. 在 `packages/shared/src/miniapp/index.ts` 中统一导出
5. 更新 `packages/shared/package.json` 添加子路径导出:
   ```json
   "./miniapp": "./src/miniapp/index.ts",
   "./miniapp/*": "./src/miniapp/*.ts"
   ```
6. 在各小程序中替换为 `import { ... } from '@hospital/shared/miniapp'`
7. 删除各小程序中的重复文件
8. 验证构建

#### 3.1.3 特殊处理

**Icons.tsx 合并策略**:
- 取 patient-miniapp 的完整版本（包含所有图标 + TabBar 图标 + DeptIconMap）
- 保留所有命名导出
- miniapp-instance 的额外图标（star）合并进来

**LoginPopup.tsx 不合并**:
- 两个版本功能差异太大，不适合强行统一
- patient-miniapp 版保留为独立组件（含头像/昵称流程）
- miniapp-instance 版保留为独立组件（简化版）
- 未来可考虑提供 `LoginPopupFull` 和 `LoginPopupSimple` 两个变体

**PageContainer.tsx 不合并**:
- patient-miniapp 依赖 fontMode
- miniapp-instance 依赖 TemplateContext
- 保留各自实现，但提取公共样式逻辑到 shared

**empty-axios.ts / empty-module.ts**:
- 取 patient-miniapp 的完整 mock 版本作为 shared 版本
- miniapp-instance 改为引用 shared 版本

### 3.2 统一依赖版本

| 依赖 | patient-miniapp | miniapp-instance | mini-appointment | 目标 |
|------|----------------|-----------------|-----------------|------|
| Taro | 4.1.9 | 4.1.9 | 4.1.9 | 4.1.9 (不变) |
| React | 18.2.0 | 18.2.0 | ^18.2.0 | 18.2.0 |
| NutUI | 3.0.18 | 3.0.18 | 无 | 3.0.18 (不变) |
| TypeScript | ^5.3.3 | ^5.3.3 | ^5.1.0 | ^5.3.3 |

**mini-appointment-miniapp 需要**:
- 升级 TypeScript 到 ^5.3.3
- 添加 `@hospital/api` 和 `@hospital/shared` 依赖
- 保留无 NutUI 的轻量定位

### 3.3 接入共享包（mini-appointment-miniapp）

mini-appointment-miniapp 当前完全独立，需要逐步接入:

1. **添加依赖**: `@hospital/api: workspace:*`, `@hospital/shared: workspace:*`
2. **替换 auth**: 当前 `utils/auth.ts` 自行实现 → 改为 `import ... from '@hospital/shared/miniapp-auth'`
3. **替换 request**: 当前 `utils/request.ts` 自行封装 → 改为使用 `@hospital/api` 的 Taro 适配器
4. **替换 constants**: 当前 `constants/index.ts` 自行定义 → 改为使用 `@hospital/shared` 的常量
5. **替换 types**: 当前 `types/api.ts` 自行定义 → 改为使用 `@hospital/shared` 的类型

**渐进策略**: 先替换 auth 和 constants（影响最小），再替换 request 和 types（影响较大需测试）。

### 3.4 构建优化

#### 3.4.1 分包优化

当前 patient-miniapp 的分包结构:
- 主包: `pages/index`, `pages/appointment`, `pages/doctor`, `pages/department`, `pages/profile`
- `packageBooking`: 预约流程子包
- `packageOther`: 其他页面子包

优化方向:
- 检查主包体积是否超过微信 2MB 限制
- 将低频页面移到分包
- 共享组件提取到主包或独立分包

#### 3.4.2 Taro 编译优化

在 `config/index.ts` 中添加:
```typescript
mini: {
  postcss: {
    pxtransform: {
      enable: true,
    },
    cssModules: {
      enable: false,
    },
  },
  webpackChain(chain) {
    // 移除 console.log (生产环境)
    if (process.env.NODE_ENV === 'production') {
      chain.optimization.minimizer('terser').tap((args) => {
        args[0].terserOptions.compress.drop_console = true;
        return args;
      });
    }
  },
},
```

#### 3.4.3 图标优化

当前 Icons.tsx 使用 SVG → data URI 方式内联，增加了 JS 体积。

优化方案:
- 将静态 SVG 图标改为微信小程序的 `<image>` + 远程 CDN 托管
- 或使用 iconfont 方案减少 JS 体积
- 预估可减少 ~15KB JS 体积

### 3.5 TypeScript 严格模式

当前各小程序的 `tsconfig.json` 未开启严格模式。建议统一开启:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

先在 shared 包启用，再逐步推广到各小程序。

---

## 4. 共享包提取详细计划

### 4.1 Phase 1: 纯函数提取（零风险）

以下模块是纯函数/Taro 无状态工具，提取风险最低:

| 优先级 | 模块 | 源文件 | 目标路径 | 预估工时 |
|--------|------|--------|----------|----------|
| P0 | url.ts | utils/url.ts | `miniapp/url.ts` | 10 min |
| P0 | payment.ts | utils/payment.ts | `miniapp/payment.ts` | 10 min |
| P0 | checkin.ts | utils/checkin.ts | `miniapp/checkin.ts` | 10 min |
| P0 | store.ts | utils/store.ts | `miniapp/store.ts` | 10 min |
| P0 | fontMode.ts | utils/fontMode.ts | `miniapp/fontMode.ts` | 10 min |
| P1 | empty-axios.ts | utils/empty-axios.ts | `miniapp/stubs/empty-axios.ts` | 5 min |
| P1 | empty-module.ts | utils/empty-module.ts | `miniapp/stubs/empty-module.ts` | 5 min |

### 4.2 Phase 2: 有状态模块提取（低风险）

| 优先级 | 模块 | 源文件 | 注意事项 | 预估工时 |
|--------|------|--------|----------|----------|
| P0 | navigate.ts | utils/navigate.ts | 依赖 auth 模块，需调整 import | 15 min |
| P0 | wechatAuth.ts | utils/wechatAuth.ts | 依赖 auth 和 userApi | 15 min |
| P0 | theme.ts | utils/theme.ts | 依赖 theme.config 和 store | 20 min |
| P1 | useProtectedPage | hooks/useProtectedPage.ts | 依赖 auth 模块 | 10 min |
| P1 | useTenantGuard | hooks/useTenantGuard.ts | 依赖 shared 类型 | 10 min |
| P1 | useSubscribeMessage | hooks/useSubscribeMessage.ts | 无外部依赖 | 5 min |

### 4.3 Phase 3: 组件提取（中风险）

| 优先级 | 组件 | 策略 | 预估工时 |
|--------|------|------|----------|
| P0 | Icons.tsx | 合并两个版本到 shared | 30 min |
| P0 | CheckinSuccessModal.tsx | 直接提取（完全相同） | 10 min |
| P2 | LoginPopup.tsx | 不合并，保留各自实现 | 0 min |
| P2 | PageContainer.tsx | 不合并，保留各自实现 | 0 min |

### 4.4 Phase 4: theme.config.ts 统一

当前两个小程序的 `config/theme.config.ts` 仅注释不同，逻辑完全一致。可以:
- 删除各小程序的 `config/theme.config.ts`
- 改为直接从 `@hospital/shared/miniapp/theme` 导入 `THEME_CONFIG` 等

---

## 5. 执行时间线

### Track A: 共享包提取（主线）

```
Week 1 (2 天)
  Day 1: Phase 1 — 纯函数提取
    - 创建 miniapp/ 目录结构
    - 提取 url, payment, checkin, store, fontMode, stubs
    - 更新 package.json 子路径导出
    - patient-miniapp 切换引用 + 验证构建
  Day 2: Phase 2 — 有状态模块提取
    - 提取 navigate, wechatAuth, theme, hooks
    - patient-miniapp 切换引用 + 验证构建

Week 2 (2 天)
  Day 3: Phase 3 — 组件提取
    - 合并 Icons.tsx 到 shared
    - 提取 CheckinSuccessModal
    - patient-miniapp 切换引用 + 验证构建
  Day 4: miniapp-instance 切换
    - 所有模块切换到 shared 引用
    - 删除重复文件
    - 验证构建 + 模板功能测试
```

### Track B: mini-appointment-miniapp 接入（并行）

```
Week 2 (与 Track A Day 4 并行)
  Day 3-4: 接入共享包
    - 添加 @hospital/api, @hospital/shared 依赖
    - 替换 auth → shared/miniapp-auth
    - 替换 constants → shared/constants
    - 替换 types → shared/types
    - 升级 TypeScript 到 ^5.3.3
    - 验证构建 + 功能测试
```

### Track C: 构建优化（后续）

```
Week 3 (1 天)
  - 生产环境移除 console.log
  - 分包体积审计
  - 图标方案优化评估
  - TypeScript 严格模式启用
```

### 里程碑

| 里程碑 | 时间 | 验收标准 |
|--------|------|----------|
| M1: shared 包提取完成 | Week 2 Day 2 | patient-miniapp 构建通过，重复文件已删除 |
| M2: 三个小程序统一引用 | Week 2 Day 4 | miniapp-instance + mini-appointment-miniapp 构建通过 |
| M3: 构建优化 | Week 3 Day 1 | 生产包体积减少 >= 5% |

---

## 6. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| 提取后 import 路径错误导致构建失败 | 中 | 低 | 每个模块提取后立即验证构建 |
| theme.ts 全局状态在 shared 包中产生多实例 | 低 | 高 | 确认 Taro webpack 配置中 shared 包不被重复打包 |
| miniapp-instance 模板系统依赖 theme.config 的特定导出路径 | 中 | 中 | 先 grep 确认所有 import 路径，逐一替换 |
| Icons.tsx 合并后丢失 miniapp-instance 独有图标 | 低 | 低 | 合并前 diff 两个文件的 svgs 对象 |
| mini-appointment-miniapp 接入 @hospital/api 后引入不需要的依赖 | 中 | 低 | 使用 tree-shaking，webpack 自动排除未引用模块 |
| 构建优化 (drop_console) 误删业务日志 | 低 | 中 | 仅在生产环境启用，保留 console.error/warn |

---

## 7. 验证清单

每个 Phase 完成后执行:

- [ ] `cd apps/patient-miniapp && pnpm build:weapp` 构建成功
- [ ] `cd apps/miniapp-instance && pnpm build:weapp` 构建成功
- [ ] `cd apps/mini-appointment-miniapp && pnpm build:weapp` 构建成功（Phase 4 后）
- [ ] 微信开发者工具中预览各页面功能正常
- [ ] 主题切换功能正常
- [ ] 登录流程正常
- [ ] 支付流程正常
- [ ] 扫码签到正常
- [ ] 租户暂停状态守卫正常
- [ ] 生产包体积无明显增长（< 5% 波动）
