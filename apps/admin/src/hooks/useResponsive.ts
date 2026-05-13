/**
 * 声明式设计 Hook
 *
 * 提供响应式断点检测和布局配置
 */
import { useMemo } from 'react';
import { Grid } from 'antd';
import {
  BREAKPOINTS,
  RESPONSIVE_CONFIG,
  TABLE_CONFIG,
  MODAL_CONFIG,
  FORM_LAYOUT,
} from '@/constants/responsive';

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
    const isTablet = screens.md && !screens.lg;
    const isDesktop = screens.lg;

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

/**
 * 获取表格配置
 */
export function useTableConfig(): typeof TABLE_CONFIG {
  const { breakpoint } = useResponsive();

  return useMemo(() => {
    switch (breakpoint) {
      case 'xs':
      return TABLE_CONFIG.mobile;
      case 'sm':
      return TABLE_CONFIG.tablet;
      default:
        return TABLE_CONFIG.desktop;
    }
  }, [breakpoint]);
}

/**
 * 获取弹窗配置
 */
export function useModalConfig(): typeof MODAL_CONFIG {
  const { breakpoint } = useResponsive();

  return useMemo(() => {
    switch (breakpoint) {
      case 'xs':
      return MODAL_CONFIG.mobile;
      case 'sm':
      return MODAL_CONFIG.tablet;
      default:
        return MODAL_CONFIG.desktop;
    }
  }, [breakpoint]);
}

/**
 * 获取表单布局配置
 */
export function useFormLayoutConfig(): typeof FORM_LAYOUT {
  const { breakpoint } = useResponsive();

  return useMemo(() => {
    switch (breakpoint) {
      case 'xs':
      return FORM_LAYOUT.mobile;
      case 'sm':
      return FORM_LAYOUT.tablet;
      default:
        return FORM_LAYOUT.desktop;
    }
  }, [breakpoint]);
}

/**
 * 获取自适应宽度
 * @param mobileWidth 移动端宽度
 * @param desktopWidth 桌面端宽度
 */
export function useAdaptiveWidth(
  mobileWidth: string | number = '100%',
  desktopWidth: string | number = 'md'
): string | number {
  const { isMobile } = useResponsive();

  return isMobile ? mobileWidth : desktopWidth;
}

/**
 * 获取自适应列宽
 * @param mobileSpan 移动端栅格数
 * @param tabletSpan 平板栅格数
 * @param desktopSpan 桌面端栅格数
 */
export function useAdaptiveColSpan(
  mobileSpan: number = 24,
  tabletSpan: number = 12,
  desktopSpan: number = 8
): number {
  const { isMobile, isTablet } = useResponsive();

  if (isMobile) return mobileSpan;
  if (isTablet) return tabletSpan;
  return desktopSpan;
}

export default useResponsive;
