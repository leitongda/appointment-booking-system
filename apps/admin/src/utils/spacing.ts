/**
 * 间距模式配置
 * 支持三种模式：紧凑、标准、宽松
 */

export type SpacingMode = 'compact' | 'standard' | 'comfortable';

// 间距模式标签
export const SPACING_LABELS: Record<SpacingMode, string> = {
  compact: '紧凑',
  standard: '标准',
  comfortable: '宽松',
};

// 间距配置值 (单位: px)
export interface SpacingValues {
  card: number;      // Card 组件的 margin
  section: number;   // 区块之间的间距
  component: number; // 组件之间的间距
  padding: number;   // 内边距
}

export const SPACING_CONFIG: Record<SpacingMode, SpacingValues> = {
  compact: {
    card: 12,
    section: 12,
    component: 8,
    padding: 12,
  },
  standard: {
    card: 16,
    section: 16,
    component: 12,
    padding: 16,
  },
  comfortable: {
    card: 24,
    section: 24,
    component: 16,
    padding: 24,
  },
};

// localStorage key
const STORAGE_KEY = 'admin_spacing_mode';

/**
 * 获取当前间距模式
 */
export function getSpacingMode(): SpacingMode {
  if (typeof window === 'undefined') return 'standard';
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && stored in SPACING_CONFIG) {
    return stored as SpacingMode;
  }
  return 'standard';
}

/**
 * 设置间距模式
 */
export function setSpacingMode(mode: SpacingMode): void {
  localStorage.setItem(STORAGE_KEY, mode);
}

/**
 * 获取当前间距配置值
 */
export function getSpacingValues(): SpacingValues {
  return SPACING_CONFIG[getSpacingMode()];
}

/**
 * 应用 CSS 变量到 document
 */
export function applySpacingCSSVariables(mode: SpacingMode): void {
  if (typeof document === 'undefined') return;
  
  const values = SPACING_CONFIG[mode];
  const root = document.documentElement;
  
  root.style.setProperty('--spacing-card', `${values.card}px`);
  root.style.setProperty('--spacing-section', `${values.section}px`);
  root.style.setProperty('--spacing-component', `${values.component}px`);
  root.style.setProperty('--spacing-padding', `${values.padding}px`);
}

