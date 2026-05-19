/**
 * ProLayout 运行时默认设置
 *
 * 由 `apps/admin/src/app.tsx` 通过 `initialState.settings` 注入运行时使用，
 * 与 `settings.ts`（构建期 umi defineConfig.layout）区分用途。
 *
 * 历史路径：曾位于 `apps/admin/config/defaultSettings.ts`，已合并到 `layout/`。
 *
 * @doc https://procomponents.ant.design/components/layout
 */
import type { ProLayoutProps } from '@ant-design/pro-components';
import {
  APP_PRIMARY_COLOR,
  APP_TITLE,
  DEFAULT_LOGO,
} from '../constants/app';

const runtimeSettings: ProLayoutProps & {
  pwa?: boolean;
  logo?: string;
} = {
  navTheme: 'light',
  colorPrimary: APP_PRIMARY_COLOR,
  layout: 'mix',
  contentWidth: 'Fluid',
  fixedHeader: true,
  fixSiderbar: true,
  colorWeak: false,
  title: APP_TITLE,
  pwa: true,
  logo: DEFAULT_LOGO,
  iconfontUrl: '',

  // 侧边菜单类型
  siderMenuType: 'group',

  token: {
    // 参考 https://procomponents.ant.design/components/layout#api
  },
};

export default runtimeSettings;
