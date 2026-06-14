import React, { useEffect, useRef } from 'react';
import { useEditorStore } from '../store';

interface ContextMenuProps {
  nodeId: string;
  x: number;
  y: number;
  onClose: () => void;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({ nodeId, x, y, onClose }) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const {
    removeNode,
    duplicateNode,
    selectNode,
    moveNodeUp,
    moveNodeDown,
  } = useEditorStore();

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  const menuItems = [
    {
      label: '复制',
      shortcut: 'Ctrl+C',
      action: () => {
        duplicateNode(nodeId);
        onClose();
      },
    },
    {
      label: '删除',
      shortcut: 'Delete',
      action: () => {
        removeNode(nodeId);
        onClose();
      },
    },
    { type: 'divider' as const },
    {
      label: '上移',
      shortcut: '↑',
      action: () => {
        moveNodeUp(nodeId);
        onClose();
      },
    },
    {
      label: '下移',
      shortcut: '↓',
      action: () => {
        moveNodeDown(nodeId);
        onClose();
      },
    },
  ];

  return (
    <div
      ref={menuRef}
      style={{
        position: 'fixed',
        left: x,
        top: y,
        background: '#fff',
        borderRadius: 6,
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        padding: '4px 0',
        minWidth: 160,
        zIndex: 1000,
      }}
    >
      {menuItems.map((item, i) => {
        if (item.type === 'divider') {
          return <div key={i} style={{ height: 1, background: '#f0f0f0', margin: '4px 0' }} />;
        }
        return (
          <div
            key={i}
            onClick={item.action}
            style={{
              padding: '8px 16px',
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: 13,
            }}
            onMouseEnter={(e) => {
              (e.target as HTMLElement).style.background = '#f5f5f5';
            }}
            onMouseLeave={(e) => {
              (e.target as HTMLElement).style.background = 'transparent';
            }}
          >
            <span>{item.label}</span>
            <span style={{ color: '#999', fontSize: 11 }}>{item.shortcut}</span>
          </div>
        );
      })}
    </div>
  );
};
