/** 数据源面板 -- 管理页面级 API 数据源 */

import React, { useState, useCallback, useMemo } from 'react';
import { useDraggable } from '@dnd-kit/react';
import {
  Button,
  Form,
  Input,
  Select,
  Switch,
  Modal,
  Tag,
  Space,
  Typography,
  Tooltip,
  Popconfirm,
  message,
  InputNumber,
  Collapse,
} from 'antd';
import {
  PlusOutlined,
  ApiOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  DragOutlined,
  LinkOutlined,
} from '@ant-design/icons';
import { useEditorStore } from '../store';
import { lowcodeApi } from '@hospital/api';
import type { ApiDataSource, StaticDataSource, MockDataSource, DataSource } from '@hospital/shared';
import type { DataSourceTestResponse } from '@hospital/api';

const { Text } = Typography;

// ---------------------------------------------------------------------------
// KV (key-value) pair editor for params / headers
// ---------------------------------------------------------------------------

interface KVPair {
  key: string;
  value: string;
}

/** 将 Record<string, any> 转为 KVPair[] */
function recordToKV(record?: Record<string, any>): KVPair[] {
  if (!record || Object.keys(record).length === 0) return [{ key: '', value: '' }];
  return Object.entries(record).map(([key, value]) => ({
    key,
    value: typeof value === 'string' ? value : JSON.stringify(value),
  }));
}

/** 将 KVPair[] 转为 Record<string, any> (跳过空 key) */
function kvToRecord(pairs: KVPair[]): Record<string, any> | undefined {
  const result: Record<string, any> = {};
  let hasEntries = false;
  for (const pair of pairs) {
    if (pair.key.trim()) {
      result[pair.key.trim()] = pair.value;
      hasEntries = true;
    }
  }
  return hasEntries ? result : undefined;
}

/** KV 编辑器组件 */
function KVEditor({
  value,
  onChange,
  placeholder,
}: {
  value?: KVPair[];
  onChange?: (pairs: KVPair[]) => void;
  placeholder?: { key: string; value: string };
}) {
  const pairs = value && value.length > 0 ? value : [{ key: '', value: '' }];

  const update = (index: number, field: 'key' | 'value', val: string) => {
    const next = [...pairs];
    next[index] = { ...next[index], [field]: val };
    // 如果最后一行有内容，自动追加空行
    if (index === pairs.length - 1 && (next[index].key || next[index].value)) {
      next.push({ key: '', value: '' });
    }
    onChange?.(next);
  };

  const remove = (index: number) => {
    const next = pairs.filter((_, i) => i !== index);
    if (next.length === 0) next.push({ key: '', value: '' });
    onChange?.(next);
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={4}>
      {pairs.map((pair, i) => (
        <Space key={i} style={{ width: '100%' }} size={4}>
          <Input
            size="small"
            placeholder={placeholder?.key || 'Key'}
            value={pair.key}
            onChange={(e) => update(i, 'key', e.target.value)}
            style={{ width: 100 }}
          />
          <Input
            size="small"
            placeholder={placeholder?.value || 'Value'}
            value={pair.value}
            onChange={(e) => update(i, 'value', e.target.value)}
            style={{ width: 140 }}
          />
          {pairs.length > 1 && i < pairs.length - 1 && (
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => remove(i)}
            />
          )}
        </Space>
      ))}
    </Space>
  );
}

// ---------------------------------------------------------------------------
// Draggable data source item
// ---------------------------------------------------------------------------

function DraggableDataSource({ ds }: { ds: DataSource }) {
  const { ref } = useDraggable({
    id: `datasource-${ds.id}`,
    data: {
      type: 'data-source',
      dataSource: ds,
    },
  });

  return (
    <div
      ref={ref}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        cursor: 'grab',
        color: 'var(--color-text-tertiary)',
        fontSize: 12,
      }}
    >
      <DragOutlined />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Data source list item
// ---------------------------------------------------------------------------

function DataSourceItem({
  ds,
  onEdit,
  onDelete,
}: {
  ds: DataSource;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const methodColors: Record<string, string> = {
    GET: 'var(--color-success)',
    POST: 'var(--color-primary)',
    PUT: 'var(--color-warning)',
    DELETE: 'var(--color-error)',
    PATCH: '#722ed1',
  };

  const typeColors: Record<string, string> = {
    api: 'blue',
    static: 'cyan',
    mock: 'magenta',
  };

  const typeLabels: Record<string, string> = {
    api: 'API',
    static: '静态',
    mock: 'Mock',
  };

  const subtitle = ds.type === 'api'
    ? (ds as ApiDataSource).url || '未配置 URL'
    : ds.type === 'static'
      ? '内联静态数据'
      : `Mock 数据${(ds as MockDataSource).delay ? ` (${(ds as MockDataSource).delay}ms)` : ''}`;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '6px 8px',
        borderRadius: 6,
        border: '1px solid var(--color-border-secondary)',
        background: 'var(--color-bg-container)',
        marginBottom: 6,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 0 }}>
        <DraggableDataSource ds={ds} />
        <div style={{ minWidth: 0, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Text strong style={{ fontSize: 12 }} ellipsis>
              {ds.name || ds.id}
            </Text>
            <Tag
              color={typeColors[ds.type] || 'default'}
              style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}
            >
              {typeLabels[ds.type] || ds.type}
            </Tag>
            {ds.type === 'api' && (ds as ApiDataSource).method && (
              <Tag
                color={methodColors[(ds as ApiDataSource).method] || 'var(--color-text-tertiary)'}
                style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}
              >
                {(ds as ApiDataSource).method}
              </Tag>
            )}
            {ds.type === 'api' && (ds as ApiDataSource).manual && (
              <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>
                手动
              </Tag>
            )}
          </div>
          <Text
            type="secondary"
            style={{ fontSize: 11 }}
            ellipsis
          >
            {subtitle}
          </Text>
        </div>
      </div>
      <Space size={0}>
        <Tooltip title="编辑">
          <Button type="text" size="small" icon={<EditOutlined />} onClick={onEdit} />
        </Tooltip>
        <Popconfirm title="确定删除此数据源?" onConfirm={onDelete} okText="删除" cancelText="取消">
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      </Space>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Test result display
// ---------------------------------------------------------------------------

function TestResultPanel({ result }: { result: DataSourceTestResponse | null }) {
  if (!result) return null;

  if (!result.success) {
    return (
      <div style={{ marginTop: 12, padding: 12, background: 'var(--color-white)2f0', borderRadius: 6, border: '1px solid #ffccc7' }}>
        <Text type="danger" style={{ fontSize: 12 }}>
          请求失败: {result.error || '未知错误'}
        </Text>
        {result.statusCode && (
          <div><Text type="secondary" style={{ fontSize: 11 }}>HTTP {result.statusCode}</Text></div>
        )}
        <div><Text type="secondary" style={{ fontSize: 11 }}>耗时 {result.elapsedMs}ms</Text></div>
      </div>
    );
  }

  return (
    <div style={{ marginTop: 12, padding: 12, background: 'var(--color-success-bg)', borderRadius: 6, border: '1px solid #b7eb8f' }}>
      <div style={{ marginBottom: 8 }}>
        <Text type="success" style={{ fontSize: 12 }}>
          请求成功
        </Text>
        {result.statusCode && (
          <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>HTTP {result.statusCode}</Text>
        )}
        <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>耗时 {result.elapsedMs}ms</Text>
      </div>

      {result.fields && result.fields.length > 0 && (
        <div style={{ marginBottom: 8 }}>
          <Text strong style={{ fontSize: 11, display: 'block', marginBottom: 4 }}>
            字段建议 (可绑定到组件属性):
          </Text>
          {result.fields.slice(0, 10).map((f) => (
            <Tag key={f.path} style={{ fontSize: 10, marginBottom: 2 }}>
              {f.path} <Text type="secondary">({f.type})</Text>
            </Tag>
          ))}
        </div>
      )}

      {result.sampleData !== undefined && (
        <Collapse ghost size="small" items={[{
          key: 'sample',
          label: <Text style={{ fontSize: 11 }}>样本数据</Text>,
          children: (
            <pre style={{
              fontSize: 10,
              maxHeight: 150,
              overflow: 'auto',
              background: 'var(--color-bg-layout)',
              padding: 8,
              borderRadius: 4,
              margin: 0,
            }}>
              {JSON.stringify(result.sampleData, null, 2)}
            </pre>
          ),
        }]} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Add / Edit modal
// ---------------------------------------------------------------------------

interface DataSourceFormProps {
  visible: boolean;
  editingDs: DataSource | null;
  onOk: (ds: DataSource) => void;
  onCancel: () => void;
}

function DataSourceFormModal({ visible, editingDs, onOk, onCancel }: DataSourceFormProps) {
  const [form] = Form.useForm();
  const [paramsKV, setParamsKV] = useState<KVPair[]>([{ key: '', value: '' }]);
  const [headersKV, setHeadersKV] = useState<KVPair[]>([{ key: '', value: '' }]);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<DataSourceTestResponse | null>(null);
  const [dsType, setDsType] = useState<'api' | 'static' | 'mock'>('api');
  const [staticData, setStaticData] = useState<string>('');
  const [mockData, setMockData] = useState<string>('');
  const [mockDelay, setMockDelay] = useState<number>(0);

  /** 当编辑对象变化时，回填表单 */
  React.useEffect(() => {
    if (visible) {
      if (editingDs) {
        setDsType(editingDs.type || 'api');
        form.setFieldsValue({
          name: editingDs.name || '',
          type: editingDs.type || 'api',
        });

        if (editingDs.type === 'api') {
          const apiDs = editingDs as ApiDataSource;
          form.setFieldsValue({
            url: apiDs.url,
            method: apiDs.method,
            dataPath: apiDs.dataPath || '',
            pollingInterval: apiDs.pollingInterval || 0,
            manual: apiDs.manual || false,
          });
          setParamsKV(recordToKV(apiDs.params));
          setHeadersKV(recordToKV(apiDs.headers));
        } else if (editingDs.type === 'static') {
          const staticDs = editingDs as StaticDataSource;
          setStaticData(staticDs.data != null ? JSON.stringify(staticDs.data, null, 2) : '');
        } else if (editingDs.type === 'mock') {
          const mockDs = editingDs as MockDataSource;
          setMockData(mockDs.data != null ? JSON.stringify(mockDs.data, null, 2) : '');
          setMockDelay(mockDs.delay || 0);
        }
      } else {
        form.resetFields();
        setDsType('api');
        setParamsKV([{ key: '', value: '' }]);
        setHeadersKV([{ key: '', value: '' }]);
        setStaticData('');
        setMockData('');
        setMockDelay(0);
      }
      setTestResult(null);
    }
  }, [visible, editingDs, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      const currentType = values.type || 'api';
      const base = {
        id: editingDs?.id || `ds_${Date.now()}`,
        name: values.name || undefined,
      };

      if (currentType === 'static') {
        let parsed: any = undefined;
        if (staticData.trim()) {
          try {
            parsed = JSON.parse(staticData);
          } catch {
            form.setFields([{ name: 'staticData', errors: ['JSON 格式不正确'] }]);
            return;
          }
        }
        const ds: StaticDataSource = { ...base, type: 'static', data: parsed };
        onOk(ds);
      } else if (currentType === 'mock') {
        let parsed: any = undefined;
        if (mockData.trim()) {
          try {
            parsed = JSON.parse(mockData);
          } catch {
            form.setFields([{ name: 'mockData', errors: ['JSON 格式不正确'] }]);
            return;
          }
        }
        const ds: MockDataSource = {
          ...base,
          type: 'mock',
          data: parsed,
          delay: mockDelay || undefined,
        };
        onOk(ds);
      } else {
        const ds: ApiDataSource = {
          ...base,
          type: 'api',
          url: values.url,
          method: values.method,
          params: kvToRecord(paramsKV),
          headers: kvToRecord(headersKV),
          dataPath: values.dataPath || undefined,
          pollingInterval: values.pollingInterval || undefined,
          manual: values.manual || undefined,
        };
        onOk(ds);
      }
    } catch {
      // form validation failed, errors already shown
    }
  };

  const handleTest = async () => {
    try {
      const values = await form.validateFields(['url', 'method']);
      setTesting(true);
      setTestResult(null);
      const result = await lowcodeApi.testDataSource({
        url: values.url,
        method: values.method,
        params: kvToRecord(paramsKV),
        headers: kvToRecord(headersKV),
        responsePath: form.getFieldValue('dataPath') || undefined,
      });
      // 后端返回的是 camelCase (通过 BaseSchema alias_generator)，直接使用
      setTestResult(result as unknown as DataSourceTestResponse);
    } catch (err: any) {
      setTestResult({
        success: false,
        error: err?.message || '测试请求失败',
        elapsedMs: 0,
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <Modal
      title={editingDs ? '编辑数据源' : '添加数据源'}
      open={visible}
      onOk={handleOk}
      onCancel={onCancel}
      width={560}
      okText={editingDs ? '保存' : '添加'}
      cancelText="取消"
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        size="small"
        initialValues={{
          type: 'api',
          method: 'GET',
          manual: false,
          pollingInterval: 0,
        }}
      >
        <Form.Item name="name" label="数据源名称">
          <Input placeholder="如: 科室列表接口" />
        </Form.Item>

        <Form.Item
          name="type"
          label="数据源类型"
          rules={[{ required: true }]}
        >
          <Select
            options={[
              { label: 'API — 远程接口', value: 'api' },
              { label: 'Static — 内联静态数据', value: 'static' },
              { label: 'Mock — 模拟数据', value: 'mock' },
            ]}
            onChange={(val) => setDsType(val)}
          />
        </Form.Item>

        {/* ---- API 类型字段 ---- */}
        {dsType === 'api' && (
          <>
            <Form.Item
              name="url"
              label="请求 URL"
              rules={[{ required: true, message: '请输入请求 URL' }]}
            >
              <Input placeholder="/api/v1/departments 或 https://example.com/api" />
            </Form.Item>

            <Space style={{ width: '100%' }} size={12} align="start">
              <Form.Item
                name="method"
                label="请求方法"
                rules={[{ required: true }]}
                style={{ width: 120 }}
              >
                <Select
                  options={['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((m) => ({
                    label: m,
                    value: m,
                  }))}
                />
              </Form.Item>

              <Form.Item name="dataPath" label="数据路径" style={{ flex: 1 }}>
                <Input placeholder="如: data.list (从响应中提取)" />
              </Form.Item>
            </Space>

            <Collapse
              ghost
              size="small"
              items={[
                {
                  key: 'params',
                  label: <Text style={{ fontSize: 12 }}>请求参数 (Query Params)</Text>,
                  children: <KVEditor value={paramsKV} onChange={setParamsKV} placeholder={{ key: '参数名', value: '参数值' }} />,
                },
                {
                  key: 'headers',
                  label: <Text style={{ fontSize: 12 }}>自定义 Headers</Text>,
                  children: <KVEditor value={headersKV} onChange={setHeadersKV} placeholder={{ key: 'Header', value: 'Value' }} />,
                },
              ]}
              style={{ marginBottom: 16 }}
            />

            <Space style={{ width: '100%' }} size={12}>
              <Form.Item name="pollingInterval" label="轮询间隔 (ms)" style={{ width: 160 }}>
                <InputNumber min={0} step={1000} placeholder="0 = 不轮询" style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item name="manual" label="手动触发" valuePropName="checked">
                <Switch size="small" />
              </Form.Item>
            </Space>

            {/* 测试按钮 */}
            <div style={{ marginBottom: 12 }}>
              <Button
                icon={<ThunderboltOutlined />}
                onClick={handleTest}
                loading={testing}
                size="small"
              >
                测试请求
              </Button>
            </div>

            <TestResultPanel result={testResult} />
          </>
        )}

        {/* ---- Static 类型字段 ---- */}
        {dsType === 'static' && (
          <Form.Item
            name="staticData"
            label="静态数据 (JSON)"
            rules={[{ required: true, message: '请输入静态数据' }]}
          >
            <Input.TextArea
              rows={8}
              placeholder={'[\n  { "id": 1, "name": "选项一" },\n  { "id": 2, "name": "选项二" }\n]'}
              value={staticData}
              onChange={(e) => setStaticData(e.target.value)}
              style={{ fontFamily: 'monospace', fontSize: 12 }}
            />
          </Form.Item>
        )}

        {/* ---- Mock 类型字段 ---- */}
        {dsType === 'mock' && (
          <>
            <Space style={{ width: '100%' }} size={12}>
              <Form.Item name="mockDelay" label="延迟 (ms)" style={{ width: 160 }}>
                <InputNumber
                  min={0}
                  step={100}
                  placeholder="0 = 无延迟"
                  style={{ width: '100%' }}
                  value={mockDelay}
                  onChange={(val) => setMockDelay(val || 0)}
                />
              </Form.Item>
            </Space>

            <Form.Item
              name="mockData"
              label="Mock 数据 (JSON)"
              rules={[{ required: true, message: '请输入 Mock 数据' }]}
            >
              <Input.TextArea
                rows={8}
                placeholder={'[\n  { "id": 1, "name": "模拟项一" },\n  { "id": 2, "name": "模拟项二" }\n]'}
                value={mockData}
                onChange={(e) => setMockData(e.target.value)}
                style={{ fontFamily: 'monospace', fontSize: 12 }}
              />
            </Form.Item>
          </>
        )}
      </Form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

/** 数据源面板 */
export const DataSourcePanel: React.FC = () => {
  const schema = useEditorStore((s) => s.schema);
  const setSchema = useEditorStore((s) => s.setSchema);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingDs, setEditingDs] = useState<DataSource | null>(null);

  // 从 schema 中读取数据源列表
  const dataSources: DataSource[] = useMemo(
    () => (schema as any).dataSources || [],
    [schema],
  );

  /** 更新 schema 中的 dataSources */
  const updateDataSources = useCallback(
    (next: DataSource[]) => {
      const newSchema = { ...schema, dataSources: next };
      setSchema(newSchema);
    },
    [schema, setSchema],
  );

  /** 打开新增弹窗 */
  const handleAdd = useCallback(() => {
    setEditingDs(null);
    setModalVisible(true);
  }, []);

  /** 打开编辑弹窗 */
  const handleEdit = useCallback((ds: DataSource) => {
    setEditingDs(ds);
    setModalVisible(true);
  }, []);

  /** 删除数据源 */
  const handleDelete = useCallback(
    (dsId: string) => {
      updateDataSources(dataSources.filter((ds) => ds.id !== dsId));
      message.success('数据源已删除');
    },
    [dataSources, updateDataSources],
  );

  /** 新增或编辑确认 */
  const handleFormOk = useCallback(
    (ds: DataSource) => {
      const existing = dataSources.findIndex((d) => d.id === ds.id);
      if (existing >= 0) {
        // 编辑: 替换
        const next = [...dataSources];
        next[existing] = ds;
        updateDataSources(next);
        message.success('数据源已更新');
      } else {
        // 新增: 追加
        updateDataSources([...dataSources, ds]);
        message.success('数据源已添加');
      }
      setModalVisible(false);
    },
    [dataSources, updateDataSources],
  );

  return (
    <div
      style={{
        padding: 12,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* 头部 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 12,
        }}
      >
        <Space size={4}>
          <ApiOutlined style={{ color: 'var(--color-primary)' }} />
          <Text strong style={{ fontSize: 13 }}>
            数据源
          </Text>
          {dataSources.length > 0 && (
            <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>
              {dataSources.length}
            </Tag>
          )}
        </Space>
        <Tooltip title="添加数据源">
          <Button
            type="text"
            size="small"
            icon={<PlusOutlined />}
            onClick={handleAdd}
          />
        </Tooltip>
      </div>

      {/* 数据源列表 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {dataSources.length === 0 ? (
          <div
            style={{
              textAlign: 'center',
              padding: '24px 0',
              color: 'var(--color-border)',
            }}
          >
            <LinkOutlined style={{ fontSize: 24, marginBottom: 8, display: 'block' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              暂无数据源
            </Text>
            <div style={{ marginTop: 8 }}>
              <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={handleAdd}>
                添加数据源
              </Button>
            </div>
          </div>
        ) : (
          dataSources.map((ds) => (
            <DataSourceItem
              key={ds.id}
              ds={ds}
              onEdit={() => handleEdit(ds)}
              onDelete={() => handleDelete(ds.id)}
            />
          ))
        )}
      </div>

      {/* 提示信息 */}
      {dataSources.length > 0 && (
        <div
          style={{
            borderTop: '1px solid var(--color-border-secondary)',
            paddingTop: 8,
            marginTop: 8,
          }}
        >
          <Text type="secondary" style={{ fontSize: 10 }}>
            拖拽数据源到画布组件上可自动创建绑定
          </Text>
        </div>
      )}

      {/* 新增/编辑弹窗 */}
      <DataSourceFormModal
        visible={modalVisible}
        editingDs={editingDs}
        onOk={handleFormOk}
        onCancel={() => setModalVisible(false)}
      />
    </div>
  );
};
