/** 低代码编辑器主页面 */

import React, { useEffect, useCallback, useRef, useState } from 'react';
import { useParams, history } from '@umijs/max';
import { Button, Dropdown, Space, message, Spin, Tooltip, Modal, Input, Tabs } from 'antd';
import {
  SaveOutlined,
  UndoOutlined,
  RedoOutlined,
  EyeOutlined,
  SendOutlined,
  ArrowLeftOutlined,
  AppstoreOutlined,
  ApiOutlined,
  ApartmentOutlined,
  CodeOutlined,
  HistoryOutlined,
  ShareAltOutlined,
  CloudUploadOutlined,
  MoreOutlined,
} from '@ant-design/icons';
import CodePreviewModal from './components/CodePreviewModal';
import DeployPanel from './components/DeployPanel';
import ShareDialog from './components/ShareDialog';
import VersionHistory from './components/VersionHistory';
import { useEditorStore } from './store';
import type { LowCodeNode } from '@hospital/shared';
import { ComponentPanel } from './components/ComponentPanel';
import { DataSourcePanel } from './components/DataSourcePanel';
import { LayerPanel } from './components/LayerPanel';
import { Canvas, EditorDndProvider } from './components/Canvas';
import { PropertyPanel } from './components/PropertyPanel';
import EditorTour from './components/EditorTour';
import { lowcodeApi } from '@hospital/api';
import { EDITOR_COLORS, EDITOR_LAYOUT } from './constants';
import { findNodeById, findParentNode, regenerateIds } from './utils/tree';

/** 从 localStorage 读取属性面板宽度 */
function getStoredPanelWidth(): number {
  try {
    const stored = localStorage.getItem('lowcode-property-panel-width');
    if (stored) {
      const width = Number(stored);
      if (width >= 260 && width <= 600) return width;
    }
  } catch {}
  return EDITOR_LAYOUT.rightPanelWidth;
}
import { pinyin } from 'pinyin-pro';

/** 编辑器主页面 */
const LowCodeEditor: React.FC = () => {
  const params = useParams();
  const id = params.id as string | undefined;
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [saveModalName, setSaveModalName] = useState('');
  const [saveModalSlug, setSaveModalSlug] = useState('');
  const [saveModalSlugTouched, setSaveModalSlugTouched] = useState(false);
  const [codeModalVisible, setCodeModalVisible] = useState(false);
  const [versionHistoryVisible, setVersionHistoryVisible] = useState(false);
  const [shareDialogVisible, setShareDialogVisible] = useState(false);
  const [deployPanelVisible, setDeployPanelVisible] = useState(false);
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);

  // P1-2: 属性面板可拖拽调整宽度
  const [rightPanelWidth, setRightPanelWidth] = useState(getStoredPanelWidth);
  const [isResizing, setIsResizing] = useState(false);
  const resizeStartXRef = useRef(0);
  const resizeStartWidthRef = useRef(0);

  // P1-3: 编辑器引导 Tour refs
  const componentPanelRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  const propertyPanelRef = useRef<HTMLDivElement>(null);
  const saveButtonRef = useRef<HTMLDivElement>(null);
  const undoButtonRef = useRef<HTMLDivElement>(null);

  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    resizeStartXRef.current = e.clientX;
    resizeStartWidthRef.current = rightPanelWidth;
  }, [rightPanelWidth]);

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = resizeStartXRef.current - e.clientX;
      const newWidth = Math.max(260, Math.min(600, resizeStartWidthRef.current + deltaX));
      setRightPanelWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      // 保存到 localStorage
      try {
        localStorage.setItem('lowcode-property-panel-width', String(rightPanelWidth));
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
  }, [isResizing, rightPanelWidth]);

  const schema = useEditorStore((s) => s.schema);
  const pageId = useEditorStore((s) => s.pageId);
  const setPageId = useEditorStore((s) => s.setPageId);
  const setSchema = useEditorStore((s) => s.setSchema);
  const setLoading = useEditorStore((s) => s.setLoading);
  const loading = useEditorStore((s) => s.loading);
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);
  const historyIndex = useEditorStore((s) => s.historyIndex);
  const historyLength = useEditorStore((s) => s.history.length);
  const isDirty = useEditorStore((s) => s.isDirty);
  const markSaved = useEditorStore((s) => s.markSaved);
  const removeNode = useEditorStore((s) => s.removeNode);
  const addNode = useEditorStore((s) => s.addNode);
  const selectAll = useEditorStore((s) => s.selectAll);
  const toggleNodeSelect = useEditorStore((s) => s.toggleNodeSelect);
  const addToRoot = useEditorStore((s) => s.addToRoot);
  const updateNodeProps = useEditorStore((s) => s.updateNodeProps);

  /** 加载页面数据 */
  useEffect(() => {
    if (!id || id === 'new') return;

    const loadPage = async () => {
      setLoading(true);
      try {
        const page = await lowcodeApi.getPage(id);
        setPageId(page.id);
        if (page.schemaData && Object.keys(page.schemaData).length > 0) {
          setSchema(page.schemaData as any);
        }
        markSaved();
      } catch (err) {
        message.error('加载页面失败');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadPage();
  }, [id, setPageId, setSchema, setLoading, markSaved]);

  /** 将中文名称转换为拼音 slug */
  const generateSlug = useCallback((name: string): string => {
    if (!name.trim()) return `page_${Date.now()}`;
    const py = pinyin(name, { toneType: 'none', type: 'array' });
    return py
      .map((s) => s.toLowerCase())
      .join('-')
      .replace(/[^a-z0-9-]/g, '')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '');
  }, []);

  /** 执行实际保存逻辑 */
  const doSave = useCallback(
    async (name?: string, slug?: string) => {
      setSaving(true);
      try {
        if (pageId) {
          await lowcodeApi.updatePage(pageId, { schemaData: schema as any });
        } else {
          const result = await lowcodeApi.createPage({
            name: name || '新页面',
            slug: slug || `page_${Date.now()}`,
            schemaData: schema as any,
          });
          setPageId(result.id);
          history.replace(`/platform/lowcode/editor/${result.id}`);
        }
        message.success('保存成功');
        setLastSavedAt(new Date());
        markSaved();
      } catch (err) {
        message.error('保存失败');
        console.error(err);
      } finally {
        setSaving(false);
      }
    },
    [pageId, schema, setPageId, markSaved],
  );

  /** 保存页面 — 新页面先弹窗填写名称 */
  const handleSave = useCallback(() => {
    if (pageId) {
      return doSave();
    } else {
      setSaveModalName('');
      setSaveModalSlug('');
      setSaveModalSlugTouched(false);
      setSaveModalVisible(true);
      return Promise.resolve();
    }
  }, [pageId, doSave]);

  /** 保存弹窗确认 */
  const handleSaveModalOk = useCallback(() => {
    const name = saveModalName.trim();
    if (!name) {
      message.warning('请输入页面名称');
      return;
    }
    const slug = saveModalSlug.trim() || generateSlug(name);
    setSaveModalVisible(false);
    doSave(name, slug);
  }, [saveModalName, saveModalSlug, generateSlug, doSave]);

  /** 发布页面 */
  const handlePublish = useCallback(async () => {
    if (!pageId) {
      message.warning('请先保存页面');
      return;
    }
    setPublishing(true);
    try {
      // 先保存
      await lowcodeApi.updatePage(pageId, { schemaData: schema as any });
      // 再发布
      await lowcodeApi.publishPage(pageId);
      message.success('发布成功');
      markSaved();
    } catch (err) {
      message.error('发布失败');
      console.error(err);
    } finally {
      setPublishing(false);
    }
  }, [pageId, schema, markSaved]);

  /** 预览 */
  const handlePreview = useCallback(() => {
    if (!pageId) {
      message.warning('请先保存页面再预览');
      return;
    }
    window.open(`/platform/lowcode/preview/${pageId}`, '_blank');
  }, [pageId]);

  /** 打开代码生成弹窗 */
  const handleOpenCodeModal = useCallback(() => {
    if (isDirty) {
      message.warning('请先保存页面再生成代码');
      return;
    }
    setCodeModalVisible(true);
  }, [isDirty]);

  /** 剪贴板 ref，避免闭包过期 */
  const clipboardRef = useRef<string | null>(null);

  /** 键盘快捷键 */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const isMod = e.metaKey || e.ctrlKey;
      const activeId = useEditorStore.getState().selectedNodeId;

      // Ctrl+Z / Ctrl+Shift+Z — 撤销 / 重做
      if (isMod && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          redo();
        } else {
          undo();
        }
        return;
      }

      // Ctrl+S — 保存
      if (isMod && e.key === 's') {
        e.preventDefault();
        handleSave();
        return;
      }

      // Delete / Backspace — 删除选中组件
      if ((e.key === 'Delete' || e.key === 'Backspace') && activeId) {
        // 忽略输入框内的 Delete/Backspace
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable) {
          return;
        }
        e.preventDefault();
        removeNode(activeId);
        return;
      }

      // Ctrl+C — 复制选中组件到剪贴板
      if (isMod && e.key === 'c' && activeId) {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable) {
          return; // 输入框内走浏览器默认
        }
        e.preventDefault();
        const { schema } = useEditorStore.getState();
        const node = findNodeById(schema.children, activeId);
        if (node) {
          const json = JSON.stringify(node, null, 2);
          clipboardRef.current = json;
          navigator.clipboard?.writeText(json).catch(() => {
            // 非安全上下文 fallback，已经写入 ref
          });
        }
        return;
      }

      // Ctrl+V — 粘贴组件
      if (isMod && e.key === 'v') {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable) {
          return;
        }
        e.preventDefault();

        const pasteFromClipboard = async () => {
          let json = clipboardRef.current;
          if (!json) {
            try {
              json = await navigator.clipboard?.readText();
            } catch {
              // 无权限
            }
          }
          if (!json) return;

          let pastedNode: LowCodeNode;
          try {
            pastedNode = JSON.parse(json);
          } catch {
            return; // 非法 JSON
          }
          if (!pastedNode?.componentName) return;

          // 重新生成 ID，避免重复
          const regenerated = regenerateIds(pastedNode);

          // 找到目标父节点：选中节点的父节点，或者根
          const { schema } = useEditorStore.getState();
          const targetParent = activeId
            ? findParentNode(schema.children, activeId)
            : null;
          if (targetParent) {
            const index = targetParent.children?.length ?? 0;
            addNode(regenerated, targetParent.id, index);
          } else {
            // 粘贴到根 children
            addToRoot(regenerated, schema.children.length);
          }
        };
        pasteFromClipboard();
        return;
      }

      // Ctrl+D — 复制选中组件（原位复制，偏移 10px）
      if (isMod && e.key === 'd' && activeId) {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable) {
          return;
        }
        e.preventDefault();
        const { schema } = useEditorStore.getState();
        const node = findNodeById(schema.children, activeId);
        if (!node) return;

        const clone = JSON.parse(JSON.stringify(node));
        const duplicated = regenerateIds(clone);

        // 偏移 10px（通过 style.left / style.top）
        const oldLeft = Number(duplicated.props?.style?.left) || 0;
        const oldTop = Number(duplicated.props?.style?.top) || 0;
        duplicated.props = {
          ...duplicated.props,
          style: {
            ...duplicated.props?.style,
            left: oldLeft + 10,
            top: oldTop + 10,
          },
        };

        // 添加到同一父节点，紧跟在原节点后面
        const parent = findParentNode(schema.children, activeId);
        const siblings = parent?.children ?? schema.children;
        const originalIndex = siblings.findIndex((c: LowCodeNode) => c.id === activeId);
        if (parent) {
          addNode(duplicated, parent.id, originalIndex + 1);
        } else {
          addToRoot(duplicated, originalIndex + 1);
        }
        return;
      }

      // Ctrl+A — 全选
      if (isMod && e.key === 'a') {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable) {
          return;
        }
        e.preventDefault();
        selectAll();
        return;
      }

      // 方向键 — 微调选中组件位置
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key) && activeId) {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable) {
          return;
        }
        e.preventDefault();
        const step = e.shiftKey ? 10 : 1;
        const styleUpdate: Record<string, number> = {};

        switch (e.key) {
          case 'ArrowLeft':
            styleUpdate.left = step * -1;
            break;
          case 'ArrowRight':
            styleUpdate.left = step;
            break;
          case 'ArrowUp':
            styleUpdate.top = step * -1;
            break;
          case 'ArrowDown':
            styleUpdate.top = step;
            break;
        }

        // 读取当前 style，叠加偏移
        const { schema } = useEditorStore.getState();
        const node = findNodeById(schema.children, activeId);
        if (!node) return;
        const currentLeft = Number(node.props?.style?.left) || 0;
        const currentTop = Number(node.props?.style?.top) || 0;
        updateNodeProps(activeId, {
          style: {
            ...node.props?.style,
            left: currentLeft + (styleUpdate.left ?? 0),
            top: currentTop + (styleUpdate.top ?? 0),
          },
        });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo, handleSave, removeNode, addNode, addToRoot, updateNodeProps, selectAll, toggleNodeSelect]);

  /** 浏览器关闭/刷新时的未保存更改警告 */
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [isDirty]);

  /** 带未保存检查的导航 — 有脏数据时弹窗确认 */
  const navigateWithDirtyCheck = useCallback(
    (targetPath: string) => {
      if (!isDirty) {
        history.push(targetPath);
        return;
      }
      Modal.confirm({
        title: '离开确认',
        content: '当前页面有未保存的更改，确定要离开吗？',
        okText: '保存并离开',
        cancelText: '不保存，直接离开',
        onOk: async () => {
          try {
            await handleSave();
          } catch {
            return;
          }
          history.push(targetPath);
        },
        onCancel: () => {
          history.push(targetPath);
        },
      });
    },
    [isDirty, handleSave],
  );

  /** 定时自动保存（30秒） */
  useEffect(() => {
    if (!pageId || !isDirty) return;

    autoSaveTimerRef.current = setInterval(() => {
      doSave();
      setLastSavedAt(new Date());
    }, 30000);

    return () => {
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current);
        autoSaveTimerRef.current = null;
      }
    };
  }, [isDirty, pageId, doSave]);

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: EDITOR_COLORS.workspaceBg }}>
      {/* 顶部工具栏 */}
      <div
        style={{
          height: EDITOR_LAYOUT.toolbarHeight,
          flexShrink: 0,
          borderBottom: `1px solid ${EDITOR_COLORS.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          padding: '0 16px',
          background: EDITOR_COLORS.panelBg,
        }}
      >
        <Space size={8} style={{ minWidth: 0, flexShrink: 0 }}>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigateWithDirtyCheck('/platform/lowcode/list')}
          >
            返回
          </Button>
          <span style={{ fontWeight: 500, fontSize: 15 }}>页面搭建</span>
        </Space>
        <Space size={4} style={{ flex: 1, justifyContent: 'center', minWidth: 160 }}>
          <Tooltip title="撤销 (Ctrl+Z)">
            <div ref={undoButtonRef} style={{ display: 'inline-flex' }}>
              <Button
                type="text"
                icon={<UndoOutlined />}
                onClick={undo}
                disabled={historyIndex <= 0}
              />
            </div>
          </Tooltip>
          <Tooltip title="重做 (Ctrl+Shift+Z)">
            <Button
              type="text"
              icon={<RedoOutlined />}
              onClick={redo}
              disabled={historyIndex >= historyLength - 1}
            />
          </Tooltip>
        </Space>
        <Space size={8} style={{ flexShrink: 0 }}>
          {lastSavedAt && (
            <span style={{ fontSize: 12, color: EDITOR_COLORS.textMuted, whiteSpace: 'nowrap' }}>
              上次保存: {lastSavedAt.toLocaleTimeString()}
            </span>
          )}
          <Dropdown
            trigger={['click']}
            menu={{
              items: [
                {
                  key: 'preview',
                  icon: <EyeOutlined />,
                  label: '预览',
                  disabled: !pageId,
                },
                {
                  key: 'code',
                  icon: <CodeOutlined />,
                  label: isDirty ? '生成代码（请先保存）' : '生成代码',
                  disabled: !pageId || isDirty,
                },
                {
                  key: 'history',
                  icon: <HistoryOutlined />,
                  label: '版本历史',
                  disabled: !pageId,
                },
                {
                  key: 'share',
                  icon: <ShareAltOutlined />,
                  label: '分享到市场',
                  disabled: !pageId,
                },
                {
                  key: 'deploy',
                  icon: <CloudUploadOutlined />,
                  label: '部署',
                  disabled: !pageId,
                },
              ],
              onClick: ({ key }) => {
                if (key === 'preview') handlePreview();
                if (key === 'code') handleOpenCodeModal();
                if (key === 'history') setVersionHistoryVisible(true);
                if (key === 'share') setShareDialogVisible(true);
                if (key === 'deploy') setDeployPanelVisible(true);
              },
            }}
          >
            <Button icon={<MoreOutlined />}>更多</Button>
          </Dropdown>
          <div ref={saveButtonRef} style={{ display: 'inline-flex' }}>
            <Button
              icon={<SaveOutlined />}
              onClick={handleSave}
              loading={saving}
            >
              保存
            </Button>
          </div>
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handlePublish}
            loading={publishing}
          >
            发布
          </Button>
        </Space>
      </div>

      {/* 主体区域 */}
      <Spin spinning={loading}>
        <EditorDndProvider>
          <div
            style={{
              height: `calc(100vh - ${EDITOR_LAYOUT.toolbarHeight}px)`,
              display: 'flex',
              overflow: 'hidden',
            }}
          >
            {/* 左侧面板 (物料 + 数据源) */}
            <div
              ref={componentPanelRef}
              style={{
                width: EDITOR_LAYOUT.leftPanelWidth,
                flexShrink: 0,
                borderRight: `1px solid ${EDITOR_COLORS.border}`,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                background: EDITOR_COLORS.panelBg,
              }}
            >
              <Tabs
                defaultActiveKey="components"
                size="small"
                className="lowcode-editor-tabs"
                style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}
                tabBarStyle={{ margin: 0, paddingLeft: 12, minHeight: 36, borderColor: EDITOR_COLORS.border }}
                items={[
                  {
                    key: 'components',
                    label: <span><AppstoreOutlined /> 物料</span>,
                    children: <ComponentPanel />,
                  },
                  {
                    key: 'datasource',
                    label: <span><ApiOutlined /> 数据</span>,
                    children: <DataSourcePanel />,
                  },
                  {
                    key: 'layers',
                    label: <span><ApartmentOutlined /> 图层</span>,
                    children: <LayerPanel />,
                  },
                ]}
              />
            </div>

            {/* 中间画布 */}
            <div ref={canvasRef} style={{ flex: 1, display: 'flex' }}>
              <Canvas />
            </div>

            {/* 可拖拽分隔条 */}
            <div
              onMouseDown={handleResizeStart}
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
            <div ref={propertyPanelRef} style={{ width: rightPanelWidth, flexShrink: 0, overflow: 'hidden' }}>
              <PropertyPanel />
            </div>
          </div>
        </EditorDndProvider>
      </Spin>
      {/* 保存新页面弹窗 */}
      <Modal
        title="保存页面"
        open={saveModalVisible}
        onOk={handleSaveModalOk}
        onCancel={() => setSaveModalVisible(false)}
        okText="保存"
        cancelText="取消"
        confirmLoading={saving}
      >
        <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
            页面名称 <span style={{ color: '#ff4d4f' }}>*</span>
          </label>
          <Input
            placeholder="例如: 科室介绍"
            value={saveModalName}
            onChange={(e) => {
              const val = e.target.value;
              setSaveModalName(val);
              if (!saveModalSlugTouched) {
                setSaveModalSlug(generateSlug(val));
              }
            }}
            onPressEnter={handleSaveModalOk}
            autoFocus
          />
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: 4, fontWeight: 500 }}>
            页面标识 (slug)
          </label>
          <Input
            placeholder="自动生成，可手动修改"
            value={saveModalSlug}
            onChange={(e) => {
              setSaveModalSlugTouched(true);
              setSaveModalSlug(e.target.value);
            }}
            onPressEnter={handleSaveModalOk}
          />
        </div>
      </Modal>
      {/* 代码生成弹窗 */}
      <CodePreviewModal
        open={codeModalVisible}
        onClose={() => setCodeModalVisible(false)}
        pageId={pageId}
      />
      {/* 版本历史面板 */}
      <VersionHistory
        open={versionHistoryVisible}
        onClose={() => setVersionHistoryVisible(false)}
      />
      {/* 分享到模板市场 */}
      <ShareDialog
        open={shareDialogVisible}
        onClose={() => setShareDialogVisible(false)}
      />
      {/* 部署管理面板 */}
      <DeployPanel
        open={deployPanelVisible}
        onClose={() => setDeployPanelVisible(false)}
      />
      {/* P1-3: 首次使用引导 */}
      <EditorTour
        componentPanelRef={componentPanelRef}
        canvasRef={canvasRef}
        propertyPanelRef={propertyPanelRef}
        saveButtonRef={saveButtonRef}
        undoButtonRef={undoButtonRef}
      />
    </div>
  );
};

export default LowCodeEditor;
