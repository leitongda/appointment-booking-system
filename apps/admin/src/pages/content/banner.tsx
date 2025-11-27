import { PageContainer, ProTable, ModalForm, ProFormText, ProFormDigit, ProFormSwitch, ProFormSelect } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Image, Switch } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { contentApi } from '@hospital/api';

interface BannerRecord {
  id: string;
  title: string;
  imageUrl: string;
  linkType: number;
  linkUrl: string;
  position: string;
  sortOrder: number;
  status: number;
  createdAt: string;
}

const linkTypes = [
  { label: '无跳转', value: 0 },
  { label: '内部页面', value: 1 },
  { label: '外部链接', value: 2 },
  { label: '新闻详情', value: 3 },
];

const positions = [
  { label: '首页轮播', value: 'home' },
  { label: '科室页面', value: 'department' },
  { label: '个人中心', value: 'profile' },
];

const BannerPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingBanner, setEditingBanner] = useState<BannerRecord | null>(null);

  const handleAdd = () => {
    setEditingBanner(null);
    setModalVisible(true);
  };

  const handleEdit = (record: BannerRecord) => {
    setEditingBanner(record);
    setModalVisible(true);
  };

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
      const submitData = {
        ...values,
        status: values.status ? 1 : 0,
      };

      if (editingBanner) {
        await contentApi.updateBanner(editingBanner.id, submitData);
        message.success('更新成功');
      } else {
        await contentApi.createBanner(submitData);
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
      await contentApi.updateBanner(id, { status });
      message.success(status === 1 ? '已启用' : '已禁用');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<BannerRecord>[] = [
    { 
      title: '图片', 
      dataIndex: 'imageUrl', 
      width: 160, 
      search: false, 
      render: (_, r) => <Image width={140} height={60} src={r.imageUrl} style={{ objectFit: 'cover', borderRadius: 4 }} /> 
    },
    { title: '标题', dataIndex: 'title', width: 200 },
    { 
      title: '位置', 
      dataIndex: 'position', 
      width: 100,
      valueEnum: Object.fromEntries(positions.map((p) => [p.value, p.label]))
    },
    { 
      title: '跳转类型', 
      dataIndex: 'linkType', 
      width: 100, 
      search: false,
      valueEnum: Object.fromEntries(linkTypes.map((t) => [t.value, t.label]))
    },
    { title: '排序', dataIndex: 'sortOrder', width: 80, search: false },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100,
      valueEnum: { 0: { text: '禁用' }, 1: { text: '启用', status: 'Success' } },
      render: (_, r) => (
        <Switch 
          checked={r.status === 1} 
          onChange={(checked) => handleStatusChange(r.id, checked ? 1 : 0)}
          checkedChildren="启用" 
          unCheckedChildren="禁用"
        />
      )
    },
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

  const mockData: BannerRecord[] = [
    { id: '1', title: '欢迎使用预约挂号系统', imageUrl: 'https://via.placeholder.com/750x300', linkType: 0, linkUrl: '', position: 'home', sortOrder: 1, status: 1, createdAt: '2024-11-27' },
    { id: '2', title: '健康体检套餐优惠', imageUrl: 'https://via.placeholder.com/750x300', linkType: 2, linkUrl: 'https://example.com', position: 'home', sortOrder: 2, status: 1, createdAt: '2024-11-26' },
  ];

  return (
    <PageContainer>
      <ProTable<BannerRecord>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增轮播图
          </Button>
        ]}
        request={async () => ({ data: mockData, success: true, total: mockData.length })}
      />

      <ModalForm
        title={editingBanner ? '编辑轮播图' : '新增轮播图'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        onFinish={handleSubmit}
        initialValues={editingBanner || { linkType: 0, position: 'home', sortOrder: 0, status: true }}
        modalProps={{ destroyOnClose: true }}
        width={600}
      >
        <ProFormText name="title" label="标题" rules={[{ required: true }]} />
        <ProFormText name="imageUrl" label="图片URL" rules={[{ required: true }]} placeholder="请输入图片URL，建议尺寸 750x300" />
        <ProFormSelect name="position" label="展示位置" options={positions} rules={[{ required: true }]} />
        <ProFormSelect name="linkType" label="跳转类型" options={linkTypes} />
        <ProFormText name="linkUrl" label="跳转链接" placeholder="跳转类型为无跳转时可不填" />
        <ProFormDigit name="sortOrder" label="排序" min={0} max={999} tooltip="数字越小越靠前" />
        <ProFormSwitch name="status" label="状态" checkedChildren="启用" unCheckedChildren="禁用" initialValue={true} />
      </ModalForm>
    </PageContainer>
  );
};

export default BannerPage;
