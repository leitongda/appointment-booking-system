export const ROOT_DROP_ID = '__lowcode_root__';

export const EDITOR_LAYOUT = {
  headerHeight: 60,
  toolbarHeight: 60,
  leftSidebarWidth: 280,
  leftPanelWidth: 280,
  rightPanelWidth: 320,
  canvasPadding: 32,
  canvasRadius: 16,
  bottomBarHeight: 44,
  bottomConsoleHeight: 200,
} as const;

export const EDITOR_COLORS = {
  border: '#ECECEC',
  borderSubtle: '#F3F4F6',
  panelBg: '#FFFFFF',
  workspaceBg: '#F9FAFB',
  itemBg: '#FFFFFF',
  itemHoverBg: '#F9FAFB',
  textSecondary: '#6B7280',
  textMuted: '#9CA3AF',
  primary: '#000000',
  primaryBg: 'rgba(0,0,0,0.04)',
  statusBarBg: '#000000',
  statusText: '#ffffff',
} as const;

export const EDITOR_SPACING = {
  panelPadding: 16,
  sectionPadding: '16px 20px',
  itemGap: 8,
  formItem: 16,
  formItemCompact: 12,
} as const;
