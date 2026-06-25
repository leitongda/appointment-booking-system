# 前端架构自适应评审报告

**评审日期**: 2026-06-23
**评审范围**: admin / doctor / patient-h5 + @hospital/api + @hospital/shared
**复杂度级别**: 深度（3 应用 + 2 共享包, 221+ 页面文件, 57 API 模块）
**协作模式**: 领域主导（Architecture + Frontend Engineering 双镜头）
**风险升级因子**: 无（仅查看结构, 非修改）

---

## Phase 1: Round 1 关键事实

| 维度 | 事实 | 证据级别 |
|------|------|----------|
| 应用规模 | admin 33 模块/221 文件, doctor 13 模块/16 文件, patient-h5 16 目录/32 文件 | E1 |
| 共享包 | @hospital/api 57 模块, @hospital/shared 17 类型/6 常量/10 工具 | E1 |
| 框架一致性 | 三端均使用 UmiJS 4 + React 18 + TypeScript | E1 |
| API 层 | 单例 axios + HttpClient 接口 + Taro 适配器 + ApiError + 重试熔断 | E1 |
| 认证体系 | 三端各自配置拦截器, 双 auth 系统 (localStorage + Taro Storage) | E1 |
| 状态管理 | admin: model + initialState, doctor: initialState, patient-h5: Context | E1 |
| 实时能力 | doctor/patient-h5 有 WebSocket hooks, admin 无 | E1 |
| 测试覆盖 | admin 40 E2E + 1 单元, patient-h5 3 E2E, doctor 0 测试, 共享包 3 单元 | E1 |
| 样式方案 | admin: LESS + antd v6, doctor: antd v5, patient-h5: Tailwind + antd-mobile | E2 |

---

## Phase 2: Round 2 交叉辩论发现

### 去重合并矩阵

| # | 发现 | 架构镜头 | 前端工程镜头 | 合并严重度 |
|---|------|---------|------------|-----------|
| 1 | Admin 双拦截器系统 | P1 | P1 | **P1** |
| 2 | WebSocket hook 跨端重复 + 共享类型死代码 | P1 | - | **P1** |
| 3 | 跨端 401/403 错误处理行为不一致 | - | P1 | **P1** |
| 4 | camelCase→snake_case 冗余转换 (57 模块) | P2 | - | **P2** |
| 5 | Admin 结构化错误码三处重复实现 | P2 | P2 | **P2** |
| 6 | Admin 无实时能力 (轮询 vs WebSocket) | P2 | - | **P2** |
| 7 | 未使用的重量级依赖 (@ant-design/charts, plots) | P2 | - | **P2** |
| 8 | HttpClient 接口 data 参数全为 any | - | P2 | **P2** |
| 9 | errorDetails 类型断言无运行时校验 | - | P2 | **P2** |
| 10 | useFormDraft debounce cleanup 缺失 | - | P2 | **P2** |
| 11 | 共享包循环依赖 (miniapp → api → shared) | P3 | - | **P3** |
| 12 | ImageUpload 潜在 ReferenceError | P3 | - | **P3** |
| 13 | patient-h5 token 路径模糊匹配 | P3 | - | **P3** |
| 14 | RBAC 66 属性标志爆炸 | P3 | - | **P3** |
| 15 | 单元测试严重缺失 (admin 1 个, doctor 0 个) | - | P1 | **P2** (降级) |

> 测试缺失降级理由: 虽然覆盖率为零, 但 40 个 E2E 测试提供了端到端保护, 不构成 P0/P1 级别的安全或数据风险。标记为 P2 表示需要优先改善。

---

## Phase 3: 共识收敛 — 行动项

### P1 — 必须修复 (3 项)

#### P1-1: 合并 Admin 双拦截器系统

```
发现: Admin 同时维护 @hospital/api 拦截器 (request.ts, 377 行) 和 Umi RequestConfig 拦截器
      (requestInterceptors.ts, 113 行), 两套系统行为不一致:
      - Path A 排除 11 个认证路径注入 token; Path B 无条件注入
      - Path A 处理 5 个结构化错误码; Path B 仅 3 个
      - Path A 注入 X-Tenant-ID; Path B 不注入
证据级别: E1
证据来源: apps/admin/src/utils/request.ts, apps/admin/src/utils/requestInterceptors.ts
置信度: High

触发条件: 开发者通过 Umi 原生 request() 发起租户范围 API 调用
频率: 取决于 Umi request 路径的使用量
已有防护: 无

工程成本: Medium
风险降低: High
杠杆率: High (成本中等, 收益高)
负责角色: Frontend Architect

行动计划:
1. 审计所有使用 Umi request() 的页面, 迁移到 @hospital/api
2. 将 requestInterceptors.ts 的独有逻辑合并到 request.ts
3. 删除 requestInterceptors.ts
4. 验证所有页面的错误处理行为一致
```

#### P1-2: 提取共享 WebSocket 连接 Hook

```
发现: doctor/useWebSocket (336 行) 和 patient-h5/usePatientWebSocket (274 行) 有 65-70%
      重复代码; @hospital/api/websocket.ts 导出了共享类型但两端均未使用
证据级别: E1
证据来源: apps/doctor/src/hooks/useWebSocket.ts, apps/patient-h5/src/hooks/usePatientWebSocket.ts,
         packages/api/src/modules/websocket.ts
置信度: High

触发条件: WebSocket 断连时仅修复一端会导致另一端体验不一致
频率: 每次网络不稳定的会话
已有防护: 无

工程成本: Medium
风险降低: High
杠杆率: High
负责角色: Frontend Architect

行动计划:
1. 在 @hospital/shared 创建 useWebSocketConnection(options) 基础 hook
2. 封装连接生命周期、心跳 (25s)、指数退避重连 (3s base, 30s cap, jitter)
3. doctor 和 patient-h5 hook 改为薄包装层
4. 删除 @hospital/api/websocket.ts 死代码
5. (可选) 为 admin 添加 WebSocket hook 用于队列/通知实时更新
```

#### P1-3: 统一跨端错误处理行为

```
发现: 三端 401/403 处理行为不一致:
      - 401: admin/doctor 有静默模式, patient-h5 直接 Toast 无静默
      - 403 租户暂停: admin 跳转专用页面, doctor 仅 message.error,
        patient-h5 显示 Dialog 但不跳转
      - patient-h5 不使用 ApiError, 丢失 errorCode/errorDetails 结构化信息
证据级别: E1
证据来源: 三端各自 src/utils/request.ts
置信度: High

触发条件: 租户订阅过期或被暂停
频率: 低频但影响全部用户
已有防护: admin 有专用页面, doctor/patient-h5 无

工程成本: Low
风险降低: High
杠杆率: Very High (低成本, 高收益)
负责角色: Frontend Engineer

行动计划:
1. 将 ERROR_MESSAGES、shouldAddToken、handle401 提取到 @hospital/api
2. 统一 403 租户暂停处理: 跳转专用页面或显示标准化 Dialog
3. patient-h5 改用 ApiError 类, 保留结构化错误信息
4. 统一 token 路径排除列表 (当前 admin 8 个, doctor 3 个, patient-h5 4 个)
```

---

### P2 — 建议修复 (7 项)

#### P2-1: 移除冗余 camelCase→snake_case 转换

```
发现: 57 个 API 模块中存在三种不一致的大小写转换模式;
      后端 BaseSchema 使用 populate_by_name=True 同时接受两种格式
证据级别: E1
证据来源: packages/api/src/modules/ (doctor.ts, appointment.ts, patient.ts),
         apps/server/app/schemas/base.py
工程成本: Low | 风险降低: Medium | 杠杆率: High
负责角色: Frontend Engineer

行动: 统一为 Pattern C (直接传 camelCase), 移除所有手动转换代码
```

#### P2-2: 合并 Admin 结构化错误码三处实现

```
发现: request.ts、requestInterceptors.ts、errorHandler.ts 各有一套
      SCHEDULE_CONFLICT/PERMISSION_DENIED/RATE_LIMITED switch-case
证据级别: E1
证据来源: apps/admin/src/utils/ (3 个文件)
工程成本: Low | 风险降低: Medium | 杠杆率: High
负责角色: Frontend Engineer

行动: 提取为单一共享函数, 参考 doctor 的 handle401 提取模式
```

#### P2-3: 清理 Admin 未使用重量级依赖

```
发现: @ant-design/charts 和 @ant-design/plots 声明为依赖但零引用
证据级别: E1
证据来源: apps/admin/package.json (声明), apps/admin/src/ (0 引用)
工程成本: Very Low | 风险降低: Low | 杠杆率: High
负责角色: Frontend Engineer

行动: 从 package.json 移除, 未来需要时再添加
```

#### P2-4: 改善 HttpClient 类型安全

```
发现: @hospital/api HttpClient 接口的 data 参数全部为 any;
      ApiError.data 也是 any
证据级别: E1
证据来源: packages/api/src/request.ts L65-70
工程成本: Medium | 风险降低: Medium | 杠杆率: Medium
负责角色: Frontend Architect

行动: 为 HttpClient 接口添加泛型参数, 逐步替换 any 为 unknown
```

#### P2-5: 为 errorDetails 添加运行时校验

```
发现: 服务端返回的 errorDetails 直接用 as 断言, 无运行时校验;
      后端 schema 变更时 TypeScript 不报错
证据级别: E1
证据来源: apps/admin/src/utils/request.ts L49, L79
工程成本: Low | 风险降低: Medium | 杠杆率: High
负责角色: Frontend Engineer

行动: 添加 zod 或简单运行时校验, 优雅降级到通用错误消息
```

#### P2-6: 修复 useFormDraft debounce cleanup

```
发现: saveDraftInternal 使用 useMemo 包裹 debounce 但未在卸载时 cancel;
      excludeFields 新引用会重建 debounce
证据级别: E1
证据来源: apps/admin/src/hooks/useFormDraft.ts L219-227
工程成本: Very Low | 风险降低: Low | 杠杆率: High
负责角色: Frontend Engineer

行动: 添加 useEffect cleanup 调用 debounce.cancel(), 用 useRef 稳定 excludeFields
```

#### P2-7: 补充核心 hooks 单元测试

```
发现: admin 14 个 hooks 仅 1 个单元测试文件, doctor 零测试;
      @hospital/api 57 模块仅 2 个测试文件
证据级别: E1
证据来源: 各应用 src/hooks/, packages/api/src/utils/__tests__/
工程成本: Medium | 风险降低: Medium | 杠杆率: Medium
负责角色: Frontend Engineer

行动: 优先为 useListPage、useListRequest、useFormDraft、useWebSocket 添加测试
```

---

### P3 — 记录备查 (5 项)

| # | 发现 | 工程成本 | 风险降低 | 杠杆率 | 说明 |
|---|------|---------|---------|--------|------|
| P3-1 | 共享包循环依赖 (miniapp→api→shared) | Low | Low | Medium | 当前由 Taro bundler 隔离, 改为注入模式可彻底解决 |
| P3-2 | ImageUpload 潜在 ReferenceError | Very Low | Low | High | 仅当新端不注入 onUpload 时触发, 添加运行时警告即可 |
| P3-3 | patient-h5 token 路径模糊匹配 | Very Low | Low | High | includes() 可能误匹配子串, 改为精确匹配即可 |
| P3-4 | RBAC 66 属性标志爆炸 | Medium | Low | Low | 纯 DX 问题, 按域分组可改善但优先级低 |
| P3-5 | 样式方案不统一 (LESS vs Tailwind) | N/A | N/A | N/A | 各端 UI 需求差异大, 当前不需要统一 |

---

## Open Risks (未解决分歧)

1. **Admin WebSocket 缺失是有意为之还是遗漏?**
   - 架构镜头认为应补充; 前端工程镜头认为轮询已足够
   - 建议: 确认业务需求后决定, 不强制共识

2. **是否应将 patient-h5 的自建 UI 组件库提升为共享组件?**
   - 当前各端 UI 需求差异大 (后台 vs 移动端), 强行统一会增加复杂度
   - 建议: 暂不统一, 未来新增端时再评估

---

## 正面发现 (值得保持的模式)

1. **admin hooks 层设计良好** — useListPage/useListRequest/useFormDraft/useDict/useGuidedTour 显著减少样板代码, 有完整 JSDoc 文档
2. **@hospital/api 可插拔 HttpClient** — Taro 适配器模式优雅, 支持 Web/小程序双环境
3. **patient-h5 无障碍支持** — LiveRegion、aria-label、prefers-reduced-motion、44px 最小触控目标
4. **admin 配置模块化** — 16 路由模块 + 7 配置子模块, 职责清晰
5. **@hospital/shared 导出分层** — main/miniapp/components 四个入口, 避免依赖膨胀

---

## 执行优先级排序 (按杠杆率)

| 优先级 | 行动项 | 杠杆率 | 预估工时 |
|--------|--------|--------|---------|
| 1 | P1-3 统一错误处理 | Very High | 2-3h |
| 2 | P2-3 清理未使用依赖 | High | 15min |
| 3 | P2-6 修复 debounce cleanup | High | 30min |
| 4 | P2-1 移除冗余大小写转换 | High | 2-4h |
| 5 | P2-2 合并错误码实现 | High | 1-2h |
| 6 | P1-1 合并双拦截器 | High | 4-6h |
| 7 | P1-2 提取共享 WebSocket hook | High | 4-6h |
| 8 | P2-5 errorDetails 运行时校验 | High | 1h |
| 9 | P2-4 HttpClient 类型安全 | Medium | 2-3h |
| 10 | P2-7 补充单元测试 | Medium | 1-2 天 |

---

## 执行记录 (2026-06-23)

### 已完成

| 任务 | 状态 | 变更文件 |
|------|------|---------|
| P2-3 清理未使用依赖 | 已完成 | admin/package.json (移除 @ant-design/charts, @ant-design/plots) |
| P2-6 修复 debounce cleanup | 已完成 | admin/hooks/useFormDraft.ts (useRef 稳定引用 + useEffect cleanup) |
| P2-5 errorDetails 运行时校验 | 已完成 | admin/request.ts, requestInterceptors.ts, errorHandler.ts (Array.isArray 防护) |
| P1-3 统一错误处理 | 已完成 | 新建 packages/api/src/utils/error-handling.ts, 三端 request.ts 重写 |
| P2-2 合并错误码实现 | 已完成 | admin/request.ts, requestInterceptors.ts, errorHandler.ts 共享 handleStructuredErrorCode |

### 关键改进

1. **净减少 110 行代码** (206 增 / 316 删)
2. **三端共享** ERROR_MESSAGES、getRequestPath、shouldAddToken、handleStructuredErrorCode、isRsaDecryptError、handleNetworkError
3. **patient-h5 改用 ApiError** 替代 plain Error，保留 errorCode/errorDetails 结构化信息
4. **patient-h5 修复模糊匹配** url.includes() → 精确路径匹配
5. **doctor 补充 403 租户暂停处理** (之前仅 message.error，现在跳转 /tenant-suspended)

### 待执行 (建议后续 PR)

| 任务 | 说明 |
|------|------|
| P1-1 合并双拦截器 | 2 个 useRequest 页面需迁移，requestInterceptors.ts 需全面审计后删除 |
| P1-2 提取共享 WebSocket hook | 需设计决策: @hospital/shared 还是 @hospital/api |
| P2-4 HttpClient 类型安全 | 泛型参数改造，影响面广 |
| P2-7 补充单元测试 | 优先 useListPage/useListRequest/useFormDraft |
