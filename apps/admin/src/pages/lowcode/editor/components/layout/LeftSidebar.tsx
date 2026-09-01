/**
 * LeftSidebar — 低代码编辑器左栏（组件库 / 图层）
 */

import React, { useState } from 'react';
import { ComponentPanel } from '../ComponentPanel';
import { LayerPanel } from '../LayerPanel';
import { EDITOR_COLORS, EDITOR_LAYOUT } from '../../constants';
import { Tabs } from 'antd';

export interface LeftSidebarProps {
  componentPanelRef: React.RefObject<HTMLDivElement>;
}

const LeftSidebar: React.FC<LeftSidebarProps> = ({ componentPanelRef }) => {
  const [activeTab, setActiveTab] = useState('components');

  return (
    <div
      style={{
        width: EDITOR_LAYOUT.leftSidebarWidth,
        flexShrink: 0,
        borderRight: `1px solid ${EDITOR_COLORS.border}`,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: EDITOR_COLORS.panelBg,
      }}
    >
      <div style={{ padding: '0 16px', borderBottom: `1px solid ${EDITOR_COLORS.border}` }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            { key: 'components', label: 'Components' },
            { key: 'layers', label: 'Layers' },
            { key: 'assets', label: 'Assets' },
          ]}
          tabBarStyle={{ marginBottom: 0 }}
        />
      </div>

      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {activeTab === 'components' && <ComponentPanel containerRef={componentPanelRef} />}
        {activeTab === 'layers' && <LayerPanel />}
        {activeTab === 'assets' && (
          <div style={{ padding: 16, color: EDITOR_COLORS.textSecondary, fontSize: 13, textAlign: 'center' }}>
            No assets found.
          </div>
        )}
      </div>
    </div>
  );
};

export default LeftSidebar;
