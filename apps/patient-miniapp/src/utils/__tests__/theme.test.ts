import { beforeEach, describe, expect, test, vi } from 'vitest';
import { STORAGE_KEYS, normalizeMiniappThemeName } from '@hospital/shared';
import {
  FOLLOW_STORE_THEME,
  applyTheme,
  getCurrentTheme,
  getStoreDefaultThemeName,
  getThemeSelection,
  getThemeStyleObject,
  initThemeFromStore,
  resetThemeToStore,
} from '../theme';

const { storage, trigger } = vi.hoisted(() => ({
  storage: new Map<string, unknown>(),
  trigger: vi.fn(),
}));

vi.mock('@tarojs/taro', () => ({
  default: {
    getStorageSync: (key: string) => storage.get(key),
    setStorageSync: (key: string, value: unknown) => storage.set(key, value),
    removeStorageSync: (key: string) => storage.delete(key),
    setNavigationBarColor: vi.fn().mockResolvedValue(undefined),
    eventCenter: {
      on: vi.fn(),
      off: vi.fn(),
      trigger,
    },
  },
}));

vi.mock('../store', () => ({
  getStoreId: vi.fn(() => ''),
}));

describe('theme utils', () => {
  beforeEach(() => {
    storage.clear();
    trigger.mockClear();
  });

  test('normalizeMiniappThemeName maps legacy theme values to compact theme names', () => {
    expect(normalizeMiniappThemeName('中医-红')).toBe('red');
    expect(normalizeMiniappThemeName('茶韵')).toBe('yellow');
    expect(normalizeMiniappThemeName('现代-蓝')).toBe('blue');
    expect(normalizeMiniappThemeName('中医-绿')).toBe('green');
    expect(normalizeMiniappThemeName('unknown-theme')).toBe('blue');
  });

  test('getThemeStyleObject derives compatibility css variables from theme config', () => {
    const styleObject = getThemeStyleObject('green');

    expect(styleObject['--theme-primary']).toBe('#5F8F74');
    expect(styleObject['--color-primary']).toBe('#5F8F74');
    expect(styleObject['--color-primary-dark']).toBe('#466B56');
    expect(styleObject['--gradient-primary']).toContain('#5F8F74');
    expect(styleObject['--gradient-light']).toContain('#DCEADF');
  });

  test('initThemeFromStore prefers stored user override and marks selection as custom', () => {
    storage.set(`${STORAGE_KEYS.CURRENT_THEME}:store-1`, '中医-红');

    initThemeFromStore('现代-蓝', 'store-1');

    expect(getCurrentTheme()).toBe('red');
    expect(getThemeSelection('store-1')).toBe('red');
  });

  test('resetThemeToStore clears stored override and returns to store default theme', () => {
    applyTheme('中医-红', 'store-1');
    expect(storage.get(`${STORAGE_KEYS.CURRENT_THEME}:store-1`)).toBe('red');

    resetThemeToStore('中医-绿', 'store-1');

    expect(storage.has(`${STORAGE_KEYS.CURRENT_THEME}:store-1`)).toBe(false);
    expect(getCurrentTheme()).toBe('green');
    expect(getThemeSelection('store-1')).toBe(FOLLOW_STORE_THEME);
  });

  test('getStoreDefaultThemeName falls back to store context and then system default', () => {
    storage.set(STORAGE_KEYS.STORE_CONTEXT, {
      storeId: 'store-1',
      storeTheme: '茶韵',
    });

    expect(getStoreDefaultThemeName(undefined, 'store-1')).toBe('yellow');
    expect(getStoreDefaultThemeName(undefined, 'another-store')).toBe('blue');
  });
});
