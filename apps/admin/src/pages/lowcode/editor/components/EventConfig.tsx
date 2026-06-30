/** 事件配置组件 — 管理选中组件的事件处理器 */

import React, { useState, useCallback, useMemo } from 'react';
import {
  Button,
  Form,
  Input,
  Select,
  Modal,
  Tag,
  Space,
  Typography,
  Tooltip,
  Popconfirm,
  Empty,
} from 'antd';
import {
  PlusOutlined,
  ThunderboltOutlined,
  DeleteOutlined,
  EditOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import { useEditorStore } from '../store';
import { findNodeById } from '../utils/tree';
import type { EventHandler, EventAction } from '@hospital/shared';

const { Text } = Typography;

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** 支持的事件类型 */
const EVENT_OPTIONS = [
  { label: 'onClick — 点击', value: 'onClick' },
  { label: 'onChange — 值变化', value: 'onChange' },
  { label: 'onSubmit — 提交', value: 'onSubmit' },
  { label: 'onLoad — 加载完成', value: 'onLoad' },
];

/** 支持的动作类型 */
const ACTION_TYPE_OPTIONS = [
  { label: 'navigate — 页面跳转', value: 'navigate' },
  { label: 'showToast — 提示消息', value: 'showToast' },
  { label: 'updateVariable — 更新变量', value: 'updateVariable' },
  { label: 'fetchApi — 请求数据源', value: 'fetchApi' },
  { label: 'setData — 设置组件属性', value: 'setData' },
];

/** 动作类型的中文名称 */
const ACTION_TYPE_LABELS: Record<string, string> = {
  navigate: '跳转',
  showToast: '提示',
  updateVariable: '更新变量',
  fetchApi: '请求API',
  setData: '设置属性',
};

/** 动作类型的标签颜色 */
const ACTION_TYPE_COLORS: Record<string, string> = {
  navigate: 'blue',
  showToast: 'green',
  updateVariable: 'orange',
  fetchApi: 'purple',
  setData: 'cyan',
};

// ---------------------------------------------------------------------------
// Action form — renders payload fields based on action type
// ---------------------------------------------------------------------------

interface ActionFormProps {
  actionType: EventAction['type'];
  payload: Record<string, any>;
  onChange: (payload: Record<string, any>) => void;
}

function ActionPayloadForm({ actionType, payload, onChange }: ActionFormProps) {
  const update = (key: string, value: any) => {
    onChange({ ...payload, [key]: value });
  };

  switch (actionType) {
    case 'navigate':
      return (
        <Form.Item label="跳转地址" style={{ marginBottom: 0 }}>
          <Input
            size="small"
            placeholder="/pages/detail/index?id=123"
            value={payload.url || ''}
            onChange={(e) => update('url', e.target.value)}
          />
        </Form.Item>
      );

    case 'showToast':
      return (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          <Form.Item label="消息内容" style={{ marginBottom: 0 }}>
            <Input
              size="small"
              placeholder="操作成功"
              value={payload.message || ''}
              onChange={(e) => update('message', e.target.value)}
            />
          </Form.Item>
          <Form.Item label="图标" style={{ marginBottom: 0 }}>
            <Select
              size="small"
              allowClear
              placeholder="选择图标"
              value={payload.icon}
              onChange={(val) => update('icon', val)}
              options={[
                { label: '成功 (success)', value: 'success' },
                { label: '错误 (error)', value: 'error' },
                { label: '警告 (warning)', value: 'warning' },
                { label: '信息 (info)', value: 'info' },
                { label: '加载 (loading)', value: 'loading' },
              ]}
            />
          </Form.Item>
        </Space>
      );

    case 'updateVariable':
      return (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          <Form.Item label="变量名" style={{ marginBottom: 0 }}>
            <Input
              size="small"
              placeholder="count"
              value={payload.key || ''}
              onChange={(e) => update('key', e.target.value)}
            />
          </Form.Item>
          <Form.Item label="变量值" style={{ marginBottom: 0 }}>
            <Input
              size="small"
              placeholder="值或表达式，如 {{state.count + 1}}"
              value={payload.value ?? ''}
              onChange={(e) => update('value', e.target.value)}
            />
          </Form.Item>
        </Space>
      );

    case 'fetchApi':
      return (
        <Form.Item label="数据源 ID" style={{ marginBottom: 0 }}>
          <Input
            size="small"
            placeholder="数据源 ID，如 ds_123456"
            value={payload.dataSourceId || ''}
            onChange={(e) => update('dataSourceId', e.target.value)}
          />
        </Form.Item>
      );

    case 'setData':
      return (
        <Space direction="vertical" size={4} style={{ width: '100%' }}>
          <Form.Item label="目标节点 ID" style={{ marginBottom: 0 }}>
            <Input
              size="small"
              placeholder="目标组件节点 ID"
              value={payload.targetNodeId || ''}
              onChange={(e) => update('targetNodeId', e.target.value)}
            />
          </Form.Item>
          <Form.Item label="属性名" style={{ marginBottom: 0 }}>
            <Input
              size="small"
              placeholder="如: text、value、disabled"
              value={payload.key || ''}
              onChange={(e) => update('key', e.target.value)}
            />
          </Form.Item>
          <Form.Item label="属性值" style={{ marginBottom: 0 }}>
            <Input
              size="small"
              placeholder="值或表达式，如 {{state.title}}"
              value={payload.value ?? ''}
              onChange={(e) => update('value', e.target.value)}
            />
          </Form.Item>
        </Space>
      );

    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Single action item in the chain
// ---------------------------------------------------------------------------

interface ActionItemProps {
  index: number;
  total: number;
  action: EventAction;
  onChange: (action: EventAction) => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

function ActionItem({
  index,
  total,
  action,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
}: ActionItemProps) {
  return (
    <div
      style={{
        border: '1px solid var(--color-border-secondary)',
        borderRadius: 6,
        padding: 8,
        marginBottom: 8,
        background: 'var(--color-bg-container)',
      }}
    >
      {/* 动作头部 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 8,
        }}
      >
        <Space size={4}>
          <Tag
            color={ACTION_TYPE_COLORS[action.type] || 'default'}
            style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}
          >
            {index + 1}
          </Tag>
          <Text strong style={{ fontSize: 12 }}>
            {ACTION_TYPE_LABELS[action.type] || action.type}
          </Text>
        </Space>
        <Space size={0}>
          <Tooltip title="上移">
            <Button
              type="text"
              size="small"
              icon={<ArrowUpOutlined />}
              disabled={index === 0}
              onClick={onMoveUp}
            />
          </Tooltip>
          <Tooltip title="下移">
            <Button
              type="text"
              size="small"
              icon={<ArrowDownOutlined />}
              disabled={index === total - 1}
              onClick={onMoveDown}
            />
          </Tooltip>
          <Popconfirm title="确定删除此动作?" onConfirm={onRemove} okText="删除" cancelText="取消">
            <Button type="text" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      </div>

      {/* 动作类型选择 */}
      <Form.Item label="动作类型" style={{ marginBottom: 8 }}>
        <Select
          size="small"
          value={action.type}
          onChange={(val) => onChange({ ...action, type: val, payload: {} })}
          options={ACTION_TYPE_OPTIONS}
        />
      </Form.Item>

      {/* 动作参数 */}
      <ActionPayloadForm
        actionType={action.type}
        payload={action.payload}
        onChange={(payload) => onChange({ ...action, payload })}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Event edit modal
// ---------------------------------------------------------------------------

interface EventEditModalProps {
  visible: boolean;
  editingEvent: EventHandler | null;
  existingEvents: EventHandler[];
  onOk: (event: EventHandler) => void;
  onCancel: () => void;
}

function EventEditModal({
  visible,
  editingEvent,
  existingEvents,
  onOk,
  onCancel,
}: EventEditModalProps) {
  const [form] = Form.useForm();
  const [actions, setActions] = useState<EventAction[]>([]);
  const [whenExpr, setWhenExpr] = useState('');

  // 回填表单
  React.useEffect(() => {
    if (visible) {
      if (editingEvent) {
        form.setFieldsValue({ event: editingEvent.event });
        setActions([...editingEvent.actions]);
        setWhenExpr((editingEvent as any).when || '');
      } else {
        form.resetFields();
        setActions([]);
        setWhenExpr('');
      }
    }
  }, [visible, editingEvent, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      if (actions.length === 0) {
        form.setFields([{ name: 'actions', errors: ['请至少添加一个动作'] }]);
        return;
      }
      const event: EventHandler = {
        event: values.event,
        actions,
        ...(whenExpr.trim() ? { when: whenExpr.trim() } : {}),
      } as EventHandler;
      onOk(event);
    } catch {
      // form validation errors already shown
    }
  };

  const addAction = () => {
    setActions([...actions, { type: 'showToast', payload: { message: '' } }]);
  };

  const updateAction = (index: number, action: EventAction) => {
    const next = [...actions];
    next[index] = action;
    setActions(next);
  };

  const removeAction = (index: number) => {
    setActions(actions.filter((_, i) => i !== index));
  };

  const moveAction = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= actions.length) return;
    const next = [...actions];
    [next[index], next[target]] = [next[target], next[index]];
    setActions(next);
  };

  // 过滤掉已使用的事件名（编辑时保留自身）
  const usedEvents = useMemo(() => {
    const used = new Set(existingEvents.map((e) => e.event));
    if (editingEvent) used.delete(editingEvent.event);
    return used;
  }, [existingEvents, editingEvent]);

  const filteredEventOptions = useMemo(
    () => EVENT_OPTIONS.filter((opt) => !usedEvents.has(opt.value)),
    [usedEvents],
  );

  return (
    <Modal
      title={editingEvent ? '编辑事件' : '添加事件'}
      open={visible}
      onOk={handleOk}
      onCancel={onCancel}
      width={520}
      okText={editingEvent ? '保存' : '添加'}
      cancelText="取消"
      destroyOnClose
    >
      <Form form={form} layout="vertical" size="small">
        <Form.Item
          name="event"
          label="事件类型"
          rules={[{ required: true, message: '请选择事件类型' }]}
        >
          <Select
            placeholder="选择事件"
            options={filteredEventOptions}
          />
        </Form.Item>

        <Form.Item label="条件执行 (可选)">
          <Input
            placeholder="表达式，如 {{state.isLoggedIn}}"
            value={whenExpr}
            onChange={(e) => setWhenExpr(e.target.value)}
          />
          <Text type="secondary" style={{ fontSize: 11 }}>
            仅当表达式为真时执行此事件的动作链
          </Text>
        </Form.Item>

        <div style={{ marginBottom: 8 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 8,
            }}
          >
            <Text strong style={{ fontSize: 12 }}>
              动作链
            </Text>
            <Button
              type="dashed"
              size="small"
              icon={<PlusOutlined />}
              onClick={addAction}
            >
              添加动作
            </Button>
          </div>

          {actions.length === 0 ? (
            <Empty
              description="暂无动作，请添加"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              style={{ margin: '16px 0' }}
            />
          ) : (
            actions.map((action, index) => (
              <ActionItem
                key={index}
                index={index}
                total={actions.length}
                action={action}
                onChange={(a) => updateAction(index, a)}
                onRemove={() => removeAction(index)}
                onMoveUp={() => moveAction(index, -1)}
                onMoveDown={() => moveAction(index, 1)}
              />
            ))
          )}
        </div>
      </Form>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Event list item
// ---------------------------------------------------------------------------

function EventListItem({
  event,
  onEdit,
  onDelete,
}: {
  event: EventHandler;
  onEdit: () => void;
  onDelete: () => void;
}) {
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
      <div style={{ minWidth: 0, flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <ThunderboltOutlined style={{ fontSize: 12, color: 'var(--color-warning)' }} />
          <Text strong style={{ fontSize: 12 }} ellipsis>
            {event.event}
          </Text>
          <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>
            {event.actions.length} 个动作
          </Tag>
        </div>
        <div style={{ display: 'flex', gap: 2, marginTop: 2, flexWrap: 'wrap' }}>
          {event.actions.map((action, i) => (
            <Tag
              key={i}
              color={ACTION_TYPE_COLORS[action.type] || 'default'}
              style={{ fontSize: 9, lineHeight: '14px', padding: '0 3px', margin: 0 }}
            >
              {ACTION_TYPE_LABELS[action.type] || action.type}
            </Tag>
          ))}
        </div>
      </div>
      <Space size={0}>
        <Tooltip title="编辑">
          <Button type="text" size="small" icon={<EditOutlined />} onClick={onEdit} />
        </Tooltip>
        <Popconfirm title="确定删除此事件?" onConfirm={onDelete} okText="删除" cancelText="取消">
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      </Space>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const EventConfig: React.FC = () => {
  const selectedNodeId = useEditorStore((s) => s.selectedNodeId);
  const schema = useEditorStore((s) => s.schema);
  const updateNodeEvents = useEditorStore((s) => s.updateNodeEvents);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingEvent, setEditingEvent] = useState<EventHandler | null>(null);

  /** 查找选中的节点 */
  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return findNodeById(schema.children || [], selectedNodeId);
  }, [selectedNodeId, schema]);

  const events: EventHandler[] = useMemo(
    () => selectedNode?.events || [],
    [selectedNode],
  );

  const handleAdd = useCallback(() => {
    setEditingEvent(null);
    setModalVisible(true);
  }, []);

  const handleEdit = useCallback((event: EventHandler) => {
    setEditingEvent(event);
    setModalVisible(true);
  }, []);

  const handleDelete = useCallback(
    (eventName: string) => {
      if (!selectedNodeId) return;
      const next = events.filter((e) => e.event !== eventName);
      updateNodeEvents(selectedNodeId, next);
    },
    [selectedNodeId, events, updateNodeEvents],
  );

  const handleFormOk = useCallback(
    (event: EventHandler) => {
      if (!selectedNodeId) return;
      const existing = events.findIndex((e) => e.event === event.event);
      let next: EventHandler[];
      if (existing >= 0) {
        next = [...events];
        next[existing] = event;
      } else {
        next = [...events, event];
      }
      updateNodeEvents(selectedNodeId, next);
      setModalVisible(false);
    },
    [selectedNodeId, events, updateNodeEvents],
  );

  if (!selectedNode) return null;

  return (
    <div style={{ marginTop: 16 }}>
      {/* 标题行 */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 8,
        }}
      >
        <Space size={4}>
          <ThunderboltOutlined style={{ color: 'var(--color-warning)', fontSize: 13 }} />
          <Text strong style={{ fontSize: 13 }}>
            事件
          </Text>
          {events.length > 0 && (
            <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px', margin: 0 }}>
              {events.length}
            </Tag>
          )}
        </Space>
        <Tooltip title="添加事件">
          <Button
            type="text"
            size="small"
            icon={<PlusOutlined />}
            onClick={handleAdd}
          />
        </Tooltip>
      </div>

      {/* 事件列表 */}
      {events.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '12px 0', color: 'var(--color-border)' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            暂无事件配置
          </Text>
          <div style={{ marginTop: 8 }}>
            <Button size="small" type="dashed" icon={<PlusOutlined />} onClick={handleAdd}>
              添加事件
            </Button>
          </div>
        </div>
      ) : (
        events.map((event) => (
          <EventListItem
            key={event.event}
            event={event}
            onEdit={() => handleEdit(event)}
            onDelete={() => handleDelete(event.event)}
          />
        ))
      )}

      {/* 编辑弹窗 */}
      <EventEditModal
        visible={modalVisible}
        editingEvent={editingEvent}
        existingEvents={events}
        onOk={handleFormOk}
        onCancel={() => setModalVisible(false)}
      />
    </div>
  );
};
