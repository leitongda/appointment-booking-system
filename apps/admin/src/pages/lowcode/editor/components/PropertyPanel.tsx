/** 属性面板 — 右侧配置区域，支持数据绑定 */

import React, { useMemo, useState, useCallback, useRef, useEffect } from 'react';
import {
  Form,
  Input,
  Select,
  Switch,
  ColorPicker,
  InputNumber,
  Empty,
  Typography,
  Tooltip,
  Dropdown,
  Button,
} from 'antd';
import { LinkOutlined, DisconnectOutlined } from '@ant-design/icons';
import { useEditorStore } from '../store';
import { findMaterial } from '../materials';
import type { PropertyConfig, LowCodeNode, ApiDataSource } from '@hospital/shared';
import ImageUpload from '@/components/ImageUpload';
import { EventConfig } from './EventConfig';

const { Text } = Typography;
const { TextArea } = Input;

// ---------------------------------------------------------------------------
// Expression helpers
// ---------------------------------------------------------------------------

/** 表达式正则：匹配 {{...}} */
const EXPRESSION_RE = /^\{\{(.+)\}\}$/;

/** 验证表达式语法是否合法 */
function isValidExpression(expr: string): boolean {
  if (!expr.trim()) return false;
  // 检查花括号匹配
  const openCount = (expr.match(/\{\{/g) || []).length;
  const closeCount = (expr.match(/\}\}/g) || []).length;
  if (openCount !== closeCount) return false;
  // 提取所有 {{...}} 内部内容，做基本语法检查
  const innerParts = expr.match(/\{\{(.+?)\}\}/g);
  if (!innerParts && expr.includes('{{')) return false;
  if (innerParts) {
    for (const part of innerParts) {
      const inner = part.slice(2, -2).trim();
      if (!inner) return false;
    }
  }
  return true;
}

/** 收集可用变量列表 */
function collectVariables(
  node: LowCodeNode | null,
  schemaDataSources?: ApiDataSource[],
): VariableGroup[] {
  const groups: VariableGroup[] = [];

  // pageParams
  groups.push({
    label: '页面参数',
    prefix: 'pageParams',
    items: [
      { key: 'pageParams.id', desc: '页面ID' },
      { key: 'pageParams.name', desc: '页面名称' },
    ],
  });

  // api 数据源
  if (schemaDataSources && schemaDataSources.length > 0) {
    const apiItems = schemaDataSources.map((ds) => ({
      key: `api.${ds.id}.data`,
      desc: `${ds.name || ds.id} 响应数据`,
    }));
    groups.push({ label: 'API 数据源', prefix: 'api', items: apiItems });
  }

  // formData（表单域）
  groups.push({
    label: '表单数据',
    prefix: 'formData',
    items: [
      { key: 'formData.fieldName', desc: '表单字段值' },
    ],
  });

  // 自定义变量
  groups.push({
    label: '自定义变量',
    prefix: 'state',
    items: [
      { key: 'state.title', desc: '自定义状态变量' },
      { key: 'state.count', desc: '计数器' },
    ],
  });

  return groups;
}

interface VariableItem {
  key: string;
  desc: string;
}

interface VariableGroup {
  label: string;
  prefix: string;
  items: VariableItem[];
}

// ---------------------------------------------------------------------------
// Variable Picker Dropdown
// ---------------------------------------------------------------------------

function VariablePicker({
  groups,
  onSelect,
  children,
}: {
  groups: VariableGroup[];
  onSelect: (varKey: string) => void;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  const items = useMemo(() => {
    return groups.map((group) => ({
      key: group.prefix,
      label: (
        <Text strong style={{ fontSize: 12, color: '#8c8c8c' }}>
          {group.label}
        </Text>
      ),
      type: 'group' as const,
      children: group.items.map((item) => ({
        key: item.key,
        label: (
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
            <Text code style={{ fontSize: 11 }}>
              {item.key}
            </Text>
            <Text type="secondary" style={{ fontSize: 10 }}>
              {item.desc}
            </Text>
          </div>
        ),
      })),
    }));
  }, [groups]);

  return (
    <Dropdown
      menu={{
        items,
        onClick: ({ key }) => {
          onSelect(key);
          setOpen(false);
        },
        style: { maxHeight: 280, overflow: 'auto', minWidth: 240 },
      }}
      trigger={['click']}
      open={open}
      onOpenChange={setOpen}
    >
      {children}
    </Dropdown>
  );
}

// ---------------------------------------------------------------------------
// Autocomplete suggestions (inline)
// ---------------------------------------------------------------------------

function AutocompleteSuggestions({
  value,
  groups,
  onSelect,
  visible,
}: {
  value: string;
  groups: VariableGroup[];
  onSelect: (varKey: string) => void;
  visible: boolean;
}) {
  const suggestions = useMemo(() => {
    if (!value.trim()) return [];
    // 提取光标附近的 token（最后一个 {{ 之后的内容）
    const lastOpen = value.lastIndexOf('{{');
    if (lastOpen < 0) return [];
    const partial = value.slice(lastOpen + 2).trim().toLowerCase();
    if (!partial) return [];

    const allItems = groups.flatMap((g) => g.items);
    return allItems
      .filter(
        (item) =>
          item.key.toLowerCase().includes(partial) ||
          item.desc.toLowerCase().includes(partial),
      )
      .slice(0, 8);
  }, [value, groups]);

  if (!visible || suggestions.length === 0) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: '100%',
        left: 0,
        right: 0,
        zIndex: 1050,
        background: '#fff',
        border: '1px solid #d9d9d9',
        borderRadius: 6,
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
        maxHeight: 180,
        overflow: 'auto',
        marginTop: 2,
      }}
    >
      {suggestions.map((item) => (
        <div
          key={item.key}
          style={{
            padding: '4px 8px',
            cursor: 'pointer',
            fontSize: 11,
            display: 'flex',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f5f5f5',
          }}
          onMouseDown={(e) => {
            e.preventDefault();
            onSelect(item.key);
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLDivElement).style.background = '#f5f5f5';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLDivElement).style.background = '';
          }}
        >
          <Text code style={{ fontSize: 11 }}>
            {item.key}
          </Text>
          <Text type="secondary" style={{ fontSize: 10 }}>
            {item.desc}
          </Text>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expression Input (with syntax hint, variable picker, autocomplete)
// ---------------------------------------------------------------------------

function ExpressionInput({
  value,
  onChange,
  onBlur,
  groups,
  invalid,
}: {
  value: string;
  onChange: (val: string) => void;
  onBlur: () => void;
  groups: VariableGroup[];
  invalid: boolean;
}) {
  const [focused, setFocused] = useState(false);
  const inputRef = useRef<any>(null);

  const handleVariableSelect = useCallback(
    (varKey: string) => {
      // 插入 {{varKey}} 到当前值
      const newValue = value ? `${value} {{${varKey}}}` : `{{${varKey}}}`;
      onChange(newValue);
    },
    [value, onChange],
  );

  return (
    <div style={{ position: 'relative' }}>
      <div style={{ display: 'flex', gap: 4, alignItems: 'flex-start' }}>
        <Input
          ref={inputRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onBlur={() => {
            setFocused(false);
            onBlur();
          }}
          onFocus={() => setFocused(true)}
          placeholder="{{api.dataSource.data}}"
          size="small"
          style={{
            flex: 1,
            fontFamily: 'monospace',
            fontSize: 11,
            borderColor: invalid ? '#ff4d4f' : undefined,
          }}
          status={invalid ? 'error' : undefined}
        />
        <VariablePicker groups={groups} onSelect={handleVariableSelect}>
          <Tooltip title="插入变量">
            <Button
              size="small"
              icon={<LinkOutlined />}
              style={{
                width: 28,
                padding: 0,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            />
          </Tooltip>
        </VariablePicker>
      </div>

      {/* 语法提示 */}
      <Text
        type="secondary"
        style={{ fontSize: 10, lineHeight: '16px', marginTop: 2, display: 'block' }}
      >
        使用 {'{{表达式}}'} 语法，如 {'{{api.users.data}}'}
      </Text>

      {/* 自动补全 */}
      <AutocompleteSuggestions
        value={value}
        groups={groups}
        onSelect={(varKey) => {
          // 替换最后一个 {{ 后的内容
          const lastOpen = value.lastIndexOf('{{');
          if (lastOpen >= 0) {
            onChange(value.slice(0, lastOpen) + `{{${varKey}}}`);
          } else {
            onChange(`{{${varKey}}}`);
          }
        }}
        visible={focused}
      />

      {/* 验证错误提示 */}
      {invalid && (
        <Text type="danger" style={{ fontSize: 10, display: 'block', marginTop: 2 }}>
          表达式语法不正确
        </Text>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Binding-aware Property Form Item
// ---------------------------------------------------------------------------

interface BindingAwareFormItemProps {
  config: PropertyConfig;
  /** 静态值 */
  staticValue: any;
  /** 当前绑定表达式（undefined 表示无绑定） */
  bindingExpression: string | undefined;
  /** 切换到静态模式 */
  onSwitchToStatic: () => void;
  /** 切换到绑定模式 */
  onSwitchToBinding: () => void;
  /** 更新静态值 */
  onStaticChange: (val: any) => void;
  /** 更新绑定表达式 */
  onBindingChange: (expr: string) => void;
  /** 可用变量组 */
  variableGroups: VariableGroup[];
}

function BindingAwareFormItem({
  config,
  staticValue,
  bindingExpression,
  onSwitchToStatic,
  onSwitchToBinding,
  onStaticChange,
  onBindingChange,
  variableGroups,
}: BindingAwareFormItemProps) {
  const isBinding = bindingExpression !== undefined;
  const [exprInvalid, setExprInvalid] = useState(false);

  // 切换时重置验证状态
  useEffect(() => {
    setExprInvalid(false);
  }, [isBinding]);

  const handleExprBlur = useCallback(() => {
    if (bindingExpression !== undefined) {
      setExprInvalid(!isValidExpression(bindingExpression));
    }
  }, [bindingExpression]);

  const toggleButton = (
    <Tooltip title={isBinding ? '切换到静态值' : '切换到表达式绑定'}>
      <span
        onClick={(e) => {
          e.stopPropagation();
          if (isBinding) {
            onSwitchToStatic();
          } else {
            onSwitchToBinding();
          }
        }}
        style={{
          cursor: 'pointer',
          fontSize: 12,
          color: isBinding ? '#1677ff' : '#bfbfbf',
          display: 'inline-flex',
          alignItems: 'center',
          padding: '0 2px',
          marginLeft: 4,
          transition: 'color 0.2s',
        }}
      >
        {isBinding ? <LinkOutlined /> : <DisconnectOutlined />}
      </span>
    </Tooltip>
  );

  if (isBinding) {
    // 表达式绑定模式
    return (
      <Form.Item
        label={
          <span>
            {config.label}
            {toggleButton}
          </span>
        }
        key={config.key}
        validateStatus={exprInvalid ? 'error' : undefined}
      >
        <ExpressionInput
          value={bindingExpression ?? ''}
          onChange={onBindingChange}
          onBlur={handleExprBlur}
          groups={variableGroups}
          invalid={exprInvalid}
        />
      </Form.Item>
    );
  }

  // 静态值模式 — 复用原有表单控件
  return (
    <Form.Item
      label={
        <span>
          {config.label}
          {toggleButton}
        </span>
      }
      key={config.key}
    >
      <StaticValueInput config={config} value={staticValue} onChange={onStaticChange} />
    </Form.Item>
  );
}

// ---------------------------------------------------------------------------
// Static value input (extracted from original PropertyFormItem)
// ---------------------------------------------------------------------------

function StaticValueInput({
  config,
  value,
  onChange,
}: {
  config: PropertyConfig;
  value: any;
  onChange: (val: any) => void;
}) {
  switch (config.type) {
    case 'input':
      return (
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={config.placeholder}
        />
      );

    case 'textarea':
      return (
        <TextArea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={config.placeholder}
          rows={3}
        />
      );

    case 'number':
      return (
        <InputNumber
          value={value}
          onChange={(val) => onChange(val)}
          style={{ width: '100%' }}
        />
      );

    case 'select':
      return (
        <Select
          value={value}
          onChange={(val) => onChange(val)}
          options={config.options}
        />
      );

    case 'color':
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <ColorPicker
            value={value}
            onChange={(_, hex) => onChange(hex)}
            size="small"
          />
          <Input
            value={value}
            onChange={(e) => onChange(e.target.value)}
            size="small"
            style={{ flex: 1 }}
          />
        </div>
      );

    case 'switch':
      return (
        <Switch
          checked={value}
          onChange={(checked) => onChange(checked)}
        />
      );

    case 'image':
      return (
        <ImageUpload
          value={value}
          onChange={(url) => onChange(url ?? '')}
          width={100}
          height={100}
          allowUrlTransfer
          showCrop={false}
          folder="lowcode"
        />
      );

    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// PropertyPanel (main)
// ---------------------------------------------------------------------------

/** 属性面板 */
export const PropertyPanel: React.FC = () => {
  const selectedNodeId = useEditorStore((s) => s.selectedNodeId);
  const schema = useEditorStore((s) => s.schema);
  const updateNodeProps = useEditorStore((s) => s.updateNodeProps);
  const updateNodeDataBinding = useEditorStore((s) => s.updateNodeDataBinding);
  const removeNode = useEditorStore((s) => s.removeNode);

  /** 查找选中的节点 */
  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;

    function find(nodes: any[]): any {
      for (const node of nodes) {
        if (node.id === selectedNodeId) return node;
        if (node.children) {
          const found = find(node.children);
          if (found) return found;
        }
      }
      return null;
    }

    return find([schema]);
  }, [selectedNodeId, schema]);

  /** 可用变量列表 */
  const variableGroups = useMemo(
    () => collectVariables(selectedNode, schema.dataSources),
    [selectedNode, schema.dataSources],
  );

  if (!selectedNode) {
    return (
      <div
        style={{
          width: 280,
          borderLeft: '1px solid #f0f0f0',
          padding: 16,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Empty description="选择一个组件查看属性" />
      </div>
    );
  }

  const material = findMaterial(selectedNode.componentName);

  return (
    <div
      style={{
        width: 280,
        borderLeft: '1px solid #f0f0f0',
        overflow: 'auto',
      }}
    >
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Text strong>{material?.title || selectedNode.componentName}</Text>
        <a
          style={{ fontSize: 12, color: '#ff4d4f' }}
          onClick={() => removeNode(selectedNode.id)}
        >
          删除
        </a>
      </div>
      <div style={{ padding: 16 }}>
        <Form layout="vertical" size="small">
          {/* ID 显示 */}
          <Form.Item label="节点ID">
            <Input value={selectedNode.id} disabled size="small" />
          </Form.Item>

          {/* 属性配置项（带数据绑定切换） */}
          {material?.configureSchema.map((config) => {
            const bindingExpr = selectedNode.dataBinding?.bindings?.[config.key];
            const isBound = bindingExpr !== undefined;

            return (
              <BindingAwareFormItem
                key={config.key}
                config={config}
                staticValue={selectedNode.props[config.key] ?? config.defaultValue}
                bindingExpression={bindingExpr}
                onSwitchToStatic={() => {
                  // 切回静态：移除绑定，恢复到 props 中的值（或 defaultValue）
                  if (selectedNodeId) {
                    updateNodeDataBinding(selectedNodeId, config.key, null);
                  }
                }}
                onSwitchToBinding={() => {
                  // 切到绑定：用空表达式初始化
                  if (selectedNodeId) {
                    updateNodeDataBinding(selectedNodeId, config.key, '{{}}');
                  }
                }}
                onStaticChange={(val) => {
                  if (selectedNodeId) {
                    updateNodeProps(selectedNodeId, { [config.key]: val });
                  }
                }}
                onBindingChange={(expr) => {
                  if (selectedNodeId) {
                    updateNodeDataBinding(selectedNodeId, config.key, expr || '{{}}');
                  }
                }}
                variableGroups={variableGroups}
              />
            );
          })}

          {/* 如果没有配置项 */}
          {(!material?.configureSchema ||
            material.configureSchema.length === 0) && (
            <Empty description="无可配置属性" />
          )}
        </Form>

        {/* 事件配置 */}
        <EventConfig />
      </div>
    </div>
  );
};
