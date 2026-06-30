/**
 * 声明式设计 Hook
 *
 * 提供响应式断点检测
 */
import { useMemo } from 'react';
import { Grid } from 'antd';
import { BREAKPOINTS, RESPONSIVE_CONFIG } from '@/constants/responsive';

import type { Breakpoint } from '@/constants/responsive';

const { useBreakpoint } = Grid;

/**
 * 响应式状态
 */
export interface ResponsiveState {
  /** 当前断点 */
  breakpoint: Breakpoint;
  /** 是否为移动端 */
  isMobile: boolean;
  /** 是否为平板 */
  isTablet: boolean;
  /** 是否为桌面端 */
  isDesktop: boolean;
  /** 屏幕宽度 */
  screenWidth: number;
  /** 当前配置 */
  config: typeof RESPONSIVE_CONFIG;
}

/**
 * 获取响应式状态
 */
export function useResponsive(): ResponsiveState {
  const screens = useBreakpoint();

  return useMemo(() => {
    // 判断当前断点（取最大的匹配断点）
    let currentBreakpoint: Breakpoint = 'xs';
    let screenWidth = 0;

    // 按优先级判断：xxl > xl > lg > md > sm > xs
    if (screens.xxl) {
      currentBreakpoint = 'xxl';
      screenWidth = BREAKPOINTS.xxl;
    } else if (screens.xl) {
      currentBreakpoint = 'xl';
      screenWidth = BREAKPOINTS.xl;
    } else if (screens.lg) {
      currentBreakpoint = 'lg';
      screenWidth = BREAKPOINTS.lg;
    } else if (screens.md) {
      currentBreakpoint = 'md';
      screenWidth = BREAKPOINTS.md;
    } else if (screens.sm) {
      currentBreakpoint = 'sm';
      screenWidth = BREAKPOINTS.sm;
    } else {
      currentBreakpoint = 'xs';
      screenWidth = BREAKPOINTS.xs;
    }

    const isMobile = !screens.md;
    const isTablet = !!(screens.md && !screens.lg);
    const isDesktop = !!screens.lg;

    return {
      breakpoint: currentBreakpoint,
      isMobile,
      isTablet,
      isDesktop,
      screenWidth,
      config: RESPONSIVE_CONFIG,
    };
  }, [screens]);
}

export default useResponsive;
