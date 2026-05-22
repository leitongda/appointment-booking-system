import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { useState, useMemo } from 'react';
import { messageApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { OperationGroup, OperationButton, CreateButton } from '@/components/ListOperations';
import { useDict } from '@/hooks/useDict';
import type { RecipientRule } from '@hospital/shared';

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

const RecipientRulesPage: React.FC = () => {
  const { actionRef, message } = useListPage();
  const { options: ruleTypeOptions } = useDict('rule_type');
  const { options: eventTypeOptions } = useDict('notification_event_type');
  const ruleTypeEnum = useMemo(
    () => Object.fromEntries(ruleTypeOptions.map((o) => [o.value, { text: o.label }])),
    [ruleTypeOptions],
  );
  const eventTypeEnum = useMemo(
    () => Object.fromEntries(eventTypeOptions.map((o) => [o.value, { text: o.label }])),
    [eventTypeOptions],
  );
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
      valueEnum: eventTypeEnum,
      render: (_, record) => {
        const opt = eventTypeOptions.find(o => o.value === record.eventType);
        return <Tag>{opt?.label || record.eventType || '通用'}</Tag>;
      },
    },
    {
      title: '规则类型',
      dataIndex: 'ruleType',
      width: 100,
      valueEnum: ruleTypeEnum,
      render: (_, record) => (
        <Tag color={RULE_TYPE_COLORS[record.ruleType]}>
          {ruleTypeOptions.find(o => o.value === record.ruleType)?.label || record.ruleType}
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
      width: 120,
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="edit"
            permission="message:send"
            onClick={() => {
              setCurrentRule(record);
              setSelectedRuleType(record.ruleType);
              setModalVisible(true);
            }}
          />
          <OperationButton
            type="delete"
            permission="message:delete"
            confirmText="确认删除此规则？"
            onClick={() => handleDelete(record.id)}
          />
        </OperationGroup>
      ),
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
          <CreateButton
            key="create"
            permission="message:send"
            label="新建规则"
            onClick={() => {
              setCurrentRule(null);
              setSelectedRuleType('role');
              setModalVisible(true);
            }}
          />,
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
          options={eventTypeOptions}
          placeholder="留空表示通用规则"
          allowClear
        />
        <ProFormSelect
          name="ruleType"
          label="规则类型"
          options={ruleTypeOptions}
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
              validator: async (_: any, value: any) => {
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
