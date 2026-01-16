import { THEME_CONFIG } from '../../config/theme.config';

// 从配置文件获取默认主题色（编译时执行）
const defaultTheme = THEME_CONFIG.getTheme(THEME_CONFIG.default);

export default definePageConfig({
  navigationBarTitleText: '个人中心',
  navigationBarBackgroundColor: defaultTheme.primary,
  navigationBarTextStyle: 'white',
});

