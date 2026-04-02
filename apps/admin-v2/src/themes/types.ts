export interface ThemePreset {
  name: string;
  label: string;
  cssVars: {
    light: Record<string, string>;
    dark: Record<string, string>;
  };
}
