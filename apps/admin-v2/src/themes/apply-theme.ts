import type { ThemePreset } from './types';

export function applyTheme(preset: ThemePreset, mode: 'light' | 'dark') {
  const root = document.documentElement;
  const vars = preset.cssVars[mode];
  for (const [key, value] of Object.entries(vars)) {
    root.style.setProperty(`--${key}`, value);
  }
}
