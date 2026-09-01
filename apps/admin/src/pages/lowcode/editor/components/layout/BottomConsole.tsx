import React, { useState } from 'react';
import { Tabs } from 'antd';
import { EDITOR_COLORS, EDITOR_LAYOUT } from '../../constants';

const BottomConsole: React.FC = () => {
  const [activeTab, setActiveTab] = useState('console');
  const [isOpen, setIsOpen] = useState(true);

  if (!isOpen) {
    return (
      <div 
        style={{ 
          height: 32, 
          borderTop: `1px solid ${EDITOR_COLORS.border}`,
          background: EDITOR_COLORS.panelBg,
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          cursor: 'pointer',
          fontSize: 12,
          color: EDITOR_COLORS.textSecondary
        }}
        onClick={() => setIsOpen(true)}
      >
        <span>Show Console</span>
      </div>
    );
  }

  return (
    <div
      style={{
        height: EDITOR_LAYOUT.bottomConsoleHeight,
        borderTop: `1px solid ${EDITOR_COLORS.border}`,
        background: EDITOR_COLORS.panelBg,
        display: 'flex',
        flexDirection: 'column',
        position: 'relative'
      }}
    >
      <div 
        style={{ 
          position: 'absolute', 
          right: 16, 
          top: 8, 
          cursor: 'pointer',
          zIndex: 10,
          color: EDITOR_COLORS.textSecondary
        }}
        onClick={() => setIsOpen(false)}
      >
        ✕
      </div>
      <div style={{ padding: '0 16px', borderBottom: `1px solid ${EDITOR_COLORS.border}` }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="small"
          items={[
            { key: 'console', label: 'Console' },
            { key: 'logs', label: 'Logs' },
            { key: 'history', label: 'History' },
            { key: 'workflow', label: 'Workflow' },
            { key: 'api', label: 'API' },
            { key: 'ai', label: 'AI Chat' },
          ]}
          tabBarStyle={{ marginBottom: 0 }}
        />
      </div>
      <div style={{ flex: 1, padding: 16, overflowY: 'auto', fontFamily: 'monospace', fontSize: 12, color: EDITOR_COLORS.textSecondary }}>
        {activeTab === 'console' && (
          <div>
            <div style={{ marginBottom: 8 }}><span style={{ color: '#9CA3AF', marginRight: 8 }}>10:32:01</span><span style={{ color: '#3B82F6' }}>[Info] Component library loaded successfully.</span></div>
            <div style={{ marginBottom: 8 }}><span style={{ color: '#9CA3AF', marginRight: 8 }}>10:32:05</span><span>[Action] User added Button component to Canvas.</span></div>
          </div>
        )}
        {activeTab === 'logs' && <div>No recent logs.</div>}
        {activeTab === 'history' && <div>No history.</div>}
        {activeTab === 'workflow' && <div>Workflow not configured.</div>}
        {activeTab === 'api' && <div>No API requests.</div>}
        {activeTab === 'ai' && <div>AI Chat initialized.</div>}
      </div>
    </div>
  );
};

export default BottomConsole;
