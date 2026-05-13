import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { HolderOutlined } from '@ant-design/icons';
import { theme } from 'antd';

interface SortableRowProps extends React.HTMLAttributes<HTMLTableRowElement> {
  'data-row-key'?: string;
}

// 创建 Context 用于传递拖拽手柄的 props
interface DragHandleContextType {
  setActivatorNodeRef?: (element: HTMLElement | null) => void;
  listeners?: Record<string, any>;
}

export const DragHandleContext = React.createContext<DragHandleContextType>({});

export const SortableRow: React.FC<SortableRowProps> = ({ children, style, ...props }) => {
  const id = props['data-row-key'] || '';

  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id,
  });

  const rowStyle: React.CSSProperties = {
    ...style,
    transform: CSS.Transform.toString(transform && { ...transform, scaleY: 1 }),
    transition,
    ...(isDragging ? { position: 'relative', zIndex: 9999, background: '#fafafa' } : {}),
  };

  // 将拖拽手柄的 ref 和 listeners 注入到 context 中，供 DragHandle 使用
  const contextValue = {
    setActivatorNodeRef,
    listeners,
  };

  return (
    <DragHandleContext.Provider value={contextValue}>
      <tr {...props} ref={setNodeRef} style={rowStyle} {...attributes}>
        {children}
      </tr>
    </DragHandleContext.Provider>
  );
};

// 拖拽手柄组件
export const DragHandle: React.FC = () => {
  const { setActivatorNodeRef, listeners } = React.useContext(DragHandleContext);
  const { token } = theme.useToken();

  return (
    <HolderOutlined
      ref={setActivatorNodeRef}
      style={{
        cursor: 'grab',
        color: token.colorTextTertiary,
        fontSize: 16,
        touchAction: 'none',
      }}
      {...listeners}
    />
  );
};

