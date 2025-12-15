import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space } from 'antd';
import { useRef, useState } from 'react';
import { useAccess } from '@umijs/max';
import { consultationFeeTypeApi } from '@hospital/api';
import type { ConsultationFeeType } from '@hospital/shared';

const ConsultationFeeTypesPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<ConsultationFeeType | null>(null);

  const handleDelete = async (id: string) => {
    try {
      await consultationFeeTypeApi.delete(id);
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
        status: values.status ? 1 : 0,
      };
      if (editingRecord) {
        await consultationFeeTypeApi.update(editingRecord.id, data);
        message.success('更新成功');
      } else {
        await consultationFeeTypeApi.create(data);
        message.success('创建成功');
      }
      setModalOpen(false);
      setEditingRecord(null);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const columns: ProColumns<ConsultationFeeType>[] = [
    {
      title: '类型名称',
      dataIndex: 'name',
      ellipsis: true,
    },
    {
      title: '类型编码',
      dataIndex: 'code',
      ellipsis: true,
      search: false,
    },
    {
      title: '描述',
      dataIndex: 'description',
      ellipsis: true,
      search: false,
    },
    {
      title: '排序',
      dataIndex: 'sortOrder',
      width: 80,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueType: 'select',
      valueEnum: {
        1: { text: '启用', status: 'Success' },
        0: { text: '禁用', status: 'Default' },
      },
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
      width: 120,
      render: (_, record) => (
        <Space>
          {access.hasPermission('system:consultation-fee') && (
            <a
              onClick={() => {
                setEditingRecord(record);
                setModalOpen(true);
              }}
            >
              编辑
            </a>
          )}
          {access.hasPermission('system:consultation-fee') && (
            <Popconfirm
              title="确定删除该诊费类型吗？"
              description="删除后相关诊费配置也会受影响"
              onConfirm={() => handleDelete(record.id)}
            >
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<ConsultationFeeType>
        headerTitle="诊费类型列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={false}
        request={async (params) => {
          const list = await consultationFeeTypeApi.getList({ status: params.status });
          return {
            data: list,
            success: true,
            total: list.length,
          };
        }}
        toolBarRender={() => [
          access.hasPermission('system:consultation-fee') && (
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingRecord(null);
                setModalOpen(true);
              }}
            >
              新增诊费类型
            </Button>
          ),
        ]}
        pagination={false}
      />

      <ModalForm
        title={editingRecord ? '编辑诊费类型' : '新增诊费类型'}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        initialValues={editingRecord ? {
          ...editingRecord,
          status: editingRecord.status === 1,
        } : { sortOrder: 0, status: true }}
        modalProps={{ destroyOnClose: true }}
        width={500}
      >
        <ProFormText
          name="name"
          label="类型名称"
          placeholder="请输入诊费类型名称，如：专家、普通、加急"
          rules={[{ required: true, message: '请输入类型名称' }]}
        />
        <ProFormText
          name="code"
          label="类型编码"
          placeholder="请输入类型编码，如：expert、normal、urgent"
          tooltip="用于系统识别，建议使用英文"
        />
        <ProFormTextArea
          name="description"
          label="描述"
          placeholder="请输入诊费类型描述"
        />
        <ProFormDigit
          name="sortOrder"
          label="排序"
          placeholder="数字越小越靠前"
          min={0}
          max={999}
        />
        <ProFormSwitch name="status" label="启用状态" />
      </ModalForm>
    </PageContainer>
  );
};

export default ConsultationFeeTypesPage;
