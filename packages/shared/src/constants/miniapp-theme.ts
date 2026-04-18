export type MiniappThemeName = 'red' | 'yellow' | 'blue' | 'green';
export type MiniappStoreThemeValue = '中医-红' | '茶韵' | '现代-蓝' | '中医-绿';

export interface MiniappThemePreset {
  key: MiniappThemeName;
  label: string;
  optionLabel: string;
  storeThemeValue: MiniappStoreThemeValue;
  primary: string;
  primarySoft: string;
  primarySoft2: string;
  accent: string;
  gradientSoft: string;
  borderAccent: string;
  shadowAccent: string;
  legacyValues: string[];
}

export const DEFAULT_MINIAPP_THEME: MiniappThemeName = 'blue';

export const MINIAPP_THEME_PRESETS: MiniappThemePreset[] = [
  {
    key: 'red',
    label: '红',
    optionLabel: '红色主题',
    storeThemeValue: '中医-红',
    primary: '#B85A5F',
    primarySoft: '#F5E8E8',
    primarySoft2: '#EED9DA',
    accent: '#8E4348',
    gradientSoft: 'linear-gradient(180deg, rgba(184, 90, 95, 0.12) 0%, rgba(184, 90, 95, 0.04) 55%, transparent 100%)',
    borderAccent: 'rgba(184, 90, 95, 0.18)',
    shadowAccent: 'rgba(184, 90, 95, 0.16)',
    legacyValues: ['中医-红', '故宫红'],
  },
  {
    key: 'yellow',
    label: '黄',
    optionLabel: '黄色主题',
    storeThemeValue: '茶韵',
    primary: '#A98B57',
    primarySoft: '#F6F0E3',
    primarySoft2: '#EBDDCA',
    accent: '#8B7145',
    gradientSoft: 'linear-gradient(180deg, rgba(169, 139, 87, 0.14) 0%, rgba(169, 139, 87, 0.05) 55%, transparent 100%)',
    borderAccent: 'rgba(169, 139, 87, 0.18)',
    shadowAccent: 'rgba(169, 139, 87, 0.14)',
    legacyValues: ['简约-白', '茶韵'],
  },
  {
    key: 'blue',
    label: '蓝',
    optionLabel: '蓝色主题',
    storeThemeValue: '现代-蓝',
    primary: '#4D7CB8',
    primarySoft: '#EAF1F8',
    primarySoft2: '#DCE8F4',
    accent: '#385E92',
    gradientSoft: 'linear-gradient(180deg, rgba(77, 124, 184, 0.14) 0%, rgba(77, 124, 184, 0.05) 55%, transparent 100%)',
    borderAccent: 'rgba(77, 124, 184, 0.18)',
    shadowAccent: 'rgba(77, 124, 184, 0.16)',
    legacyValues: ['现代-蓝', '青花瓷'],
  },
  {
    key: 'green',
    label: '绿',
    optionLabel: '绿色主题',
    storeThemeValue: '中医-绿',
    primary: '#5F8F74',
    primarySoft: '#EAF3EE',
    primarySoft2: '#DCEADF',
    accent: '#466B56',
    gradientSoft: 'linear-gradient(180deg, rgba(95, 143, 116, 0.14) 0%, rgba(95, 143, 116, 0.05) 55%, transparent 100%)',
    borderAccent: 'rgba(95, 143, 116, 0.18)',
    shadowAccent: 'rgba(95, 143, 116, 0.16)',
    legacyValues: ['中医-绿', '紫禁'],
  },
];

export const MINIAPP_THEME_MAP: Record<MiniappThemeName, MiniappThemePreset> = MINIAPP_THEME_PRESETS.reduce(
  (acc, theme) => {
    acc[theme.key] = theme;
    return acc;
  },
  {} as Record<MiniappThemeName, MiniappThemePreset>
);

export const MINIAPP_THEME_ALIAS_MAP: Record<string, MiniappThemeName> = MINIAPP_THEME_PRESETS.reduce(
  (acc, theme) => {
    acc[theme.key] = theme.key;
    acc[theme.label] = theme.key;
    acc[theme.storeThemeValue] = theme.key;
    theme.legacyValues.forEach((value) => {
      acc[value] = theme.key;
    });
    return acc;
  },
  {} as Record<string, MiniappThemeName>
);

export const DEFAULT_MINIAPP_STORE_THEME = MINIAPP_THEME_MAP[DEFAULT_MINIAPP_THEME].storeThemeValue;

export const MINIAPP_STORE_THEME_OPTIONS = MINIAPP_THEME_PRESETS.map((theme) => ({
  label: theme.optionLabel,
  value: theme.storeThemeValue,
  color: theme.primary,
  themeName: theme.key,
}));

export function normalizeMiniappThemeName(name?: string | null): MiniappThemeName {
  if (!name) {
    return DEFAULT_MINIAPP_THEME;
  }

  return MINIAPP_THEME_ALIAS_MAP[name] || DEFAULT_MINIAPP_THEME;
}

export function getMiniappThemePreset(name?: string | null): MiniappThemePreset {
  return MINIAPP_THEME_MAP[normalizeMiniappThemeName(name)];
}

export function getMiniappThemeLabel(name?: string | null): string {
  return getMiniappThemePreset(name).label;
}

export function getMiniappThemeOptionLabel(name?: string | null): string {
  return getMiniappThemePreset(name).optionLabel;
}

export function getMiniappStoreThemeValue(name?: string | null): MiniappStoreThemeValue {
  return getMiniappThemePreset(name).storeThemeValue;
}
