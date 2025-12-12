import type { ProLayoutProps } from '@ant-design/pro-components';

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
  title: '医院挂号管理系统',
  pwa: false,
  logo: '/logo.svg',
  iconfontUrl: '',
  token: {
    // 参考 https://procomponents.ant.design/components/layout#api
  },
};

export default Settings;

