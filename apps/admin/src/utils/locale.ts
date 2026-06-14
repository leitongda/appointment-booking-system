/**
 * 轻量级 i18n 工具
 *
 * 不引入完整 i18n 框架，仅提供：
 * - 语言偏好持久化（localStorage）
 * - 多语言文本取值函数 t()
 * - 语言切换 hook
 */

export type Locale = 'zh' | 'en';

export type LocaleMap = Record<string, string>;

const LOCALE_KEY = 'admin_locale';

/** 获取当前语言偏好 */
export function getLocale(): Locale {
  const stored = localStorage.getItem(LOCALE_KEY);
  if (stored === 'en') return 'en';
  return 'zh';
}

/** 设置语言偏好 */
export function setLocale(locale: Locale): void {
  localStorage.setItem(LOCALE_KEY, locale);
  // 触发自定义事件，供组件响应
  window.dispatchEvent(new CustomEvent('locale-change', { detail: locale }));
}

/** 从多语言 Map 中取当前语言的值，fallback 到中文 */
export function t(map: LocaleMap | undefined | null): string {
  if (!map) return '';
  const locale = getLocale();
  return map[locale] || map.zh || '';
}
