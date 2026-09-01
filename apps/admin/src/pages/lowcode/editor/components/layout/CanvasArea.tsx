/**
 * CanvasArea — 低代码编辑器中栏画布容器
 *
 * 包裹 <Canvas />，canvasRef 透传供 EditorTour 锚定。
 * Canvas 内部自身管理缩放/设备/状态栏/底部工具栏。
 */

import React from 'react';
import { Canvas } from '../Canvas';

export interface CanvasAreaProps {
  /** Tour 锚点 ref（透传自父组件） */
  canvasRef: React.RefObject<HTMLDivElement>;
}

const CanvasArea: React.FC<CanvasAreaProps> = ({ canvasRef }) => {
  return (
    <div ref={canvasRef} style={{ flex: 1, display: 'flex', minWidth: 0 }}>
      <Canvas />
    </div>
  );
};

export default CanvasArea;
