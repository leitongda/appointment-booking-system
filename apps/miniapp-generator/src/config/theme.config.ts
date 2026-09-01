/**
 * 小程序主题配置
 * 复用 @hospital/shared 的主题预设，在模板系统中由 designTokens 覆盖
 */

import {
  DEFAULT_MINIAPP_THEME,
  MINIAPP_THEME_PRESETS,
  getMiniappThemeLabel,
  getMiniappThemeOptionLabel,
  getMiniappThemePreset,
  normalizeMiniappThemeName,
  type MiniappThemeName,
  type MiniappThemePreset,
} from '@hospital/shared';

export type ThemeName = MiniappThemeName;

export interface ThemeConfig extends MiniappThemePreset {}

export const THEME_CONFIG = {
  default: DEFAULT_MINIAPP_THEME,
  getTheme(name?: string | null): ThemeConfig {
    return getMiniappThemePreset(name ? normalizeThemeName(name) : this.default);
  },
  getThemeList(): Array<{ value: ThemeName; label: string; color: string }> {
    return MINIAPP_THEME_PRESETS.map((theme) => ({
      value: theme.key,
      label: theme.optionLabel,
      color: theme.primary,
    }));
  },
  getThemeNames(): ThemeName[] {
    return MINIAPP_THEME_PRESETS.map((theme) => theme.key);
  },
};

export function normalizeThemeName(name?: string | null): ThemeName {
  return normalizeMiniappThemeName(name);
}

export function getThemeLabel(name?: string | null): string {
  return getMiniappThemeLabel(name);
}

export function getThemeOptionLabel(name?: string | null): string {
  return getMiniappThemeOptionLabel(name);
}
