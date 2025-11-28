import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Image, Switch } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { contentApi } from '@hospital/api';
import type { News } from '@hospital/api';

const newsTypes = [
  { label: '医院动态', value: 1 },
  { label: '健康科普', value: 2 },
  { label: '通知公告', value: 3 },
  { label: '政策法规', value: 4 },
];

const NewsPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingNews, setEditingNews] = useState<News | null>(null);

  const handleAdd = () => {
    setEditingNews(null);
    setModalVisible(true);
  };

  const handleEdit = (record: News) => {
    setEditingNews(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await contentApi.deleteNews(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const submitData = {
        title: values.title,
        type: values.type,
        coverImage: values.coverImage,
        summary: values.summary,
        content: values.content,
        isTop: values.isTop ? 1 : 0,
        status: values.status ? 1 : 0,
      };

      if (editingNews) {
        await contentApi.updateNews(editingNews.id, submitData);
        message.success('更新成功');
      } else {
        await contentApi.createNews(submitData);
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

  const handleStatusChange = async (id: string, status: number) => {
    try {
      await contentApi.updateNews(id, { status });
      message.success(status === 1 ? '已发布' : '已下架');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<News>[] = [
    { 
      title: '封面', 
      dataIndex: 'coverImage', 
      width: 100, 
      search: false, 
      render: (_, r) => r.coverImage ? <Image width={80} height={50} src={r.coverImage} style={{ objectFit: 'cover' }} /> : '-' 
    },
    { title: '标题', dataIndex: 'title', width: 250, ellipsis: true },
    { 
      title: '分类', 
      dataIndex: 'type', 
      width: 100, 
      valueEnum: Object.fromEntries(newsTypes.map((t) => [t.value, t.label]))
    },
    { title: '浏览量', dataIndex: 'viewCount', width: 80, search: false },
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
      valueEnum: { 0: { text: '草稿', status: 'Default' }, 1: { text: '已发布', status: 'Success' } },
      render: (_, r) => (
        <Switch 
          checked={r.status === 1} 
          onChange={(checked) => handleStatusChange(r.id, checked ? 1 : 0)}
          checkedChildren="发布" 
          unCheckedChildren="草稿"
        />
      )
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

  return (
    <PageContainer>
      <ProTable<News>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增新闻
          </Button>
        ]}
        request={async (params) => {
          try {
            const { current, pageSize, type, status } = params;
            const result = await contentApi.getNewsList({
              type,
              status,
              page: current || 1,
              pageSize: pageSize || 10,
            });
            return { 
              data: result.data || [], 
              success: true, 
              total: result.total || 0 
            };
          } catch (error: any) {
            message.error(error.message || '获取数据失败');
            return { data: [], success: false, total: 0 };
          }
        }}
      />

      <ModalForm
        title={editingNews ? '编辑新闻' : '新增新闻'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        onFinish={handleSubmit}
        initialValues={editingNews ? {
          ...editingNews,
          isTop: Boolean(editingNews.isTop),
          status: editingNews.status === 1,
        } : { type: 1, isTop: false, status: true }}
        modalProps={{ destroyOnClose: true }}
        width={700}
      >
        <ProFormText name="title" label="标题" rules={[{ required: true }]} />
        <ProFormSelect name="type" label="分类" options={newsTypes} rules={[{ required: true }]} />
        <ProFormText name="coverImage" label="封面图片" placeholder="请输入图片URL" />
        <ProFormTextArea name="summary" label="摘要" fieldProps={{ rows: 2 }} />
        <ProFormTextArea name="content" label="内容" rules={[{ required: true }]} fieldProps={{ rows: 8 }} />
        <ProFormSwitch name="isTop" label="置顶" />
        <ProFormSwitch name="status" label="发布" initialValue={true} />
      </ModalForm>
    </PageContainer>
  );
};

export default NewsPage;
