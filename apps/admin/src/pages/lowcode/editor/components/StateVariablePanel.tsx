import React, { useState } from 'react';
import { Button, Input, Select, Space, Card, Popconfirm, message } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import { useEditorStore } from '../store';
import type { StateVariable } from '../store';

const TYPE_OPTIONS = [
  { label: '字符串', value: 'string' },
  { label: '数字', value: 'number' },
  { label: '布尔', value: 'boolean' },
  { label: '数组', value: 'array' },
  { label: '对象', value: 'object' },
];

function parseValueByType(value: string, type: string): any {
  if (!value) {
    switch (type) {
      case 'string': return '';
      case 'number': return 0;
      case 'boolean': return false;
      case 'array': return [];
      case 'object': return {};
      default: return '';
    }
  }
  try {
    return JSON.parse(value);
  } catch {
    return value;
  }
}

export const StateVariablePanel: React.FC = () => {
  const { stateSchema, setStateSchema } = useEditorStore();
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [newKey, setNewKey] = useState('');
  const [newLabel, setNewLabel] = useState('');
  const [newType, setNewType] = useState('string');
  const [newValue, setNewValue] = useState('');

  const variables = Object.entries(stateSchema || {});

  const handleAdd = () => {
    if (!newKey.trim()) {
      message.warning('请输入变量名');
      return;
    }
    if (stateSchema?.[newKey]) {
      message.warning('变量名已存在');
      return;
    }

    const parsedValue = parseValueByType(newValue, newType);
    setStateSchema({
      ...stateSchema,
      [newKey]: {
        type: newType,
        defaultValue: parsedValue,
        label: newLabel || newKey,
      },
    });
    setNewKey('');
    setNewLabel('');
    setNewValue('');
    message.success('添加成功');
  };

  const handleDelete = (key: string) => {
    const { [key]: _, ...rest } = stateSchema || {};
    setStateSchema(rest);
    message.success('删除成功');
  };

  const handleUpdate = (key: string, updates: Partial<StateVariable>) => {
    setStateSchema({
      ...stateSchema,
      [key]: {
        ...stateSchema![key],
        ...updates,
      },
    });
  };

  return (
    <div style={{ padding: '4px 0' }}>
      {variables.map(([key, variable]) => (
        <Card key={key} size="small" style={{ marginBottom: 8, marginLeft: 8, marginRight: 8 }}>
          {editingKey === key ? (
            <Space direction="vertical" style={{ width: '100%' }}>
              <Input
                size="small"
                placeholder="显示名称"
                value={variable.label}
                onChange={(e) => handleUpdate(key, { label: e.target.value })}
              />
              <Select
                size="small"
                style={{ width: '100%' }}
                value={variable.type}
                options={TYPE_OPTIONS}
                onChange={(v) => handleUpdate(key, { type: v })}
              />
              <Input
                size="small"
                placeholder="默认值 (JSON)"
                value={JSON.stringify(variable.defaultValue)}
                onChange={(e) => handleUpdate(key, {
                  defaultValue: parseValueByType(e.target.value, variable.type)
                })}
              />
              <Button size="small" onClick={() => setEditingKey(null)}>
                完成
              </Button>
            </Space>
          ) : (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 500 }}>{variable.label || key}</div>
                <div style={{ fontSize: 12, color: 'var(--color-text-tertiary)' }}>
                  {key} · {variable.type}
                </div>
              </div>
              <Space size={4}>
                <EditOutlined
                  style={{ cursor: 'pointer', color: 'var(--color-text-tertiary)' }}
                  onClick={() => setEditingKey(key)}
                />
                <Popconfirm title="确定删除？" onConfirm={() => handleDelete(key)}>
                  <DeleteOutlined style={{ cursor: 'pointer', color: 'var(--color-error)' }} />
                </Popconfirm>
              </Space>
            </div>
          )}
        </Card>
      ))}

      <Card size="small" style={{ marginLeft: 8, marginRight: 8, marginTop: 12, borderStyle: 'dashed' }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input
            size="small"
            placeholder="变量名 (英文)"
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
          />
          <Input
            size="small"
            placeholder="显示名称"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
          />
          <Select
            size="small"
            style={{ width: '100%' }}
            value={newType}
            options={TYPE_OPTIONS}
            onChange={setNewType}
          />
          <Input
            size="small"
            placeholder="默认值 (JSON)"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
          />
          <Button
            type="primary"
            size="small"
            icon={<PlusOutlined />}
            onClick={handleAdd}
            block
          >
            添加变量
          </Button>
        </Space>
      </Card>
    </div>
  );
};
