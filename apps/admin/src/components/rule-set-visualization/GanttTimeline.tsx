/**
 * 时间窗甘特图组件
 * 以横道图形式展示时间窗，每个时间窗占一行
 */

import React, { useMemo, useRef, useState, useEffect, useCallback } from 'react';
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

export interface GanttTimelineProps {
  windows: RuleWindow[];
  shiftStart: Date;
  shiftEnd: Date;
  bookingCreatedAt?: Date;
  showLegend?: boolean;
  height?: number;
  style?: React.CSSProperties;
  className?: string;
}

// ==================== 常量定义 ====================


const WINDOW_COLORS: Record<string, {
  fill: string;
  stroke: string;
  label: string;
  gradientStart: string;
  gradientEnd: string;
}> = {
  BOOK: {
    fill: 'rgba(24, 144, 255, 0.15)',
    stroke: '#1677ff',
    label: '预约时间窗',
    gradientStart: 'rgba(24, 144, 255, 0.35)',
    gradientEnd: 'rgba(24, 144, 255, 0.08)',
  },
  CHECKIN: {
    fill: 'rgba(34, 197, 94, 0.15)',
    stroke: '#22c55e',
    label: '签到时间窗',
    gradientStart: 'rgba(34, 197, 94, 0.35)',
    gradientEnd: 'rgba(34, 197, 94, 0.08)',
  },
  CANCEL: {
    fill: 'rgba(249, 115, 22, 0.15)',
    stroke: '#f97316',
    label: '取消时间窗',
    gradientStart: 'rgba(249, 115, 22, 0.35)',
    gradientEnd: 'rgba(249, 115, 22, 0.08)',
  },
  HOLD_RELEASE: {
    fill: 'rgba(168, 85, 247, 0.15)',
    stroke: '#a855f7',
    label: '释放时间窗',
    gradientStart: 'rgba(168, 85, 247, 0.35)',
    gradientEnd: 'rgba(168, 85, 247, 0.08)',
  },
};

const CONFIG = {
  // 尺寸
  rowHeight: 48,           // 每行高度
  labelWidth: 120,         // 左侧标签宽度
  paddingTop: 40,          // 顶部刻度区域高度
  paddingBottom: 20,
  minTickWidth: 100,       // 每个刻度的最小宽度（像素）
  tickIntervalSeconds: 1800, // 刻度间隔（30分钟）

  // 不限制状态样式
  unlimitedDashArray: '4 4',
  infinitySymbolSize: 12,

  // 颜色
  gridLineColor: '#f0f0f0',
  shiftBackground: '#fafafa',
  shiftBorder: '#d9d9d9',
  textColor: '#666',
  tickColor: '#999',
  axisColor: '#d9d9d9',
};

// ==================== 主组件 ====================

/**
 * 时间窗甘特图组件
 */
const GanttTimeline: React.FC<GanttTimelineProps> = ({
  windows,
  shiftStart,
  shiftEnd,
  bookingCreatedAt,
  showLegend = true,
  height = 300,
  style,
  className,
}) => {
  const { token } = theme.useToken();
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(800); // 设置默认初始宽度

  // 响应式处理
  useEffect(() => {
    const updateWidth = () => {
      // 优先使用 containerRef，其次使用 svgRef
      const element = containerRef.current || svgRef.current?.parentElement;
      if (element) {
        const width = element.getBoundingClientRect().width;
        const newWidth = Math.max(width, 600);
        setContainerWidth(newWidth);
      }
    };

    // 延迟执行确保 DOM 已渲染
    const timer = setTimeout(updateWidth, 50);

    // 使用 requestAnimationFrame 作为备用
    const rafId = requestAnimationFrame(() => {
      setTimeout(updateWidth, 0);
    });

    const resizeObserver = new ResizeObserver(updateWidth);

    // 监听容器元素
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(rafId);
      resizeObserver.disconnect();
    };
  }, []);

  // 序列化 windows 用于深度比较依赖
  // 当 windows 数组引用不变但内容变化时（如修改 closeOffsetSec），需要重新计算
  const windowsKey = useMemo(() => {
    return JSON.stringify(windows.map(w => ({
      id: w.id,
      action: w.action,
      referencePoint: w.referencePoint,
      openOffsetSec: w.openOffsetSec,
      closeOffsetSec: w.closeOffsetSec,
      enabled: w.enabled,
    })));
  }, [windows]);

  // 计算时间轴范围
  const timelineRange = useMemo<TimelineRange>(() => {
    return calculateTimelineRange(shiftStart, shiftEnd, windows, bookingCreatedAt);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shiftStart, shiftEnd, windowsKey, bookingCreatedAt]);

  // 计算班次比例位置
  const shiftRatio = useMemo(() => {
    return {
      start: timeToRatio(shiftStart, timelineRange),
      end: timeToRatio(shiftEnd, timelineRange),
    };
  }, [shiftStart, shiftEnd, timelineRange]);

  // 生成时间刻度
  const timeTicks = useMemo(() => {
    return generateTimeTicks(timelineRange, containerWidth, 100, shiftStart);
  }, [timelineRange, containerWidth, shiftStart]);

  // 计算启用的时间窗
  const enabledWindows = useMemo(() => {
    return windows.filter((w) => w.enabled);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [windowsKey]);

  // 计算布局尺寸
  const layout = useMemo(() => {
    const totalSeconds = dayjs(timelineRange.max).diff(dayjs(timelineRange.min), 'second');
    const tickCount = Math.ceil(totalSeconds / CONFIG.tickIntervalSeconds) + 1;
    const minChartWidth = tickCount * CONFIG.minTickWidth;
    const chartWidth = Math.max(containerWidth - CONFIG.labelWidth, minChartWidth);
    const totalWidth = CONFIG.labelWidth + chartWidth;
    const totalHeight = CONFIG.paddingTop + enabledWindows.length * CONFIG.rowHeight + CONFIG.paddingBottom;

    return {
      chartWidth,
      totalWidth,
      totalHeight: Math.max(height, totalHeight),
      needsScroll: totalWidth > containerWidth,
      // 从 token 获取颜色配置
      shiftBackground: token.colorFillAlter,
      shiftBorder: token.colorBorderSecondary,
      axisColor: token.colorBorderSecondary,
      tickColor: token.colorBorderSecondary,
      textColor: token.colorTextSecondary,
      gridLineColor: token.colorBorder,
    };
  }, [containerWidth, timelineRange, enabledWindows.length, height, token]);

  // 坐标转换：时间转 X 坐标
  const timeToX = useCallback((time: Date): number => {
    const ratio = timeToRatio(time, timelineRange);
    return CONFIG.labelWidth + ratio * layout.chartWidth;
  }, [timelineRange, layout.chartWidth]);

  // 计算日期分隔信息
  const dateSeparators = useMemo(() => {
    const minDate = dayjs(timelineRange.min).startOf('day');
    const maxDate = dayjs(timelineRange.max).startOf('day');
    const shiftDate = dayjs(shiftStart).startOf('day');

    const separators: Array<{
      date: dayjs.Dayjs;
      x: number;
      label: string;
      isShiftDay: boolean;
    }> = [];

    // 遍历每一天
    let currentDate = minDate;
    while (currentDate.isBefore(maxDate) || currentDate.isSame(maxDate)) {
      const x = timeToX(currentDate.toDate());
      const isShiftDay = currentDate.isSame(shiftDate, 'day');

      // 生成日期标签
      let label = currentDate.format('MM-DD');
      if (currentDate.isSame(shiftDate, 'day')) {
        label = `${label} (当天)`;
      } else if (currentDate.isSame(shiftDate.subtract(1, 'day'), 'day')) {
        label = `${label} (前一天)`;
      } else if (currentDate.isSame(shiftDate.add(1, 'day'), 'day')) {
        label = `${label} (后一天)`;
      }

      separators.push({
        date: currentDate,
        x,
        label,
        isShiftDay,
      });

      currentDate = currentDate.add(1, 'day');
    }

    return separators;
  }, [timelineRange, shiftStart, timeToX]);

  // 计算每个时间窗的渲染数据
  const windowRenderData = useMemo(() => {
    return enabledWindows.map((window, index) => {
      const windowId = window.id || `temp-${index}`;
      const colorConfig = WINDOW_COLORS[window.action] || WINDOW_COLORS.BOOK;

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

      // 确定显示的起止时间
      // 注意：openTime 表示"开放时间"（时间窗开始允许操作），closeTime 表示"截止时间"（时间窗停止允许操作）
      let displayStart: Date;
      let displayEnd: Date;

      if (hasNoOpenLimit) {
        displayStart = timelineRange.min;
      } else {
        displayStart = openTime || timelineRange.min;
      }

      if (hasNoCloseLimit) {
        displayEnd = timelineRange.max;
      } else {
        displayEnd = closeTime || timelineRange.max;
      }

      // 确保 displayStart <= displayEnd，处理配置异常（开放时间晚于截止时间）的情况
      if (displayStart && displayEnd && dayjs(displayStart).isAfter(dayjs(displayEnd))) {
        // 交换开始和结束时间，保证条形能正确渲染
        [displayStart, displayEnd] = [displayEnd, displayStart];
      }

      const x1 = timeToX(displayStart);
      const x2 = timeToX(displayEnd);
      const y = CONFIG.paddingTop + index * CONFIG.rowHeight;
      const barHeight = CONFIG.rowHeight - 16;

      // 调试日志：帮助排查宽度计算问题
      if (process.env.NODE_ENV === 'development') {
        console.log('[GanttTimeline] Window render data:', {
          action: window.action,
          referencePoint: window.referencePoint,
          openOffsetSec: window.openOffsetSec,
          closeOffsetSec: window.closeOffsetSec,
          hasNoOpenLimit,
          hasNoCloseLimit,
          openTime: openTime ? dayjs(openTime).format('YYYY-MM-DD HH:mm:ss') : null,
          closeTime: closeTime ? dayjs(closeTime).format('YYYY-MM-DD HH:mm:ss') : null,
          displayStart: dayjs(displayStart).format('YYYY-MM-DD HH:mm:ss'),
          displayEnd: dayjs(displayEnd).format('YYYY-MM-DD HH:mm:ss'),
          shiftStart: dayjs(shiftStart).format('YYYY-MM-DD HH:mm:ss'),
          shiftEnd: dayjs(shiftEnd).format('YYYY-MM-DD HH:mm:ss'),
          x1,
          x2,
          width: x2 - x1,
          timelineRange: {
            min: dayjs(timelineRange.min).format('YYYY-MM-DD HH:mm:ss'),
            max: dayjs(timelineRange.max).format('YYYY-MM-DD HH:mm:ss'),
          },
        });
      }

      return {
        window,
        windowId,
        index,
        x1,
        x2,
        y,
        barHeight,
        width: Math.max(x2 - x1, 2),
        colorConfig,
        hasNoOpenLimit,
        hasNoCloseLimit,
        openTime: displayStart,
        closeTime: displayEnd,
        displayStart,
        displayEnd,
      };
    });
  }, [enabledWindows, timelineRange, shiftStart, shiftEnd, bookingCreatedAt, timeToX]);

  if (enabledWindows.length === 0) {
    return (
      <div className={className} style={{ ...style, padding: '24px 0', textAlign: 'center' }}>
        <Empty description="暂无时间窗配置" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    );
  }

  return (
    <div ref={containerRef} className={className} style={style}>
      {/* 可滚动容器 */}
      <div
        style={{
          overflowX: layout.needsScroll ? 'auto' : 'visible',
          overflowY: 'hidden',
          maxWidth: '100%',
        }}
      >
        <svg
          ref={svgRef}
          width={layout.totalWidth}
          height={layout.totalHeight}
        >
          {/* 定义渐变和阴影 */}
          <defs>
            {enabledWindows.map((window, index) => {
              const windowId = window.id || `temp-${index}`;
              const colorConfig = WINDOW_COLORS[window.action];
              return (
                <linearGradient
                  key={`gradient-${windowId}`}
                  id={`gantt-gradient-${windowId}`}
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
            {/* 阴影滤镜 */}
            <filter id="bar-shadow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="2" floodOpacity="0.15" />
            </filter>
          </defs>

          {/* 背景网格 - 垂直线（每个刻度一条） */}
          {timeTicks.map((tick, index) => {
            const x = CONFIG.labelWidth + tick.position * layout.chartWidth;
            return (
              <line
                key={`grid-${index}`}
                x1={x}
                y1={CONFIG.paddingTop}
                x2={x}
                y2={layout.totalHeight - CONFIG.paddingBottom}
                stroke={CONFIG.gridLineColor}
                strokeWidth={1}
                strokeDasharray="2 2"
              />
            );
          })}

          {/* 班次背景区域 */}
          <rect
            x={CONFIG.labelWidth + shiftRatio.start * layout.chartWidth}
            y={CONFIG.paddingTop}
            width={Math.max((shiftRatio.end - shiftRatio.start) * layout.chartWidth, 0)}
            height={enabledWindows.length * CONFIG.rowHeight}
            fill={CONFIG.shiftBackground}
            stroke={CONFIG.shiftBorder}
            strokeWidth={1}
            rx={4}
          />
          <text
            x={CONFIG.labelWidth + (shiftRatio.start + shiftRatio.end) * layout.chartWidth / 2}
            y={CONFIG.paddingTop + enabledWindows.length * CONFIG.rowHeight / 2}
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize={12}
            fill={CONFIG.textColor}
            opacity={0.5}
            fontWeight={500}
            style={{ pointerEvents: 'none' }}
          >
            班次时间
          </text>

          {/* 时间刻度 */}
          {timeTicks.map((tick, index) => {
            const x = CONFIG.labelWidth + tick.position * layout.chartWidth;
            return (
              <g key={`tick-${index}`}>
                {/* 刻度线 */}
                <line
                  x1={x}
                  y1={CONFIG.paddingTop - 8}
                  x2={x}
                  y2={CONFIG.paddingTop - 2}
                  stroke={CONFIG.tickColor}
                  strokeWidth={1}
                />
                {/* 时间标签 */}
                <text
                  x={x}
                  y={CONFIG.paddingTop - 12}
                  textAnchor="middle"
                  fontSize={11}
                  fill={CONFIG.textColor}
                >
                  {tick.label}
                </text>
              </g>
            );
          })}

          {/* 横向轴线 */}
          <line
            x1={CONFIG.labelWidth}
            y1={CONFIG.paddingTop - 2}
            x2={layout.totalWidth}
            y2={CONFIG.paddingTop - 2}
            stroke={CONFIG.axisColor}
            strokeWidth={1}
          />

          {/* 垂向分隔线（标签和图表之间） */}
          <line
            x1={CONFIG.labelWidth}
            y1={CONFIG.paddingTop - 10}
            x2={CONFIG.labelWidth}
            y2={layout.totalHeight - CONFIG.paddingBottom}
            stroke={CONFIG.axisColor}
            strokeWidth={1}
          />

          {/* 日期分隔线 */}
          {dateSeparators.map((sep, index) => {
            // 只绘制在图表范围内的分隔线
            if (sep.x < CONFIG.labelWidth || sep.x > layout.totalWidth) return null;

            return (
              <g key={`date-sep-${index}`}>
                {/* 日期分隔线（虚线） */}
                <line
                  x1={sep.x}
                  y1={CONFIG.paddingTop}
                  x2={sep.x}
                  y2={layout.totalHeight - CONFIG.paddingBottom}
                  stroke={sep.isShiftDay ? token.colorPrimary : token.colorTextTertiary}
                  strokeWidth={1}
                  strokeDasharray="4 2"
                  opacity={0.5}
                />
                {/* 日期标签 */}
                <text
                  x={sep.x + 5}
                  y={CONFIG.paddingTop + 20}
                  textAnchor="start"
                  fontSize={10}
                  fill={sep.isShiftDay ? token.colorPrimary : token.colorTextTertiary}
                  fontWeight={sep.isShiftDay ? 600 : 400}
                  opacity={0.8}
                  style={{ pointerEvents: 'none' }}
                >
                  {sep.label}
                </text>
              </g>
            );
          })}

          {/* 时间窗行 */}
          {windowRenderData.map((data) => {
            const { window, windowId, x1, x2, y, barHeight, width: _width, colorConfig, hasNoOpenLimit, hasNoCloseLimit, displayStart, displayEnd } = data;

            // 限制在图表范围内
            const chartLeft = CONFIG.labelWidth;
            const chartRight = layout.totalWidth;
            const clampedX1 = Math.max(chartLeft, x1);
            const clampedX2 = Math.min(chartRight, x2);
            const clampedWidth = Math.max(clampedX2 - clampedX1, 1);

            const formatTime = (time: Date) => {
              if (!time) return '--:--';
              return dayjs(time).format('HH:mm');
            };

            const tooltipText = [
              `${colorConfig.label}`,
              `参考点: ${window.referencePoint === 'SHIFT_START' ? '班次开始' : window.referencePoint === 'SHIFT_END' ? '班次结束' : '预约创建'}`,
              `开放: ${hasNoOpenLimit ? '∞ 不限制' : formatTime(displayStart)}`,
              `截止: ${hasNoCloseLimit ? '∞ 不限制' : formatTime(displayEnd)}`,
            ].join('\n');

            return (
              <g key={windowId}>
                {/* 原生 SVG tooltip */}
                <title>{tooltipText}</title>

                {/* 左侧标签 */}
                <text
                  x={CONFIG.labelWidth - 12}
                  y={y + CONFIG.rowHeight / 2}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fontSize={12}
                  fill={CONFIG.textColor}
                  fontWeight={500}
                >
                  {colorConfig.label}
                </text>

                {/* 行分隔线 */}
                <line
                  x1={CONFIG.labelWidth}
                  y1={y + CONFIG.rowHeight}
                  x2={layout.totalWidth}
                  y2={y + CONFIG.rowHeight}
                  stroke={CONFIG.gridLineColor}
                  strokeWidth={1}
                />

                {/* 左侧不限制表示 */}
                {hasNoOpenLimit && (
                  <g>
                    <line
                      x1={chartLeft}
                      y1={y + CONFIG.rowHeight / 2}
                      x2={clampedX1}
                      y2={y + CONFIG.rowHeight / 2}
                      stroke={colorConfig.stroke}
                      strokeWidth={2}
                      strokeDasharray={CONFIG.unlimitedDashArray}
                      opacity={0.6}
                    />
                    <text
                      x={chartLeft + 10}
                      y={y + CONFIG.rowHeight / 2}
                      dominantBaseline="middle"
                      fontSize={CONFIG.infinitySymbolSize}
                      fill={colorConfig.stroke}
                      opacity={0.7}
                    >
                      ∞
                    </text>
                  </g>
                )}

                {/* 右侧不限制表示 */}
                {hasNoCloseLimit && (
                  <g>
                    <line
                      x1={clampedX2}
                      y1={y + CONFIG.rowHeight / 2}
                      x2={chartRight}
                      y2={y + CONFIG.rowHeight / 2}
                      stroke={colorConfig.stroke}
                      strokeWidth={2}
                      strokeDasharray={CONFIG.unlimitedDashArray}
                      opacity={0.6}
                    />
                    <text
                      x={chartRight - 10}
                      y={y + CONFIG.rowHeight / 2}
                      textAnchor="end"
                      dominantBaseline="middle"
                      fontSize={CONFIG.infinitySymbolSize}
                      fill={colorConfig.stroke}
                      opacity={0.7}
                    >
                      ∞
                    </text>
                  </g>
                )}

                {/* 主条形图 */}
                <g filter="url(#bar-shadow)">
                  <rect
                    x={clampedX1}
                    y={y + (CONFIG.rowHeight - barHeight) / 2}
                    width={clampedWidth}
                    height={barHeight}
                    fill={`url(#gantt-gradient-${windowId})`}
                    stroke={colorConfig.stroke}
                    strokeWidth={1.5}
                    rx={8}
                    style={{
                      cursor: 'pointer',
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.opacity = '0.85';
                      e.currentTarget.style.filter = 'brightness(1.1)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.opacity = '1';
                      e.currentTarget.style.filter = 'none';
                    }}
                  />
                </g>

                {/* 时间标签 */}
                {clampedWidth > 100 && (
                  <text
                    x={clampedX1 + clampedWidth / 2}
                    y={y + CONFIG.rowHeight / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={11}
                    fill={colorConfig.stroke}
                    fontWeight={500}
                    style={{ pointerEvents: 'none', textShadow: '0 1px 2px rgba(255,255,255,0.8)' }}
                  >
                    {formatTime(displayStart)} - {formatTime(displayEnd)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      {/* 图例 */}
      {showLegend && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            marginTop: 12,
            gap: 16,
            flexWrap: 'wrap',
          }}
        >
          {Array.from(new Set(enabledWindows.map((w) => w.action))).map((action) => {
            const colorConfig = WINDOW_COLORS[action];
            if (!colorConfig) return null;

            return (
              <div key={action} style={{ display: 'flex', alignItems: 'center', fontSize: 12, color: token.colorTextSecondary }}>
                <svg width={16} height={12} style={{ marginRight: 4 }}>
                  <rect width={16} height={12} fill={colorConfig.fill} stroke={colorConfig.stroke} rx={2} />
                </svg>
                {colorConfig.label}
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

export default React.memo(GanttTimeline);
