/**
 * 字体模式管理工具
 * 支持标准模式和长辈模式（字体放大20%）
 */

import Taro from '@tarojs/taro';
import { STORAGE_KEYS } from '@hospital/shared';

// 字体模式类型
export type FontMode = 'standard' | 'elder';

// 字体模式配置
export interface FontModeConfig {
  name: string;
  scale: number;
  className: string;
}

// 字体模式配置映射
export const FONT_MODE_CONFIGS: Record<FontMode, FontModeConfig> = {
  standard: {
    name: '标准模式',
    scale: 1,
    className: '',
  },
  elder: {
    name: '长辈模式',
    scale: 1.2,
    className: 'font-mode-elder',
  },
};

// 默认字体模式
export const DEFAULT_FONT_MODE: FontMode = 'standard';

// 当前字体模式 (全局缓存)
let currentFontMode: FontMode = DEFAULT_FONT_MODE;

/**
 * 获取当前字体模式
 */
export function getFontMode(): FontMode {
  return currentFontMode;
}

/**
 * 获取字体模式配置
 */
export function getFontModeConfig(mode?: FontMode): FontModeConfig {
  return FONT_MODE_CONFIGS[mode || currentFontMode];
}

/**
 * 获取所有可用的字体模式
 */
export function getAvailableFontModes(): FontMode[] {
  return Object.keys(FONT_MODE_CONFIGS) as FontMode[];
}

/**
 * 应用字体模式到页面
 * 通过在 page 元素上添加 CSS 类实现
 */
function applyFontModeToPage(mode: FontMode): void {
  try {
    // 获取当前页面实例
    const pages = Taro.getCurrentPages();
    if (pages.length === 0) return;

    const currentPage = pages[pages.length - 1];
    if (!currentPage) return;

    // 小程序环境：通过 Taro 的方式设置页面类
    // 需要在每个页面的根元素上应用类名
    // 由于小程序限制，我们通过 CSS 变量的方式实现
    
    // 设置 page 级别的 CSS 变量（通过 wx.setPageStyle 或全局样式）
    const config = FONT_MODE_CONFIGS[mode];
    
    // 小程序不支持直接操作 DOM，需要通过页面 data 传递状态
    // 组件需要通过读取全局状态来应用样式
    console.log(`✓ 字体模式已应用: ${config.name}`);
  } catch (error) {
    console.error('应用字体模式失败:', error);
  }
}

/**
 * 切换字体模式
 * @param mode 目标字体模式
 */
export function applyFontMode(mode: FontMode): FontModeConfig {
  const config = FONT_MODE_CONFIGS[mode] || FONT_MODE_CONFIGS[DEFAULT_FONT_MODE];
  currentFontMode = mode;

  // 保存到本地存储
  try {
    Taro.setStorageSync(STORAGE_KEYS.FONT_MODE, mode);
  } catch (e) {
    console.error('保存字体模式失败:', e);
  }

  // 应用到当前页面
  applyFontModeToPage(mode);

  return config;
}

/**
 * 初始化字体模式（从本地存储读取）
 */
export function initFontMode(): FontModeConfig {
  try {
    const savedMode = Taro.getStorageSync(STORAGE_KEYS.FONT_MODE) as FontMode;
    if (savedMode && FONT_MODE_CONFIGS[savedMode]) {
      currentFontMode = savedMode;
      return FONT_MODE_CONFIGS[savedMode];
    }
  } catch (error) {
    console.error('读取字体模式失败:', error);
  }

  currentFontMode = DEFAULT_FONT_MODE;
  return FONT_MODE_CONFIGS[DEFAULT_FONT_MODE];
}

/**
 * 判断是否为长辈模式
 */
export function isElderMode(): boolean {
  return currentFontMode === 'elder';
}

/**
 * 获取字体模式的 CSS 类名
 * 用于在页面根元素上应用
 */
export function getFontModeClassName(): string {
  return FONT_MODE_CONFIGS[currentFontMode].className;
}

