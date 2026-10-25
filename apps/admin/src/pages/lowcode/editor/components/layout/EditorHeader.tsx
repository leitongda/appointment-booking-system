/**
 * EditorHeader — 低代码编辑器顶部工具栏
 */

import React from 'react';
import {Button, Dropdown, Space, Tooltip} from 'antd';
import {UndoOutlined, RedoOutlined, ArrowLeftOutlined, CodeOutlined, ShareAltOutlined, CloudUploadOutlined, MoreOutlined, RobotOutlined, UserOutlined} from '@ant-design/icons';
import {EDITOR_COLORS, EDITOR_LAYOUT} from '../../constants';

export interface EditorHeaderProps {
  onBack: () => void;
  onUndo: () => void;
  onRedo: () => void;
  historyIndex: number;
  historyLength: number;
  lastSavedAt: Date | null;
  pageId: string | null;
  isDirty: boolean;
  saving: boolean;
  publishing: boolean;
  onPreview: () => void;
  onCode: () => void;
  onHistory: () => void;
  onShare: () => void;
  onDeploy: () => void;
  onSave: () => void;
  onPublish: () => void;
  saveButtonRef: React.RefObject<HTMLDivElement>;
  undoButtonRef: React.RefObject<HTMLDivElement>;
}

const EditorHeader: React.FC<EditorHeaderProps> = ({
  onBack,
  onUndo,
  onRedo,
  historyIndex,
  historyLength,
  lastSavedAt,
  pageId,
  isDirty,
  saving,
  publishing,
  onPreview,
  onCode,
  onHistory,
  onShare,
  onDeploy,
  onSave,
  onPublish,
  saveButtonRef,
  undoButtonRef,
}) => {
    return (
      <div
        style={{
          height: EDITOR_LAYOUT.headerHeight,
          flexShrink: 0,
          borderBottom: `1px solid ${EDITOR_COLORS.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: EDITOR_COLORS.panelBg,
          zIndex: 10,
        }}
      >
        {/* 左侧：返回 + Logo + 名称 */}
        <Space size={16} style={{ minWidth: 0, flexShrink: 0 }}>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={onBack} />
          <div style={{ fontWeight: 600, fontSize: 16, letterSpacing: '-0.02em', color: EDITOR_COLORS.primary }}>Builder</div>
          <div style={{ fontSize: 14, color: EDITOR_COLORS.textSecondary, padding: '6px 12px', borderRadius: 8, cursor: 'pointer', transition: 'background 0.2s' }} className="project-name-hover">
            Untitled Project / Page 1
          </div>
        </Space>

        {/* 中间：Undo/Redo + AI Copilot */}
        <Space size={16} style={{ flexShrink: 0 }}>
          <Space size={4}>
            <Tooltip title="撤销 (Ctrl+Z)">
              <div ref={undoButtonRef} style={{ display: 'inline-flex' }}>
                <Button type="text" icon={<UndoOutlined />} onClick={onUndo} disabled={historyIndex <= 0} />
              </div>
            </Tooltip>
            <Tooltip title="重做 (Ctrl+Shift+Z)">
              <Button type="text" icon={<RedoOutlined />} onClick={onRedo} disabled={historyIndex >= historyLength - 1} />
            </Tooltip>
          </Space>
          <Button 
            icon={<RobotOutlined />} 
            style={{ 
              background: 'linear-gradient(to right, #f9f9f9, #ffffff)', 
              borderColor: EDITOR_COLORS.border, 
              color: EDITOR_COLORS.primary,
              fontWeight: 500
            }}
          >
            AI Copilot
          </Button>
        </Space>

        {/* 右侧：状态 + 保存 + 预览 + 发布 + 头像 */}
        <Space size={12} style={{ flexShrink: 0 }}>
          {lastSavedAt && (
            <span style={{ fontSize: 12, color: EDITOR_COLORS.textMuted, whiteSpace: 'nowrap', marginRight: 8 }}>
              保存于 {lastSavedAt.toLocaleTimeString()}
            </span>
          )}

          <div ref={saveButtonRef} style={{ display: 'inline-flex' }}>
            <Button onClick={onSave} loading={saving}>保存</Button>
          </div>

          <Button onClick={onHistory} disabled={!pageId}>版本历史</Button>
          <Button onClick={onPreview} disabled={!pageId}>预览</Button>

          <Button type="primary" onClick={onPublish} loading={publishing} style={{ background: EDITOR_COLORS.primary, borderColor: EDITOR_COLORS.primary }}>
            发布
          </Button>

          <Dropdown
            trigger={['click']}
            menu={{
              items: [
                { key: 'code', icon: <CodeOutlined />, label: '生成代码', disabled: !pageId || isDirty },
                { key: 'share', icon: <ShareAltOutlined />, label: '分享到市场', disabled: !pageId },
                { key: 'deploy', icon: <CloudUploadOutlined />, label: '部署', disabled: !pageId },
              ],
              onClick: ({ key }) => {
                if (key === 'code') onCode();
                if (key === 'share') onShare();
                if (key === 'deploy') onDeploy();
              },
            }}
          >
            <Button icon={<MoreOutlined />} />
          </Dropdown>

          <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#F3F4F6', display: 'flex', alignItems: 'center', justifyContent: 'center', marginLeft: 8 }}>
            <UserOutlined style={{ color: EDITOR_COLORS.textSecondary }} />
          </div>
        </Space>
      </div>
    );
};

export default EditorHeader;
