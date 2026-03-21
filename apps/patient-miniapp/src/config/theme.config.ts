/**
 * 小程序主题配置
 * 收敛为 4 套轻量主题，统一通过 CSS 变量驱动关键业务组件配色。
 */

export type ThemeName = 'red' | 'yellow' | 'blue' | 'green';

export interface ThemeConfig {
  key: ThemeName;
  label: string;
  className: string;
  primary: string;
  primarySoft: string;
  primarySoft2: string;
  accent: string;
  gradientSoft: string;
  borderAccent: string;
  shadowAccent: string;
  legacyValues: string[];
}

export const THEME_CONFIG = {
  default: 'blue' as ThemeName,
  themes: {
    red: {
      key: 'red',
      label: '红',
      className: 'theme-red',
      primary: '#B85A5F',
      primarySoft: '#F5E8E8',
      primarySoft2: '#EED9DA',
      accent: '#8E4348',
      gradientSoft: 'linear-gradient(180deg, rgba(184, 90, 95, 0.12) 0%, rgba(184, 90, 95, 0.04) 55%, transparent 100%)',
      borderAccent: 'rgba(184, 90, 95, 0.18)',
      shadowAccent: 'rgba(184, 90, 95, 0.16)',
      legacyValues: ['中医-红', '故宫红'],
    },
    yellow: {
      key: 'yellow',
      label: '黄',
      className: 'theme-yellow',
      primary: '#A98B57',
      primarySoft: '#F6F0E3',
      primarySoft2: '#EBDDCA',
      accent: '#8B7145',
      gradientSoft: 'linear-gradient(180deg, rgba(169, 139, 87, 0.14) 0%, rgba(169, 139, 87, 0.05) 55%, transparent 100%)',
      borderAccent: 'rgba(169, 139, 87, 0.18)',
      shadowAccent: 'rgba(169, 139, 87, 0.14)',
      legacyValues: ['简约-白', '茶韵'],
    },
    blue: {
      key: 'blue',
      label: '蓝',
      className: 'theme-blue',
      primary: '#4D7CB8',
      primarySoft: '#EAF1F8',
      primarySoft2: '#DCE8F4',
      accent: '#385E92',
      gradientSoft: 'linear-gradient(180deg, rgba(77, 124, 184, 0.14) 0%, rgba(77, 124, 184, 0.05) 55%, transparent 100%)',
      borderAccent: 'rgba(77, 124, 184, 0.18)',
      shadowAccent: 'rgba(77, 124, 184, 0.16)',
      legacyValues: ['现代-蓝', '青花瓷'],
    },
    green: {
      key: 'green',
      label: '绿',
      className: 'theme-green',
      primary: '#5F8F74',
      primarySoft: '#EAF3EE',
      primarySoft2: '#DCEADF',
      accent: '#466B56',
      gradientSoft: 'linear-gradient(180deg, rgba(95, 143, 116, 0.14) 0%, rgba(95, 143, 116, 0.05) 55%, transparent 100%)',
      borderAccent: 'rgba(95, 143, 116, 0.18)',
      shadowAccent: 'rgba(95, 143, 116, 0.16)',
      legacyValues: ['中医-绿', '紫禁'],
    },
  },
  getTheme(name?: string | null): ThemeConfig {
    const normalized = name ? normalizeThemeName(name) : this.default;
    return this.themes[normalized];
  },
  getThemeList(): Array<{ value: ThemeName; label: string; color: string }> {
    return (Object.keys(this.themes) as ThemeName[]).map((key) => ({
      value: key,
      label: this.themes[key].label,
      color: this.themes[key].primary,
    }));
  },
  getThemeNames(): ThemeName[] {
    return Object.keys(this.themes) as ThemeName[];
  },
};

const LEGACY_THEME_MAP: Record<string, ThemeName> = Object.values(THEME_CONFIG.themes).reduce<Record<string, ThemeName>>(
  (acc, theme) => {
    const key = theme.key as ThemeName;
    acc[key] = key;
    acc[theme.label] = key;
    theme.legacyValues.forEach((value) => {
      acc[value] = key;
    });
    return acc;
  },
  {}
);

export function normalizeThemeName(name?: string | null): ThemeName {
  if (!name) {
    return THEME_CONFIG.default;
  }

  return LEGACY_THEME_MAP[name] || THEME_CONFIG.default;
}

export function getThemeLabel(name?: string | null): string {
  return THEME_CONFIG.getTheme(name).label;
}

export function getThemeClass(themeName?: string | null): string {
  return THEME_CONFIG.getTheme(themeName).className;
}
