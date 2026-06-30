import { Card, Form, Input, Select, InputNumber, Button, Space, Divider, Tooltip, Collapse, Modal, Tag } from 'antd';
import { DeleteOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { memo, useEffect, useRef, useState } from 'react';
import type { Node } from '@xyflow/react';
import type { ListenerConfig, ListenerEvent, ListenerActionType } from '@hospital/shared';

const { TextArea } = Input;

const APPROVAL_MODE_OPTIONS = [
  { label: '或签（一人通过即可）', value: 'or' },
  { label: '会签（所有人通过）', value: 'and' },
  { label: '顺签（按顺序审批）', value: 'sequential' },
];

const ASSIGNEE_TYPE_OPTIONS = [
  { label: '指定角色', value: 'role' },
  { label: '指定人员', value: 'user' },
  { label: '部门负责人', value: 'department' },
  { label: '表单字段指定', value: 'dynamic' },
];

const OPERATOR_OPTIONS = [
  { label: '等于', value: 'eq' },
  { label: '不等于', value: 'neq' },
  { label: '大于', value: 'gt' },
  { label: '大于等于', value: 'gte' },
  { label: '小于', value: 'lt' },
  { label: '小于等于', value: 'lte' },
  { label: '包含', value: 'contains' },
  { label: '属于', value: 'in' },
  { label: '不属于', value: 'not_in' },
  { label: '存在', value: 'exists' },
];

const EXECUTION_EVENTS: { value: ListenerEvent; label: string }[] = [
  { value: 'start', label: '节点开始' },
  { value: 'end', label: '节点完成' },
  { value: 'take', label: '边遍历' },
];

const TASK_EVENTS: { value: ListenerEvent; label: string }[] = [
  { value: 'create', label: '任务创建' },
  { value: 'assignment', label: '任务分配' },
  { value: 'complete', label: '任务完成' },
  { value: 'timeout', label: '任务超时' },
];

const ACTION_TYPES: { value: ListenerActionType; label: string }[] = [
  { value: 'webhook', label: 'Webhook' },
  { value: 'notification', label: '站内通知' },
  { value: 'sms', label: '短信通知' },
  { value: 'callback', label: '回调函数' },
];

interface PropertyPanelProps {
  selectedNode: Node | null;
  onUpdate: (nodeId: string, data: Record<string, any>) => void;
  onDelete: (nodeId: string) => void;
}

/** 将扁平 conditions 数组转换为嵌套结构（按 targetNodeKey -> groupId 分组） */
function conditionsToNested(conditions: any[]): any[] {
  if (!conditions || conditions.length === 0) return [];

  const targetMap = new Map<string, Map<string, any[]>>();
  for (const c of conditions) {
    const target = c.targetNodeKey || '';
    const gid = c.groupId || 'default';
    if (!targetMap.has(target)) targetMap.set(target, new Map());
    const groupMap = targetMap.get(target)!;
    if (!groupMap.has(gid)) groupMap.set(gid, []);
    groupMap.get(gid)!.push({
      fieldName: c.fieldName,
      operator: c.operator,
      value: c.value,
    });
  }

  const result: any[] = [];
  for (const [target, groupMap] of targetMap) {
    const groups: any[] = [];
    for (const [, conds] of groupMap) {
      groups.push({ conditions: conds });
    }
    result.push({ targetNodeKey: target, groups });
  }
  return result;
}

/** 将嵌套结构展平为扁平 conditions 数组 */
function nestedToConditions(targets: any[]): any[] {
  if (!targets) return [];
  const result: any[] = [];
  for (const target of targets) {
    const gidBase = `${target.targetNodeKey}_g`;
    for (let gi = 0; gi < (target.groups?.length || 0); gi++) {
      const group = target.groups[gi];
      const groupId = (target.groups?.length || 0) > 1 ? `${gidBase}${gi}` : null;
      for (const cond of group?.conditions || []) {
        result.push({
          targetNodeKey: target.targetNodeKey,
          fieldName: cond.fieldName,
          operator: cond.operator,
          value: cond.value,
          priority: 0,
          groupId,
        });
      }
    }
  }
  return result;
}

let _condIdSeq = 0;
const newCondId = () => `__cond_${++_condIdSeq}`;

const PropertyPanel: React.FC<PropertyPanelProps> = memo(({ selectedNode, onUpdate, onDelete }) => {
  const [form] = Form.useForm();
  const condIdMapRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    if (selectedNode) {
      form.resetFields();
      const d = selectedNode.data as any;
      const nested = conditionsToNested(d.conditions || []);
      form.setFieldsValue({
        label: d.label,
        approvalMode: d.approvalMode,
        assigneeType: d.assigneeType,
        timeoutHours: d.timeoutHours,
        timeoutAction: d.timeoutAction,
        timeoutTransferUserId: d.assigneeConfig?.timeout_transfer_user_id,
        timeoutTransferUserName: d.assigneeConfig?.timeout_transfer_user_name,
        conditionGroups: nested,
      });
      condIdMapRef.current = new Map();
    }
  }, [selectedNode, form]);

  if (!selectedNode) {
    return (
      <Card size="small" title="属性" style={{ width: 280 }}>
        <div style={{ color: '#999', textAlign: 'center', padding: 20 }}>点击节点查看属性</div>
      </Card>
    );
  }

  const d = selectedNode.data as any;
  const nodeType = d.nodeType;

  const handleValuesChange = (_: any, allValues: any) => {
    const nextData = { ...d, ...allValues };
    if (nodeType === 'approval') {
      const assigneeConfig = { ...(d.assigneeConfig || {}) };
      if (allValues.timeoutAction === 'transfer') {
        assigneeConfig.timeout_transfer_user_id = allValues.timeoutTransferUserId;
        assigneeConfig.timeout_transfer_user_name = allValues.timeoutTransferUserName;
      } else {
        delete assigneeConfig.timeout_transfer_user_id;
        delete assigneeConfig.timeout_transfer_user_name;
      }
      nextData.assigneeConfig = assigneeConfig;
    }
    if (nodeType === 'condition' && allValues.conditionGroups) {
      nextData.conditions = nestedToConditions(allValues.conditionGroups);
    }
    onUpdate(selectedNode.id, nextData);
  };

  const getCondId = (path: string): string => {
    if (!condIdMapRef.current.has(path)) condIdMapRef.current.set(path, newCondId());
    return condIdMapRef.current.get(path)!;
  };

  // ──── 监听器状态与处理 ────
  const listeners: ListenerConfig[] = (d.listeners as ListenerConfig[]) || [];
  const [listenerModalOpen, setListenerModalOpen] = useState(false);
  const [editingListener, setEditingListener] = useState<ListenerConfig | null>(null);
  const [listenerForm] = Form.useForm();

  const showListenerEvents = nodeType === 'approval' ? [...EXECUTION_EVENTS, ...TASK_EVENTS] : EXECUTION_EVENTS;

  const handleAddListener = () => {
    setEditingListener(null);
    listenerForm.resetFields();
    listenerForm.setFieldsValue({ event: 'start', actionType: 'webhook' });
    setListenerModalOpen(true);
  };

  const handleEditListener = (listener: ListenerConfig) => {
    setEditingListener(listener);
    listenerForm.setFieldsValue({
      label: listener.label,
      event: listener.event,
      actionType: listener.actionType,
      webhookUrl: (listener.actionConfig as any)?.url || '',
      webhookBodyTemplate: (listener.actionConfig as any)?.bodyTemplate || '',
      callbackName: (listener.actionConfig as any)?.callbackName || '',
    });
    setListenerModalOpen(true);
  };

  const handleDeleteListener = (listenerId: string) => {
    const newListeners = listeners.filter((l) => l.id !== listenerId);
    onUpdate(selectedNode.id, { ...d, listeners: newListeners });
  };

  const handleListenerModalOk = () => {
    listenerForm.validateFields().then((values) => {
      let actionConfig: ListenerConfig['actionConfig'];
      if (values.actionType === 'webhook') {
        actionConfig = { url: values.webhookUrl, bodyTemplate: values.webhookBodyTemplate };
      } else if (values.actionType === 'callback') {
        actionConfig = { callbackName: values.callbackName };
      } else {
        actionConfig = { targetType: "user" as const, targetIds: [] };
      }
      const newListener: ListenerConfig = {
        id: editingListener?.id || `listener_${Date.now()}`,
        event: values.event,
        actionType: values.actionType,
        actionConfig,
        label: values.label || undefined,
      };
      const newListeners = editingListener
        ? listeners.map((l) => (l.id === editingListener.id ? newListener : l))
        : [...listeners, newListener];
      onUpdate(selectedNode.id, { ...d, listeners: newListeners });
      setListenerModalOpen(false);
    });
  };

  const getListenerSummary = (l: ListenerConfig): string => {
    const eventLabel = showListenerEvents.find((e) => e.value === l.event)?.label || l.event;
    const actionLabel = ACTION_TYPES.find((a) => a.value === l.actionType)?.label || l.actionType;
    return `${eventLabel} → ${actionLabel}`;
  };

  return (
    <Card
      size="small"
      title={`属性 — ${d.label || nodeType}`}
      style={{ width: 300 }}
      extra={
        !['start', 'end'].includes(nodeType) && (
          <Button type="text" danger size="small" icon={<DeleteOutlined />} onClick={() => onDelete(selectedNode.id)} />
        )
      }
    >
      <Form form={form} layout="vertical" size="small" onValuesChange={handleValuesChange}>
        <Form.Item label="节点名称" name="label">
          <Input />
        </Form.Item>

        {nodeType === 'approval' && (
          <>
            <Divider style={{ margin: '8px 0' }}>审批配置</Divider>
            <Form.Item label="审批方式" name="approvalMode">
              <Select options={APPROVAL_MODE_OPTIONS} placeholder="选择审批方式" />
            </Form.Item>
            <Form.Item label="审批人来源" name="assigneeType">
              <Select options={ASSIGNEE_TYPE_OPTIONS} placeholder="选择审批人来源" />
            </Form.Item>
            <Form.Item label="超时时间(小时)" name="timeoutHours">
              <InputNumber min={1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="超时动作" name="timeoutAction">
              <Select options={[
                { label: '提醒', value: 'remind' },
                { label: '自动通过', value: 'auto_approve' },
                { label: '自动拒绝', value: 'auto_reject' },
                { label: '转交', value: 'transfer' },
              ]} allowClear />
            </Form.Item>
            <Form.Item noStyle shouldUpdate={(prev, cur) => prev.timeoutAction !== cur.timeoutAction}>
              {({ getFieldValue }) => (
                getFieldValue('timeoutAction') === 'transfer' ? (
                  <>
                    <Form.Item
                      label="超时转交用户 ID"
                      name="timeoutTransferUserId"
                      rules={[{ required: true, message: '请填写超时转交用户 ID' }]}
                    >
                      <Input placeholder="目标用户 ID" />
                    </Form.Item>
                    <Form.Item label="超时转交用户姓名" name="timeoutTransferUserName">
                      <Input placeholder="目标用户姓名（选填）" />
                    </Form.Item>
                  </>
                ) : null
              )}
            </Form.Item>
          </>
        )}

        {nodeType === 'condition' && (
          <>
            <Divider style={{ margin: '8px 0' }}>条件规则</Divider>
            <div style={{ fontSize: 11, color: '#999', marginBottom: 8 }}>
              每个目标节点内的条件组之间为 OR 关系，组内条件为 AND 关系。
            </div>
            <Form.List name="conditionGroups">
              {(targetFields, { add: addTarget, remove: removeTarget }) => (
                <>
                  {targetFields.map(({ key: targetKey, name: targetName }) => (
                    <Card
                      key={targetKey}
                      size="small"
                      title={
                        <Space>
                          <span style={{ fontWeight: 500 }}>目标节点</span>
                          <Form.Item
                            name={[targetName, 'targetNodeKey']}
                            noStyle
                            rules={[{ required: true, message: '必填' }]}
                          >
                            <Input size="small" placeholder="节点 key" style={{ width: 120 }} />
                          </Form.Item>
                        </Space>
                      }
                      extra={
                        <Button
                          type="text"
                          danger
                          size="small"
                          icon={<DeleteOutlined />}
                          onClick={() => removeTarget(targetName)}
                        />
                      }
                      style={{ marginBottom: 8, border: '1px solid #e8e8e8' }}
                    >
                      <Form.List name={[targetName, 'groups']}>
                        {(groupFields, { add: addGroup, remove: removeGroup }) => (
                          <>
                            {groupFields.map(({ key: groupKey, name: groupName }, groupIdx) => (
                              <div key={groupKey}>
                                {groupIdx > 0 && (
                                  <Divider plain style={{ margin: '4px 0', fontSize: 11, color: '#1677ff' }}>
                                    OR
                                  </Divider>
                                )}
                                <Card
                                  size="small"
                                  style={{ marginBottom: 4, background: '#fafafa', border: '1px dashed #d9d9d9' }}
                                >
                                  <Form.List name={[groupName, 'conditions']}>
                                    {(condFields, { add: addCond, remove: removeCond }) => (
                                      <>
                                        {condFields.map(({ key: condKey, name: condName }) => (
                                          <Space
                                            key={condKey}
                                            align="start"
                                            style={{ display: 'flex', marginBottom: 4 }}
                                            size={4}
                                          >
                                            <Form.Item
                                              name={[condName, 'fieldName']}
                                              noStyle
                                              rules={[{ required: true }]}
                                            >
                                              <Input size="small" placeholder="字段" style={{ width: 80 }} />
                                            </Form.Item>
                                            <Form.Item
                                              name={[condName, 'operator']}
                                              noStyle
                                              rules={[{ required: true }]}
                                            >
                                              <Select
                                                size="small"
                                                options={OPERATOR_OPTIONS}
                                                style={{ width: 90 }}
                                                placeholder="操作符"
                                              />
                                            </Form.Item>
                                            <Form.Item
                                              name={[condName, 'value']}
                                              noStyle
                                              rules={[{ required: true }]}
                                            >
                                              <Input size="small" placeholder="值" style={{ width: 80 }} />
                                            </Form.Item>
                                            <Button
                                              type="text"
                                              danger
                                              size="small"
                                              icon={<DeleteOutlined />}
                                              onClick={() => removeCond(condName)}
                                            />
                                          </Space>
                                        ))}
                                        <Button
                                          type="dashed"
                                          size="small"
                                          block
                                          icon={<PlusOutlined />}
                                          onClick={() => addCond({ fieldName: '', operator: 'eq', value: '' })}
                                        >
                                          添加条件
                                        </Button>
                                      </>
                                    )}
                                  </Form.List>
                                </Card>
                              </div>
                            ))}
                            <Tooltip title="不同条件组之间为 OR 关系（满足任一组即可）">
                              <Button
                                type="dashed"
                                size="small"
                                block
                                icon={<PlusOutlined />}
                                style={{ marginTop: 4 }}
                                onClick={() => addGroup({ conditions: [{ fieldName: '', operator: 'eq', value: '' }] })}
                              >
                                添加条件组 (OR)
                              </Button>
                            </Tooltip>
                          </>
                        )}
                      </Form.List>
                    </Card>
                  ))}
                  <Button
                    type="dashed"
                    block
                    size="small"
                    icon={<PlusOutlined />}
                    onClick={() =>
                      addTarget({
                        targetNodeKey: '',
                        groups: [{ conditions: [{ fieldName: '', operator: 'eq', value: '' }] }],
                      })
                    }
                  >
                    添加目标节点
                  </Button>
                </>
              )}
            </Form.List>
          </>
        )}

        {nodeType === 'cc' && (
          <>
            <Divider style={{ margin: '8px 0' }}>抄送配置</Divider>
            <Form.Item label="抄送说明" name="ccDescription">
              <TextArea rows={2} placeholder="抄送说明" />
            </Form.Item>
          </>
        )}

        {['approval', 'cc', 'condition'].includes(nodeType) && (
          <>
            <Divider style={{ margin: '8px 0' }} />
            <Collapse
              size="small"
              items={[{
                key: 'listeners',
                label: <span><ThunderboltOutlined style={{ marginRight: 4 }} />监听器 ({listeners.length})</span>,
                children: (
                  <>
                    {listeners.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        {listeners.map((l) => (
                          <div
                            key={l.id}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '4px 0',
                              borderBottom: '1px solid #f0f0f0',
                              cursor: 'pointer',
                            }}
                            onClick={() => handleEditListener(l)}
                          >
                            <Space size={4}>
                              <Tag color="blue" style={{ margin: 0 }}>{getListenerSummary(l)}</Tag>
                              {l.label && <span style={{ fontSize: 12, color: '#666' }}>{l.label}</span>}
                            </Space>
                            <Button
                              type="text"
                              danger
                              size="small"
                              icon={<DeleteOutlined />}
                              onClick={(e) => { e.stopPropagation(); handleDeleteListener(l.id); }}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                    <Button
                      type="dashed"
                      size="small"
                      block
                      icon={<PlusOutlined />}
                      onClick={handleAddListener}
                    >
                      添加监听器
                    </Button>
                  </>
                ),
              }]}
            />
          </>
        )}
      </Form>

      <Modal
        title={editingListener ? '编辑监听器' : '添加监听器'}
        open={listenerModalOpen}
        onOk={handleListenerModalOk}
        onCancel={() => setListenerModalOpen(false)}
        destroyOnClose
        width={400}
      >
        <Form form={listenerForm} layout="vertical" size="small">
          <Form.Item label="标签" name="label">
            <Input placeholder="可选，便于识别" />
          </Form.Item>
          <Form.Item label="触发事件" name="event" rules={[{ required: true, message: '请选择事件' }]}>
            <Select options={showListenerEvents} />
          </Form.Item>
          <Form.Item label="动作类型" name="actionType" rules={[{ required: true, message: '请选择动作' }]}>
            <Select options={ACTION_TYPES} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.actionType !== cur.actionType}>
            {({ getFieldValue }) => {
              const actionType = getFieldValue('actionType');
              if (actionType === 'webhook') {
                return (
                  <>
                    <Form.Item label="Webhook URL" name="webhookUrl" rules={[{ required: true, message: '必填' }]}>
                      <Input placeholder="https://..." />
                    </Form.Item>
                    <Form.Item label="Body 模板" name="webhookBodyTemplate">
                      <TextArea rows={2} placeholder="JSON 模板，可选" />
                    </Form.Item>
                  </>
                );
              }
              if (actionType === 'callback') {
                return (
                  <Form.Item label="回调函数名" name="callbackName" rules={[{ required: true, message: '必填' }]}>
                    <Input placeholder="函数名称" />
                  </Form.Item>
                );
              }
              return null;
            }}
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
});

PropertyPanel.displayName = 'PropertyPanel';

export default PropertyPanel;
