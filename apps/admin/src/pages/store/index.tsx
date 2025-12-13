import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSwitch } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag } from 'antd';
import { useRef, useState } from 'react';
import { storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Store } from '@hospital/shared';

const StorePage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Store | null>(null);

  const handleDelete = async (id: string) => {
    try {
      await storeApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = { ...values, status: values.status ? 1 : 0 };
      if (editingRecord) {
        await storeApi.update(editingRecord.id, data);
        message.success('更新成功');
      } else {
        await storeApi.create(data);
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

  const columns: ProColumns<Store>[] = [
    { title: '门店名称', dataIndex: 'name', ellipsis: true },
    { title: '门店编码', dataIndex: 'code', width: 100, search: false },
    { title: '城市', dataIndex: 'city', width: 80 },
    { title: '地址', dataIndex: 'address', ellipsis: true, search: false },
    { title: '联系电话', dataIndex: 'phone', width: 120, search: false },
    { title: '营业时间', width: 140, search: false, render: (_, r) => r.openingTime && r.closingTime ? `${r.openingTime}-${r.closingTime}` : '-' },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: { 1: { text: '营业', status: 'Success' }, 0: { text: '停业', status: 'Default' } },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          <a onClick={() => { setEditingRecord(record); setModalOpen(true); }}>编辑</a>
          <Popconfirm title="确定删除该门店吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Store>
        headerTitle="门店列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, name, ...rest } = params;
          return toProTableResult(await storeApi.getList({ ...rest, keyword: name, page: current, pageSize }));
        }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRecord(null); setModalOpen(true); }}>
            新增门店
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title={editingRecord ? '编辑门店' : '新增门店'}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        initialValues={editingRecord ? { ...editingRecord, status: editingRecord.status === 1 } : { status: true, sortOrder: 0 }}
        modalProps={{ destroyOnHidden: true }}
        width={600}
      >
        <ProFormText name="name" label="门店名称" rules={[{ required: true }]} />
        <ProFormText name="code" label="门店编码" />
        <ProFormText name="city" label="城市" />
        <ProFormText name="address" label="详细地址" />
        <ProFormText name="phone" label="联系电话" />
        <ProFormText name="contactPerson" label="联系人" />
        <ProFormText name="openingTime" label="开始营业时间" placeholder="如：08:00" />
        <ProFormText name="closingTime" label="结束营业时间" placeholder="如：18:00" />
        <ProFormTextArea name="description" label="描述" />
        <ProFormDigit name="sortOrder" label="排序" min={0} />
        <ProFormSwitch name="status" label="营业状态" />
      </ModalForm>
    </PageContainer>
  );
};

export default StorePage;
