/**
 * 主题管理工具
 * 当前门店维度下：用户自定义主题 > 门店默认主题 > 系统默认蓝色。
 */

import { useEffect, useState } from 'react';
import Taro from '@tarojs/taro';
import { STORAGE_KEYS } from '../utils/storage';
import {
  THEME_CONFIG,
  getThemeLabel,
  getThemeOptionLabel,
  normalizeThemeName,
  type ThemeConfig as ConfigThemeConfig,
  type ThemeName,
} from './theme.config';
import { getStoreId } from './store';

export interface ThemeConfig extends ConfigThemeConfig {}

export const DEFAULT_THEME = THEME_CONFIG.default;
export const FOLLOW_STORE_THEME = 'follow-store';
const THEME_CHANGE_EVENT = 'theme:change';
const THEME_NAVIGATION_FRONT_COLOR = '#000000';

export type ThemeSelection = ThemeName | typeof FOLLOW_STORE_THEME;

let currentThemeName: ThemeName = DEFAULT_THEME;
let currentThemeConfig: ThemeConfig = THEME_CONFIG.getTheme(DEFAULT_THEME);
let routeThemeSyncRegistered = false;

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

function removeThemePreference(storeId?: string): void {
  try {
    Taro.removeStorageSync(getThemeStorageKey(storeId));
  } catch (error) {
    console.error('移除主题配置失败:', error);
  }
}

function getSavedThemePreference(storeId?: string): ThemeName | null {
  try {
    const savedTheme = Taro.getStorageSync(getThemeStorageKey(storeId));
    return savedTheme ? normalizeThemeName(savedTheme) : null;
  } catch {
    return null;
  }
}

function resolveStoreTheme(storeTheme?: string | null, storeId = resolveStoreId()): ThemeName {
  if (storeTheme) {
    return normalizeThemeName(storeTheme);
  }

  try {
    const storeContext = Taro.getStorageSync(STORAGE_KEYS.STORE_CONTEXT);
    if (!storeContext) {
      return DEFAULT_THEME;
    }

    if (!storeId || !storeContext.storeId || storeContext.storeId === storeId) {
      return normalizeThemeName(storeContext.storeTheme);
    }
  } catch {
    return DEFAULT_THEME;
  }

  return DEFAULT_THEME;
}

function emitThemeChange(): void {
  Taro.eventCenter.trigger(THEME_CHANGE_EVENT, {
    themeName: currentThemeName,
    themeConfig: currentThemeConfig,
  });
}

export function applyThemeNavigationBar(themeName?: string | null): void {
  const themeConfig = getThemeConfig(themeName);
  void Taro.setNavigationBarColor?.({
    frontColor: THEME_NAVIGATION_FRONT_COLOR,
    backgroundColor: themeConfig.primarySoft,
  }).catch?.(() => undefined);
}

function setThemeState(themeName: ThemeName, options?: { persist?: boolean; storeId?: string }): ThemeConfig {
  currentThemeName = themeName;
  currentThemeConfig = THEME_CONFIG.getTheme(themeName);

  if (options?.persist !== false) {
    saveThemePreference(themeName, options?.storeId);
  }

  applyThemeNavigationBar(themeName);
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

export function getThemeSelection(storeId = resolveStoreId()): ThemeSelection {
  return getSavedThemePreference(storeId) ?? FOLLOW_STORE_THEME;
}

export function getStoreDefaultThemeName(storeTheme?: string | null, storeId = resolveStoreId()): ThemeName {
  return resolveStoreTheme(storeTheme, storeId);
}

export function resetThemeToStore(storeTheme?: string | null, storeId = resolveStoreId()): ThemeConfig {
  removeThemePreference(storeId);
  return setThemeState(resolveStoreTheme(storeTheme, storeId), { persist: false, storeId });
}

export function initThemeFromStore(storeTheme?: string | null, storeId = resolveStoreId()): ThemeConfig {
  try {
    const savedTheme = getSavedThemePreference(storeId);
    if (savedTheme) {
      return setThemeState(savedTheme, { persist: false, storeId });
    }

    return setThemeState(resolveStoreTheme(storeTheme, storeId), { persist: false, storeId });
  } catch (error) {
    console.error('初始化主题失败:', error);
    return setThemeState(DEFAULT_THEME, { persist: false, storeId });
  }
}

export function getCurrentTheme(): ThemeName {
  return currentThemeName;
}

export function getCurrentThemeLabel(): string {
  return getThemeOptionLabel(currentThemeName);
}

export function getCurrentThemeConfig(): ThemeConfig {
  return currentThemeConfig;
}

export function subscribeThemeChange(listener: (payload: { themeName: ThemeName; themeConfig: ThemeConfig }) => void): () => void {
  Taro.eventCenter.on(THEME_CHANGE_EVENT, listener);
  return () => Taro.eventCenter.off(THEME_CHANGE_EVENT, listener);
}

export function registerThemeRouteSync(): void {
  if (routeThemeSyncRegistered) {
    return;
  }

  routeThemeSyncRegistered = true;

  const globalWx = (globalThis as { wx?: { onAppRoute?: (listener: () => void) => void } }).wx;
  if (typeof globalWx?.onAppRoute !== 'function') {
    return;
  }

  globalWx.onAppRoute(() => {
    setTimeout(() => {
      applyThemeNavigationBar();
    }, 0);
  });
}

export { getThemeLabel, getThemeOptionLabel };

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

export function useApplyThemeNavigationBar(themeName?: string | null): void {
  Taro.useDidShow(() => {
    applyThemeNavigationBar(themeName);
  });
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
    '--color-primary': config.primary,
    '--color-primary-dark': config.accent,
    '--color-primary-light': config.primary,
    '--color-secondary': config.accent,
    '--color-secondary-light': config.primary,
    '--gradient-primary': `linear-gradient(135deg, ${config.primary} 0%, ${config.accent} 100%)`,
    '--gradient-primary-h': `linear-gradient(90deg, ${config.primary} 0%, ${config.accent} 100%)`,
    '--gradient-light': `linear-gradient(135deg, ${config.primarySoft} 0%, ${config.primarySoft2} 100%)`,
    '--shadow-color': config.shadowAccent,
    '--shadow-button': `0 10rpx 28rpx 0 ${config.shadowAccent}`,
    '--badge-bg': config.primarySoft,
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
