import type { ProLayoutProps } from '@ant-design/pro-components';
import { APP_TITLE, DEFAULT_LOGO } from './appConfig';

/**
 * 默认配置
 * @doc https://procomponents.ant.design/components/layout
 */
const Settings: ProLayoutProps & {
  pwa?: boolean;
  logo?: string;
} = {
  navTheme: 'light',
  colorPrimary: '#1677ff',
  layout: 'mix',
  contentWidth: 'Fluid',
  fixedHeader: true,
  fixSiderbar: true,
  colorWeak: false,
  title: APP_TITLE,
  pwa: false,
  logo: DEFAULT_LOGO,
  iconfontUrl: '',

  // 侧边菜单类型
  siderMenuType: "sub",
  
  token: {
    // 参考 https://procomponents.ant.design/components/layout#api
  },
};

export default Settings;
