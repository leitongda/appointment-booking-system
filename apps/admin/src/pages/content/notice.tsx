import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Switch } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { contentApi } from '@hospital/api';

interface NoticeRecord {
  id: string;
  title: string;
  type: number;
  content: string;
  isTop: boolean;
  status: number;
  publishTime: string;
  createdAt: string;
}

const noticeTypes = [
  { label: '系统公告', value: 1 },
  { label: '停诊通知', value: 2 },
  { label: '活动通知', value: 3 },
  { label: '重要提醒', value: 4 },
];

const NoticePage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingNotice, setEditingNotice] = useState<NoticeRecord | null>(null);

  const handleAdd = () => {
    setEditingNotice(null);
    setModalVisible(true);
  };

  const handleEdit = (record: NoticeRecord) => {
    setEditingNotice(record);
    setModalVisible(true);
  };

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
      const submitData = {
        ...values,
        isTop: values.isTop ? 1 : 0,
        status: values.status ? 1 : 0,
      };

      if (editingNotice) {
        await contentApi.updateNotice(editingNotice.id, submitData);
        message.success('更新成功');
      } else {
        await contentApi.createNotice(submitData);
        message.success('创建成功');
      }
      setModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '操作失败');
      return false;
    }
  };

  const columns: ProColumns<NoticeRecord>[] = [
    { title: '标题', dataIndex: 'title', width: 300, ellipsis: true },
    { 
      title: '类型', 
      dataIndex: 'type', 
      width: 120, 
      valueEnum: Object.fromEntries(noticeTypes.map((t) => [t.value, t.label]))
    },
    { 
      title: '置顶', 
      dataIndex: 'isTop', 
      width: 80, 
      search: false,
      render: (_, r) => r.isTop ? <Tag color="red">是</Tag> : <Tag>否</Tag> 
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100,
      valueEnum: { 0: { text: '草稿' }, 1: { text: '已发布', status: 'Success' } }
    },
    { title: '发布时间', dataIndex: 'publishTime', width: 180, valueType: 'dateTime', search: false },
    { 
      title: '操作', 
      valueType: 'option', 
      width: 150, 
      render: (_, record) => (
        <Space>
          <a onClick={() => handleEdit(record)}>编辑</a>
          <Popconfirm title="确定删除吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      )
    },
  ];

  const mockData: NoticeRecord[] = [
    { id: '1', title: '关于调整门诊挂号时间的通知', type: 1, content: '为方便患者就诊...', isTop: true, status: 1, publishTime: '2024-11-27 08:00:00', createdAt: '2024-11-27' },
    { id: '2', title: '张医生11月30日停诊通知', type: 2, content: '因个人原因...', isTop: false, status: 1, publishTime: '2024-11-26 10:00:00', createdAt: '2024-11-26' },
  ];

  return (
    <PageContainer>
      <ProTable<NoticeRecord>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增公告
          </Button>
        ]}
        request={async () => ({ data: mockData, success: true, total: mockData.length })}
      />

      <ModalForm
        title={editingNotice ? '编辑公告' : '新增公告'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        onFinish={handleSubmit}
        initialValues={editingNotice || { type: 1, isTop: false, status: true }}
        modalProps={{ destroyOnClose: true }}
        width={600}
      >
        <ProFormText name="title" label="标题" rules={[{ required: true }]} />
        <ProFormSelect name="type" label="类型" options={noticeTypes} rules={[{ required: true }]} />
        <ProFormTextArea name="content" label="内容" rules={[{ required: true }]} fieldProps={{ rows: 6 }} />
        <ProFormSwitch name="isTop" label="置顶" />
        <ProFormSwitch name="status" label="发布" initialValue={true} />
      </ModalForm>
    </PageContainer>
  );
};

export default NoticePage;
