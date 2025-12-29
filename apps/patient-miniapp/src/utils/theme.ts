/**
 * 主题管理工具
 * 根据门店配置的主题风格切换小程序主题
 */

import Taro from '@tarojs/taro';
import { STORAGE_KEYS } from '@hospital/shared';

// 主题名称到 CSS 变量的映射
const THEME_CONFIGS: Record<string, ThemeConfig> = {
  // 中医-红 (朱砂红)
  '中医-红': {
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
  
  // 中医-绿 (翡翠绿)
  '中医-绿': {
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
  
  // 现代-蓝 (琉璃蓝)
  '现代-蓝': {
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
  
  // 简约-白 (玄墨灰)
  '简约-白': {
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
  
  // 故宫红 (宫墙红)
  '故宫红': {
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
  
  // 青花瓷 (钴蓝)
  '青花瓷': {
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
  
  // 茶韵 (茶褐)
  '茶韵': {
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
  
  // 紫禁 (帝王紫)
  '紫禁': {
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
};

// 主题配置类型
export interface ThemeConfig {
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

// 默认主题
export const DEFAULT_THEME = '中医-红';

// 当前主题配置 (全局缓存)
let currentThemeConfig: ThemeConfig = THEME_CONFIGS[DEFAULT_THEME];
let currentThemeName: string = DEFAULT_THEME;

/**
 * 获取主题配置
 */
export function getThemeConfig(themeName?: string): ThemeConfig {
  if (themeName && THEME_CONFIGS[themeName]) {
    return THEME_CONFIGS[themeName];
  }
  return currentThemeConfig;
}

/**
 * 获取所有可用主题列表
 */
export function getAvailableThemes(): string[] {
  return Object.keys(THEME_CONFIGS);
}

/**
 * 应用主题
 * @param themeName 主题名称
 */
export function applyTheme(themeName: string): ThemeConfig {
  const config = THEME_CONFIGS[themeName] || THEME_CONFIGS[DEFAULT_THEME];
  currentThemeName = themeName;
  currentThemeConfig = config;
  
  // 保存到本地存储
  try {
    Taro.setStorageSync(STORAGE_KEYS.CURRENT_THEME, themeName);
  } catch (e) {
    console.error('保存主题配置失败:', e);
  }
  
  return config;
}

/**
 * 从门店配置初始化主题
 */
export function initThemeFromStore(): ThemeConfig {
  try {
    // 优先从存储中获取已保存的主题
    const savedTheme = Taro.getStorageSync(STORAGE_KEYS.CURRENT_THEME);
    if (savedTheme && THEME_CONFIGS[savedTheme]) {
      return applyTheme(savedTheme);
    }
    
    // 否则从门店上下文获取
    const storeContext = Taro.getStorageSync(STORAGE_KEYS.STORE_CONTEXT);
    if (storeContext?.storeTheme && THEME_CONFIGS[storeContext.storeTheme]) {
      return applyTheme(storeContext.storeTheme);
    }
    
    // 使用默认主题
    return applyTheme(DEFAULT_THEME);
  } catch (error) {
    console.error('初始化主题失败:', error);
    return applyTheme(DEFAULT_THEME);
  }
}

/**
 * 获取当前主题名称
 */
export function getCurrentTheme(): string {
  return currentThemeName;
}

/**
 * 获取当前主题配置
 */
export function getCurrentThemeConfig(): ThemeConfig {
  return currentThemeConfig;
}

/**
 * 获取主题相关的内联样式对象
 * 用于需要动态应用主题色的组件
 */
export function getThemeStyleObject(themeName?: string): Record<string, string> {
  const config = getThemeConfig(themeName);
  return {
    '--color-primary': config.primary,
    '--color-primary-dark': config.primaryDark,
    '--color-primary-light': config.primaryLight,
    '--color-secondary': config.secondary,
    '--color-secondary-light': config.secondaryLight,
    '--gradient-primary': config.gradientPrimary,
    '--gradient-primary-h': config.gradientPrimaryH,
    '--gradient-light': config.gradientLight,
    '--shadow-color': config.shadowColor,
    '--shadow-button': config.shadowButton,
    '--badge-bg': config.badgeBg,
  };
}

/**
 * 获取主题主色 (用于需要纯色值的场景)
 */
export function getThemePrimaryColor(themeName?: string): string {
  return getThemeConfig(themeName).primary;
}

/**
 * 获取主题渐变 (用于背景等场景)
 */
export function getThemeGradient(themeName?: string): string {
  return getThemeConfig(themeName).gradientPrimary;
}

/**
 * 获取页面根元素需要设置的 CSS 变量样式字符串
 * 用于在页面最外层容器上设置样式
 */
export function getThemeCssVarsString(themeName?: string): string {
  const obj = getThemeStyleObject(themeName);
  return Object.entries(obj)
    .map(([key, value]) => `${key}: ${value}`)
    .join('; ');
}
