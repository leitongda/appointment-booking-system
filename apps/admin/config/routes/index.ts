/**
 * 路由聚合入口
 *
 * 顺序敏感：
 *   1. auth：免登录页面（layout:false）
 *   2. dashboard：仪表盘
 *   3. platform → medicalServices → organization → operations → system：业务一级菜单
 *   4. redirects：旧路径重定向（必须在新业务路由之后，否则被旧路径覆盖）
 *   5. account：个人设置（hideInMenu）
 *   6. fallbacks：`/` 与 `*`，必须放在最末
 *
 * @name 配置名称
 * @icon 菜单图标
 * @access 权限配置
 * @hideInMenu 隐藏菜单
 */
import auth from './auth';
import dashboard from './dashboard';
import platform from './platform';
import medicalServices from './medical-services';
import finance from './finance';
import organization from './organization';
import operations from './operations';
import approval from './approval';
import system from './system';
import redirects from './redirects';
import account from './account';
import fallbacks from './fallbacks';
import screen from './screen';

const routes = [
  ...auth,
  ...dashboard,
  ...screen,
  ...platform,
  ...medicalServices,
  ...finance,
  ...organization,
  ...operations,
  ...approval,
  ...system,
  ...redirects,
  ...account,
  ...fallbacks, // 必须放最后：'/' 与 '*'
];

export default routes;
