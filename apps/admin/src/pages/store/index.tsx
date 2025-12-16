import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSwitch, ProFormSelect, ProForm } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Avatar, Form } from 'antd';
import { useRef, useState } from 'react';
import { useAccess } from '@umijs/max';
import { storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Store } from '@hospital/shared';
import { ProFormRegionSelector } from '@hospital/shared';
import ImageUpload from '@/components/ImageUpload';

// 风格选项
const THEME_STYLE_OPTIONS = [
  { label: '中医-红', value: '中医-红' },
  { label: '中医-绿', value: '中医-绿' },
  { label: '现代-蓝', value: '现代-蓝' },
  { label: '简约-白', value: '简约-白' },
];

const StorePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
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
      // 处理地区数据：将region数组转换为province/city/district字段
      const { region, ...rest } = values;
      const [province, city, district] = region || [];
      const data = {
        ...rest,
        province,
        city,
        district,
        status: values.status ? 1 : 0
      };

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
    {
      title: 'Logo',
      dataIndex: 'logo',
      width: 60,
      search: false,
      render: (_, record) => record.logo ? <Avatar src={record.logo} size={40} /> : '-',
    },
    { title: '门店名称', dataIndex: 'name', ellipsis: true },
    { title: '门店编码', dataIndex: 'code', width: 100, search: false },
    { title: '城市', dataIndex: 'city', width: 80 },
    { title: '地址', dataIndex: 'address', ellipsis: true, search: false },
    { title: '联系电话', dataIndex: 'phone', width: 120, search: false },
    { title: '风格', dataIndex: 'themeStyle', width: 80, search: false },
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
          {access.hasPermission('store:update') && (
            <a onClick={() => { setEditingRecord(record); setModalOpen(true); }}>编辑</a>
          )}
          {access.hasPermission('store:delete') && (
            <Popconfirm title="确定删除该门店吗？" onConfirm={() => handleDelete(record.id)}>
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
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
          access.hasPermission('store:create') && (
            <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRecord(null); setModalOpen(true); }}>
              新增门店
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title={editingRecord ? '编辑门店' : '新增门店'}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        initialValues={editingRecord ? {
          ...editingRecord,
          region: [editingRecord.province, editingRecord.city, editingRecord.district].filter(Boolean),
          status: editingRecord.status === 1
        } : { status: true, sortOrder: 0, themeStyle: '中医-红' }}
        modalProps={{ destroyOnHidden: true }}
        width={800}
      >
        {/* 基础信息 */}
        <ProForm.Group title="基础信息">
          <ProFormText
            name="name"
            label="门店名称"
            width="md"
            rules={[{ required: true, message: '请输入门店名称' }]}
            placeholder="如：朴泽堂中医馆"
          />
          <ProFormText.Password
            name="password"
            label="门店密码"
            width="md"
            placeholder="请输入门店密码"
          />
        </ProForm.Group>
        <ProForm.Group>
          <ProFormText
            name="phone"
            label="联系方式"
            width="md"
            placeholder="如：18984332758"
            rules={[{ pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号' }]}
          />
          <ProFormText
            name="email"
            label="邮箱"
            width="md"
            placeholder="如：2544600916@qq.com"
            rules={[{ type: 'email', message: '请输入正确的邮箱地址' }]}
          />
        </ProForm.Group>

        {/* 地址信息 */}
        <ProForm.Group title="地址信息">
          <ProFormRegionSelector
            name="region"
            label="所在地区"
            width="md"
            placeholder="请选择省/市/区"
          />
        </ProForm.Group>
        <ProFormTextArea
          name="address"
          label="门店地址"
          placeholder="如：贵州省贵阳市观山湖区金阳街道碧海南路与林城路西南侧国电新时代大楼1层7号"
          fieldProps={{ rows: 2 }}
        />
        <ProForm.Group>
          <ProFormText
            name="longitude"
            label="经度"
            width="sm"
            placeholder="如：106.619922"
          />
          <ProFormText
            name="latitude"
            label="纬度"
            width="sm"
            placeholder="如：26.644479"
          />
        </ProForm.Group>

        {/* 展示设置 */}
        <ProForm.Group title="展示设置">
          <ProFormDigit
            name="sortOrder"
            label="排序"
            width="xs"
            min={0}
            fieldProps={{ precision: 0 }}
            tooltip="数字越大越靠前"
          />
          <ProFormSelect
            name="themeStyle"
            label="风格选择"
            width="sm"
            options={THEME_STYLE_OPTIONS}
            placeholder="请选择风格"
          />
        </ProForm.Group>
        <Form.Item
          name="logo"
          label="Logo"
          tooltip="1:1比例，推荐尺寸：160px × 160px"
        >
          <ImageUpload
            aspectRatio="1:1"
            folder="store"
            placeholder="上传Logo"
            width={120}
            height={120}
          />
        </Form.Item>

        {/* 营业设置 */}
        <ProForm.Group title="营业设置">
          <ProFormText
            name="openingTime"
            label="开始营业时间"
            width="sm"
            placeholder="如：08:00"
          />
          <ProFormText
            name="closingTime"
            label="结束营业时间"
            width="sm"
            placeholder="如：18:00"
          />
          <ProFormSwitch name="status" label="营业状态" />
        </ProForm.Group>

        {/* 其他信息 */}
        <ProForm.Group title="其他信息">
          <ProFormText name="code" label="门店编码" width="md" />
          <ProFormText name="contactPerson" label="联系人" width="md" />
        </ProForm.Group>
        <ProFormTextArea
          name="description"
          label="门店简介"
          placeholder="请输入门店简介"
          fieldProps={{ rows: 3 }}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default StorePage;
