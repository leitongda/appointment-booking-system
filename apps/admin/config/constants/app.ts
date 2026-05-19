/**
 * 应用全局品牌常量
 *
 * 集中管理应用标题、Logo、主题色等全局品牌相关配置，避免多处硬编码与不一致。
 */

/**
 * 系统标题
 */
export const APP_TITLE = '管理系统';

/**
 * 默认 Logo 路径（本地静态资源，用于登录页等场景）
 */
export const DEFAULT_LOGO = '/logo.svg';

/**
 * Layout 中使用的远程 Logo URL（与 DEFAULT_LOGO 区分用途，保持当前实际呈现不变）
 */
export const LAYOUT_LOGO_URL =
  'https://gw.alipayobjects.com/zos/rmsportal/KDpgvguMpGfqaHPjicRK.svg';

/**
 * 应用主题主色
 *
 * 统一为当前实际生效的 `#722ED1`（修复 config.ts 与 defaultSettings.ts 的不一致）
 */
export const APP_PRIMARY_COLOR = '#1677ff';
