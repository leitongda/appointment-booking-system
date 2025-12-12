import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag } from 'antd';
import { useRef, useState } from 'react';
import { contentApi } from '@hospital/api';
import type { Notice } from '@hospital/api';

const TYPE_OPTIONS = [
  { label: '系统公告', value: 1 },
  { label: '停诊通知', value: 2 },
  { label: '活动通知', value: 3 },
];

const NoticePage: React.FC = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Notice | null>(null);

  const handleDelete = async (id: string) => {
    try {
      await contentApi.deleteNotice(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = { ...values, isTop: values.isTop ? 1 : 0, status: values.status ? 1 : 0 };
      if (editingRecord) {
        await contentApi.updateNotice(editingRecord.id, data);
        message.success('更新成功');
      } else {
        await contentApi.createNotice(data);
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

  const columns: ProColumns<Notice>[] = [
    { title: '标题', dataIndex: 'title', ellipsis: true },
    { title: '类型', dataIndex: 'type', width: 100, valueEnum: { 1: '系统公告', 2: '停诊通知', 3: '活动通知' } },
    { title: '置顶', dataIndex: 'isTop', width: 70, search: false, render: (_, r) => r.isTop ? <Tag color="red">置顶</Tag> : '-' },
    { title: '状态', dataIndex: 'status', width: 80, valueEnum: { 1: { text: '发布', status: 'Success' }, 0: { text: '草稿', status: 'Default' } } },
    { title: '发布时间', dataIndex: 'publishTime', valueType: 'dateTime', width: 160, search: false },
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
      <ProTable<Notice>
        headerTitle="公告列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          const result = await contentApi.getNoticeList({ ...rest, page: current, pageSize });
          return { data: result.data, total: result.total, success: true };
        }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRecord(null); setModalOpen(true); }}>
            发布公告
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title={editingRecord ? '编辑公告' : '发布公告'}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        initialValues={editingRecord ? { ...editingRecord, isTop: editingRecord.isTop, status: editingRecord.status === 1 } : { type: 1, isTop: false, status: true }}
        modalProps={{ destroyOnClose: true }}
        width={600}
      >
        <ProFormText name="title" label="标题" rules={[{ required: true }]} />
        <ProFormSelect name="type" label="类型" options={TYPE_OPTIONS} rules={[{ required: true }]} />
        <ProFormTextArea name="content" label="内容" rules={[{ required: true }]} fieldProps={{ rows: 6 }} />
        <ProFormSwitch name="isTop" label="置顶" />
        <ProFormSwitch name="status" label="立即发布" />
      </ModalForm>
    </PageContainer>
  );
};

export default NoticePage;
