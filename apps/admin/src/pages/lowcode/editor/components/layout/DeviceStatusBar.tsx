/**
 * DeviceStatusBar — 手机模拟器状态栏
 *
 * 渲染在设备外壳内顶部、SchemaRenderer 之前。
 * 显示时间 + 信号/WiFi/电池图标。
 *
 * 重要：此组件严格禁止添加 data-node-id 属性。
 * Canvas 拖拽落点计算（computeInsertion）依赖 `:scope > [data-node-id]`
 * 选择直接子元素来确定插入索引，状态栏作为纯装饰 DOM 不能参与落点计算。
 */

import React, { useEffect, useState } from 'react';
import { EDITOR_COLORS } from '../../constants';

function formatNow(): string {
  const d = new Date();
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

const DeviceStatusBar: React.FC = () => {
  // 时间每分钟更新（对齐线框图 08:08 风格，但用真实时间更自然）
  const [time, setTime] = useState(() => formatNow());

  useEffect(() => {
    const timer = setInterval(() => setTime(formatNow()), 30 * 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div
      style={{
        height: 28,
        flexShrink: 0,
        background: EDITOR_COLORS.statusBarBg,
        color: EDITOR_COLORS.statusText,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        fontSize: 13,
        fontWeight: 600,
        userSelect: 'none',
      }}
    >
      {/* 左：时间 */}
      <span>{time}</span>

      {/* 右：信号 + WiFi + 电池（纯 SVG/字符示意） */}
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        {/* 信号格 */}
        <svg width="18" height="12" viewBox="0 0 18 12" fill="currentColor">
          <rect x="0" y="8" width="3" height="4" rx="0.5" />
          <rect x="5" y="5" width="3" height="7" rx="0.5" />
          <rect x="10" y="2" width="3" height="10" rx="0.5" />
          <rect x="15" y="0" width="3" height="12" rx="0.5" opacity="0.4" />
        </svg>
        {/* WiFi */}
        <svg width="16" height="12" viewBox="0 0 16 12" fill="currentColor">
          <path d="M8 11.5l1.8-2.2a2.3 2.3 0 0 0-3.6 0L8 11.5z" />
          <path d="M3.5 6.3a6.4 6.4 0 0 1 9 0l-1.3 1.6a4.4 4.4 0 0 0-6.4 0L3.5 6.3z" opacity="0.9" />
          <path d="M1 3.7a10.1 10.1 0 0 1 14 0l-1.3 1.6a8.1 8.1 0 0 0-11.4 0L1 3.7z" opacity="0.8" />
        </svg>
        {/* 电池 */}
        <svg width="24" height="12" viewBox="0 0 24 12" fill="none">
          <rect x="0.5" y="0.5" width="20" height="11" rx="2.5" stroke="currentColor" opacity="0.5" />
          <rect x="2" y="2" width="16" height="8" rx="1.5" fill="currentColor" />
          <rect x="21.5" y="3.5" width="2" height="5" rx="1" fill="currentColor" opacity="0.5" />
        </svg>
      </span>
    </div>
  );
};


export default DeviceStatusBar;
