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
  Collapse,
} from 'antd';
import { LinkOutlined, DisconnectOutlined, TranslationOutlined } from '@ant-design/icons';
import { useEditorStore } from '../store';
import { findMaterial } from '../materials';
import { findNodeById } from '../utils/tree';
import type { PropertyConfig, LowCodeNode, ApiDataSource, ValidationRules } from '@hospital/shared';
import ImageUpload from '@/components/ImageUpload';
import { EventConfig } from './EventConfig';
import { LinkageRulesPanel } from './LinkageRulesPanel';
import { EDITOR_COLORS, EDITOR_LAYOUT, EDITOR_SPACING } from '../constants';

const { Text } = Typography;
const { TextArea } = Input;

const FORM_ITEM_STYLE = { marginBottom: EDITOR_SPACING.formItem };
const COMPACT_FORM_ITEM_STYLE = { marginBottom: EDITOR_SPACING.formItemCompact };
const PANEL_SECTION_STYLE = {
  marginTop: 12,
  padding: '12px 0',
  borderTop: `1px solid ${EDITOR_COLORS.borderSubtle}`,
};
const SECTION_TITLE_STYLE = {
  fontSize: 12,
  marginBottom: 8,
  display: 'block',
};

// ---------------------------------------------------------------------------
// Expression helpers
// ---------------------------------------------------------------------------

/** i18n 标记正则：匹配 $t('key') */
const I18N_RE = /^\$t\('(.+)'\)$/;

/** 检查值是否为 i18n 标记 */
function isI18nMark(value: any): boolean {
  return typeof value === 'string' && I18N_RE.test(value);
}

/** 从 i18n 标记中提取 key */
function extractI18nKey(value: string): string {
  const match = value.match(I18N_RE);
  return match ? match[1] : '';
}

/** 构造 i18n 标记值 */
function buildI18nMark(key: string): string {
  return `$t('${key}')`;
}

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
  /** i18n 标记切换 */
  onI18nToggle?: () => void;
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
  onI18nToggle,
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
        style={FORM_ITEM_STYLE}
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
      style={FORM_ITEM_STYLE}
    >
      {/* eslint-disable-next-line @typescript-eslint/no-use-before-define */}
      <StaticValueInput config={config} value={staticValue} onChange={onStaticChange} onI18nToggle={onI18nToggle} />
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
  onI18nToggle,
}: {
  config: PropertyConfig;
  value: any;
  onChange: (val: any) => void;
  onI18nToggle?: () => void;
}) {
  const i18nActive = isI18nMark(value);

  switch (config.type) {
    case 'input':
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <Input
            value={i18nActive ? extractI18nKey(value) : value}
            onChange={(e) => {
              if (i18nActive) {
                onChange(buildI18nMark(e.target.value));
              } else {
                onChange(e.target.value);
              }
            }}
            placeholder={i18nActive ? 'i18n key' : config.placeholder}
            style={{ flex: 1 }}
          />
          {onI18nToggle && (
            <Tooltip title={i18nActive ? '取消 i18n 标记' : '设为 i18n 标记'}>
              <Button
                size="small"
                icon={<TranslationOutlined />}
                style={{
                  width: 28,
                  padding: 0,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: i18nActive ? '#1677ff' : undefined,
                  borderColor: i18nActive ? '#1677ff' : undefined,
                }}
                onClick={onI18nToggle}
              />
            </Tooltip>
          )}
        </div>
      );

    case 'textarea':
      return (
        <div>
          <TextArea
            value={i18nActive ? extractI18nKey(value) : value}
            onChange={(e) => {
              if (i18nActive) {
                onChange(buildI18nMark(e.target.value));
              } else {
                onChange(e.target.value);
              }
            }}
            placeholder={i18nActive ? 'i18n key' : config.placeholder}
            rows={3}
          />
          {onI18nToggle && (
            <div style={{ marginTop: 4 }}>
              <Tooltip title={i18nActive ? '取消 i18n 标记' : '设为 i18n 标记'}>
                <Button
                  size="small"
                  icon={<TranslationOutlined />}
                  style={{
                    color: i18nActive ? '#1677ff' : undefined,
                    borderColor: i18nActive ? '#1677ff' : undefined,
                  }}
                  onClick={onI18nToggle}
                >
                  {i18nActive ? 'i18n 已启用' : '标记为 i18n'}
                </Button>
              </Tooltip>
            </div>
          )}
        </div>
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
          onChange={(url: string | null | undefined) => onChange(url ?? '')}
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
// Form component detection + Validation Rules Panel
// ---------------------------------------------------------------------------

const FORM_COMPONENTS = new Set([
  'NutInput',
  'NutTextarea',
  'NutPicker',
  'NutSwitch',
  'NutCheckbox',
  'NutRadio',
  'NutDatePicker',
]);

function isFormComponent(componentName: string): boolean {
  return FORM_COMPONENTS.has(componentName);
}

function ValidationRulesPanel({
  rules,
  onChange,
}: {
  rules?: ValidationRules;
  onChange: (rules: ValidationRules | undefined) => void;
}) {
  const update = (key: keyof ValidationRules, value: any) => {
    const next = { ...rules, [key]: value };
    // 如果所有字段都是 undefined/null/空字符串，清除整个 rules
    const hasValue = Object.values(next).some(
      (v) => v !== undefined && v !== null && v !== '',
    );
    onChange(hasValue ? next : undefined);
  };

  return (
    <div style={PANEL_SECTION_STYLE}>
      <Collapse
        ghost
        size="small"
        items={[
          {
            key: 'validation',
            label: <Text type="secondary" style={{ fontSize: 12 }}>验证规则</Text>,
            children: (
              <Form layout="vertical" size="small">
                <Form.Item label="必填" style={COMPACT_FORM_ITEM_STYLE}>
                  <Switch
                    size="small"
                    checked={!!rules?.required}
                    onChange={(checked) => update('required', checked || undefined)}
                  />
                </Form.Item>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <Form.Item label="最小长度" style={COMPACT_FORM_ITEM_STYLE}>
                    <InputNumber
                      size="small"
                      min={0}
                      placeholder="不限"
                      value={rules?.minLength}
                      onChange={(val) => update('minLength', val || undefined)}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                  <Form.Item label="最大长度" style={COMPACT_FORM_ITEM_STYLE}>
                    <InputNumber
                      size="small"
                      min={0}
                      placeholder="不限"
                      value={rules?.maxLength}
                      onChange={(val) => update('maxLength', val || undefined)}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <Form.Item label="最小值" style={COMPACT_FORM_ITEM_STYLE}>
                    <InputNumber
                      size="small"
                      placeholder="不限"
                      value={rules?.min}
                      onChange={(val) => update('min', val || undefined)}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                  <Form.Item label="最大值" style={COMPACT_FORM_ITEM_STYLE}>
                    <InputNumber
                      size="small"
                      placeholder="不限"
                      value={rules?.max}
                      onChange={(val) => update('max', val || undefined)}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </div>
                <Form.Item label="正则表达式" style={COMPACT_FORM_ITEM_STYLE}>
                  <Input
                    size="small"
                    placeholder="如: ^[a-zA-Z]+$"
                    value={rules?.pattern || ''}
                    onChange={(e) => update('pattern', e.target.value || undefined)}
                  />
                </Form.Item>
                <Form.Item label="错误提示" style={{ marginBottom: 0 }}>
                  <Input
                    size="small"
                    placeholder="如: 请输入有效内容"
                    value={rules?.message || ''}
                    onChange={(e) => update('message', e.target.value || undefined)}
                  />
                </Form.Item>
              </Form>
            ),
          },
        ]}
      />
    </div>
  );
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
  const dataSources = useEditorStore((s) => s.dataSources);
  const updateTheme = useEditorStore((s) => s.updateTheme);

  /** 查找选中的节点 */
  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return findNodeById(schema.children || [], selectedNodeId);
  }, [selectedNodeId, schema]);

  /** 可用变量列表 */
  const variableGroups = useMemo(
    () => collectVariables(selectedNode, dataSources),
    [selectedNode, dataSources],
  );

  const theme = schema.theme;

  /** 主题配置面板 */
  const themePanel = (
    <Collapse
      ghost
      size="small"
      defaultActiveKey={[]}
      items={[
        {
          key: 'theme',
          label: <Text type="secondary" style={{ fontSize: 12 }}>主题</Text>,
          children: (
            <Form layout="vertical" size="small">
              <Form.Item label="主色调" style={COMPACT_FORM_ITEM_STYLE}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <ColorPicker
                    value={theme?.primaryColor || '#1677ff'}
                    onChange={(_, hex) => updateTheme({ ...theme, primaryColor: hex })}
                    size="small"
                  />
                  <Input
                    size="small"
                    value={theme?.primaryColor || ''}
                    placeholder="#1677ff"
                    onChange={(e) => updateTheme({ ...theme, primaryColor: e.target.value || undefined })}
                  />
                </div>
              </Form.Item>
              <Form.Item label="背景色" style={COMPACT_FORM_ITEM_STYLE}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <ColorPicker
                    value={theme?.backgroundColor || '#ffffff'}
                    onChange={(_, hex) => updateTheme({ ...theme, backgroundColor: hex })}
                    size="small"
                  />
                  <Input
                    size="small"
                    value={theme?.backgroundColor || ''}
                    placeholder="#ffffff"
                    onChange={(e) => updateTheme({ ...theme, backgroundColor: e.target.value || undefined })}
                  />
                </div>
              </Form.Item>
              <Form.Item label="字体族" style={COMPACT_FORM_ITEM_STYLE}>
                <Input
                  size="small"
                  value={theme?.fontFamily || ''}
                  placeholder="例: -apple-system, sans-serif"
                  onChange={(e) => updateTheme({ ...theme, fontFamily: e.target.value || undefined })}
                />
              </Form.Item>
              <Form.Item label="字体大小基准" style={{ marginBottom: 0 }}>
                <Input
                  size="small"
                  value={theme?.fontSize || ''}
                  placeholder="例: 14px"
                  onChange={(e) => updateTheme({ ...theme, fontSize: e.target.value || undefined })}
                />
              </Form.Item>
            </Form>
          ),
        },
      ]}
    />
  );

  if (!selectedNode) {
    return (
      <div
        style={{
          width: EDITOR_LAYOUT.rightPanelWidth,
          flexShrink: 0,
          borderLeft: `1px solid ${EDITOR_COLORS.border}`,
          padding: 16,
          overflow: 'auto',
          background: EDITOR_COLORS.panelBg,
        }}
      >
        {themePanel}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginTop: 24,
          }}
        >
          <Empty description="选择一个组件查看属性" />
        </div>
      </div>
    );
  }

  const material = findMaterial(selectedNode.componentName);

  return (
    <div
      style={{
        width: EDITOR_LAYOUT.rightPanelWidth,
        flexShrink: 0,
        borderLeft: `1px solid ${EDITOR_COLORS.border}`,
        overflow: 'auto',
        background: EDITOR_COLORS.panelBg,
      }}
    >
      {/* 主题配置面板 */}
      <div style={{ padding: EDITOR_SPACING.sectionPadding, borderBottom: `1px solid ${EDITOR_COLORS.borderSubtle}` }}>
        {themePanel}
      </div>
      <div
        style={{
          padding: EDITOR_SPACING.sectionPadding,
          borderBottom: `1px solid ${EDITOR_COLORS.borderSubtle}`,
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
          <Form.Item label="节点ID" style={FORM_ITEM_STYLE}>
            <Input value={selectedNode.id} disabled size="small" />
          </Form.Item>

          {/* 属性配置项（带数据绑定切换） */}
          {material?.configureSchema.map((config) => {
            const bindingExpr = selectedNode.dataBinding?.bindings?.[config.key];
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
                onI18nToggle={() => {
                  if (selectedNodeId) {
                    const currentVal = selectedNode.props[config.key] ?? config.defaultValue ?? '';
                    if (isI18nMark(currentVal)) {
                      // 取消 i18n 标记，恢复为 key
                      updateNodeProps(selectedNodeId, { [config.key]: extractI18nKey(currentVal) });
                    } else {
                      // 添加 i18n 标记
                      updateNodeProps(selectedNodeId, { [config.key]: buildI18nMark(String(currentVal || 'key')) });
                    }
                  }
                }}
              />
            );
          })}

          {/* 如果没有配置项 */}
          {(!material?.configureSchema ||
            material.configureSchema.length === 0) && (
            <Empty description="无可配置属性" />
          )}
        </Form>

        {/* 样式配置 */}
        <div style={PANEL_SECTION_STYLE}>
          <Text type="secondary" style={SECTION_TITLE_STYLE}>
            样式
          </Text>
          <Form layout="vertical" size="small">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <Form.Item label="宽度" style={COMPACT_FORM_ITEM_STYLE}>
                <Input
                  size="small"
                  placeholder="例: 100% 或 375px"
                  value={selectedNode.style?.width || ''}
                  onChange={(e) => {
                    if (selectedNodeId) {
                      updateNodeProps(selectedNodeId, {
                        style: { ...selectedNode.style, width: e.target.value || undefined },
                      });
                    }
                  }}
                />
              </Form.Item>
              <Form.Item label="高度" style={COMPACT_FORM_ITEM_STYLE}>
                <Input
                  size="small"
                  placeholder="例: auto 或 100px"
                  value={selectedNode.style?.height || ''}
                  onChange={(e) => {
                    if (selectedNodeId) {
                      updateNodeProps(selectedNodeId, {
                        style: { ...selectedNode.style, height: e.target.value || undefined },
                      });
                    }
                  }}
                />
              </Form.Item>
            </div>
            <Form.Item label="内边距" style={COMPACT_FORM_ITEM_STYLE}>
              <Input
                size="small"
                placeholder="例: 12px 或 8px 16px"
                value={selectedNode.style?.padding || ''}
                onChange={(e) => {
                  if (selectedNodeId) {
                    updateNodeProps(selectedNodeId, {
                      style: { ...selectedNode.style, padding: e.target.value || undefined },
                    });
                  }
                }}
              />
            </Form.Item>
            <Form.Item label="外边距" style={COMPACT_FORM_ITEM_STYLE}>
              <Input
                size="small"
                placeholder="例: 0 auto 或 16px 0"
                value={selectedNode.style?.margin || ''}
                onChange={(e) => {
                  if (selectedNodeId) {
                    updateNodeProps(selectedNodeId, {
                      style: { ...selectedNode.style, margin: e.target.value || undefined },
                    });
                  }
                }}
              />
            </Form.Item>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <Form.Item label="背景色" style={COMPACT_FORM_ITEM_STYLE}>
                <Input
                  size="small"
                  placeholder="#ffffff"
                  value={selectedNode.style?.backgroundColor || ''}
                  onChange={(e) => {
                    if (selectedNodeId) {
                      updateNodeProps(selectedNodeId, {
                        style: { ...selectedNode.style, backgroundColor: e.target.value || undefined },
                      });
                    }
                  }}
                />
              </Form.Item>
              <Form.Item label="圆角" style={COMPACT_FORM_ITEM_STYLE}>
                <Input
                  size="small"
                  placeholder="例: 8px"
                  value={selectedNode.style?.borderRadius || ''}
                  onChange={(e) => {
                    if (selectedNodeId) {
                      updateNodeProps(selectedNodeId, {
                        style: { ...selectedNode.style, borderRadius: e.target.value || undefined },
                      });
                    }
                  }}
                />
              </Form.Item>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
              <Form.Item label="边框" style={COMPACT_FORM_ITEM_STYLE}>
                <Input
                  size="small"
                  placeholder="例: 1px solid #eee"
                  value={selectedNode.style?.border || ''}
                  onChange={(e) => {
                    if (selectedNodeId) {
                      updateNodeProps(selectedNodeId, {
                        style: { ...selectedNode.style, border: e.target.value || undefined },
                      });
                    }
                  }}
                />
              </Form.Item>
              <Form.Item label="透明度" style={COMPACT_FORM_ITEM_STYLE}>
                <Input
                  size="small"
                  placeholder="0-1"
                  value={selectedNode.style?.opacity || ''}
                  onChange={(e) => {
                    if (selectedNodeId) {
                      updateNodeProps(selectedNodeId, {
                        style: { ...selectedNode.style, opacity: e.target.value || undefined },
                      });
                    }
                  }}
                />
              </Form.Item>
            </div>
          </Form>
        </div>

        {/* 条件渲染配置 */}
        <div style={PANEL_SECTION_STYLE}>
          <Text type="secondary" style={SECTION_TITLE_STYLE}>
            显示条件
          </Text>
          <Input
            size="small"
            placeholder="例: {{state.showHeader}} 或留空始终显示"
            value={selectedNode.visible || ''}
            onChange={(e) => {
              if (selectedNodeId) {
                updateNodeProps(selectedNodeId, { visible: e.target.value || undefined });
              }
            }}
          />
          <Text type="secondary" style={{ fontSize: 11, marginTop: 4, display: 'block' }}>
            表达式为 true 时显示组件，支持 state/api 变量
          </Text>
        </div>

        {/* 动画配置 */}
        <div style={PANEL_SECTION_STYLE}>
          <Text type="secondary" style={SECTION_TITLE_STYLE}>
            动画效果
          </Text>
          <Form layout="vertical" size="small">
            <Form.Item label="动画类型" style={COMPACT_FORM_ITEM_STYLE}>
              <Select
                size="small"
                placeholder="选择动画类型"
                allowClear
                value={selectedNode.animation?.type}
                onChange={(val) => {
                  if (selectedNodeId) {
                    updateNodeProps(selectedNodeId, {
                      animation: val
                        ? { type: val, duration: 300, delay: 0, easing: 'ease' }
                        : undefined,
                    });
                  }
                }}
                options={[
                  { label: '淡入', value: 'fadeIn' },
                  { label: '淡出', value: 'fadeOut' },
                  { label: '滑入', value: 'slideIn' },
                  { label: '缩放', value: 'scale' },
                ]}
              />
            </Form.Item>
            {selectedNode.animation?.type && (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <Form.Item label="持续时间(ms)" style={COMPACT_FORM_ITEM_STYLE}>
                    <InputNumber
                      size="small"
                      min={0}
                      step={50}
                      value={selectedNode.animation.duration ?? 300}
                      onChange={(val) => {
                        if (selectedNodeId) {
                          updateNodeProps(selectedNodeId, {
                            animation: { ...selectedNode.animation, duration: val ?? 300 },
                          });
                        }
                      }}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                  <Form.Item label="延迟(ms)" style={COMPACT_FORM_ITEM_STYLE}>
                    <InputNumber
                      size="small"
                      min={0}
                      step={50}
                      value={selectedNode.animation.delay ?? 0}
                      onChange={(val) => {
                        if (selectedNodeId) {
                          updateNodeProps(selectedNodeId, {
                            animation: { ...selectedNode.animation, delay: val ?? 0 },
                          });
                        }
                      }}
                      style={{ width: '100%' }}
                    />
                  </Form.Item>
                </div>
                <Form.Item label="缓动函数" style={{ marginBottom: 0 }}>
                  <Input
                    size="small"
                    placeholder="例: ease, ease-in-out, cubic-bezier(...)"
                    value={selectedNode.animation.easing || ''}
                    onChange={(e) => {
                      if (selectedNodeId) {
                        updateNodeProps(selectedNodeId, {
                          animation: { ...selectedNode.animation, easing: e.target.value || undefined },
                        });
                      }
                    }}
                  />
                </Form.Item>
              </>
            )}
          </Form>
        </div>

        {/* 验证规则配置 — 仅表单组件 */}
        {isFormComponent(selectedNode.componentName) && (
          <ValidationRulesPanel
            rules={selectedNode.validationRules}
            onChange={(rules) => {
              if (selectedNodeId) {
                updateNodeProps(selectedNodeId, { validationRules: rules || undefined });
              }
            }}
          />
        )}

        {/* 循环渲染配置 */}
        <div style={PANEL_SECTION_STYLE}>
          <Text type="secondary" style={SECTION_TITLE_STYLE}>
            循环渲染
          </Text>
          <Form layout="vertical" size="small">
            <Form.Item label="数据源" style={COMPACT_FORM_ITEM_STYLE}>
              <Input
                size="small"
                placeholder="例: {{api.users}} 或 {{state.items}}"
                value={selectedNode.loop?.dataSource || ''}
                onChange={(e) => {
                  if (selectedNodeId) {
                    updateNodeProps(selectedNodeId, {
                      loop: e.target.value
                        ? { dataSource: e.target.value, itemName: 'item', indexName: 'index' }
                        : undefined,
                    });
                  }
                }}
              />
            </Form.Item>
            {selectedNode.loop?.dataSource && (
              <>
                <Form.Item label="项变量名" style={COMPACT_FORM_ITEM_STYLE}>
                  <Input
                    size="small"
                    value={selectedNode.loop.itemName || 'item'}
                    onChange={(e) => {
                      if (selectedNodeId) {
                        updateNodeProps(selectedNodeId, {
                          loop: { ...selectedNode.loop, itemName: e.target.value },
                        });
                      }
                    }}
                  />
                </Form.Item>
                <Form.Item label="索引变量名" style={{ marginBottom: 0 }}>
                  <Input
                    size="small"
                    value={selectedNode.loop.indexName || 'index'}
                    onChange={(e) => {
                      if (selectedNodeId) {
                        updateNodeProps(selectedNodeId, {
                          loop: { ...selectedNode.loop, indexName: e.target.value },
                        });
                      }
                    }}
                  />
                </Form.Item>
              </>
            )}
          </Form>
        </div>

        {/* 事件配置 */}
        <EventConfig />

        {/* 联动规则配置 */}
        <div style={PANEL_SECTION_STYLE}>
          <LinkageRulesPanel />
        </div>
      </div>
    </div>
  );
};
