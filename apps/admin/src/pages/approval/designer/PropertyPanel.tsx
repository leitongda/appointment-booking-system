import { Card, Form, Input, Select, InputNumber, Button, Space, Divider } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { memo, useEffect } from 'react';
import type { Node } from '@xyflow/react';

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

interface PropertyPanelProps {
  selectedNode: Node | null;
  onUpdate: (nodeId: string, data: Record<string, any>) => void;
  onDelete: (nodeId: string) => void;
}

const PropertyPanel: React.FC<PropertyPanelProps> = memo(({ selectedNode, onUpdate, onDelete }) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (selectedNode) {
      form.resetFields();
      const d = selectedNode.data as any;
      form.setFieldsValue({
        label: d.label,
        approvalMode: d.approvalMode,
        assigneeType: d.assigneeType,
        timeoutHours: d.timeoutHours,
        timeoutAction: d.timeoutAction,
        conditions: d.conditions || [],
      });
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
    onUpdate(selectedNode.id, { ...d, ...allValues });
  };

  return (
    <Card
      size="small"
      title={`属性 — ${d.label || nodeType}`}
      style={{ width: 280 }}
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
          </>
        )}

        {nodeType === 'condition' && (
          <>
            <Divider style={{ margin: '8px 0' }}>条件规则</Divider>
            <Form.List name="conditions">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name }) => (
                    <Card key={key} size="small" style={{ marginBottom: 8 }}>
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Form.Item name={[name, 'fieldName']} label="字段" rules={[{ required: true }]}>
                          <Input placeholder="如 amount" />
                        </Form.Item>
                        <Form.Item name={[name, 'operator']} label="操作符" rules={[{ required: true }]}>
                          <Select options={OPERATOR_OPTIONS} />
                        </Form.Item>
                        <Form.Item name={[name, 'value']} label="值" rules={[{ required: true }]}>
                          <Input placeholder="条件值" />
                        </Form.Item>
                        <Form.Item name={[name, 'targetNodeKey']} label="目标节点" rules={[{ required: true }]}>
                          <Input placeholder="满足条件时跳转的节点 key" />
                        </Form.Item>
                        <Button type="link" danger size="small" onClick={() => remove(name)}>删除此条件</Button>
                      </Space>
                    </Card>
                  ))}
                  <Button type="dashed" block size="small" onClick={() => add({ operator: 'eq', priority: 0 })}>
                    + 添加条件
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
      </Form>
    </Card>
  );
});

PropertyPanel.displayName = 'PropertyPanel';

export default PropertyPanel;
