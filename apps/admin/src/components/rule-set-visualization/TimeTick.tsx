/**
 * 时间轴刻度组件
 * 显示时间轴上的时间刻度标记
 */

import React from 'react';
import { Typography } from 'antd';
import type { TimeTick as TimeTickType } from '@/utils/ruleSetFormatter';

const { Text } = Typography;

// ==================== 类型定义 ====================

export interface TimeTickProps {
  tick: TimeTickType;
}

// ==================== 主组件 ====================

/**
 * 时间轴刻度组件
 */
const TimeTick: React.FC<TimeTickProps> = ({ tick }) => {
  return (
    <div
      style={{
        position: 'absolute',
        left: `${tick.position * 100}%`,
        transform: 'translateX(-50%)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}
    >
      {/* 刻度线 */}
      <div
        style={{
          width: 1,
          height: 8,
          backgroundColor: '#d9d9d9',
        }}
      />
      {/* 时间标签 */}
      <Text
        style={{
          fontSize: 11,
          color: '#8c8c8c',
          marginTop: 2,
          whiteSpace: 'nowrap',
        }}
      >
        {tick.label}
      </Text>
    </div>
  );
};

export default React.memo(TimeTick);
