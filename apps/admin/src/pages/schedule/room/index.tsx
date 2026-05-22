import { useState, useRef, useEffect } from 'react';
import { PageContainer } from '@ant-design/pro-components';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { Button, Space, Switch, Modal, message, Form, Input, Select, InputNumber, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { scheduleApi, departmentApi, storeApi } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';

const { TextArea } = Input;

interface RoomRecord {
  id: string;
  name: string;
  storeId: string;
  storeName?: string;
  roomNumber?: string;
  floor?: string;
  departmentId?: string;
  departmentName?: string;
  capacity: number;
  status: number;
  remark?: string;
  createdAt: string;
  updatedAt: string;
}

interface StoreOption {
  label: string;
  value: string;
}

interface DepartmentOption {
  label: string;
  value: string;
}

const ScheduleRoomPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [form] = Form.useForm();
  const [modalVisible, setModalVisible] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [storeOptions, setStoreOptions] = useState<StoreOption[]>([]);
  const [departmentOptions, setDepartmentOptions] = useState<DepartmentOption[]>([]);

  // 加载门店和科室选项
  const loadOptions = async () => {
    try {
      const [stores, departments] = await Promise.all([
        storeApi.getAll(),
        departmentApi.getAll(),
      ]);
      setStoreOptions(stores.map((s: any) => ({ label: s.name, value: s.id })));
      setDepartmentOptions(departments.map((d: any) => ({ label: d.name, value: d.id })));
    } catch {
      // 忽略加载失败
    }
  };

  useEffect(() => {
    loadOptions();
  }, []);

  // 打开新增/编辑弹窗
  const handleOpenModal = (record?: RoomRecord) => {
    if (record) {
      setEditingId(record.id);
      form.setFieldsValue({
        name: record.name,
        storeId: record.storeId,
        roomNumber: record.roomNumber,
        floor: record.floor,
        departmentId: record.departmentId,
        capacity: record.capacity,
        status: record.status,
        remark: record.remark,
      });
    } else {
      setEditingId(null);
      form.resetFields();
      form.setFieldsValue({ status: 1, capacity: 1 });
    }
    setModalVisible(true);
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setModalLoading(true);

      if (editingId) {
        await scheduleApi.updateRoom(editingId, values);
        message.success('更新成功');
      } else {
        await scheduleApi.createRoom(values);
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
    try {
      await scheduleApi.deleteRoom(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  // 切换状态
  const handleStatusChange = async (id: string, checked: boolean) => {
    try {
      await scheduleApi.updateRoom(id, { status: checked ? 1 : 0 });
      message.success('状态更新成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '状态更新失败');
    }
  };

  const columns: ProColumns<RoomRecord>[] = [
    {
      title: '诊室名称',
      dataIndex: 'name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '房间号',
      dataIndex: 'roomNumber',
      width: 100,
      ellipsis: true,
      search: false,
    },
    {
      title: '楼层',
      dataIndex: 'floor',
      width: 80,
      search: false,
    },
    {
      title: '所属门店',
      dataIndex: 'storeName',
      width: 120,
      ellipsis: true,
      search: false,
    },
    {
      title: '所属科室',
      dataIndex: 'departmentName',
      width: 120,
      ellipsis: true,
      search: false,
      render: (_, record) => record.departmentName || '-',
    },
    {
      title: '容量',
      dataIndex: 'capacity',
      width: 70,
      search: false,
      align: 'center',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
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
      title: '备注',
      dataIndex: 'remark',
      ellipsis: true,
      width: 150,
      search: false,
      render: (_, record) => record.remark || '-',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 120,
      fixed: 'right',
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
          <Popconfirm
            title="确认删除"
            description="确定要删除该诊室吗？删除后无法恢复。"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<RoomRecord>
        headerTitle="诊室管理"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(scheduleApi.getRoomList)}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleOpenModal()}
          >
            新增诊室
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
        scroll={{ x: 1100 }}
      />

      <Modal
        title={editingId ? '编辑诊室' : '新增诊室'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        confirmLoading={modalLoading}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="诊室名称"
            rules={[{ required: true, message: '请输入诊室名称' }]}
          >
            <Input placeholder="请输入诊室名称" maxLength={100} />
          </Form.Item>
          <Form.Item
            name="storeId"
            label="所属门店"
            rules={[{ required: true, message: '请选择所属门店' }]}
          >
            <Select
              placeholder="请选择所属门店"
              options={storeOptions}
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name="roomNumber" label="房间号">
            <Input placeholder="请输入房间号" maxLength={50} />
          </Form.Item>
          <Form.Item name="floor" label="楼层">
            <Input placeholder="请输入楼层" maxLength={20} />
          </Form.Item>
          <Form.Item name="departmentId" label="所属科室">
            <Select
              placeholder="请选择所属科室（可选）"
              options={departmentOptions}
              allowClear
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name="capacity" label="容量" extra="该诊室可同时容纳的就诊人数">
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select
              options={[
                { label: '启用', value: 1 },
                { label: '禁用', value: 0 },
              ]}
            />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <TextArea
              rows={3}
              placeholder="请输入备注（可选）"
              showCount
              maxLength={500}
            />
          </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default ScheduleRoomPage;
