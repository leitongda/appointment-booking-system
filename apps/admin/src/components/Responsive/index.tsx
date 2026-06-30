/**
 * 响应式布局组件
 *
 * 提供响应式容器、网格、显示/隐藏等组件。
 */
import React from 'react';
import { useResponsive, useResponsiveCols, type Breakpoint } from '@/utils/useResponsive';

// ==================== ResponsiveContainer ====================

export interface ResponsiveContainerProps {
  children: React.ReactNode;
  /** 移动端最大宽度 */
  maxWidth?: number;
  /** 是否居中 */
  centered?: boolean;
  /** 自定义样式 */
  style?: React.CSSProperties;
  /** 自定义类名 */
  className?: string;
}

/**
 * 响应式容器
 *
 * 在移动端自动限制最大宽度并居中。
 */
export const ResponsiveContainer: React.FC<ResponsiveContainerProps> = ({
  children,
  maxWidth = 1200,
  centered = true,
  style,
  className,
}) => {
  const { isMobile } = useResponsive();

  return (
    <div
      style={{
        maxWidth: isMobile ? '100%' : maxWidth,
        margin: centered ? '0 auto' : undefined,
        padding: isMobile ? '0 8px' : '0 16px',
        ...style,
      }}
      className={className}
    >
      {children}
    </div>
  );
};

// ==================== ResponsiveGrid ====================

export interface ResponsiveGridProps {
  children: React.ReactNode;
  /** 各断点列数配置 */
  cols?: Partial<Record<Breakpoint, number>>;
  /** 间距 */
  gap?: number;
  /** 自定义样式 */
  style?: React.CSSProperties;
  /** 自定义类名 */
  className?: string;
}

/**
 * 响应式网格
 *
 * @example
 * ```tsx
 * <ResponsiveGrid cols={{ xs: 1, sm: 2, md: 3, lg: 4 }}>
 *   <Card>1</Card>
 *   <Card>2</Card>
 *   <Card>3</Card>
 *   <Card>4</Card>
 * </ResponsiveGrid>
 * ```
 */
export const ResponsiveGrid: React.FC<ResponsiveGridProps> = ({
  children,
  cols = { xs: 1, sm: 2, md: 3, lg: 4 },
  gap = 16,
  style,
  className,
}) => {
  const colCount = useResponsiveCols(cols);

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${colCount}, 1fr)`,
        gap,
        ...style,
      }}
      className={className}
    >
      {children}
    </div>
  );
};

// ==================== ShowOn / HideOn ====================

export interface ResponsiveShowProps {
  children: React.ReactNode;
  /** 在哪些断点显示 */
  breakpoints: Breakpoint[];
}

/**
 * 在指定断点显示内容
 *
 * @example
 * ```tsx
 * <ShowOn breakpoints={['lg', 'xl', 'xxl']}>
 *   <Sidebar />
 * </ShowOn>
 * ```
 */
export const ShowOn: React.FC<ResponsiveShowProps> = ({ children, breakpoints }) => {
  const { breakpoint } = useResponsive();

  if (!breakpoints.includes(breakpoint)) {
    return null;
  }

  return <>{children}</>;
};

/**
 * 在指定断点隐藏内容
 *
 * @example
 * ```tsx
 * <HideOn breakpoints={['xs', 'sm']}>
 *   <DesktopOnlyContent />
 * </HideOn>
 * ```
 */
export const HideOn: React.FC<ResponsiveShowProps> = ({ children, breakpoints }) => {
  const { breakpoint } = useResponsive();

  if (breakpoints.includes(breakpoint)) {
    return null;
  }

  return <>{children}</>;
};

// ==================== ResponsiveStats ====================

export interface ResponsiveStatsProps {
  children: React.ReactNode;
  /** 自定义样式 */
  style?: React.CSSProperties;
}

/**
 * 响应式统计卡片网格
 *
 * 自动根据屏幕宽度调整列数：手机 2 列，平板 3 列，桌面 4 列，大桌面 5 列。
 */
export const ResponsiveStats: React.FC<ResponsiveStatsProps> = ({ children, style }) => {
  return (
    <ResponsiveGrid
      cols={{ xs: 2, sm: 2, md: 3, lg: 4, xl: 5 }}
      gap={16}
      style={style}
    >
      {children}
    </ResponsiveGrid>
  );
};
