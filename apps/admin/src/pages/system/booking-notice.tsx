import { useState, useRef } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { Button, Space, Tag, Switch, Modal, App, Form, Input, Select, InputNumber } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { bookingNoticeApi } from '@hospital/api';
import type { BookingNotice } from '@hospital/api';

const { TextArea } = Input;

// 类型选项
const TYPE_OPTIONS = [
  { label: '预约须知', value: 'BOOKING' },
  { label: '就诊须知', value: 'VISIT' },
  { label: '退号须知', value: 'REFUND' },
];

const TYPE_COLOR_MAP: Record<string, string> = {
  BOOKING: 'blue',
  VISIT: 'green',
  REFUND: 'orange',
};

const BookingNoticePage = () => {
  const { message } = App.useApp();
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();
  const [modalVisible, setModalVisible] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // 打开新增/编辑弹窗
  const handleOpenModal = (record?: BookingNotice) => {
    if (record) {
      setEditingId(record.id);
      form.setFieldsValue({
        type: record.type,
        title: record.title,
        content: record.content,
        sortOrder: record.sortOrder,
        status: record.status,
      });
    } else {
      setEditingId(null);
      form.resetFields();
      form.setFieldsValue({ status: 1, sortOrder: 0 });
    }
    setModalVisible(true);
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setModalLoading(true);

      if (editingId) {
        await bookingNoticeApi.update(editingId, values);
        message.success('更新成功');
      } else {
        await bookingNoticeApi.create(values);
        message.success('创建成功');
      }

      setModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      if (error.errorFields) return; // 表单验证错误
      message.error(error.message || '操作失败');
    } finally {
      setModalLoading(false);
    }
  };

  // 删除
  const handleDelete = async (id: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这条预约须知吗？',
      onOk: async () => {
        try {
          await bookingNoticeApi.delete(id);
          message.success('删除成功');
          actionRef.current?.reload();
        } catch (error: any) {
          message.error(error.message || '删除失败');
        }
      },
    });
  };

  // 切换状态
  const handleStatusChange = async (id: string, checked: boolean) => {
    try {
      await bookingNoticeApi.updateStatus(id, checked ? 1 : 0);
      message.success('状态更新成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '状态更新失败');
    }
  };

  const columns: ProColumns<BookingNotice>[] = [
    {
      title: '类型',
      dataIndex: 'type',
      valueType: 'select',
      fieldProps: {
        options: TYPE_OPTIONS,
      },
      render: (_, record) => {
        const option = TYPE_OPTIONS.find(o => o.value === record.type);
        return <Tag color={TYPE_COLOR_MAP[record.type]}>{option?.label || record.type}</Tag>;
      },
    },
    {
      title: '标题',
      dataIndex: 'title',
      ellipsis: true,
    },
    {
      title: '内容',
      dataIndex: 'content',
      ellipsis: true,
      width: 300,
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
      valueType: 'select',
      fieldProps: {
        options: [
          { label: '启用', value: 1 },
          { label: '禁用', value: 0 },
        ],
      },
      render: (_, record) => (
        <Switch
          checked={record.status === 1}
          onChange={(checked) => handleStatusChange(record.id, checked)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      valueType: 'dateTime',
      search: false,
      width: 180,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<BookingNotice>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, type, status } = params;
          const result = await bookingNoticeApi.getList({
            type,
            status,
            page: current,
            pageSize,
          });
          return {
            data: result.data,
            total: result.total,
            success: true,
          };
        }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleOpenModal()}
          >
            新增须知
          </Button>,
        ]}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
        }}
      />

      <Modal
        title={editingId ? '编辑预约须知' : '新增预约须知'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        confirmLoading={modalLoading}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="type"
            label="类型"
            rules={[{ required: true, message: '请选择类型' }]}
          >
            <Select options={TYPE_OPTIONS} placeholder="请选择类型" />
          </Form.Item>
          <Form.Item
            name="title"
            label="标题"
          >
            <Input placeholder="请输入标题（可选）" maxLength={100} />
          </Form.Item>
          <Form.Item
            name="content"
            label="内容"
            rules={[{ required: true, message: '请输入内容' }]}
          >
            <TextArea
              rows={4}
              placeholder="请输入须知内容"
              showCount
              maxLength={1000}
            />
          </Form.Item>
          <Form.Item name="sortOrder" label="排序" extra="数字越小越靠前">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select
              options={[
                { label: '启用', value: 1 },
                { label: '禁用', value: 0 },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default BookingNoticePage;

