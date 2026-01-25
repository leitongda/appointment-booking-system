/**
 * 小程序主题配置
 * 统一管理所有主题颜色，支持轻松扩展新主题
 *
 * 开发说明：
 * 1. 修改 default 值可切换整个应用的默认主题
 * 2. 添加新主题只需在 themes 对象中添加配置
 * 3. 同时需要在 styles/themes.less 添加对应的 CSS 变量
 */

/**
 * 主题配置类型
 */
export interface ThemeConfig {
  name: string;
  nameEn: string;
  primary: string;
  primaryDark: string;
  primaryLight: string;
  secondary: string;
  secondaryLight: string;
  gradientPrimary: string;
  gradientPrimaryH: string;
  gradientLight: string;
  shadowColor: string;
  shadowButton: string;
  badgeBg: string;
}

/**
 * 主题配置
 *
 * 开发快捷切换：修改 default 值即可更改整个应用的主题
 */
export const THEME_CONFIG = {
  // 默认主题（开发可通过修改此值切换默认主题）
  default: '现代-蓝',

  // 主题定义
  themes: {
    '中医-红': {
      name: '中医-红',
      nameEn: 'tcm-red',
      primary: '#C41E3A',
      primaryDark: '#A31631',
      primaryLight: '#DC3545',
      secondary: '#8B2942',
      secondaryLight: '#A23B55',
      gradientPrimary: 'linear-gradient(135deg, #C41E3A 0%, #8B2942 100%)',
      gradientPrimaryH: 'linear-gradient(90deg, #C41E3A 0%, #8B2942 100%)',
      gradientLight: 'linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%)',
      shadowColor: 'rgba(196, 30, 58, 0.15)',
      shadowButton: '0 8rpx 28rpx 0 rgba(196, 30, 58, 0.3)',
      badgeBg: 'rgba(196, 30, 58, 0.1)',
    },

    '中医-绿': {
      name: '中医-绿',
      nameEn: 'tcm-green',
      primary: '#2D8B56',
      primaryDark: '#1E6B42',
      primaryLight: '#3DA868',
      secondary: '#0D5C38',
      secondaryLight: '#1A7A4C',
      gradientPrimary: 'linear-gradient(135deg, #2D8B56 0%, #0D5C38 100%)',
      gradientPrimaryH: 'linear-gradient(90deg, #2D8B56 0%, #0D5C38 100%)',
      gradientLight: 'linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%)',
      shadowColor: 'rgba(45, 139, 86, 0.15)',
      shadowButton: '0 8rpx 28rpx 0 rgba(45, 139, 86, 0.3)',
      badgeBg: 'rgba(45, 139, 86, 0.1)',
    },

    '现代-蓝': {
      name: '现代-蓝',
      nameEn: 'modern-blue',
      primary: '#1E6FD9',
      primaryDark: '#1557B0',
      primaryLight: '#3B82F6',
      secondary: '#4F46E5',
      secondaryLight: '#6366F1',
      gradientPrimary: 'linear-gradient(135deg, #1E6FD9 0%, #4F46E5 100%)',
      gradientPrimaryH: 'linear-gradient(90deg, #1E6FD9 0%, #4F46E5 100%)',
      gradientLight: 'linear-gradient(135deg, #DBEAFE 0%, #E0E7FF 100%)',
      shadowColor: 'rgba(30, 111, 217, 0.15)',
      shadowButton: '0 8rpx 28rpx 0 rgba(30, 111, 217, 0.3)',
      badgeBg: 'rgba(30, 111, 217, 0.1)',
    },

    '简约-白': {
      name: '简约-白',
      nameEn: 'minimal-white',
      primary: '#374151',
      primaryDark: '#1F2937',
      primaryLight: '#4B5563',
      secondary: '#6B7280',
      secondaryLight: '#9CA3AF',
      gradientPrimary: 'linear-gradient(135deg, #374151 0%, #1F2937 100%)',
      gradientPrimaryH: 'linear-gradient(90deg, #374151 0%, #1F2937 100%)',
      gradientLight: 'linear-gradient(135deg, #F9FAFB 0%, #F3F4F6 100%)',
      shadowColor: 'rgba(55, 65, 81, 0.12)',
      shadowButton: '0 8rpx 28rpx 0 rgba(55, 65, 81, 0.25)',
      badgeBg: 'rgba(55, 65, 81, 0.08)',
    },

    '故宫红': {
      name: '故宫红',
      nameEn: 'forbidden-city',
      primary: '#9D2933',
      primaryDark: '#7A1F28',
      primaryLight: '#B8323F',
      secondary: '#C5A028',
      secondaryLight: '#D4B23D',
      gradientPrimary: 'linear-gradient(135deg, #9D2933 0%, #7A1F28 100%)',
      gradientPrimaryH: 'linear-gradient(90deg, #9D2933 0%, #C5A028 100%)',
      gradientLight: 'linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)',
      shadowColor: 'rgba(157, 41, 51, 0.15)',
      shadowButton: '0 8rpx 28rpx 0 rgba(157, 41, 51, 0.3)',
      badgeBg: 'rgba(157, 41, 51, 0.1)',
    },

    '青花瓷': {
      name: '青花瓷',
      nameEn: 'blue-porcelain',
      primary: '#2563EB',
      primaryDark: '#1D4ED8',
      primaryLight: '#3B82F6',
      secondary: '#1E40AF',
      secondaryLight: '#3B5998',
      gradientPrimary: 'linear-gradient(135deg, #2563EB 0%, #1E40AF 100%)',
      gradientPrimaryH: 'linear-gradient(90deg, #2563EB 0%, #1E40AF 100%)',
      gradientLight: 'linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)',
      shadowColor: 'rgba(37, 99, 235, 0.15)',
      shadowButton: '0 8rpx 28rpx 0 rgba(37, 99, 235, 0.3)',
      badgeBg: 'rgba(37, 99, 235, 0.1)',
    },

    '茶韵': {
      name: '茶韵',
      nameEn: 'tea',
      primary: '#6B4423',
      primaryDark: '#523318',
      primaryLight: '#8B5A2B',
      secondary: '#4A5D23',
      secondaryLight: '#5C7A2D',
      gradientPrimary: 'linear-gradient(135deg, #6B4423 0%, #4A5D23 100%)',
      gradientPrimaryH: 'linear-gradient(90deg, #6B4423 0%, #4A5D23 100%)',
      gradientLight: 'linear-gradient(135deg, #FEF9E7 0%, #F7F3E3 100%)',
      shadowColor: 'rgba(107, 68, 35, 0.15)',
      shadowButton: '0 8rpx 28rpx 0 rgba(107, 68, 35, 0.3)',
      badgeBg: 'rgba(107, 68, 35, 0.1)',
    },

    '紫禁': {
      name: '紫禁',
      nameEn: 'imperial-purple',
      primary: '#6B21A8',
      primaryDark: '#581C87',
      primaryLight: '#7C3AED',
      secondary: '#9333EA',
      secondaryLight: '#A855F7',
      gradientPrimary: 'linear-gradient(135deg, #6B21A8 0%, #9333EA 100%)',
      gradientPrimaryH: 'linear-gradient(90deg, #6B21A8 0%, #9333EA 100%)',
      gradientLight: 'linear-gradient(135deg, #FAF5FF 0%, #F3E8FF 100%)',
      shadowColor: 'rgba(107, 33, 168, 0.15)',
      shadowButton: '0 8rpx 28rpx 0 rgba(107, 33, 168, 0.3)',
      badgeBg: 'rgba(107, 33, 168, 0.1)',
    },
  },

  /**
   * 获取主题配置
   * 如果指定主题不存在，回退到默认主题；如果默认主题也不存在，回退到第一个可用主题
   */
  getTheme(name: string): ThemeConfig {
    // 尝试获取指定主题
    const theme = this.themes[name as keyof typeof this.themes];
    if (theme) return theme;

    // 回退到默认主题
    const defaultTheme = this.themes[this.default as keyof typeof this.themes];
    if (defaultTheme) return defaultTheme;

    // 回退到第一个可用主题（确保永远返回有效主题）
    const firstThemeName = Object.keys(this.themes)[0];
    return this.themes[firstThemeName as keyof typeof this.themes];
  },

  /**
   * 获取所有主题名称列表
   */
  getThemeNames(): string[] {
    return Object.keys(this.themes);
  },

  /**
   * 获取主题列表（用于UI展示）
   */
  getThemeList(): Array<{ name: string; color: string }> {
    return this.getThemeNames().map(name => ({
      name,
      color: this.themes[name as keyof typeof this.themes].primary,
    }));
  },
};

/**
 * 主题名称到 CSS 类名的映射
 */
export const THEME_CLASS_MAP: Record<string, string> = {
  '中医-红': 'tcm-red',
  '中医-绿': 'tcm-green',
  '现代-蓝': 'modern-blue',
  '简约-白': 'minimal-white',
  '故宫红': 'forbidden-city',
  '青花瓷': 'blue-porcelain',
  '茶韵': 'tea',
  '紫禁': 'imperial-purple',
};

/**
 * 获取主题对应的 CSS 类名
 */
export function getThemeClass(themeName: string): string {
  return THEME_CLASS_MAP[themeName] || THEME_CLASS_MAP[THEME_CONFIG.default];
}
