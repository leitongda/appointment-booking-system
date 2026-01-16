/**
 * 主题管理工具
 * 根据门店配置的主题风格切换小程序主题
 */

import Taro from '@tarojs/taro';
import { STORAGE_KEYS } from '@hospital/shared';
import { THEME_CONFIG, getThemeClass, type ThemeConfig as ConfigThemeConfig } from '../config/theme.config';

// 主题配置类型（重新导出）
export interface ThemeConfig extends ConfigThemeConfig {}

// 默认主题（从配置文件导出）
export const DEFAULT_THEME = THEME_CONFIG.default;

// 当前主题配置 (全局缓存)
let currentThemeConfig: ThemeConfig = THEME_CONFIG.getTheme(DEFAULT_THEME);
let currentThemeName: string = DEFAULT_THEME;

/**
 * 获取主题配置
 */
export function getThemeConfig(themeName?: string): ThemeConfig {
  if (themeName) {
    return THEME_CONFIG.getTheme(themeName);
  }
  return currentThemeConfig;
}

/**
 * 获取所有可用主题列表
 */
export function getAvailableThemes(): string[] {
  return THEME_CONFIG.getThemeNames();
}

/**
 * 获取主题列表（用于UI展示）
 */
export function getThemeList(): Array<{ name: string; color: string }> {
  return THEME_CONFIG.getThemeList();
}

/**
 * 应用主题
 * @param themeName 主题名称
 */
export function applyTheme(themeName: string): ThemeConfig {
  const config = THEME_CONFIG.getTheme(themeName);
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
    if (savedTheme && THEME_CONFIG.getThemeNames().includes(savedTheme)) {
      return applyTheme(savedTheme);
    }

    // 否则从门店上下文获取
    const storeContext = Taro.getStorageSync(STORAGE_KEYS.STORE_CONTEXT);
    if (storeContext?.storeTheme && THEME_CONFIG.getThemeNames().includes(storeContext.storeTheme)) {
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
 * 获取主题对应的 CSS 类名
 */
export { getThemeClass };

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
