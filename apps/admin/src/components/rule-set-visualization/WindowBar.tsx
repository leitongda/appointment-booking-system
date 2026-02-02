/**
 * 时间窗条组件
 * 在时间轴上显示单个时间窗的条形图
 */

import React from 'react';
import { Tooltip } from 'antd';
import { formatOffset } from '@/utils/ruleSetFormatter';
import type { RuleWindow } from '@hospital/shared';

// ==================== 类型定义 ====================

export interface WindowBarProps {
  window: RuleWindow;
  ratioStart: number; // 开始比例位置 (0-1)
  ratioEnd: number; // 结束比例位置 (0-1)
  height?: number;
  showLabel?: boolean;
}

// ==================== 常量定义 ====================

/**
 * 动作类型颜色配置
 */
const ACTION_COLORS = {
  BOOK: {
    primary: '#1890ff',
    background: 'rgba(24, 144, 255, 0.2)',
    border: '#1890ff',
    label: '预约',
  },
  CHECKIN: {
    primary: '#52c41a',
    background: 'rgba(82, 196, 26, 0.2)',
    border: '#52c41a',
    label: '签到',
  },
  CANCEL: {
    primary: '#fa8c16',
    background: 'rgba(250, 140, 22, 0.2)',
    border: '#fa8c16',
    label: '取消',
  },
  HOLD_RELEASE: {
    primary: '#722ed1',
    background: 'rgba(114, 46, 209, 0.2)',
    border: '#722ed1',
    label: '释放',
  },
};

const REFERENCE_POINT_LABELS: Record<string, string> = {
  SHIFT_START: '班次开始',
  SHIFT_END: '班次结束',
  BOOKING_CREATED_AT: '预约创建',
};

// ==================== 主组件 ====================

/**
 * 时间窗条组件
 */
const WindowBar: React.FC<WindowBarProps> = ({
  window,
  ratioStart,
  ratioEnd,
  height = 24,
  showLabel = true,
}) => {
  const colorConfig = ACTION_COLORS[window.action] || ACTION_COLORS.BOOK;
  const refPointLabel = REFERENCE_POINT_LABELS[window.referencePoint] || window.referencePoint;

  // 判断是否"不限制"：null 表示不限制，undefined/NaN 等无效值也视为不限制
  const hasNoOpenLimit = window.openOffsetSec == null || 
    (typeof window.openOffsetSec === 'number' && !isFinite(window.openOffsetSec));
  const hasNoCloseLimit = window.closeOffsetSec == null || 
    (typeof window.closeOffsetSec === 'number' && !isFinite(window.closeOffsetSec));

  // 构建 Tooltip 内容
  const tooltipContent = (
    <div style={{ fontSize: 12 }}>
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
        {colorConfig.label}时间窗
      </div>
      <div>参考点: {refPointLabel}</div>
      <div>
        开放:{' '}
        {hasNoOpenLimit ? (
          <span style={{ color: '#ff4d4f' }}>不限制</span>
        ) : (
          formatOffset(window.openOffsetSec)
        )}
      </div>
      <div>
        截止:{' '}
        {hasNoCloseLimit ? (
          <span style={{ color: '#ff4d4f' }}>不限制</span>
        ) : (
          formatOffset(window.closeOffsetSec)
        )}
      </div>
    </div>
  );

  // 判断是否超出边界（用于显示箭头）
  const extendsBefore = ratioStart < 0;
  const extendsAfter = ratioEnd > 1;

  return (
    <Tooltip title={tooltipContent} placement="top">
      <div
        style={{
          position: 'absolute',
          left: `${Math.max(0, ratioStart) * 100}%`,
          width: `${Math.min(1, ratioEnd - ratioStart) * 100}%`,
          height,
          top: 4,
          backgroundColor: colorConfig.background,
          borderLeft: `2px solid ${colorConfig.border}`,
          borderRight: `2px solid ${colorConfig.border}`,
          borderRadius: 2,
          cursor: 'pointer',
          transition: 'all 0.2s',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = colorConfig.primary;
          e.currentTarget.style.opacity = '0.8';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = colorConfig.background;
          e.currentTarget.style.opacity = '1';
        }}
      >
        {/* 左侧延伸箭头 */}
        {extendsBefore && (
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              bottom: 0,
              width: 12,
              background: `linear-gradient(to right, transparent, ${colorConfig.background})`,
            }}
          />
        )}

        {/* 标签 */}
        {showLabel && (ratioEnd - ratioStart) > 0.05 && (
          <span
            style={{
              fontSize: 11,
              color: colorConfig.primary,
              fontWeight: 500,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              padding: '0 4px',
            }}
          >
            {colorConfig.label}
          </span>
        )}

        {/* 右侧延伸箭头 */}
        {extendsAfter && (
          <div
            style={{
              position: 'absolute',
              right: 0,
              top: 0,
              bottom: 0,
              width: 12,
              background: `linear-gradient(to left, transparent, ${colorConfig.background})`,
            }}
          />
        )}
      </div>
    </Tooltip>
  );
};

export default React.memo(WindowBar);
