/**
 * useResizablePanel — 可拖拽调整宽度的侧栏 hook
 *
 * 封装自 index.tsx 的右栏拖拽逻辑：localStorage 持久化 + 全局 mousemove/mouseup 监听 + 宽度 clamp。
 * 适用于右侧属性面板（未来也可用于左栏）。
 *
 * 实现要点：监听器 effect 只依赖 [isResizing]，width 通过 ref 镜像在 handler 内读取，
 * 避免拖拽过程中每移动 1px 就重注册监听器，并消除 mouseup 闭包陈旧 width 的竞态。
 */

import { useState, useEffect, useCallback, useRef } from 'react';

interface UseResizablePanelOptions {
  /** localStorage 持久化键 */
  storageKey: string;
  /** 默认宽度（localStorage 无效时回退） */
  defaultWidth: number;
  /** 最小宽度 */
  minWidth: number;
  /** 最大宽度 */
  maxWidth: number;
}

interface UseResizablePanelResult {
  /** 当前宽度 */
  width: number;
  /** 是否正在拖拽 */
  isResizing: boolean;
  /** 绑定到分隔条 onMouseDown 的处理函数 */
  onMouseDown: (e: React.MouseEvent) => void;
}

export function useResizablePanel({
  storageKey,
  defaultWidth,
  minWidth,
  maxWidth,
}: UseResizablePanelOptions): UseResizablePanelResult {
  const [width, setWidth] = useState<number>(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const value = Number(stored);
        if (value >= minWidth && value <= maxWidth) return value;
      }
    } catch {}
    return defaultWidth;
  });

  const [isResizing, setIsResizing] = useState(false);
  const resizeStartXRef = useRef(0);
  const resizeStartWidthRef = useRef(0);
  /** width 的 ref 镜像 — 供 mouseup 持久化读取最新值，避免闭包陈旧 */
  const widthRef = useRef(width);
  widthRef.current = width;

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    resizeStartXRef.current = e.clientX;
    resizeStartWidthRef.current = widthRef.current;
  }, []);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      // 向左拖（deltaX > 0）时增宽
      const deltaX = resizeStartXRef.current - e.clientX;
      const newWidth = Math.max(minWidth, Math.min(maxWidth, resizeStartWidthRef.current + deltaX));
      setWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      // 从 ref 读取最终宽度，避免闭包陈旧
      try {
        localStorage.setItem(storageKey, String(widthRef.current));
      } catch {}
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isResizing, storageKey, minWidth, maxWidth]);

  return { width, isResizing, onMouseDown };
}
