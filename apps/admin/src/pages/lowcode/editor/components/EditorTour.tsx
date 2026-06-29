/**
 * EditorTour - 低代码编辑器首次使用引导
 *
 * 使用 antd Tour 组件实现，步骤数据存储在本地。
 * 首次访问自动触发，之后可通过帮助按钮重新触发。
 */

import React, { useState, useCallback } from 'react';
import { Tour, Button } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import type { TourProps } from 'antd';

const TOUR_STORAGE_KEY = 'lowcode-editor-tour-seen';

/** 检查是否已完成引导 */
function hasSeenTour(): boolean {
  try {
    return localStorage.getItem(TOUR_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

/** 标记引导已完成 */
function markTourSeen(): void {
  try {
    localStorage.setItem(TOUR_STORAGE_KEY, 'true');
  } catch {}
}

interface EditorTourProps {
  /** 物料面板 ref */
  componentPanelRef: React.RefObject<HTMLDivElement>;
  /** 画布 ref */
  canvasRef: React.RefObject<HTMLDivElement>;
  /** 属性面板 ref */
  propertyPanelRef: React.RefObject<HTMLDivElement>;
  /** 工具栏保存按钮 ref */
  saveButtonRef: React.RefObject<HTMLDivElement>;
  /** 工具栏撤销按钮 ref */
  undoButtonRef: React.RefObject<HTMLDivElement>;
}

export const EditorTour: React.FC<EditorTourProps> = ({
  componentPanelRef,
  canvasRef,
  propertyPanelRef,
  saveButtonRef,
  undoButtonRef,
}) => {
  const [open, setOpen] = useState(!hasSeenTour());

  const steps: TourProps['steps'] = [
    {
      title: '欢迎使用页面搭建器',
      description: '这是一个可视化页面编辑器，通过拖拽组件即可快速搭建页面。让我们来了解一下核心功能。',
      target: () => document.body,
      placement: 'center',
    },
    {
      title: '物料面板',
      description: '从这里拖拽组件到画布。支持搜索、分类浏览，还有常用的代码片段模板。',
      target: () => componentPanelRef.current || document.body,
      placement: 'right',
    },
    {
      title: '画布区域',
      description: '这是页面预览区域。拖入组件后，可以点击选中、拖拽调整位置、右键菜单操作。',
      target: () => canvasRef.current || document.body,
      placement: 'left',
    },
    {
      title: '属性面板',
      description: '选中组件后，在这里配置属性、样式、事件和高级选项。支持数据绑定和联动规则。',
      target: () => propertyPanelRef.current || document.body,
      placement: 'left',
    },
    {
      title: '快捷操作',
      description: '支持 Ctrl+Z 撤销、Ctrl+S 保存、Ctrl+C/V 复制粘贴、Delete 删除等快捷键。',
      target: () => undoButtonRef.current || document.body,
      placement: 'bottom',
    },
    {
      title: '随时保存',
      description: '编辑器每 30 秒自动保存，也可以手动点击保存。完成后点击「发布」即可上线。',
      target: () => saveButtonRef.current || document.body,
      placement: 'bottom',
    },
  ];

  const handleFinish = useCallback(() => {
    setOpen(false);
    markTourSeen();
  }, []);

  const handleClose = useCallback(() => {
    setOpen(false);
    markTourSeen();
  }, []);

  const handleRestart = useCallback(() => {
    setOpen(true);
  }, []);

  return (
    <>
      <Tour
        open={open}
        steps={steps}
        onClose={handleClose}
        onFinish={handleFinish}
        indicatorsRender={(current, total) => (
          <span style={{ fontSize: 12, color: '#999' }}>
            {current + 1} / {total}
          </span>
        )}
        scrollIntoViewOptions={{ behavior: 'smooth', block: 'center' }}
      />
      {/* 帮助按钮 - 固定在右下角 */}
      <Button
        type="text"
        icon={<QuestionCircleOutlined />}
        onClick={handleRestart}
        style={{
          position: 'fixed',
          bottom: 16,
          right: 16,
          zIndex: 100,
          opacity: 0.6,
        }}
        title="查看使用引导"
      />
    </>
  );
};

export default EditorTour;
