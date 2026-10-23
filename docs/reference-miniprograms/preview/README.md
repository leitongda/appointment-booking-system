# 复刻一期 · 模拟器预览记录

> 2026-10-23 于微信开发者工具 Stable 2.02.2608060 预览，构建命令：
> `node scripts/build-template.mjs --template=elderly-tcm`（worktree 检出 feat/tcm-clinic-template @ e3e8bddd）。
> 未连接后端，公告/医生数据为空态属预期。

## 截图

- `01-home-elderly-tcm.png` 首页：四宫格（预约挂号/预约记录/我的就诊卡/在线客服）+ 添加健康卡 + 常看医生空态
- `02-profile-tab.png` 我的：点击登录 / 我的挂号 / 扫码签到 / 联系客服 / 就诊人管理 / 设置
- `03-appointment-tab.png` 预约：我的预约空态（无后端）

## 结论

- 一期全部改动在真机模拟器中生效：四宫格文案来自模板 tone；健康卡模块渲染正常；「在线客服」为 open-type=contact 按钮本体。
- 主题为 elderly-tcm 模板自带的棕色系（中医康养风）。若要与竞品绿色对齐，改模板 designTokens.primary（或接 shared 的 green 预设）即可，属配置级改动。

## 与竞品的已知差异（后续候选项）

1. tabBar 第二项为「预约」，竞品为「机构中心/机构简介」（门店照片+介绍页）——生成器暂无该页面，可用 lowcode 页面或新增 org 壳补齐。
2. 导航栏标题为「医院挂号」，竞品为机构品牌名——应由租户配置注入（navigationBarTitleText 走租户设置）。
3. 自定义 tabBar 切换 tab 后高亮态未跟随（首页持续高亮），页面路径切换正常；疑似 tabbar:change 事件时序问题，待查。
4. 控制台有 5 条 warning（无后端时的请求失败降级），不影响渲染。
