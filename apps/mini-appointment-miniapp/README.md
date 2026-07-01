# 医疗挂号小程序系统

> **⚠️ 独立发布项目说明（务必先读）**
>
> 本项目（`apps/mini-appointment-miniapp`）是**独立发布的扫码挂号微信小程序**
> （具备 `project.config.json`，单独审核上架），**刻意不依赖** monorepo 中的
> `@hospital/api` 与 `@hospital/shared`，自维护 `src/utils/`（request / validator /
> date 等）。这样设计是为了：
> - 保持小程序包体积最小、避免引入面向多端的冗余依赖；
> - 独立发版节奏（微信审核周期），不与 admin/doctor/patient-h5 同步发布。
>
> **代价**：部分工具逻辑与 `@hospital/shared` 存在同名实现（典型如身份证/手机号校验、
> 脱敏函数），随时间可能出现**校验漂移**（drift）。
>
> **维护红线**：如需改动 `src/utils/validator.ts` 中的身份证校验码算法、手机号正则、
> 脱敏规则等，**必须同步评估 `packages/shared/src/` 下的同名逻辑**（当前对应
> `constants/common.ts` 的 `REGEX` 与 `utils/validate.ts`、`utils/format.ts`），
> 反之亦然。两处算法的一致性结论已在 `validator.ts` 顶部注释中记录。

基于 **Taro + React + TypeScript** 开发的医疗挂号小程序，支持多租户、微信登录、预约挂号、扫码签到等核心功能。

## 项目概述

本项目是一个功能完备的医疗挂号小程序端应用，旨在为患者提供便捷的线上预约挂号服务。系统采用现代化的技术栈，具有良好的代码结构和可维护性。

### 核心功能

**首页模块**
- 轮播图展示
- 公告通知
- 快捷功能入口
- 热门科室推荐
- 推荐医生列表
- 医院信息展示

**预约挂号模块**
- 科室选择（支持科室树结构）
- 医生列表与详情
- 排班查询（含号源状态、时间窗口）
- 预约确认与提交
- 重复预约检查

**预约管理模块**
- 预约列表查询
- 预约详情查看
- 预约取消功能

**扫码签到模块**
- 扫描门店二维码
- 识别门店信息
- 显示当日预约
- 签到功能（含时间窗口控制）
- 获取排队号

**个人中心模块**
- 用户信息管理
- 就诊人管理（增删改查）
- 我的收藏（医生/科室）
- 预约记录
- 意见反馈
- 系统设置

### 技术特点

**架构设计**
- 采用 Taro 4.x 框架，支持多端编译
- 使用 React 18 + TypeScript 开发，类型安全
- 分包加载优化首屏性能
- 无状态管理库，使用 React Hooks 管理状态

**工程化**
- 完整的 TypeScript 类型定义
- 统一的 API 请求封装
- 自动化的 Token 管理
- 门店 ID 自动注入
- 环境变量配置

**用户体验**
- 友好的加载提示
- 完善的错误处理
- 下拉刷新支持
- 登录状态检查
- 实时倒计时

## 技术栈

| 技术 | 版本 | 说明 |
|------|------|------|
| Taro | 4.1.9 | 多端统一开发框架 |
| React | 18.2.0 | UI 框架 |
| TypeScript | 5.1.0 | 类型系统 |
| Sass | 1.77.8 | CSS 预处理器 |
| Webpack | 5.91.0 | 构建工具 |

## 项目结构

```
mini-appointment-miniapp/
├── config/                 # 配置文件
│   ├── index.ts           # 主配置
│   ├── dev.ts             # 开发环境配置
│   └── prod.ts            # 生产环境配置
├── src/
│   ├── app.tsx            # 应用入口
│   ├── app.scss           # 全局样式
│   ├── app.config.ts      # 应用配置
│   ├── pages/             # 页面目录
│   │   ├── home/          # 首页
│   │   ├── scan/          # 扫码签到
│   │   ├── profile/       # 个人中心
│   │   └── appointment/   # 预约挂号（分包）
│   │       ├── department/  # 科室选择
│   │       ├── doctor/      # 医生列表
│   │       ├── schedule/    # 排班选择
│   │       └── confirm/     # 预约确认
│   ├── components/        # 公共组件
│   ├── services/          # API 服务层
│   │   ├── auth.ts        # 认证服务
│   │   ├── appointment.ts # 预约服务
│   │   ├── schedule.ts    # 排班/医生/科室服务
│   │   └── user.ts        # 用户/收藏/内容/设置等服务
│   ├── utils/             # 工具函数
│   │   ├── request.ts     # 请求封装
│   │   ├── date.ts        # 日期处理
│   │   └── validator.ts   # 数据验证
│   ├── types/             # 类型定义
│   │   └── api.ts         # API 类型
│   ├── hooks/             # 自定义 Hooks
│   │   └── useLogin.ts    # 登录 Hook
│   ├── constants/         # 常量定义
│   │   └── index.ts       # 常量
│   ├── styles/            # 样式文件
│   │   └── variables.scss # 样式变量
│   └── assets/            # 静态资源
│       ├── images/        # 图片
│       └── icons/         # 图标
├── package.json           # 依赖配置
├── tsconfig.json          # TypeScript 配置
├── project.config.json    # 小程序项目配置
├── .env                   # 环境变量
└── README.md              # 项目文档
```

## 快速开始

### 环境要求

- Node.js >= 14.0.0
- npm >= 6.0.0 或 pnpm >= 7.0.0

### 安装依赖

```bash
# 使用 npm
npm install

# 或使用 pnpm（推荐）
pnpm install
```

### 配置环境变量

复制 `.env` 文件并根据实际情况修改配置：

```bash
# API 配置
TARO_APP_API_BASE_URL=https://api.example.com
TARO_APP_API_VERSION=v1

# 门店配置（构建时注入）
TARO_APP_STORE_ID=your_store_id
TARO_APP_STORE_CODE=your_store_code
TARO_APP_STORE_NAME=your_store_name

# 微信小程序配置
TARO_APP_WECHAT_APPID=your_appid
```

### 开发调试

```bash
# 微信小程序
npm run dev:weapp

# 支付宝小程序
npm run dev:alipay

# 字节跳动小程序
npm run dev:tt

# H5
npm run dev:h5
```

### 生产构建

```bash
# 微信小程序
npm run build:weapp

# 支付宝小程序
npm run build:alipay

# 字节跳动小程序
npm run build:tt

# H5
npm run build:h5
```

## 核心功能说明

### API 请求封装

项目提供了完善的 API 请求封装，支持以下特性：

**自动 Token 管理**
- 自动从缓存读取 Token
- 自动添加到请求头
- Token 过期自动跳转登录

**门店 ID 注入**
- 自动从环境变量或缓存获取门店 ID
- 自动添加到 URL 参数

**统一错误处理**
- 网络错误提示
- 业务错误提示
- 401 自动跳转登录

**加载提示**
- 可配置的加载提示
- 自动显示/隐藏

使用示例：

```typescript
import { get, post } from '@/utils/request';

// GET 请求
const data = await get('/api/endpoint', { param1: 'value1' });

// POST 请求（带加载提示）
const result = await post('/api/endpoint', 
  { data: 'value' },
  { showLoading: true, loadingText: '提交中...' }
);
```

### 微信登录流程

项目实现了完整的微信登录流程：

**基本流程**
1. 调用 `wx.login()` 获取 code
2. 将 code 发送到后端
3. 后端返回是否需要绑定手机号
4. 如需绑定，调用手机号授权
5. 保存 Token 完成登录

**使用 Hook**

```typescript
import { useLogin } from '@/hooks/useLogin';

const { login, loginWithPhone, logout } = useLogin();

// 微信登录
const result = await login();

if (result.needBindPhone) {
  // 需要绑定手机号
  const phoneResult = await loginWithPhone(phoneCode, openid);
}
```

### 分包配置

项目采用分包加载优化性能：

**主包**
- 首页
- 扫码签到
- 个人中心首页

**预约子包**
- 科室选择
- 医生列表
- 排班选择
- 预约确认

**个人中心子包**
- 就诊人管理
- 预约记录
- 我的收藏
- 意见反馈
- 设置

**预下载配置**
- 首页自动预下载预约子包
- 提升用户体验

## 多租户支持

项目支持多门店多租户部署：

**构建时注入**
- 通过环境变量配置门店信息
- 构建不同门店的独立版本

**运行时识别**
- 扫码识别门店
- 动态切换门店上下文

**API 自动适配**
- 请求自动携带门店 ID
- 后端根据门店 ID 返回对应数据

## 开发规范

### 代码风格

- 使用 TypeScript 严格模式
- 遵循 ESLint 规则
- 使用 Prettier 格式化代码

### 命名规范

**文件命名**
- 组件文件：PascalCase（如 `UserCard.tsx`）
- 工具文件：camelCase（如 `request.ts`）
- 样式文件：与对应文件同名（如 `index.scss`）

**变量命名**
- 常量：UPPER_SNAKE_CASE
- 变量/函数：camelCase
- 组件：PascalCase
- 类型/接口：PascalCase

### 目录规范

- 每个页面一个目录
- 包含 `index.tsx`、`index.scss`、`index.config.ts`
- 页面私有组件放在页面目录下的 `components/` 中

## API 文档

项目包含完整的 API 类型定义，所有接口都有对应的 TypeScript 类型。

主要 API 模块：

| 模块 | 文件 | 说明 |
|------|------|------|
| 认证 | `services/auth.ts` | 微信登录、手机号绑定、Token 刷新 |
| 预约 | `services/appointment.ts` | 预约管理、签到、重复检查 |
| 排班 | `services/schedule.ts` | 排班查询、医生/科室查询 |
| 用户 | `services/user.ts` | 用户信息、就诊人、收藏、反馈 |

详细的 API 接口说明请参考源码中的类型定义和注释。

## 常见问题

**Q: 如何配置多个门店？**

A: 通过环境变量配置不同门店的信息，构建时注入。可以创建多个环境变量文件（如 `.env.store1`、`.env.store2`），然后使用不同的构建命令。

**Q: 如何处理 Token 过期？**

A: 项目已自动处理 Token 过期情况。当接口返回 401 时，会自动清除 Token 并跳转到登录页。

**Q: 如何添加新的页面？**

A: 在 `src/pages/` 下创建新目录，包含 `index.tsx`、`index.scss`、`index.config.ts` 三个文件，然后在 `src/app.config.ts` 中注册页面路径。

**Q: 如何调试小程序？**

A: 运行 `npm run dev:weapp` 后，使用微信开发者工具打开项目根目录，选择 `dist` 目录作为小程序目录。

## 部署说明

### 微信小程序部署

1. 完成开发并构建生产版本：
   ```bash
   npm run build:weapp
   ```

2. 使用微信开发者工具打开 `dist` 目录

3. 配置小程序信息：
   - 修改 `project.config.json` 中的 `appid`
   - 配置服务器域名（在微信公众平台）

4. 上传代码并提交审核

### 其他小程序平台

类似微信小程序的部署流程，使用对应平台的开发者工具。

## 后续优化建议

**性能优化**
- 实现虚拟列表优化长列表性能
- 图片懒加载
- 接口数据缓存策略

**功能增强**
- 支付功能集成
- 消息推送
- 在线咨询
- 电子病历

**用户体验**
- 骨架屏加载
- 动画效果优化
- 无障碍访问支持

## 许可证

MIT License

## 作者

Manus AI

---

**项目创建时间**: 2026-01-08
