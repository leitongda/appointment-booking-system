/**
 * 构建期 umi `defineConfig.layout` 配置
 *
 * 由 `config.ts` 装配入口直接消费；与 `runtime-settings.ts`（ProLayout 运行时默认设置）区分用途。
 */
import {
  APP_PRIMARY_COLOR,
  APP_TITLE,
  LAYOUT_LOGO_URL,
} from '../constants/app';

const settings = {
  title: APP_TITLE,
  locale: false as const,

  navTheme: 'light' as const,
  colorPrimary: APP_PRIMARY_COLOR,
  layout: 'mix' as const,
  contentWidth: 'Fluid' as const,
  fixedHeader: true,
  fixSiderbar: true,
  pwa: true,
  logo: LAYOUT_LOGO_URL,
  token: {},
  siderMenuType: 'sub' as const,
  splitMenus: false,
};

export default settings;
