/**
 * 主题管理工具
 * 当前门店维度下：用户自定义主题 > 门店默认主题 > 系统默认蓝色。
 */

import { useEffect, useState } from 'react';
import Taro from '@tarojs/taro';
import { STORAGE_KEYS } from '@hospital/shared';
import {
  THEME_CONFIG,
  getThemeClass,
  getThemeLabel,
  normalizeThemeName,
  type ThemeConfig as ConfigThemeConfig,
  type ThemeName,
} from '../config/theme.config';
import { getStoreId } from '../utils/store';

export interface ThemeConfig extends ConfigThemeConfig {}

export const DEFAULT_THEME = THEME_CONFIG.default;
const THEME_CHANGE_EVENT = 'theme:change';

let currentThemeName: ThemeName = DEFAULT_THEME;
let currentThemeConfig: ThemeConfig = THEME_CONFIG.getTheme(DEFAULT_THEME);

function resolveStoreId(storeId?: string): string {
  if (storeId) {
    return storeId;
  }

  const envStoreId = getStoreId();
  if (envStoreId) {
    return envStoreId;
  }

  try {
    return Taro.getStorageSync(STORAGE_KEYS.STORE_CONTEXT)?.storeId || '';
  } catch {
    return '';
  }
}

function getThemeStorageKey(storeId?: string): string {
  const resolvedStoreId = resolveStoreId(storeId);
  return resolvedStoreId ? `${STORAGE_KEYS.CURRENT_THEME}:${resolvedStoreId}` : STORAGE_KEYS.CURRENT_THEME;
}

function saveThemePreference(themeName: ThemeName, storeId?: string): void {
  try {
    Taro.setStorageSync(getThemeStorageKey(storeId), themeName);
  } catch (error) {
    console.error('保存主题配置失败:', error);
  }
}

function emitThemeChange(): void {
  Taro.eventCenter.trigger(THEME_CHANGE_EVENT, {
    themeName: currentThemeName,
    themeConfig: currentThemeConfig,
  });
}

function setThemeState(themeName: ThemeName, options?: { persist?: boolean; storeId?: string }): ThemeConfig {
  currentThemeName = themeName;
  currentThemeConfig = THEME_CONFIG.getTheme(themeName);

  if (options?.persist !== false) {
    saveThemePreference(themeName, options?.storeId);
  }

  emitThemeChange();
  return currentThemeConfig;
}

export function getThemeConfig(themeName?: string | null): ThemeConfig {
  return themeName ? THEME_CONFIG.getTheme(themeName) : currentThemeConfig;
}

export function getThemeList(): Array<{ value: ThemeName; label: string; color: string }> {
  return THEME_CONFIG.getThemeList();
}

export function getAvailableThemes(): ThemeName[] {
  return THEME_CONFIG.getThemeNames();
}

export function applyTheme(themeName: string, storeId = resolveStoreId()): ThemeConfig {
  return setThemeState(normalizeThemeName(themeName), { persist: true, storeId });
}

export function initThemeFromStore(storeTheme?: string | null, storeId = resolveStoreId()): ThemeConfig {
  try {
    const savedTheme = Taro.getStorageSync(getThemeStorageKey(storeId));
    if (savedTheme) {
      return setThemeState(normalizeThemeName(savedTheme), { persist: false, storeId });
    }

    if (storeTheme) {
      return setThemeState(normalizeThemeName(storeTheme), { persist: false, storeId });
    }

    const storeContext = Taro.getStorageSync(STORAGE_KEYS.STORE_CONTEXT);
    if (storeContext?.storeTheme) {
      return setThemeState(normalizeThemeName(storeContext.storeTheme), { persist: false, storeId });
    }

    return setThemeState(DEFAULT_THEME, { persist: false, storeId });
  } catch (error) {
    console.error('初始化主题失败:', error);
    return setThemeState(DEFAULT_THEME, { persist: false, storeId });
  }
}

export function getCurrentTheme(): ThemeName {
  return currentThemeName;
}

export function getCurrentThemeLabel(): string {
  return getThemeLabel(currentThemeName);
}

export function getCurrentThemeConfig(): ThemeConfig {
  return currentThemeConfig;
}

export function subscribeThemeChange(listener: (payload: { themeName: ThemeName; themeConfig: ThemeConfig }) => void): () => void {
  Taro.eventCenter.on(THEME_CHANGE_EVENT, listener);
  return () => Taro.eventCenter.off(THEME_CHANGE_EVENT, listener);
}

export { getThemeClass, getThemeLabel };

export function useThemeName(): ThemeName {
  const [themeName, setThemeName] = useState<ThemeName>(getCurrentTheme());

  useEffect(
    () =>
      subscribeThemeChange(({ themeName: nextThemeName }) => {
        setThemeName(nextThemeName);
      }),
    []
  );

  return themeName;
}

export function useThemePrimaryColor(): string {
  const [primaryColor, setPrimaryColor] = useState(getCurrentThemeConfig().primary);

  useEffect(
    () =>
      subscribeThemeChange(({ themeConfig }) => {
        setPrimaryColor(themeConfig.primary);
      }),
    []
  );

  return primaryColor;
}

export function getThemeStyleObject(themeName?: string | null): Record<string, string> {
  const config = getThemeConfig(themeName);
  return {
    '--theme-primary': config.primary,
    '--theme-primary-soft': config.primarySoft,
    '--theme-primary-soft-2': config.primarySoft2,
    '--theme-accent': config.accent,
    '--theme-gradient-soft': config.gradientSoft,
    '--theme-border-accent': config.borderAccent,
    '--theme-shadow-accent': config.shadowAccent,
  };
}

export function getThemePrimaryColor(themeName?: string | null): string {
  return getThemeConfig(themeName).primary;
}

export function getThemeGradient(themeName?: string | null): string {
  const config = getThemeConfig(themeName);
  return `linear-gradient(135deg, ${config.primary} 0%, ${config.accent} 100%)`;
}

export function getThemeCssVarsString(themeName?: string | null): string {
  return Object.entries(getThemeStyleObject(themeName))
    .map(([key, value]) => `${key}: ${value}`)
    .join('; ');
}
