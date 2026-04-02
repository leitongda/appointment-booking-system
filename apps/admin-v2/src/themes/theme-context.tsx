import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';
import { useTheme } from 'next-themes';
import { getThemePreset, themePresets } from './registry';
import { applyTheme } from './apply-theme';
import type { ThemePreset } from './types';

const STORAGE_KEY = 'admin-v2-theme';

interface ThemePresetContextValue {
  themeName: string;
  preset: ThemePreset;
  setTheme: (name: string) => void;
  presets: ThemePreset[];
}

const ThemePresetContext = createContext<ThemePresetContextValue | null>(null);

export function ThemePresetProvider({ children }: { children: ReactNode }) {
  const [themeName, setThemeName] = useState(() => {
    return localStorage.getItem(STORAGE_KEY) || 'default';
  });
  const { resolvedTheme } = useTheme();

  const preset = getThemePreset(themeName);

  const setTheme = useCallback((name: string) => {
    const p = getThemePreset(name);
    localStorage.setItem(STORAGE_KEY, name);
    setThemeName(name);
    const mode = resolvedTheme === 'dark' ? 'dark' : 'light';
    applyTheme(p, mode);
  }, [resolvedTheme]);

  // 颜色主题或明暗模式变化时重新应用
  useEffect(() => {
    const mode = resolvedTheme === 'dark' ? 'dark' : 'light';
    applyTheme(preset, mode);
  }, [themeName, resolvedTheme, preset]);

  return (
    <ThemePresetContext.Provider value={{ themeName, preset, setTheme, presets: themePresets }}>
      {children}
    </ThemePresetContext.Provider>
  );
}

export function useThemePreset() {
  const ctx = useContext(ThemePresetContext);
  if (!ctx) throw new Error('useThemePreset must be used within ThemePresetProvider');
  return ctx;
}
