/**
 * 时间轴图例组件
 * 显示各种时间窗的图例说明
 */

import React from 'react';
import { Space } from 'antd';
import type { RuleWindow } from '@hospital/shared';

// ==================== 类型定义 ====================

export interface TimelineLegendProps {
  windows: RuleWindow[];
  showShiftLegend?: boolean;
}

// ==================== 常量定义 ====================

import { ACTION_COLORS } from '@/constants/rule-set';

// ==================== 主组件 ====================

/**
 * 时间轴图例组件
 */
const TimelineLegend: React.FC<TimelineLegendProps> = ({
  windows,
  showShiftLegend = true,
}) => {
  // 获取启用的时间窗动作类型
  const enabledActions = Array.from(
    new Set(windows.filter((w) => w.enabled).map((w) => w.action))
  );

  if (enabledActions.length === 0 && !showShiftLegend) {
    return null;
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        marginTop: 8,
        padding: '4px 0',
      }}
    >
      <Space size="small" wrap>
        {/* 班次时间图例 */}
        {showShiftLegend && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              fontSize: 12,
              color: '#595959',
            }}
          >
            <div
              style={{
                width: 16,
                height: 12,
                backgroundColor: '#fafafa',
                border: '1px solid #d9d9d9',
                marginRight: 4,
                borderRadius: 2,
              }}
            />
            班次时间
          </div>
        )}

        {/* 时间窗图例 */}
        {enabledActions.map((action) => {
          const colorConfig = ACTION_COLORS[action as keyof typeof ACTION_COLORS];
          if (!colorConfig) return null;

          return (
            <div
              key={action}
              style={{
                display: 'flex',
                alignItems: 'center',
                fontSize: 12,
                color: '#595959',
              }}
            >
              <div
                style={{
                  width: 16,
                  height: 12,
                  backgroundColor: colorConfig.primary,
                  opacity: 0.7,
                  marginRight: 4,
                  borderRadius: 2,
                }}
              />
              {colorConfig.label}
            </div>
          );
        })}
      </Space>
    </div>
  );
};

export default React.memo(TimelineLegend);
