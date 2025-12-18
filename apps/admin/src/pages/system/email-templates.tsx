import { PlusOutlined, SendOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Switch } from 'antd';
import { useRef, useState } from 'react';
import { history, useAccess } from '@umijs/max';
import { emailTemplateApi, EMAIL_TEMPLATE_TYPE_OPTIONS } from '@hospital/api';
import type { EmailTemplateListItem } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';

const EmailTemplatesPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [testModalVisible, setTestModalVisible] = useState(false);
  const [currentTemplate, setCurrentTemplate] = useState<EmailTemplateListItem | null>(null);

  const handleDelete = async (id: string) => {
    try {
      await emailTemplateApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleStatusChange = async (id: string, status: boolean) => {
    try {
      await emailTemplateApi.update(id, { status: status ? 1 : 0 });
      message.success('状态更新成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '状态更新失败');
    }
  };

  const handleSendTest = async (values: { toEmail: string }) => {
    if (!currentTemplate) return false;
    try {
      await emailTemplateApi.sendTest(currentTemplate.id, { toEmail: values.toEmail });
      message.success('测试邮件发送成功');
      setTestModalVisible(false);
      return true;
    } catch (error: any) {
      message.error(error.message || '发送测试邮件失败');
      return false;
    }
  };

  const templateTypeEnum = EMAIL_TEMPLATE_TYPE_OPTIONS.reduce((acc, item) => {
    acc[item.value] = { text: item.label };
    return acc;
  }, {} as Record<string, { text: string }>);

  const columns: ProColumns<EmailTemplateListItem>[] = [
    {
      title: '模板编码',
      dataIndex: 'code',
      width: 150,
      ellipsis: true,
    },
    {
      title: '模板名称',
      dataIndex: 'name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '模板类型',
      dataIndex: 'templateType',
      width: 120,
      valueEnum: templateTypeEnum,
      render: (_, record) => {
        const option = EMAIL_TEMPLATE_TYPE_OPTIONS.find(o => o.value === record.templateType);
        return <Tag color="blue">{option?.label || record.templateType}</Tag>;
      },
    },
    {
      title: '邮件主题',
      dataIndex: 'subjectTemplate',
      width: 200,
      ellipsis: true,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
      render: (_, record) => (
        <Switch
          checked={record.status === 1}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          onChange={(checked) => handleStatusChange(record.id, checked)}
          disabled={!access.hasPermission('system:email-template:update')}
        />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          {access.hasPermission('system:email-template:update') && (
            <a onClick={() => history.push(`/system/email-templates/${record.id}/edit`)}>编辑</a>
          )}
          <a
            onClick={() => {
              setCurrentTemplate(record);
              setTestModalVisible(true);
            }}
          >
            <SendOutlined /> 测试
          </a>
          {access.hasPermission('system:email-template:delete') && (
            <Popconfirm title="确定删除吗？" onConfirm={() => handleDelete(record.id)}>
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<EmailTemplateListItem>
        headerTitle="邮件模板列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1200 }}
        request={async (params) => {
          const { current, pageSize, templateType, status, name, ...rest } = params;
          const res = await emailTemplateApi.getList({
            ...rest,
            templateType: templateType as any,
            status: status !== undefined ? Number(status) : undefined,
            keyword: name,
            page: current,
            pageSize,
          });
          return toProTableResult(res);
        }}
        search={{
          labelWidth: 'auto',
        }}
        toolBarRender={() => [
          access.hasPermission('system:email-template:create') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/system/email-templates/create')}
            >
              新增模板
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title={`发送测试邮件 - ${currentTemplate?.name}`}
        open={testModalVisible}
        onOpenChange={setTestModalVisible}
        onFinish={handleSendTest}
        width={400}
      >
        <ProFormText
          name="toEmail"
          label="收件人邮箱"
          placeholder="请输入收件人邮箱"
          rules={[
            { required: true, message: '请输入收件人邮箱' },
            { type: 'email', message: '请输入正确的邮箱格式' },
          ]}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default EmailTemplatesPage;

