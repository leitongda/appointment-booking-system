import { Form, Input, Select, Button, Space, InputNumber } from 'antd';
import { memo, useEffect } from 'react';

const { TextArea } = Input;

const ACTION_TYPE_OPTIONS = [
  { label: 'Webhook', value: 'webhook' },
  { label: '站内通知', value: 'notification' },
  { label: '短信', value: 'sms' },
  { label: '回调', value: 'callback' },
  { label: '第三方推送', value: 'integration_push' },
];

const INTEGRATION_PROVIDER_OPTIONS = [
  { label: '钉钉', value: 'dingtalk' },
  { label: '企业微信', value: 'wecom' },
  { label: '飞书', value: 'feishu' },
];

const INTEGRATION_TARGET_OPTIONS = [
  { label: '工作通知（点对点）', value: 'work_message' },
  { label: '群机器人', value: 'robot' },
];

const DEFAULT_EVENT_OPTIONS = [
  { label: '流程启动', value: 'process.start' },
  { label: '流程结束', value: 'process.end' },
  { label: '流程取消', value: 'process.cancel' },
  { label: '流程拒绝', value: 'process.reject' },
];

const NOTIFICATION_TARGET_OPTIONS = [
  { label: '审批人', value: 'approver' },
  { label: '发起人', value: 'initiator' },
  { label: '指定角色', value: 'role' },
  { label: '指定人员', value: 'user' },
];

export interface ListenerConfig {
  id?: string;
  label?: string;
  event: string;
  actionType: 'webhook' | 'notification' | 'sms' | 'callback' | 'integration_push';
  config: Record<string, any>;
}

interface ListenerFormProps {
  initialValues?: Partial<ListenerConfig>;
  onSubmit: (values: ListenerConfig) => void;
  onCancel: () => void;
  eventOptions?: { label: string; value: string }[];
}

const ListenerForm: React.FC<ListenerFormProps> = memo(({
  initialValues,
  onSubmit,
  onCancel,
  eventOptions = DEFAULT_EVENT_OPTIONS,
}) => {
  const [form] = Form.useForm();
  const actionType = Form.useWatch('actionType', form);

  useEffect(() => {
    if (initialValues) {
      form.setFieldsValue({
        label: initialValues.label,
        event: initialValues.event,
        actionType: initialValues.actionType,
        ...initialValues.config,
      });
    } else {
      form.resetFields();
    }
  }, [initialValues, form]);

  const handleFinish = (values: any) => {
    const { label, event, actionType: at, ...rest } = values;
    let config: Record<string, any> = {};

    if (at === 'webhook') {
      config = {
        url: rest.url,
        headers: rest.headers || [],
        bodyTemplate: rest.bodyTemplate,
        timeout: rest.timeout,
        retryCount: rest.retryCount,
      };
    } else if (at === 'notification') {
      config = {
        targetType: rest.targetType,
        targetIds: rest.targetIds,
        titleTemplate: rest.titleTemplate,
        contentTemplate: rest.contentTemplate,
      };
    } else if (at === 'sms') {
      config = {
        phoneField: rest.phoneField,
        templateCode: rest.templateCode,
      };
    } else if (at === 'callback') {
      config = { callbackName: rest.callbackName };
    } else if (at === 'integration_push') {
      config = {
        provider: rest.provider,
        target: rest.pushTarget,
        userIds: rest.userIds,
        titleTemplate: rest.pushTitleTemplate,
        contentTemplate: rest.pushContentTemplate,
      };
    }

    onSubmit({
      id: initialValues?.id,
      label,
      event,
      actionType: at,
      config,
    });
  };

  return (
    <Form form={form} layout="vertical" size="small" onFinish={handleFinish}>
      <Form.Item label="名称" name="label">
        <Input placeholder="可选，便于识别" />
      </Form.Item>

      <Form.Item label="监听事件" name="event" rules={[{ required: true, message: '请选择事件' }]}>
        <Select options={eventOptions} placeholder="选择触发事件" />
      </Form.Item>

      <Form.Item label="动作类型" name="actionType" rules={[{ required: true, message: '请选择动作类型' }]}>
        <Select options={ACTION_TYPE_OPTIONS} placeholder="选择动作类型" />
      </Form.Item>

      {actionType === 'webhook' && (
        <>
          <Form.Item label="URL" name="url" rules={[{ required: true, message: '请输入 URL' }]}>
            <Input placeholder="https://example.com/webhook" />
          </Form.Item>
          <Form.List name="headers">
            {(fields, { add, remove }) => (
              <>
                <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>请求头</div>
                {fields.map(({ key, name }) => (
                  <Space key={key} style={{ display: 'flex', marginBottom: 4 }} size={4}>
                    <Form.Item name={[name, 'key']} noStyle>
                      <Input size="small" placeholder="Key" style={{ width: 100 }} />
                    </Form.Item>
                    <Form.Item name={[name, 'value']} noStyle>
                      <Input size="small" placeholder="Value" style={{ width: 140 }} />
                    </Form.Item>
                    <Button type="text" danger size="small" onClick={() => remove(name)}>
                      删除
                    </Button>
                  </Space>
                ))}
                <Button type="dashed" size="small" block onClick={() => add()}>
                  添加请求头
                </Button>
              </>
            )}
          </Form.List>
          <Form.Item label="请求体模板" name="bodyTemplate" style={{ marginTop: 8 }}>
            <TextArea rows={3} placeholder='{"event": "{{event}}", "data": {{data}}}' />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item label="超时(秒)" name="timeout" style={{ flex: 1 }}>
              <InputNumber min={1} max={60} placeholder="30" style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item label="重试次数" name="retryCount" style={{ flex: 1 }}>
              <InputNumber min={0} max={5} placeholder="0" style={{ width: '100%' }} />
            </Form.Item>
          </Space>
        </>
      )}

      {actionType === 'notification' && (
        <>
          <Form.Item label="通知目标类型" name="targetType" rules={[{ required: true }]}>
            <Select options={NOTIFICATION_TARGET_OPTIONS} placeholder="选择目标类型" />
          </Form.Item>
          <Form.Item label="目标 ID" name="targetIds">
            <Select mode="tags" placeholder="输入后回车添加" />
          </Form.Item>
          <Form.Item label="标题模板" name="titleTemplate">
            <Input placeholder="{{发起人}} 提交了审批" />
          </Form.Item>
          <Form.Item label="内容模板" name="contentTemplate">
            <TextArea rows={3} placeholder="支持 {{变量}} 插值" />
          </Form.Item>
        </>
      )}

      {actionType === 'sms' && (
        <>
          <Form.Item label="手机号字段" name="phoneField" rules={[{ required: true }]}>
            <Input placeholder="表单中手机号字段名，如 phone" />
          </Form.Item>
          <Form.Item label="短信模板编号" name="templateCode" rules={[{ required: true }]}>
            <Input placeholder="SMS_200000001" />
          </Form.Item>
        </>
      )}

      {actionType === 'callback' && (
        <Form.Item label="回调名称" name="callbackName" rules={[{ required: true }]}>
          <Input placeholder="已注册的回调函数名" />
        </Form.Item>
      )}

      {actionType === 'integration_push' && (
        <>
          <Form.Item label="平台" name="provider" rules={[{ required: true, message: '请选择平台' }]}>
            <Select options={INTEGRATION_PROVIDER_OPTIONS} placeholder="选择第三方平台" />
          </Form.Item>
          <Form.Item label="推送目标" name="pushTarget" rules={[{ required: true }]}>
            <Select options={INTEGRATION_TARGET_OPTIONS} placeholder="选择推送目标" />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, cur) => prev.pushTarget !== cur.pushTarget}>
            {({ getFieldValue }) =>
              getFieldValue('pushTarget') === 'work_message' ? (
                <Form.Item
                  label="接收人ID"
                  name="userIds"
                  rules={[{ required: true, message: '请输入接收人' }]}
                  extra="本地管理员ID，系统会自动查其绑定的第三方账号"
                >
                  <Select mode="tags" placeholder="输入管理员ID后回车" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
          <Form.Item label="标题模板" name="pushTitleTemplate">
            <Input placeholder="审批待办: {{flowName}}" />
          </Form.Item>
          <Form.Item label="内容模板" name="pushContentTemplate">
            <TextArea rows={3} placeholder="{{applicantName}} 提交的审批等待您处理" />
          </Form.Item>
        </>
      )}

      <Space style={{ marginTop: 8 }}>
        <Button type="primary" htmlType="submit">
          确定
        </Button>
        <Button onClick={onCancel}>取消</Button>
      </Space>
    </Form>
  );
});

ListenerForm.displayName = 'ListenerForm';

export default ListenerForm;
