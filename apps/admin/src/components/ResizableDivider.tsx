/**
 * 可拖拽分隔条组件
 * 用于在两个面板之间提供可拖拽调整宽度的功能
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Grid } from 'antd';

const { useBreakpoint } = Grid;

interface ResizableDividerProps {
  /** 初始右侧面板宽度 */
  initialRightWidth: number;
  /** 右侧面板最小宽度 */
  minRightWidth?: number;
  /** 右侧面板最大宽度 */
  maxRightWidth?: number;
  /** 宽度变化回调 */
  onWidthChange?: (rightWidth: number) => void;
  /** 左侧内容 */
  leftContent: React.ReactNode;
  /** 右侧内容 */
  rightContent: React.ReactNode;
  /** 容器样式 */
  style?: React.CSSProperties;
  /** 容器类名 */
  className?: string;
}

const ResizableDivider: React.FC<ResizableDividerProps> = ({
  initialRightWidth,
  minRightWidth = 300,
  maxRightWidth = 600,
  onWidthChange,
  leftContent,
  rightContent,
  style,
  className,
}) => {
  const screens = useBreakpoint();
  const isMobile = !screens.md;
  const [rightWidth, setRightWidth] = useState(initialRightWidth);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    startXRef.current = e.clientX;
    startWidthRef.current = rightWidth;
  }, [rightWidth]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;

    const deltaX = startXRef.current - e.clientX;
    let newWidth = startWidthRef.current + deltaX;

    // 限制在最小和最大宽度之间
    newWidth = Math.max(minRightWidth, Math.min(maxRightWidth, newWidth));

    setRightWidth(newWidth);
    onWidthChange?.(newWidth);
  }, [isDragging, minRightWidth, maxRightWidth, onWidthChange]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      // 禁止选择文本
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'col-resize';
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{
        display: 'flex',
        width: '100%',
        ...style,
      }}
    >
      {/* 左侧内容 */}
      <div style={{ flex: 1, minWidth: 0, overflow: 'hidden' }}>
        {leftContent}
      </div>

      {/* 可拖拽分隔条 - 仅在桌面端显示 */}
      {!isMobile && (
        <div
          onMouseDown={handleMouseDown}
          style={{
            display: 'flex',
            width: 8,
            flexShrink: 0,
            cursor: 'col-resize',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: isDragging ? '#e6f4ff' : 'transparent',
            transition: isDragging ? 'none' : 'background-color 0.2s',
            position: 'relative',
            zIndex: 10,
          }}
          title="拖拽调整宽度"
        >
          {/* 分隔线 */}
          <div
            style={{
              width: 2,
              height: '100%',
              minHeight: 200,
              backgroundColor: isDragging ? '#1677ff' : '#d9d9d9',
              borderRadius: 1,
              transition: isDragging ? 'none' : 'background-color 0.2s',
            }}
          />
          {/* 拖拽手柄指示器 */}
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: 6,
              height: 40,
              backgroundColor: isDragging ? '#1677ff' : '#bfbfbf',
              borderRadius: 3,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 3,
              transition: isDragging ? 'none' : 'background-color 0.2s',
            }}
          >
            {/* 三条横线作为拖拽指示 */}
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                style={{
                  width: 4,
                  height: 1,
                  backgroundColor: '#fff',
                  borderRadius: 0.5,
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* 右侧内容 */}
      <div style={{
        width: rightWidth,
        flexShrink: 0,
        overflow: 'hidden',
        marginTop: 'calc(46px + 16px - 3px)'
      }}>
        {rightContent}
      </div>
    </div>
  );
};

export default ResizableDivider;
