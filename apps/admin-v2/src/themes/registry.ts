import type { ThemePreset } from './types';
import {
  defaultTheme,
  blueTheme,
  greenTheme,
  roseTheme,
  orangeTheme,
  violetTheme,
  catppuccinTheme,
  vercelTheme,
  natureTheme,
  tangerineTheme,
} from './presets';

export const themePresets: ThemePreset[] = [
  defaultTheme,
  blueTheme,
  greenTheme,
  roseTheme,
  orangeTheme,
  violetTheme,
  catppuccinTheme,
  vercelTheme,
  natureTheme,
  tangerineTheme,
];

const themeMap = new Map(themePresets.map(t => [t.name, t]));

export function getThemePreset(name: string): ThemePreset {
  return themeMap.get(name) ?? defaultTheme;
}
