import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import { Tag, Button, Popconfirm, message } from 'antd';
import { useState, useRef } from 'react';
import { useAccess } from '@umijs/max';
import { messageApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import type { ActionType } from '@ant-design/pro-components';
import type { RecipientRule } from '@hospital/shared';

const RULE_TYPE_OPTIONS = [
  { label: '角色', value: 'role' },
  { label: '科室', value: 'department' },
  { label: '用户列表', value: 'user_list' },
  { label: '动态查询', value: 'dynamic' },
  { label: '事件驱动', value: 'event_driven' },
];

const RULE_TYPE_COLORS: Record<string, string> = {
  role: 'blue',
  department: 'cyan',
  user_list: 'green',
  dynamic: 'orange',
  event_driven: 'purple',
};

const RULE_CONFIG_HINTS: Record<string, string> = {
  role: '{"role": "doctor", "store_id": "xxx"}',
  department: '{"department_id": "xxx"}',
  user_list: '[{"user_id": "xxx", "user_type": "patient"}]',
  dynamic: '{"field_mapping": {"doctor_id": "appointment_doctor_id"}, "user_type": "doctor"}',
  event_driven: '{"recipient_field": "user_id", "user_type_field": "user_type"}',
};

const EVENT_TYPE_OPTIONS = [
  { label: '预约确认', value: 'appointment_confirmed' },
  { label: '预约取消', value: 'appointment_cancelled' },
  { label: '预约提醒', value: 'appointment_reminder' },
  { label: '排班变更', value: 'schedule_changed' },
  { label: '停诊通知', value: 'stop_clinic' },
  { label: '叫号通知', value: 'queue_call' },
  { label: '系统通知', value: 'system' },
];

const RecipientRulesPage: React.FC = () => {
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [currentRule, setCurrentRule] = useState<RecipientRule | null>(null);
  const [selectedRuleType, setSelectedRuleType] = useState<string>('role');

  const handleDelete = async (id: string) => {
    try {
      await messageApi.deleteRecipientRule(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = {
        ...values,
        ruleConfig: values.ruleConfig ? JSON.parse(values.ruleConfig) : {},
      };
      if (currentRule) {
        await messageApi.updateRecipientRule(currentRule.id, data);
        message.success('更新成功');
      } else {
        await messageApi.createRecipientRule(data);
        message.success('创建成功');
      }
      setModalVisible(false);
      setCurrentRule(null);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      if (error instanceof SyntaxError) {
        message.error('规则配置 JSON 格式错误');
      } else {
        message.error(error.message || '操作失败');
      }
      return false;
    }
  };

  const columns: ProColumns<RecipientRule>[] = [
    {
      title: '规则名称',
      dataIndex: 'name',
      width: 180,
      ellipsis: true,
    },
    {
      title: '事件类型',
      dataIndex: 'eventType',
      width: 140,
      valueEnum: EVENT_TYPE_OPTIONS.reduce((acc, item) => {
        acc[item.value] = { text: item.label };
        return acc;
      }, {} as Record<string, { text: string }>),
      render: (_, record) => {
        const opt = EVENT_TYPE_OPTIONS.find(o => o.value === record.eventType);
        return <Tag>{opt?.label || record.eventType || '通用'}</Tag>;
      },
    },
    {
      title: '规则类型',
      dataIndex: 'ruleType',
      width: 100,
      valueEnum: RULE_TYPE_OPTIONS.reduce((acc, item) => {
        acc[item.value] = { text: item.label };
        return acc;
      }, {} as Record<string, { text: string }>),
      render: (_, record) => (
        <Tag color={RULE_TYPE_COLORS[record.ruleType]}>
          {RULE_TYPE_OPTIONS.find(o => o.value === record.ruleType)?.label || record.ruleType}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      search: false,
      render: (_, record) => (
        <Tag color={record.status === 1 ? 'green' : 'default'}>
          {record.status === 1 ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 180,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => [
        <Button
          key="edit"
          type="link"
          size="small"
          icon={<EditOutlined />}
          onClick={() => {
            setCurrentRule(record);
            setSelectedRuleType(record.ruleType);
            setModalVisible(true);
          }}
          disabled={!access.hasPermission('message:send')}
        >
          编辑
        </Button>,
        <Popconfirm
          key="delete"
          title="确认删除此规则？"
          onConfirm={() => handleDelete(record.id)}
          disabled={!access.hasPermission('message:delete')}
        >
          <Button type="link" size="small" danger icon={<DeleteOutlined />}
            disabled={!access.hasPermission('message:delete')}
          >
            删除
          </Button>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <PageContainer>
      <ProTable<RecipientRule>
        headerTitle="收件人规则"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setCurrentRule(null);
              setSelectedRuleType('role');
              setModalVisible(true);
            }}
            disabled={!access.hasPermission('message:send')}
          >
            新建规则
          </Button>,
        ]}
        request={createListRequest(messageApi.getRecipientRules as any)}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title={currentRule ? '编辑规则' : '新建规则'}
        open={modalVisible}
        onOpenChange={(visible) => {
          setModalVisible(visible);
          if (!visible) {
            setCurrentRule(null);
          }
        }}
        initialValues={currentRule ? {
          ...currentRule,
          ruleConfig: currentRule.ruleConfig ? JSON.stringify(currentRule.ruleConfig, null, 2) : '',
        } : {}}
        onFinish={handleSubmit}
        modalProps={{ destroyOnClose: true }}
      >
        <ProFormText
          name="name"
          label="规则名称"
          placeholder="请输入规则名称"
          rules={[{ required: true, message: '请输入规则名称' }]}
        />
        <ProFormSelect
          name="eventType"
          label="事件类型"
          options={EVENT_TYPE_OPTIONS}
          placeholder="留空表示通用规则"
          allowClear
        />
        <ProFormSelect
          name="ruleType"
          label="规则类型"
          options={RULE_TYPE_OPTIONS}
          rules={[{ required: true, message: '请选择规则类型' }]}
          fieldProps={{
            onChange: (value) => setSelectedRuleType(value as string),
          }}
        />
        <ProFormTextArea
          name="ruleConfig"
          label="规则配置（JSON）"
          placeholder={RULE_CONFIG_HINTS[selectedRuleType] || '{}'}
          fieldProps={{ rows: 6 }}
          rules={[
            {
              validator: async (_, value) => {
                if (value) {
                  try {
                    JSON.parse(value);
                  } catch {
                    throw new Error('请输入有效的 JSON 格式');
                  }
                }
              },
            },
          ]}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default RecipientRulesPage;
