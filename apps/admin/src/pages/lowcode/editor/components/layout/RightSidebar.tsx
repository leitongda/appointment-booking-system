/**
 * RightSidebar — 低代码编辑器右栏（属性面板 + 可拖拽分隔条）
 */

import React, { useState } from 'react';
import { PropertyPanel } from '../PropertyPanel';
import { useResizablePanel } from '../../hooks/useResizablePanel';
import { EDITOR_COLORS, EDITOR_LAYOUT } from '../../constants';
import { Tabs } from 'antd';
import { RobotOutlined } from '@ant-design/icons';

export interface RightSidebarProps {
  propertyPanelRef: React.RefObject<HTMLDivElement>;
}

const STORAGE_KEY = 'lowcode-property-panel-width';

const RightSidebar: React.FC<RightSidebarProps> = ({ propertyPanelRef }) => {
  const { width, isResizing, onMouseDown } = useResizablePanel({
    storageKey: STORAGE_KEY,
    defaultWidth: EDITOR_LAYOUT.rightPanelWidth,
    minWidth: 260,
    maxWidth: 600,
  });

  const [activeTab, setActiveTab] = useState('design');

  return (
    <>
      {/* 可拖拽分隔条 */}
      <div
        onMouseDown={onMouseDown}
        style={{
          width: 6,
          flexShrink: 0,
          cursor: 'col-resize',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: isResizing ? EDITOR_COLORS.primaryBg : 'transparent',
          transition: isResizing ? 'none' : 'background 0.2s',
          position: 'relative',
          zIndex: 10,
        }}
        title="拖拽调整属性面板宽度"
      >
        <div
          style={{
            width: 2,
            height: '100%',
            minHeight: 200,
            background: isResizing ? EDITOR_COLORS.primary : EDITOR_COLORS.border,
            borderRadius: 1,
            transition: isResizing ? 'none' : 'background 0.2s',
          }}
        />
      </div>

      {/* 右侧属性面板 */}
      <div 
        ref={propertyPanelRef} 
        style={{ 
          width, 
          flexShrink: 0, 
          overflow: 'hidden', 
          display: 'flex', 
          flexDirection: 'column',
          background: EDITOR_COLORS.panelBg 
        }}
      >
        <div style={{ padding: '0 16px', borderBottom: `1px solid ${EDITOR_COLORS.border}` }}>
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              { key: 'design', label: 'Design' },
              { key: 'events', label: 'Events' },
              { key: 'data', label: 'Data' },
              { key: 'ai', label: <span><RobotOutlined /> AI</span> },
            ]}
            tabBarStyle={{ marginBottom: 0 }}
          />
        </div>
        <div style={{ flex: 1, overflowY: 'auto', overflowX: 'hidden' }}>
          {activeTab === 'ai' ? (
            <div style={{ padding: 24, textAlign: 'center', color: EDITOR_COLORS.textSecondary }}>
              <RobotOutlined style={{ fontSize: 32, color: EDITOR_COLORS.border, marginBottom: 12 }} />
              <div style={{ fontSize: 13 }}>Select a component to view AI suggestions</div>
            </div>
          ) : (
            <PropertyPanel />
          )}
        </div>
      </div>
    </>
  );
};

export default RightSidebar;
