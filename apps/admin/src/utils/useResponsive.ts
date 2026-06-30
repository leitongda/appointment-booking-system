/**
 * 响应式工具 Hook
 *
 * 提供断点检测和响应式布局工具。
 * 基于 antd 的 Grid 系统断点：
 * - xs: <576px（手机）
 * - sm: ≥576px（大手机/小平板）
 * - md: ≥768px（平板）
 * - lg: ≥992px（小桌面）
 * - xl: ≥1200px（桌面）
 * - xxl: ≥1600px（大桌面）
 */
import { useState, useEffect } from 'react';

/** 断点定义（与 antd Grid 一致） */
export const BREAKPOINTS = {
  xs: 576,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
} as const;

export type Breakpoint = keyof typeof BREAKPOINTS;

/**
 * 响应式断点 Hook
 *
 * @example
 * ```tsx
 * const { isMobile, isTablet, isDesktop, breakpoint } = useResponsive();
 *
 * if (isMobile) {
 *   return <MobileLayout />;
 * }
 * ```
 */
export function useResponsive() {
  const [width, setWidth] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth;
    }
    return 1200; // 默认桌面宽度
  });

  useEffect(() => {
    const handleResize = () => {
      setWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const breakpoint: Breakpoint =
    width < BREAKPOINTS.xs
      ? 'xs'
      : width < BREAKPOINTS.md
        ? 'sm'
        : width < BREAKPOINTS.lg
          ? 'md'
          : width < BREAKPOINTS.xl
            ? 'lg'
            : width < BREAKPOINTS.xxl
              ? 'xl'
              : 'xxl';

  return {
    width,
    breakpoint,
    isMobile: width < BREAKPOINTS.md,
    isTablet: width >= BREAKPOINTS.md && width < BREAKPOINTS.lg,
    isDesktop: width >= BREAKPOINTS.lg,
    isWide: width >= BREAKPOINTS.xl,
  };
}

/**
 * 响应式列数 Hook（用于网格布局）
 *
 * @example
 * ```tsx
 * const cols = useResponsiveCols({ xs: 1, sm: 2, md: 3, lg: 4 });
 * // 在手机上返回 1 列，平板 2 列，桌面 3 列，大桌面 4 列
 * ```
 */
export function useResponsiveCols(config: Partial<Record<Breakpoint, number>>): number {
  const { breakpoint } = useResponsive();

  // 从大到小查找匹配的断点
  const order: Breakpoint[] = ['xxl', 'xl', 'lg', 'md', 'sm', 'xs'];
  for (const bp of order) {
    if (config[bp] !== undefined && breakpoint >= bp) {
      return config[bp]!;
    }
  }

  // 兜底：返回最小断点的值或默认 1
  return config.xs ?? 1;
}

/**
 * 响应式值 Hook
 *
 * @example
 * ```tsx
 * const padding = useResponsiveValue({ xs: 8, md: 16, lg: 24 });
 * const showSidebar = useResponsiveValue({ xs: false, lg: true });
 * ```
 */
export function useResponsiveValue<T>(config: Partial<Record<Breakpoint, T>>): T | undefined {
  const { breakpoint } = useResponsive();

  const order: Breakpoint[] = ['xxl', 'xl', 'lg', 'md', 'sm', 'xs'];
  for (const bp of order) {
    if (config[bp] !== undefined && breakpoint >= bp) {
      return config[bp];
    }
  }

  return config.xs;
}
