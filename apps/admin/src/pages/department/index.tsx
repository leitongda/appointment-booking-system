import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag } from 'antd';
import { useRef, useState } from 'react';
import { departmentApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Department } from '@hospital/shared';

const DepartmentPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Department | null>(null);

  const handleDelete = async (id: string) => {
    try {
      await departmentApi.delete(id);
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
        isHot: values.isHot ? 1 : 0,
        status: values.status ? 1 : 0,
      };
      if (editingRecord) {
        await departmentApi.update(editingRecord.id, data);
        message.success('更新成功');
      } else {
        await departmentApi.create(data);
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

  const columns: ProColumns<Department>[] = [
    {
      title: '科室名称',
      dataIndex: 'name',
      ellipsis: true,
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
      title: '热门',
      dataIndex: 'isHot',
      width: 80,
      search: false,
      render: (_, record) => (
        record.isHot === 1 ? <Tag color="red">热门</Tag> : <Tag>普通</Tag>
      ),
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
          <a
            onClick={() => {
              setEditingRecord(record);
              setModalOpen(true);
            }}
          >
            编辑
          </a>
          <Popconfirm
            title="确定删除该科室吗？"
            onConfirm={() => handleDelete(record.id)}
          >
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Department>
        headerTitle="科室列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await departmentApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingRecord(null);
              setModalOpen(true);
            }}
          >
            新增科室
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title={editingRecord ? '编辑科室' : '新增科室'}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        initialValues={editingRecord ? {
          ...editingRecord,
          isHot: editingRecord.isHot === 1,
          status: editingRecord.status === 1,
        } : { sortOrder: 0, isHot: false, status: true }}
        modalProps={{ destroyOnHidden: true }}
      >
        <ProFormText
          name="name"
          label="科室名称"
          placeholder="请输入科室名称"
          rules={[{ required: true, message: '请输入科室名称' }]}
        />
        <ProFormTextArea
          name="description"
          label="描述"
          placeholder="请输入科室描述"
        />
        <ProFormDigit
          name="sortOrder"
          label="排序"
          placeholder="数字越小越靠前"
          min={0}
          max={999}
        />
        <ProFormSwitch name="isHot" label="设为热门" />
        <ProFormSwitch name="status" label="启用状态" />
      </ModalForm>
    </PageContainer>
  );
};

export default DepartmentPage;
