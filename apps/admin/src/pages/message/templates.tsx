import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSelect } from '@ant-design/pro-components';
import { Tag, Switch, Button, Popconfirm, message } from 'antd';
import { useState, useRef } from 'react';
import { useAccess } from '@umijs/max';
import { request } from '@umijs/max';
import type { ActionType } from '@ant-design/pro-components';

interface UnifiedTemplate {
  id: string;
  tenantId?: string;
  code?: string;
  name?: string;
  messageType?: string;
  eventType?: string;
  subjectTemplate?: string;
  htmlTemplate?: string;
  textTemplate?: string;
  wechatTemplateId?: string;
  variablesSchema?: Record<string, any>;
  status?: number;
  createdAt?: string;
  updatedAt?: string;
}

const MESSAGE_TYPE_OPTIONS = [
  { label: '系统', value: 'system' },
  { label: '预约', value: 'appointment' },
  { label: '就诊', value: 'consultation' },
  { label: '排班', value: 'schedule' },
  { label: '停诊', value: 'stop_clinic' },
  { label: '反馈', value: 'feedback' },
];

const UnifiedTemplatesPage: React.FC = () => {
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [currentTemplate, setCurrentTemplate] = useState<UnifiedTemplate | null>(null);

  const handleDelete = async (id: string) => {
    try {
      await request(`/api/v1/unified-messages/templates/${id}`, { method: 'DELETE' });
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleStatusChange = async (id: string, status: boolean) => {
    try {
      await request(`/api/v1/unified-messages/templates/${id}`, {
        method: 'PUT',
        data: { status: status ? 1 : 0 },
      });
      message.success('状态更新成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '状态更新失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (currentTemplate) {
        await request(`/api/v1/unified-messages/templates/${currentTemplate.id}`, {
          method: 'PUT',
          data: values,
        });
        message.success('更新成功');
      } else {
        await request('/api/v1/unified-messages/templates', {
          method: 'POST',
          data: values,
        });
        message.success('创建成功');
      }
      setModalVisible(false);
      setCurrentTemplate(null);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const columns: ProColumns<UnifiedTemplate>[] = [
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
      title: '消息类型',
      dataIndex: 'messageType',
      width: 100,
      valueEnum: MESSAGE_TYPE_OPTIONS.reduce((acc, item) => {
        acc[item.value] = { text: item.label };
        return acc;
      }, {} as Record<string, { text: string }>),
      render: (_, record) => {
        const option = MESSAGE_TYPE_OPTIONS.find(o => o.value === record.messageType);
        return <Tag color="blue">{option?.label || record.messageType}</Tag>;
      },
    },
    {
      title: '主题模板',
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
          disabled={!access.hasPermission('message:send')}
        />
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
            setCurrentTemplate(record);
            setModalVisible(true);
          }}
          disabled={!access.hasPermission('message:send')}
        >
          编辑
        </Button>,
        <Popconfirm
          key="delete"
          title="确认删除"
          description="删除后不可恢复，确认删除？"
          onConfirm={() => handleDelete(record.id)}
          disabled={!access.hasPermission('message:delete')}
        >
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
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
      <ProTable<UnifiedTemplate>
        headerTitle="统一模板管理"
        actionRef={actionRef}
        rowKey="id"
        search={{
          labelWidth: 'auto',
        }}
        toolBarRender={() => [
          <Button
            key="create"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setCurrentTemplate(null);
              setModalVisible(true);
            }}
            disabled={!access.hasPermission('message:send')}
          >
            新建模板
          </Button>,
        ]}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          const response = await request('/api/v1/unified-messages/templates', {
            params: {
              page: current,
              page_size: pageSize,
              ...rest,
            },
          });
          return {
            data: response.data || [],
            total: response.total || 0,
            success: true,
          };
        }}
        columns={columns}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
        }}
      />

      <ModalForm
        title={currentTemplate ? '编辑模板' : '新建模板'}
        open={modalVisible}
        onOpenChange={(visible) => {
          setModalVisible(visible);
          if (!visible) {
            setCurrentTemplate(null);
          }
        }}
        initialValues={currentTemplate || {}}
        onFinish={handleSubmit}
        modalProps={{
          destroyOnClose: true,
        }}
      >
        <ProFormText
          name="code"
          label="模板编码"
          placeholder="请输入模板编码"
          rules={[{ required: true, message: '请输入模板编码' }]}
          disabled={!!currentTemplate}
        />
        <ProFormText
          name="name"
          label="模板名称"
          placeholder="请输入模板名称"
          rules={[{ required: true, message: '请输入模板名称' }]}
        />
        <ProFormSelect
          name="messageType"
          label="消息类型"
          options={MESSAGE_TYPE_OPTIONS}
          rules={[{ required: true, message: '请选择消息类型' }]}
        />
        <ProFormText
          name="eventType"
          label="事件类型"
          placeholder="请输入事件类型（可选）"
        />
        <ProFormText
          name="subjectTemplate"
          label="主题模板"
          placeholder="请输入主题模板"
        />
        <ProFormTextArea
          name="textTemplate"
          label="文本模板"
          placeholder="请输入文本模板内容"
          fieldProps={{ rows: 4 }}
        />
        <ProFormTextArea
          name="htmlTemplate"
          label="HTML模板"
          placeholder="请输入HTML模板内容（可选）"
          fieldProps={{ rows: 4 }}
        />
        <ProFormText
          name="wechatTemplateId"
          label="微信模板ID"
          placeholder="请输入微信模板ID（可选）"
        />
      </ModalForm>
    </PageContainer>
  );
};

export default UnifiedTemplatesPage;