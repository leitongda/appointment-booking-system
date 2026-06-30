import { theme } from 'antd';
import type { ThemeConfig } from 'antd';
import { getSpacingMode, SPACING_CONFIG } from '@/utils/spacing';

/**
 * 颜色 Token 映射
 *
 * 将 CSS 变量（color-tokens.less）映射为 antd token，确保 antd 组件与自定义组件颜色一致。
 * 新代码应优先使用 antd token（如 theme.token.colorPrimary），CSS 变量作为 fallback。
 */
const COLOR_TOKENS: Partial<ThemeConfig['token']> = {
  // 主色
  colorPrimary: '#1677ff',
  colorPrimaryBg: '#e6f4ff',
  colorPrimaryBgHover: '#bae0ff',
  colorPrimaryBorder: '#91caff',
  colorPrimaryBorderHover: '#69b1ff',
  colorPrimaryHover: '#4096ff',
  colorPrimaryActive: '#0958d9',
  colorPrimaryTextHover: '#4096ff',
  colorPrimaryText: '#1677ff',
  colorPrimaryTextActive: '#0958d9',

  // 功能色
  colorSuccess: '#52c41a',
  colorWarning: '#faad14',
  colorError: '#ff4d4f',
  colorInfo: '#1677ff',

  // 文字色
  colorText: 'rgba(0, 0, 0, 0.88)',
  colorTextSecondary: 'rgba(0, 0, 0, 0.65)',
  colorTextTertiary: 'rgba(0, 0, 0, 0.45)',
  colorTextQuaternary: 'rgba(0, 0, 0, 0.25)',

  // 背景色
  colorBgContainer: '#ffffff',
  colorBgElevated: '#ffffff',
  colorBgLayout: '#f5f5f5',
  colorBgSpotlight: 'rgba(0, 0, 0, 0.85)',

  // 边框色
  colorBorder: '#d9d9d9',
  colorBorderSecondary: '#f0f0f0',

  // 填充色
  colorFill: 'rgba(0, 0, 0, 0.15)',
  colorFillSecondary: 'rgba(0, 0, 0, 0.06)',
  colorFillTertiary: 'rgba(0, 0, 0, 0.04)',
  colorFillQuaternary: 'rgba(0, 0, 0, 0.02)',
};

export function getThemeConfig(): { algorithm: typeof theme.defaultAlgorithm; tokenConfig: ThemeConfig['token'] } {
  const spacingMode = getSpacingMode();
  const spacingValues = SPACING_CONFIG[spacingMode];

  const algorithm = spacingMode === 'compact' ? theme.compactAlgorithm : theme.defaultAlgorithm;

  const tokenConfig: ThemeConfig['token'] = {
    // 间距 token
    padding: spacingValues.padding,
    paddingLG: spacingValues.padding + 8,
    paddingSM: spacingValues.padding - 4,
    paddingXS: spacingValues.padding - 8,
    margin: spacingValues.component,
    marginLG: spacingValues.section,
    marginSM: spacingValues.component - 4,
    marginXS: spacingValues.component - 8,
    // 颜色 token
    ...COLOR_TOKENS,
  };

  return { algorithm, tokenConfig };
}
