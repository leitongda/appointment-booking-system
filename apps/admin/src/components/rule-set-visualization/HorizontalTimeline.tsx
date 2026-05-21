/**
 * 横向时间轴可视化组件（SVG 版本）
 * 将时间窗配置转换为直观的横向时间轴展示
 */

import React, { useMemo, useRef, useState, useEffect } from 'react';
import { Empty, theme } from 'antd';
import dayjs from 'dayjs';
import type { RuleWindow } from '@hospital/shared';
import {
  calculateTimelineRange,
  timeToRatio,
  generateTimeTicks,
  calculateWindowTime,
  type TimelineRange,
} from '@/utils/ruleSetFormatter';
import { isUnlimitedOffset } from '@/constants/rule-set';

// ==================== 类型定义 ====================

export interface HorizontalTimelineProps {
  windows: RuleWindow[];
  shiftStart: Date;
  shiftEnd: Date;
  bookingCreatedAt?: Date;
  showShiftLabel?: boolean;
  showTimeLabels?: boolean;
  showWindowLabels?: boolean;
  showLegend?: boolean;
  compact?: boolean;
  height?: number;
  style?: React.CSSProperties;
  className?: string;
}

// ==================== 常量定义 ====================

interface WindowColorConfig {
  fill: string;
  stroke: string;
  label: string;
  gradientStart: string;
  gradientEnd: string;
  unlimitedPattern?: string;  // 不限制时的图案/颜色
}

const WINDOW_COLORS: Record<string, WindowColorConfig> = {
  BOOK: {
    fill: 'rgba(24, 144, 255, 0.2)',
    stroke: '#1890ff',
    label: '预约',
    gradientStart: 'rgba(24, 144, 255, 0.4)',
    gradientEnd: 'rgba(24, 144, 255, 0.1)',
    unlimitedPattern: 'rgba(24, 144, 255, 0.08)',
  },
  CHECKIN: {
    fill: 'rgba(82, 196, 26, 0.2)',
    stroke: '#52c41a',
    label: '签到',
    gradientStart: 'rgba(82, 196, 26, 0.4)',
    gradientEnd: 'rgba(82, 196, 26, 0.1)',
    unlimitedPattern: 'rgba(82, 196, 26, 0.08)',
  },
  CANCEL: {
    fill: 'rgba(250, 140, 22, 0.2)',
    stroke: '#fa8c16',
    label: '取消',
    gradientStart: 'rgba(250, 140, 22, 0.4)',
    gradientEnd: 'rgba(250, 140, 22, 0.1)',
    unlimitedPattern: 'rgba(250, 140, 22, 0.08)',
  },
  HOLD_RELEASE: {
    fill: 'rgba(114, 46, 209, 0.2)',
    stroke: '#722ed1',
    label: '释放',
    gradientStart: 'rgba(114, 46, 209, 0.4)',
    gradientEnd: 'rgba(114, 46, 209, 0.1)',
    unlimitedPattern: 'rgba(114, 46, 209, 0.08)',
  },
};

const TIMELINE_CONFIG = {
  // 班次背景
  shiftBackground: '#fafafa',
  shiftBorder: '#d9d9d9',
  shiftLabelColor: '#999',

  // 坐标轴
  axisColor: '#d9d9d9',
  tickColor: '#d9d9d9',
  textColor: '#999',

  // 不限制状态样式
  unlimitedDashArray: '4 4',  // 虚线样式
  unlimitedArrowSize: 12,      // 不限制箭头大小
  infinitySymbolSize: 14,      // ∞ 符号大小

  // 尺寸
  paddingTop: 30,
  paddingBottom: 20,
  barHeight: 32,
  barSpacing: 8,
  minTickWidth: 80,           // 每个刻度的最小宽度（像素）
  tickIntervalSeconds: 1800,  // 刻度间隔（30分钟）
};

// ==================== 主组件 ====================

/**
 * 横向时间轴组件（SVG 版本）
 */
const HorizontalTimeline: React.FC<HorizontalTimelineProps> = ({
  windows,
  shiftStart,
  shiftEnd,
  bookingCreatedAt,
  showShiftLabel = true,
  showTimeLabels = true,
  showWindowLabels = true,
  showLegend = true,
  compact = false,
  height = 140,
  style,
  className,
}) => {
  const { token } = theme.useToken();
  const svgRef = useRef<SVGSVGElement>(null);
  const [svgWidth, setSvgWidth] = useState(0);
  const [isReady, setIsReady] = useState(false);

  // 响应式处理
  useEffect(() => {
    const updateWidth = () => {
      if (svgRef.current) {
        const rect = svgRef.current.getBoundingClientRect();
        const parentElement = svgRef.current.parentElement;
        const newWidth = rect.width || (parentElement?.getBoundingClientRect().width || 0);
        // 只要获取到宽度就更新（即使是 0），并标记为已就绪
        setSvgWidth(Math.max(newWidth, 300));
        setIsReady(true);
      } else {
        // 如果 ref 还没准备好，设置默认宽度并标记为已就绪
        setSvgWidth(300);
        setIsReady(true);
      }
    };

    // 初始延迟执行，确保 DOM 已渲染
    const timer = setTimeout(() => {
      updateWidth();
    }, 100);

    // 使用 requestAnimationFrame 作为备用
    const rafId = requestAnimationFrame(() => {
      setTimeout(updateWidth, 0);
    });

    const resizeObserver = new ResizeObserver(() => {
      updateWidth();
    });

    // 当 ref 准备好后再添加 observer
    const observerTimer = setTimeout(() => {
      if (svgRef.current) {
        resizeObserver.observe(svgRef.current);
      }
    }, 0);

    return () => {
      clearTimeout(timer);
      clearTimeout(observerTimer);
      cancelAnimationFrame(rafId);
      resizeObserver.disconnect();
    };
  }, []);

  // 计算时间轴范围
  const timelineRange = useMemo<TimelineRange>(() => {
    return calculateTimelineRange(shiftStart, shiftEnd, windows, bookingCreatedAt);
  }, [shiftStart, shiftEnd, windows, bookingCreatedAt]);

  // 计算班次比例位置
  const shiftRatio = useMemo(() => {
    return {
      start: timeToRatio(shiftStart, timelineRange),
      end: timeToRatio(shiftEnd, timelineRange),
    };
  }, [shiftStart, shiftEnd, timelineRange]);

  // 生成时间刻度
  const timeTicks = useMemo(() => {
    if (!showTimeLabels) return [];
    // 传递 shiftStart 作为对齐参考点，确保刻度与班次时间和时间窗边界对齐
    return generateTimeTicks(timelineRange, svgWidth, 10, shiftStart);
  }, [timelineRange, svgWidth, showTimeLabels, shiftStart]);

  // 计算启用的时间窗
  const enabledWindows = useMemo(() => {
    return windows.filter((w) => w.enabled);
  }, [windows]);

  // SVG 尺寸配置
  const config = useMemo(() => {
    const barHeight = compact ? 20 : TIMELINE_CONFIG.barHeight;
    const barSpacing = compact ? 4 : TIMELINE_CONFIG.barSpacing;
    const totalBars = enabledWindows.length;
    const timelineHeight = barHeight * totalBars + barSpacing * (totalBars - 1) + TIMELINE_CONFIG.paddingTop + TIMELINE_CONFIG.paddingBottom;

    // 计算时间范围的秒数
    const totalSeconds = dayjs(timelineRange.max).diff(dayjs(timelineRange.min), 'second');

    // 根据刻度间隔（30分钟）计算需要的刻度数量
    const tickCount = Math.ceil(totalSeconds / TIMELINE_CONFIG.tickIntervalSeconds) + 1;

    // 根据刻度数量和最小刻度宽度计算图表宽度
    const minChartWidth = tickCount * TIMELINE_CONFIG.minTickWidth;

    // 容器宽度（用于判断是否需要滚动）
    const containerWidth = svgWidth > 0 ? svgWidth : 800;

    // 图表宽度取容器宽度和最小宽度的较大值
    const chartWidth = Math.max(containerWidth, minChartWidth);

    return {
      ...TIMELINE_CONFIG,
      // 从 token 获取颜色配置
      shiftBackground: token.colorFillAlter,
      shiftBorder: token.colorBorderSecondary,
      shiftLabelColor: token.colorTextTertiary,
      axisColor: token.colorBorderSecondary,
      tickColor: token.colorBorderSecondary,
      textColor: token.colorTextTertiary,
      barHeight,
      barSpacing,
      totalHeight: Math.max(height, timelineHeight),
      width: chartWidth,
      chartLeft: 60,
      chartRight: 20,
      chartWidth: chartWidth - 80, // 减去左右边距
      containerWidth,
      needsScroll: chartWidth > containerWidth,
    };
  }, [enabledWindows.length, compact, height, svgWidth, timelineRange, timeTicks.length, token]);

  // 坐标转换：时间转 X 坐标
  const timeToX = (time: Date): number => {
    const ratio = timeToRatio(time, timelineRange);
    return config.chartLeft + ratio * config.chartWidth;
  };

  // 计算每个时间窗的渲染数据（必须在条件判断之前调用所有 hooks）
  const windowRenderData = useMemo(() => {
    return enabledWindows.map((window, index) => {
      // 为没有 id 的时间窗生成临时 id
      const windowId = window.id || `temp-${index}`;

      const openTime = calculateWindowTime(
        window.referencePoint,
        window.openOffsetSec,
        shiftStart,
        shiftEnd,
        bookingCreatedAt
      );
      const closeTime = calculateWindowTime(
        window.referencePoint,
        window.closeOffsetSec,
        shiftStart,
        shiftEnd,
        bookingCreatedAt
      );

      // 判断是否"不限制"
      const hasNoOpenLimit = isUnlimitedOffset(window.openOffsetSec);
      const hasNoCloseLimit = isUnlimitedOffset(window.closeOffsetSec);

      // 计算显示范围
      let displayStart = openTime || timelineRange.min;
      let displayEnd = closeTime || timelineRange.max;

      // 如果没有开始限制，从图表左边缘开始
      if (hasNoOpenLimit) {
        displayStart = timelineRange.min;
      }
      // 如果没有结束限制，到图表右边缘结束
      if (hasNoCloseLimit) {
        displayEnd = timelineRange.max;
      }

      const x1 = timeToX(displayStart);
      const x2 = timeToX(displayEnd);
      const y = TIMELINE_CONFIG.paddingTop + index * (config.barHeight + config.barSpacing);

      const colorConfig = WINDOW_COLORS[window.action] || WINDOW_COLORS.BOOK;

      return {
        window,
        windowId,
        x1,
        x2,
        y,
        width: Math.max(x2 - x1, 2),
        colorConfig,
        hasNoOpenLimit,
        hasNoCloseLimit,
        extendsBefore: x1 < config.chartLeft,
        extendsAfter: x2 > config.chartLeft + config.chartWidth,
      };
    });
  }, [enabledWindows, timelineRange, shiftStart, shiftEnd, bookingCreatedAt, config]);

  // 生成渐变定义和图案
  const defs = useMemo(() => {
    return (
      <>
        {/* 箭头标记 - 普通边界 */}
        <marker
          id="arrow-boundary-left"
          markerWidth="10"
          markerHeight="10"
          refX="0"
          refY="3"
          orient="auto"
          markerUnits="strokeWidth"
        >
          <path d="M9,0 L9,6 L0,3 z" fill="#bfbfbf" />
        </marker>
        <marker
          id="arrow-boundary-right"
          markerWidth="10"
          markerHeight="10"
          refX="10"
          refY="3"
          orient="auto"
          markerUnits="strokeWidth"
        >
          <path d="M0,0 L0,6 L9,3 z" fill="#bfbfbf" />
        </marker>

        {/* 箭头标记 - 不限制边界（带颜色） */}
        {enabledWindows.map((window, index) => {
          const colorConfig = WINDOW_COLORS[window.action];
          if (!colorConfig) return null;

          const windowId = window.id || `temp-${index}`;

          return (
            <React.Fragment key={`markers-${windowId}`}>
              <marker
                id={`arrow-unlimited-left-${windowId}`}
                markerWidth="12"
                markerHeight="12"
                refX="0"
                refY="6"
                orient="auto"
              >
                <path d={`M10,0 L10,12 L0,6 z`} fill={colorConfig.stroke} opacity={0.6} />
              </marker>
              <marker
                id={`arrow-unlimited-right-${windowId}`}
                markerWidth="12"
                markerHeight="12"
                refX="12"
                refY="6"
                orient="auto"
              >
                <path d={`M0,0 L0,12 L10,6 z`} fill={colorConfig.stroke} opacity={0.6} />
              </marker>
            </React.Fragment>
          );
        })}

        {/* 渐变定义 */}
        {enabledWindows.map((window, index) => {
          const colorConfig = WINDOW_COLORS[window.action];
          if (!colorConfig) return null;

          const windowId = window.id || `temp-${index}`;

          return (
            <linearGradient
              key={`gradient-${windowId}`}
              id={`gradient-${windowId}`}
              x1="0%"
              y1="0%"
              x2="100%"
              y2="0%"
            >
              <stop offset="0%" stopColor={colorConfig.gradientStart} />
              <stop offset="100%" stopColor={colorConfig.gradientEnd} />
            </linearGradient>
          );
        })}

        {/* 不限制的渐变淡出效果 */}
        {enabledWindows.map((window, index) => {
          const colorConfig = WINDOW_COLORS[window.action];
          if (!colorConfig) return null;

          const windowId = window.id || `temp-${index}`;

          return (
            <React.Fragment key={`fade-${windowId}`}>
              {/* 左侧淡出 */}
              <linearGradient
                id={`fade-left-${windowId}`}
                x1="100%"
                y1="0%"
                x2="0%"
                y2="0%"
              >
                <stop offset="0%" stopColor={colorConfig.stroke} stopOpacity={0.4} />
                <stop offset="100%" stopColor={colorConfig.stroke} stopOpacity={0} />
              </linearGradient>
              {/* 右侧淡出 */}
              <linearGradient
                id={`fade-right-${windowId}`}
                x1="0%"
                y1="0%"
                x2="100%"
                y2="0%"
              >
                <stop offset="0%" stopColor={colorConfig.stroke} stopOpacity={0.4} />
                <stop offset="100%" stopColor={colorConfig.stroke} stopOpacity={0} />
              </linearGradient>
            </React.Fragment>
          );
        })}

        {/* 斜线图案 - 用于不限制区域 */}
        <pattern
          id="diagonal-hatch"
          patternUnits="userSpaceOnUse"
          width="4"
          height="4"
          patternTransform="rotate(45)"
        >
          <rect width="2" height="4" transform="translate(0,0)" fill="rgba(0,0,0,0.03)" />
        </pattern>
      </>
    );
  }, [enabledWindows]);

  // 如果没有启用的时间窗，显示提示
  if (enabledWindows.length === 0) {
    return (
      <div className={className} style={{ ...style, padding: '24px 0', textAlign: 'center' }}>
        <Empty description="暂无时间窗配置" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  // 如果 SVG 还未准备好，显示占位符
  if (!isReady) {
    return (
      <div
        className={className}
        style={{
          ...style,
          height: config.totalHeight,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: token.colorBgContainer,
          borderRadius: 4,
        }}
      >
        <span style={{ color: token.colorTextTertiary }}>加载时间轴...</span>
      </div>
    );
  }

  return (
    <div className={className} style={style}>
      {/* 可滚动容器 */}
      <div
        style={{
          overflowX: config.needsScroll ? 'auto' : 'visible',
          overflowY: 'hidden',
          maxWidth: '100%',
        }}
      >
        <svg
          ref={svgRef}
          width={config.width}
          height={config.totalHeight}
          style={{ overflow: 'visible' }}
        >
          <defs>{defs}</defs>

        {/* 时间刻度 */}
        {showTimeLabels && timeTicks.map((tick, index) => {
          const x = config.chartLeft + tick.position * config.chartWidth;
          return (
            <g key={`tick-${index}`}>
              {/* 刻度线 */}
              <line
                x1={x}
                y1={TIMELINE_CONFIG.paddingTop - 10}
                x2={x}
                y2={TIMELINE_CONFIG.paddingTop - 2}
                stroke={TIMELINE_CONFIG.tickColor}
                strokeWidth={1}
              />
              {/* 时间标签 */}
              <text
                x={x}
                y={TIMELINE_CONFIG.paddingTop - 14}
                textAnchor="middle"
                fontSize={11}
                fill={TIMELINE_CONFIG.textColor}
              >
                {tick.label}
              </text>
            </g>
          );
        })}

        {/* 横向轴线 */}
        <line
          x1={config.chartLeft}
          y1={TIMELINE_CONFIG.paddingTop - 2}
          x2={config.chartLeft + config.chartWidth}
          y2={TIMELINE_CONFIG.paddingTop - 2}
          stroke={TIMELINE_CONFIG.axisColor}
          strokeWidth={1}
        />

        {/* 班次背景区域 */}
        <rect
          x={config.chartLeft + shiftRatio.start * config.chartWidth}
          y={TIMELINE_CONFIG.paddingTop - 2}
          width={Math.max((shiftRatio.end - shiftRatio.start) * config.chartWidth, 0)}
          height={config.totalHeight - TIMELINE_CONFIG.paddingTop - TIMELINE_CONFIG.paddingBottom + 4}
          fill={TIMELINE_CONFIG.shiftBackground}
          stroke={TIMELINE_CONFIG.shiftBorder}
          strokeWidth={1}
          rx={2}
        />

        {/* 班次标签 */}
        {showShiftLabel && (
          <text
            x={config.chartLeft + (shiftRatio.start + shiftRatio.end) * config.chartWidth / 2}
            y={TIMELINE_CONFIG.paddingTop + config.totalHeight - TIMELINE_CONFIG.paddingTop - TIMELINE_CONFIG.paddingBottom + 4}
            textAnchor="middle"
            fontSize={12}
            fill={TIMELINE_CONFIG.shiftLabelColor}
            fontWeight={500}
          >
            班次时间
          </text>
        )}

        {/* 时间窗条形图 */}
        {windowRenderData.map((data) => {
          const { window, windowId, x1, x2, y, width: _width, colorConfig, hasNoOpenLimit, hasNoCloseLimit, extendsBefore, extendsAfter } = data;

          // 安全检查：确保坐标有效
          if (!isFinite(x1) || !isFinite(x2) || !isFinite(y)) {
            return null;
          }

          // 限制在图表范围内
          const clampedX1 = Math.max(config.chartLeft, x1);
          const clampedX2 = Math.min(config.chartLeft + config.chartWidth, x2);
          const clampedWidth = Math.max(clampedX2 - clampedX1, 1);

          // 再次检查计算结果
          if (!isFinite(clampedX1) || !isFinite(clampedX2) || !isFinite(clampedWidth) || clampedWidth <= 0) {
            return null;
          }

          // 构建原生 title 内容
          const tooltipText = [
            `${colorConfig.label}时间窗`,
            `参考点: ${window.referencePoint === 'SHIFT_START' ? '班次开始' : window.referencePoint === 'SHIFT_END' ? '班次结束' : '预约创建'}`,
            `开放: ${hasNoOpenLimit ? '∞ 不限制' : `${(window.openOffsetSec ?? 0) >= 0 ? '+' : ''}${window.openOffsetSec ?? 0}秒`}`,
            `截止: ${hasNoCloseLimit ? '∞ 不限制' : `${(window.closeOffsetSec ?? 0) >= 0 ? '+' : ''}${window.closeOffsetSec ?? 0}秒`}`,
          ].join('\n');

          return (
            <g key={windowId}>
              {/* 原生 SVG tooltip（替代 Ant Design Tooltip 避免 findDOMNode 警告） */}
              <title>{tooltipText}</title>

              {/* 左侧不限制表示 */}
                {hasNoOpenLimit && (
                  <g>
                    {/* 虚线延伸到图表左边缘 */}
                    <line
                      x1={config.chartLeft}
                      y1={y + config.barHeight / 2}
                      x2={clampedX1}
                      y2={y + config.barHeight / 2}
                      stroke={colorConfig.stroke}
                      strokeWidth={2}
                      strokeDasharray={TIMELINE_CONFIG.unlimitedDashArray}
                      opacity={0.6}
                    />
                    {/* 渐变淡出箭头 */}
                    <path
                      d={`M${config.chartLeft},${y + config.barHeight / 2} L${config.chartLeft + config.unlimitedArrowSize},${y + config.barHeight / 2 - config.unlimitedArrowSize / 2} L${config.chartLeft + config.unlimitedArrowSize},${y + config.barHeight / 2 + config.unlimitedArrowSize / 2} Z`}
                      fill={`url(#fade-left-${windowId})`}
                    />
                    {/* ∞ 符号 */}
                    <text
                      x={config.chartLeft + config.unlimitedArrowSize / 2}
                      y={y + config.barHeight / 2 + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={config.infinitySymbolSize}
                      fill={colorConfig.stroke}
                      fontWeight="bold"
                      opacity={0.7}
                      style={{ pointerEvents: 'none' }}
                    >
                      ∞
                    </text>
                  </g>
                )}

                {/* 右侧不限制表示 */}
                {hasNoCloseLimit && (
                  <g>
                    {/* 虚线延伸到图表右边缘 */}
                    <line
                      x1={clampedX2}
                      y1={y + config.barHeight / 2}
                      x2={config.chartLeft + config.chartWidth}
                      y2={y + config.barHeight / 2}
                      stroke={colorConfig.stroke}
                      strokeWidth={2}
                      strokeDasharray={TIMELINE_CONFIG.unlimitedDashArray}
                      opacity={0.6}
                    />
                    {/* 渐变淡出箭头 */}
                    <path
                      d={`M${config.chartLeft + config.chartWidth},${y + config.barHeight / 2} L${config.chartLeft + config.chartWidth - config.unlimitedArrowSize},${y + config.barHeight / 2 - config.unlimitedArrowSize / 2} L${config.chartLeft + config.chartWidth - config.unlimitedArrowSize},${y + config.barHeight / 2 + config.unlimitedArrowSize / 2} Z`}
                      fill={`url(#fade-right-${windowId})`}
                    />
                    {/* ∞ 符号 */}
                    <text
                      x={config.chartLeft + config.chartWidth - config.unlimitedArrowSize / 2}
                      y={y + config.barHeight / 2 + 1}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      fontSize={config.infinitySymbolSize}
                      fill={colorConfig.stroke}
                      fontWeight="bold"
                      opacity={0.7}
                      style={{ pointerEvents: 'none' }}
                    >
                      ∞
                    </text>
                  </g>
                )}

                {/* 超出班次边界的箭头（非不限制情况） */}
                {!hasNoOpenLimit && extendsBefore && (
                  <path
                    d={`M${config.chartLeft},${y + config.barHeight / 2} L${config.chartLeft + 8},${y + config.barHeight / 2 - 4} L${config.chartLeft + 8},${y + config.barHeight / 2 + 4} Z`}
                    fill={colorConfig.stroke}
                    opacity={0.5}
                  />
                )}
                {!hasNoCloseLimit && extendsAfter && (
                  <path
                    d={`M${config.chartLeft + config.chartWidth},${y + config.barHeight / 2} L${config.chartLeft + config.chartWidth - 8},${y + config.barHeight / 2 - 4} L${config.chartLeft + config.chartWidth - 8},${y + config.barHeight / 2 + 4} Z`}
                    fill={colorConfig.stroke}
                    opacity={0.5}
                  />
                )}

                {/* 主条形图 */}
                <rect
                  x={clampedX1}
                  y={y}
                  width={clampedWidth}
                  height={config.barHeight}
                  fill={`url(#gradient-${windowId})`}
                  stroke={colorConfig.stroke}
                  strokeWidth={hasNoOpenLimit || hasNoCloseLimit ? 0 : 2}
                  strokeDasharray={hasNoOpenLimit || hasNoCloseLimit ? TIMELINE_CONFIG.unlimitedDashArray : undefined}
                  rx={3}
                  style={{
                    cursor: 'pointer',
                    transition: 'opacity 0.2s',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.opacity = '0.8';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.opacity = '1';
                  }}
                />

                {/* 斜线图案叠加（不限制区域） */}
                {(hasNoOpenLimit || hasNoCloseLimit) && (
                  <rect
                    x={clampedX1}
                    y={y}
                    width={clampedWidth}
                    height={config.barHeight}
                    fill="url(#diagonal-hatch)"
                    rx={3}
                    style={{ pointerEvents: 'none' }}
                  />
                )}

                {/* 标签 */}
                {showWindowLabels && clampedWidth > 40 && (
                  <text
                    x={clampedX1 + clampedWidth / 2}
                    y={y + config.barHeight / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={11}
                    fill={colorConfig.stroke}
                    fontWeight={500}
                    style={{ pointerEvents: 'none' }}
                  >
                    {colorConfig.label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>

      {/* 滚动容器结束 */}
      </div>

      {/* 图例 */}
      {showLegend && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            marginTop: 8,
            gap: 16,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', fontSize: 12, color: token.colorTextSecondary }}>
            <svg width={16} height={12} style={{ marginRight: 4 }}>
              <rect width={16} height={12} fill={token.colorFillAlter} stroke={token.colorBorderSecondary} rx={2} />
            </svg>
            班次时间
          </div>
          {Array.from(new Set(enabledWindows.map((w) => w.action))).map((action) => {
            const colorConfig = WINDOW_COLORS[action];
            if (!colorConfig) return null;

            return (
              <div key={action} style={{ display: 'flex', alignItems: 'center', fontSize: 12, color: token.colorTextSecondary }}>
                <svg width={16} height={12} style={{ marginRight: 4 }}>
                  <rect width={16} height={12} fill={colorConfig.fill} stroke={colorConfig.stroke} rx={2} />
                </svg>
                {colorConfig.label}时间窗
              </div>
            );
          })}
          {/* 不限制图例 */}
          <div style={{ display: 'flex', alignItems: 'center', fontSize: 12, color: token.colorTextSecondary }}>
            <svg width={24} height={12} style={{ marginRight: 4 }}>
              <line x1={0} y1={6} x2={24} y2={6} stroke={token.colorError} strokeWidth={2} strokeDasharray="4 4" />
              <text x={12} y={7} textAnchor="middle" fontSize={10} fill={token.colorError} fontWeight="bold">∞</text>
            </svg>
            不限制
          </div>
        </div>
      )}
    </div>
  );
};

export default React.memo(HorizontalTimeline);
