import { PlusOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Modal, Form, Input, InputNumber, Switch } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { history, useParams } from '@umijs/max';
import { consultationFeeTypeApi, storeApi } from '@hospital/api';
import type { ConsultationFeeType, ConsultationFeeTypeCreate, Store } from '@hospital/shared';
import { createListRequest } from '@/utils/proTable';

const StoreFeeTypesPage: React.FC = () => {
  const { message } = App.useApp();
  const { storeId } = useParams();
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [store, setStore] = useState<Store | null>(null);

  const loadStore = async () => {
    try {
      const data = await storeApi.getDetail(storeId!);
      setStore(data);
    } catch (error: any) {
      message.error('加载门店信息失败');
    }
  };

  useEffect(() => {
    if (storeId) {
      loadStore();
    }
  }, [storeId]);

  const handleDelete = async (id: string) => {
    try {
      await consultationFeeTypeApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleAdd = () => {
    form.resetFields();
    setEditingId(null);
    setModalVisible(true);
  };

  const handleEdit = (record: ConsultationFeeType) => {
    if (record.isGlobal) {
      message.warning('全局类型不能编辑，请到配置中心 - 诊费类型中修改');
      return;
    }
    form.setFieldsValue({
      name: record.name,
      code: record.code,
      description: record.description,
      sortOrder: record.sortOrder,
      status: record.status === 1,
    });
    setEditingId(record.id);
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);

      const data: ConsultationFeeTypeCreate = {
        storeId: storeId,
        name: values.name,
        code: values.code,
        description: values.description,
        sortOrder: values.sortOrder || 0,
        status: values.status ? 1 : 0,
      };

      if (editingId) {
        await consultationFeeTypeApi.update(editingId, data);
        message.success('更新成功');
      } else {
        await consultationFeeTypeApi.create(data);
        message.success('创建成功');
      }

      setModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    } finally {
      setSubmitting(false);
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
      title: '类型',
      dataIndex: 'isGlobal',
      width: 100,
      search: false,
      render: (_, record) => (
        record.isGlobal ? (
          <Tag color="blue">全局</Tag>
        ) : (
          <Tag color="green">门店专属</Tag>
        )
      ),
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
      search: false,
      render: (_, record) => (
        <Tag color={record.status === 1 ? 'success' : 'default'}>
          {record.status === 1 ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => (
        <Space>
          {!record.isGlobal && (
            <>
              <a onClick={() => handleEdit(record)}>编辑</a>
              <Popconfirm
                title="确定要删除此诊费类型吗？"
                onConfirm={() => handleDelete(record.id)}
              >
                <a style={{ color: 'var(--color-error)' }}>删除</a>
              </Popconfirm>
            </>
          )}
          {record.isGlobal && (
            <span style={{ color: 'var(--color-text-tertiary)' }}>全局类型</span>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer
      header={{
        title: `${store?.name || '门店'} - 诊费类型管理`,
        breadcrumb: {
          items: [
            { title: '门店管理' },
            { title: '门店列表', href: '/organization/store/list' },
            { title: '诊费类型' },
          ],
        },
      }}
      extra={
        <Button icon={<ArrowLeftOutlined />} onClick={() => history.push('/organization/store/list')}>
          返回门店列表
        </Button>
      }
    >
      <ProTable<ConsultationFeeType>
        actionRef={actionRef}
        columns={columns}
        rowKey="id"
        search={false}
        request={createListRequest(() => consultationFeeTypeApi.getList({ storeId, includeGlobal: true }))}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleAdd}
          >
            新增门店专属类型
          </Button>,
          <Button
            key="templates"
            onClick={() => history.push(`/organization/store/${storeId}/fee-templates`)}
          >
            配置诊费模板
          </Button>,
        ]}
        pagination={false}
      />

      <Modal
        title={editingId ? '编辑诊费类型' : '新增门店专属诊费类型'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        confirmLoading={submitting}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ status: true, sortOrder: 0 }}
        >
          <Form.Item
            name="name"
            label="类型名称"
            rules={[{ required: true, message: '请输入类型名称' }]}
          >
            <Input placeholder="请输入类型名称" maxLength={50} />
          </Form.Item>
          <Form.Item
            name="code"
            label="类型编码"
            rules={[{ max: 50, message: '编码最多50个字符' }]}
          >
            <Input placeholder="请输入类型编码（可选）" maxLength={50} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="请输入描述（可选）" maxLength={255} rows={3} />
          </Form.Item>
          <Form.Item name="sortOrder" label="排序">
            <InputNumber min={0} placeholder="排序值" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default StoreFeeTypesPage;

