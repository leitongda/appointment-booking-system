import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormDigit, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Image } from 'antd';
import { useRef, useState } from 'react';
import { contentApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Banner } from '@hospital/api';

const LINK_TYPE_OPTIONS = [
  { label: '无链接', value: 0 },
  { label: '内部链接', value: 1 },
  { label: '外部链接', value: 2 },
];

const BannerPage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Banner | null>(null);

  const handleDelete = async (id: string) => {
    try {
      await contentApi.deleteBanner(id);
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
        await contentApi.updateBanner(editingRecord.id, data);
        message.success('更新成功');
      } else {
        await contentApi.createBanner(data);
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

  const columns: ProColumns<Banner>[] = [
    { title: '图片', dataIndex: 'imageUrl', width: 120, search: false, render: (_, r) => <Image src={r.imageUrl} width={100} /> },
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '位置', dataIndex: 'position', width: 100, valueEnum: { home: '首页', mine: '我的' } },
    { title: '链接类型', dataIndex: 'linkType', width: 100, search: false, valueEnum: { 0: '无链接', 1: '内部', 2: '外部' } },
    { title: '排序', dataIndex: 'sortOrder', width: 70, search: false },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 1: { text: '启用', status: 'Success' }, 0: { text: '禁用', status: 'Default' } } },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          <a onClick={() => { setEditingRecord(record); setModalOpen(true); }}>编辑</a>
          <Popconfirm title="确定删除吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: '#ff4d4f' }}>删除</a>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Banner>
        headerTitle="轮播图列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await contentApi.getBannerList({ ...rest, page: current, pageSize }));
        }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRecord(null); setModalOpen(true); }}>
            新增轮播图
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title={editingRecord ? '编辑轮播图' : '新增轮播图'}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        initialValues={editingRecord ? { ...editingRecord, status: editingRecord.status === 1 } : { linkType: 0, position: 'home', sortOrder: 0, status: true }}
        modalProps={{ destroyOnClose: true }}
      >
        <ProFormText name="title" label="标题" />
        <ProFormText name="imageUrl" label="图片URL" rules={[{ required: true }]} />
        <ProFormSelect name="linkType" label="链接类型" options={LINK_TYPE_OPTIONS} />
        <ProFormText name="linkUrl" label="链接地址" />
        <ProFormSelect name="position" label="展示位置" options={[{ label: '首页', value: 'home' }, { label: '我的', value: 'mine' }]} />
        <ProFormDigit name="sortOrder" label="排序" min={0} />
        <ProFormSwitch name="status" label="启用状态" />
      </ModalForm>
    </PageContainer>
  );
};

export default BannerPage;
