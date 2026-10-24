# 复刻一期 · 模拟器预览记录

> 2026-10-23 于微信开发者工具 Stable 2.02.2608060 预览，构建命令：
> `node scripts/build-template.mjs --template=elderly-tcm`（worktree 检出 feat/tcm-clinic-template @ e3e8bddd）。
> 未连接后端，公告/医生数据为空态属预期。

## 截图

- `01-home-elderly-tcm.png` 首页（一期棕色版，已被绿色版取代，留档）
- `02-profile-tab.png` 我的：点击登录 / 我的挂号 / 扫码签到 / 联系客服 / 就诊人管理 / 设置
- `03-appointment-tab.png` 预约：我的预约空态（无后端）
- `04-home-green.png` 首页（绿色主题）：绿色四宫格（预约挂号/预约记录/我的就诊卡/在线客服）+ 添加健康卡 + 常看医生空态
- `05-org-center.png` 机构中心：门店照片占位 / 名称卡 / 机构介绍空态；tabBar 高亮正确落在「机构中心」

## 三轮改动（二期视觉核查，2026-10-24）

### 核查发现并修复的关键不一致

**生成器未接 Taro 请求适配器**——`src/app.tsx` 此前从未调用 `setHttpClient`/`setBaseURL`，`@hospital/api` 在小程序内走 axios 空壳（`src/utils/empty-axios.ts`）直接 reject，所有数据页面只能渲染空态。这是与竞品截图「不一致」的结构性根因（竞品有真实数据）。已按 patient-miniapp 同款模式接线：`createTaroAdapter` + `TARO_APP_API_URL`（缺省 `http://localhost:9000/api/v1`）+ 登录态头注入（app.tsx）。

### 一致性静态核对清单（构建产物 vs 竞品截图）

| 竞品截图 | 实现 | 结论 |
|---|---|---|
| 01-home-top（首页） | banner→公告→四宫格→健康卡→推荐医生，模块顺序一致；四宫格文案逐字一致（预约挂号/预约记录/我的就诊卡/在线客服）；健康卡「添加健康卡/记录您的健康」一致 | 一致；banner 图与「有号」标签依赖租户数据配置 |
| 22-org-bottom（御颐草堂机构中心） | 门店照片/名称卡/电话/地址/介绍，结构一致 | 一致；颐寿清式的 5 个二级入口未实现（其特有，见差异） |
| 17/23（医生详情+评价） | 评价列表/写评价弹层/海报按钮/客服按钮，评价走 camelCase 契约 | 代码一致；视觉待模拟器确认 |
| 21（医生海报） | canvas 绘制：机构名/圆形头像/姓名职称/擅长(4行)/简介(6行)/小程序码/长按提示；scene=UUID去连字符32位十六进制 | 元素一一对应；canvas 实际渲染需真机/模拟器 |
| 19/20（预约确认+注意事项） | 费用(初诊)/机构/地点/病情主诉必填/三条注意事项 | 一致（一期已对照） |
| 20 语义（医助联系确认到店） | assistant_confirm_status 三档状态 + 结果页提示卡 + admin 操作 | 竞品无线下界面可比，按其文案语义实现 |

### 已知差异（有意或待办）

1. 颐寿清机构中心的二级入口（科室介绍/医生介绍/设备展示/科室分布/机构环境）未实现——属租户可选模块，待租户配置驱动。
2. 竞品「有号/余N」标签：生成器医生卡片暂无号源角标（需接排班余量接口），列为后续项。
3. 导航栏标题「医院挂号」待租户品牌名注入。

### 本地真实后端联调（2026-10-24）

隔离环境（不碰主开发库）：
- 独立库 `hospital_booking_tcm`（主库 dump 结构 + 手工补 127 列 + alembic stamp 127；迁移链无初始建表迁移，fresh 库无法直接 upgrade）
- 种子：`apps/server/scripts/seed_local_demo.py`（租户 tcm-demo / 管理员 tcmadmin / 门店 / 两科室 / 两演示医生 / 今明上下午排班 / 首页公告），幂等
- 后端 `127.0.0.1:9000`（DATABASE_URL 指向隔离库）、admin 9105、doctor 9103 已启动

代码侧修复（模拟器联调实测发现）：
1. 生成器请求头注入 `X-Tenant-Code`（TARO_APP_TENANT_CODE）——公开接口 fail-closed 必需；
2. 机构中心改走公开 `/stores/by-code/{code}`（原 `/stores/{id}` 为管理端接口，游客 401）；
3. **响应解包拦截器**——后端统一包装 `{code,message,data}`，此前生成器未解包，业务层拿到包装对象导致渲染空态（patient-miniapp 在其 app.tsx 有同款逻辑，生成器缺失）。

实测证据：后端日志两次收到模拟器请求并返回 200（banners + doctors/recommended，带租户头）；
curl 同接口返回两位演示医生且 `hasAvailableSlots=True`（排班生效）。

遗留：模拟器画面偶发不随新构建刷新（热重载/编译触发不稳定），验证时用「清缓存 → 编译」；
工具代理曾设为「使用系统代理」导致 127.0.0.1 请求被 Clash 拦截，已改为「不使用任何代理」。

### 视觉核查操作（真实后端联调版）

## 二轮改动（绿色主题 + 机构中心 + tabBar 高亮修复）验证

1. **绿色主题**：elderly-tcm designTokens 换绿色系（primary #4E8064 等），四宫格贴片色改为模板 customColors 驱动（tilePrimary~tileQuaternary），模拟器确认绿色渲染。
2. **机构中心**：新增 `pages/org/index` + `shells/org/OrgCenter`（门店照片 / 名称+电话+地址卡 / 机构介绍），tabBar 第二项替换为「机构中心」（elderly-tcm navSchema），与竞品结构一致；无后端时空态正常。
3. **tabBar 高亮**：根因是 CustomTabBar 从未监听 `tabbar:change` 事件且每个 tab 页持有独立实例。修复：监听事件 + 挂载时按当前路由推导选中项；模拟器确认首页 ↔ 机构中心往返高亮均正确跟随。

## 结论

- 一期全部改动在真机模拟器中生效：四宫格文案来自模板 tone；健康卡模块渲染正常；「在线客服」为 open-type=contact 按钮本体。
- 主题为 elderly-tcm 模板自带的棕色系（中医康养风）。若要与竞品绿色对齐，改模板 designTokens.primary（或接 shared 的 green 预设）即可，属配置级改动。

## 与竞品的已知差异（后续候选项）

1. tabBar 第二项为「预约」，竞品为「机构中心/机构简介」（门店照片+介绍页）——生成器暂无该页面，可用 lowcode 页面或新增 org 壳补齐。
2. 导航栏标题为「医院挂号」，竞品为机构品牌名——应由租户配置注入（navigationBarTitleText 走租户设置）。
3. 自定义 tabBar 切换 tab 后高亮态未跟随（首页持续高亮），页面路径切换正常；疑似 tabbar:change 事件时序问题，待查。
4. 控制台有 5 条 warning（无后端时的请求失败降级），不影响渲染。
