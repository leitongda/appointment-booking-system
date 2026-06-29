import React, { useEffect, useRef, useState } from 'react';
import { Input, Modal, message } from 'antd';
import { useEditorStore } from '../store';
import { saveCustomSnippet } from '../utils/customSnippets';
import { findNodeById } from '../utils/tree';

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
    schema,
  } = useEditorStore();

  const [snippetModalVisible, setSnippetModalVisible] = useState(false);
  const [snippetName, setSnippetName] = useState('');

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  /** 保存为自定义 Snippet */
  const handleSaveAsSnippet = () => {
    const node = findNodeById(schema.children, nodeId);
    if (!node) return;
    setSnippetName(node.componentName);
    setSnippetModalVisible(true);
  };

  const handleSaveSnippetConfirm = () => {
    const name = snippetName.trim();
    if (!name) {
      message.warning('请输入 Snippet 名称');
      return;
    }
    const node = findNodeById(schema.children, nodeId);
    if (!node) return;
    saveCustomSnippet(name, [node]);
    message.success(`已保存为 Snippet: ${name}`);
    setSnippetModalVisible(false);
    onClose();
  };

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
      label: '保存为 Snippet',
      shortcut: '',
      action: handleSaveAsSnippet,
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
    <>
      <div
        ref={menuRef}
        role="menu"
        aria-label="组件操作菜单"
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
            return <div key={i} role="separator" style={{ height: 1, background: '#f0f0f0', margin: '4px 0' }} />;
          }
          return (
            <div
              key={i}
              role="menuitem"
              tabIndex={0}
              onClick={item.action}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  item.action();
                }
              }}
              style={{
                padding: '8px 16px',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: 13,
              }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLElement).style.background = '#f5f5f5';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.background = 'transparent';
            }}
            >
              <span>{item.label}</span>
              <span style={{ color: '#999', fontSize: 11 }}>{item.shortcut}</span>
            </div>
          );
        })}
      </div>
      <Modal
        title="保存为 Snippet"
        open={snippetModalVisible}
        onOk={handleSaveSnippetConfirm}
        onCancel={() => setSnippetModalVisible(false)}
        okText="保存"
        cancelText="取消"
        width={360}
      >
        <div style={{ marginTop: 12 }}>
          <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
            Snippet 名称 <span style={{ color: '#ff4d4f' }}>*</span>
          </label>
          <Input
            placeholder="例如: 用户信息卡片"
            value={snippetName}
            onChange={(e) => setSnippetName(e.target.value)}
            onPressEnter={handleSaveSnippetConfirm}
            autoFocus
          />
        </div>
      </Modal>
    </>
  );
};
