import React, { useState } from 'react';
import { Button, Input, Select, Space, Card, Switch, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useEditorStore } from '../store';
import { findNodeById } from '../utils/tree';
import type { LinkageRule, LinkageCondition, LinkageAction } from '@hospital/shared';

const OPERATORS = [
  { label: '等于', value: 'equals' },
  { label: '不等于', value: 'notEquals' },
  { label: '包含', value: 'contains' },
  { label: '大于', value: 'greaterThan' },
  { label: '小于', value: 'lessThan' },
  { label: '为空', value: 'isEmpty' },
  { label: '不为空', value: 'isNotEmpty' },
];

const ACTION_TYPES = [
  { label: '设置值', value: 'setValue' },
  { label: '显示/隐藏', value: 'setVisible' },
  { label: '启用/禁用', value: 'setDisabled' },
  { label: '必填/非必填', value: 'setRequired' },
];

function getAllFieldNodes(nodes: any[]): { id: string; label: string }[] {
  const fields: { id: string; label: string }[] = [];
  const traverse = (items: any[]) => {
    for (const node of items) {
      if (node.componentName?.startsWith('Nut')) {
        fields.push({
          id: node.id,
          label: node.props?.placeholder || node.props?.text || node.componentName,
        });
      }
      if (node.children) traverse(node.children);
    }
  };
  traverse(nodes);
  return fields;
}

export const LinkageRulesPanel: React.FC = () => {
  const selectedNodeId = useEditorStore((s) => s.selectedNodeId);
  const schema = useEditorStore((s) => s.schema);
  const updateNodeLinkageRules = useEditorStore((s) => s.updateNodeLinkageRules);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  const selectedNode = findNodeById(schema?.children || [], selectedNodeId || '');
  const rules: LinkageRule[] = selectedNode?.linkageRules || [];
  const allFields = getAllFieldNodes(schema?.children || []);

  const handleAddRule = () => {
    const newRule: LinkageRule = {
      id: `rule_${Date.now()}`,
      name: `联动规则 ${rules.length + 1}`,
      conditions: [],
      actions: [],
      enabled: true,
    };
    updateNodeLinkageRules(selectedNodeId, [...rules, newRule]);
    setEditingRuleId(newRule.id);
  };

  const handleDeleteRule = (ruleId: string) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.filter((r) => r.id !== ruleId)
    );
  };

  const handleToggleRule = (ruleId: string, enabled: boolean) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.map((r) => (r.id === ruleId ? { ...r, enabled } : r))
    );
  };

  const handleUpdateCondition = (
    ruleId: string,
    condIndex: number,
    updates: Partial<LinkageCondition>
  ) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.map((r) => {
        if (r.id !== ruleId) return r;
        const newConditions = [...r.conditions];
        newConditions[condIndex] = { ...newConditions[condIndex], ...updates };
        return { ...r, conditions: newConditions };
      })
    );
  };

  const handleAddCondition = (ruleId: string) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.map((r) => {
        if (r.id !== ruleId) return r;
        return {
          ...r,
          conditions: [
            ...r.conditions,
            { sourceFieldId: '', operator: 'equals' as const, value: '' },
          ],
        };
      })
    );
  };

  const handleUpdateAction = (
    ruleId: string,
    actionIndex: number,
    updates: Partial<LinkageAction>
  ) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.map((r) => {
        if (r.id !== ruleId) return r;
        const newActions = [...r.actions];
        newActions[actionIndex] = { ...newActions[actionIndex], ...updates };
        return { ...r, actions: newActions };
      })
    );
  };

  const handleAddAction = (ruleId: string) => {
    updateNodeLinkageRules(
      selectedNodeId,
      rules.map((r) => {
        if (r.id !== ruleId) return r;
        return {
          ...r,
          actions: [
            ...r.actions,
            { type: 'setValue' as const, targetFieldId: '', value: '' },
          ],
        };
      })
    );
  };

  if (!selectedNodeId) {
    return (
      <div style={{ padding: 12, color: '#999', textAlign: 'center' }}>
        请先选择一个组件
      </div>
    );
  }

  return (
    <div style={{ padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontWeight: 600 }}>联动规则</span>
        <Button size="small" icon={<PlusOutlined />} onClick={handleAddRule}>
          添加规则
        </Button>
      </div>

      {rules.length === 0 && (
        <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>
          暂无联动规则
        </div>
      )}

      {rules.map((rule) => (
        <Card
          key={rule.id}
          size="small"
          style={{ marginBottom: 8 }}
          title={
            <Space>
              <Switch
                size="small"
                checked={rule.enabled}
                onChange={(v) => handleToggleRule(rule.id, v)}
              />
              <span>{rule.name}</span>
            </Space>
          }
          extra={
            <Popconfirm title="确定删除？" onConfirm={() => handleDeleteRule(rule.id)}>
              <DeleteOutlined style={{ cursor: 'pointer', color: '#ff4d4f' }} />
            </Popconfirm>
          }
        >
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>当</div>
            {rule.conditions.map((cond, i) => (
              <Space key={i} style={{ marginBottom: 4, display: 'flex' }}>
                <Select
                  size="small"
                  style={{ width: 120 }}
                  placeholder="字段"
                  value={cond.sourceFieldId || undefined}
                  options={allFields.map((f) => ({ label: f.label, value: f.id }))}
                  onChange={(v) => handleUpdateCondition(rule.id, i, { sourceFieldId: v })}
                />
                <Select
                  size="small"
                  style={{ width: 80 }}
                  value={cond.operator}
                  options={OPERATORS}
                  onChange={(v) => handleUpdateCondition(rule.id, i, { operator: v })}
                />
                {!['isEmpty', 'isNotEmpty'].includes(cond.operator) && (
                  <Input
                    size="small"
                    style={{ width: 80 }}
                    placeholder="值"
                    value={cond.value}
                    onChange={(e) => handleUpdateCondition(rule.id, i, { value: e.target.value })}
                  />
                )}
              </Space>
            ))}
            <Button size="small" type="link" onClick={() => handleAddCondition(rule.id)}>
              + 添加条件
            </Button>
          </div>

          <div>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>则</div>
            {rule.actions.map((action, i) => (
              <Space key={i} style={{ marginBottom: 4, display: 'flex' }}>
                <Select
                  size="small"
                  style={{ width: 100 }}
                  value={action.type}
                  options={ACTION_TYPES}
                  onChange={(v) => handleUpdateAction(rule.id, i, { type: v })}
                />
                <Select
                  size="small"
                  style={{ width: 120 }}
                  placeholder="目标字段"
                  value={action.targetFieldId || undefined}
                  options={allFields.map((f) => ({ label: f.label, value: f.id }))}
                  onChange={(v) => handleUpdateAction(rule.id, i, { targetFieldId: v })}
                />
                {action.type === 'setValue' && (
                  <Input
                    size="small"
                    style={{ width: 80 }}
                    placeholder="值"
                    value={action.value}
                    onChange={(e) => handleUpdateAction(rule.id, i, { value: e.target.value })}
                  />
                )}
              </Space>
            ))}
            <Button size="small" type="link" onClick={() => handleAddAction(rule.id)}>
              + 添加动作
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
};
