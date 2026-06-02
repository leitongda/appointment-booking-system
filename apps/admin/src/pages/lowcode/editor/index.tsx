/** 低代码编辑器主页面 */

import React, { useEffect, useCallback, useState } from 'react';
import { useParams, history } from '@umijs/max';
import { Button, Space, message, Spin, Tooltip, Modal, Input, Tabs } from 'antd';
import { pinyin } from 'pinyin-pro';
import {
  SaveOutlined,
  UndoOutlined,
  RedoOutlined,
  EyeOutlined,
  SendOutlined,
  ArrowLeftOutlined,
  AppstoreOutlined,
  ApiOutlined,
  CodeOutlined,
  HistoryOutlined,
  ShareAltOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import CodePreviewModal from './components/CodePreviewModal';
import DeployPanel from './components/DeployPanel';
import ShareDialog from './components/ShareDialog';
import VersionHistory from './components/VersionHistory';
import { useEditorStore } from './store';
import { ComponentPanel } from './components/ComponentPanel';
import { DataSourcePanel } from './components/DataSourcePanel';
import { Canvas } from './components/Canvas';
import { PropertyPanel } from './components/PropertyPanel';
import { lowcodeApi } from '@hospital/api';

/** 编辑器主页面 */
const LowCodeEditor: React.FC = () => {
  const { id } = useParams<{ id: string }>();
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
  const savedSchema = useEditorStore((s) => s.savedSchema);
  const markSaved = useEditorStore((s) => s.markSaved);

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
      doSave();
    } else {
      setSaveModalName('');
      setSaveModalSlug('');
      setSaveModalSlugTouched(false);
      setSaveModalVisible(true);
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
    if (pageId) {
      window.open(`/platform/lowcode/preview/${pageId}`, '_blank');
    }
  }, [pageId]);

  /** 未保存更改标识 */
  const isDirty = JSON.stringify(schema) !== JSON.stringify(savedSchema);

  /** 打开代码生成弹窗 */
  const handleOpenCodeModal = useCallback(() => {
    if (isDirty) {
      message.warning('请先保存页面再生成代码');
      return;
    }
    setCodeModalVisible(true);
  }, [isDirty]);

  /** 键盘快捷键 */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          redo();
        } else {
          undo();
        }
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo, handleSave]);

  /** 未保存更改警告 */
  useEffect(() => {
    const isDirty = JSON.stringify(schema) !== JSON.stringify(savedSchema);

    /** 浏览器关闭/刷新时的警告 */
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    /** 路由切换时的警告 (Umi history.block) */
    const unblock = history.block((txLocation) => {
      if (isDirty) {
        const targetPath = txLocation.pathname + (txLocation.search || '');
        Modal.confirm({
          title: '离开确认',
          content: '当前页面有未保存的更改，确定要离开吗？',
          okText: '保存并离开',
          cancelText: '不保存，直接离开',
          onOk: async () => {
            unblock();
            await handleSave();
            history.push(targetPath);
          },
          onCancel: () => {
            unblock();
            history.push(targetPath);
          },
        });
        return false;
      }
      return true;
    });

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
      unblock();
    };
  }, [schema, savedSchema, handleSave]);

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* 顶部工具栏 */}
      <div
        style={{
          height: 48,
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          background: '#fff',
        }}
      >
        <Space>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => history.push('/platform/lowcode/list')}
          >
            返回
          </Button>
          <span style={{ fontWeight: 500, fontSize: 15 }}>页面搭建</span>
        </Space>
        <Space>
          <Tooltip title="撤销 (Ctrl+Z)">
            <Button
              type="text"
              icon={<UndoOutlined />}
              onClick={undo}
              disabled={historyIndex <= 0}
            />
          </Tooltip>
          <Tooltip title="重做 (Ctrl+Shift+Z)">
            <Button
              type="text"
              icon={<RedoOutlined />}
              onClick={redo}
              disabled={historyIndex >= historyLength - 1}
            />
          </Tooltip>
          <Button icon={<EyeOutlined />} onClick={handlePreview} disabled={!pageId}>
            预览
          </Button>
          <Tooltip title={isDirty ? '请先保存页面再生成代码' : '生成小程序代码'}>
            <Button
              icon={<CodeOutlined />}
              onClick={handleOpenCodeModal}
              disabled={!pageId || isDirty}
            >
              生成代码
            </Button>
          </Tooltip>
          <Button
            icon={<HistoryOutlined />}
            onClick={() => setVersionHistoryVisible(true)}
            disabled={!pageId}
          >
            版本历史
          </Button>
          <Button
            icon={<ShareAltOutlined />}
            onClick={() => setShareDialogVisible(true)}
            disabled={!pageId}
          >
            分享到市场
          </Button>
          <Button
            icon={<CloudUploadOutlined />}
            onClick={() => setDeployPanelVisible(true)}
            disabled={!pageId}
          >
            部署
          </Button>
          <Button
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
          >
            保存
          </Button>
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
        <div
          style={{
            flex: 1,
            display: 'flex',
            overflow: 'hidden',
          }}
        >
          {/* 左侧面板 (物料 + 数据源) */}
          <div style={{ width: 240, borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Tabs
              defaultActiveKey="components"
              size="small"
              style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
              tabBarStyle={{ margin: 0, paddingLeft: 12, minHeight: 36 }}
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
              ]}
            />
          </div>

          {/* 中间画布 */}
          <Canvas />

          {/* 右侧属性面板 */}
          <PropertyPanel />
        </div>
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
    </div>
  );
};

export default LowCodeEditor;
