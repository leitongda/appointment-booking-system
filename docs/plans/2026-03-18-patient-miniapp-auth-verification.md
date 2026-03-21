# Patient Miniapp 登录态修复回归清单

## 当前结论

- `patient-miniapp` 代码层已完成登录态统一、401 静默续期、统一退登、受保护页守卫接入。
- TypeScript 校验已通过：
  - `pnpm --filter @hospital/patient-miniapp exec tsc --noEmit --skipLibCheck`
- 小程序构建已通过：
  - `pnpm --filter @hospital/patient-miniapp build:weapp`
- 构建脚本现在统一带 `--no-check`，原因是 Taro `build` 默认会触发 `@tarojs/plugin-doctor` 配置校验，而该原生插件在当前 macOS 环境下会 panic。

## 构建相关说明

### 已确认现象

- 不带 `--no-check` 时，`taro build --type weapp` 会在启动阶段崩溃。
- 通过临时 native require hook 确认，崩溃前最后加载的原生模块是 `@tarojs/plugin-doctor`。
- 带 `--no-check` 后，Webpack 构建和 `fix-wxml.js` 都可以走通。

### 当前脚本

- `pnpm --filter @hospital/patient-miniapp build:weapp`
- `pnpm --filter @hospital/patient-miniapp dev:weapp`
- `pnpm --filter @hospital/patient-miniapp dev:local`
- `pnpm --filter @hospital/patient-miniapp dev:remote`

这些脚本都已显式追加 `--no-check`。

## 重点回归场景

### 1. 未登录基础流

1. 打开首页。
   预期：首页公开内容正常显示，推荐医生、轮播图可见。
2. 切到预约 tab。
   预期：显示“立即登录”引导，不显示历史预约列表。
3. 切到我的 tab。
   预期：显示未登录态，头部文案为“点击登录”。

### 2. 公开页触发受保护动作

1. 首页点击“预约记录”。
   预期：跳转到预约 tab，并提示登录。
2. 首页点击“扫码签到”。
   预期：弹登录框；登录成功后直接进入扫码。
3. 首页点击“就诊卡”入口。
   预期：弹登录框；登录成功后按就诊人数量续跳。
4. 医生详情页点击收藏。
   预期：未登录时弹登录框；登录成功后自动刷新收藏状态。

### 3. 登录成功后的续动作

1. 首页从“就诊卡”入口完成登录。
   预期：
   - 有就诊人时跳 `/packageProfile/pages/patient/index`
   - 无就诊人时跳 `/packageProfile/pages/patient/edit`
   - 拉取就诊人失败时只 toast，不误跳新增页
2. 首页从“扫码签到”入口完成登录。
   预期：直接拉起扫码。
3. 受保护页从 `LoginPopup` 登录成功。
   预期：当前页自动继续原 loader，不需要手动返回重进。

### 4. 登出与 tab 同步

1. 先登录并进入预约 tab，确认有数据。
2. 进入设置页执行退出登录。
3. 再切回预约 tab、我的 tab、首页。
   预期：
   - 预约 tab 清空旧列表并显示未登录引导
   - 我的 tab 变回未登录态
   - 首页就诊卡状态回到未登录

### 5. access token 过期，refresh token 有效

建议做法：

1. 登录后，手动把 `hospital_token` 改为无效值，保留 `hospital_refresh_token`。
2. 进入收藏、记录、消息、预约详情等受保护页。

预期：

- 第一个 401 触发刷新。
- 只发一次 refresh。
- 原请求自动重放并成功返回。
- 页面无需手动重登。

### 6. access token 与 refresh token 都失效

建议做法：

1. 登录后，同时把 `hospital_token` 和 `hospital_refresh_token` 改为无效值。
2. 进入任意受保护页或触发受保护请求。

预期：

- 统一执行退登。
- 只提示一次“登录已失效，请重新登录”。
- tab 页切到未登录展示。
- 子页弹登录框；取消后返回上一页。

### 7. 并发请求刷新单飞

建议入口：

- 消息页
- 我的页统计
- 首页登录后就诊人加载

预期：

- 多个 401 同时发生时，只触发一次 `/auth/refresh`
- 其他请求等待同一个 refresh 结果
- 没有多次 toast，没有重复退登

## 建议检查点

### Storage Key

- `hospital_token`
- `hospital_refresh_token`
- `hospital_user_info`

### 关键事件

- `auth:login`
- `auth:updated`
- `auth:logout`
- `auth:expired`

## 当前残留项

### 1. 构建 warning

构建成功，但仍有两类 warning：

- NutUI 包内大小写路径不一致引发的 `CaseSensitiveModulesWarning`
- Sass `@import` 废弃告警

它们目前不阻断产物，但建议后续单独治理。

### 2. 旧注释代码

`pages/profile/index.tsx` 里保留了已注释的微信手机号绑定旧代码，里面仍有旧式 `setToken` 示例。它不参与运行，但后续可以清理，避免误导。

## 建议验收顺序

1. 先跑 `pnpm --filter @hospital/patient-miniapp build:weapp`
2. 在微信开发者工具中验证“未登录基础流”
3. 再验“登录成功后的续动作”
4. 最后做 token 过期与 refresh 相关场景

这样最容易快速发现回归，并把问题定位在 UI、页面守卫、还是请求层。
