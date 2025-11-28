import { 
  PageContainer, 
  ProTable, 
  ModalForm, 
  ProFormText, 
  ProFormTextArea, 
  ProFormDigit, 
  ProFormSelect,
  ProFormTimePicker,
  ProDescriptions
} from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Drawer, Table, Modal, Select } from 'antd';
import { PlusOutlined, ShopOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { storeApi, departmentApi } from '@hospital/api';
import type { Store, StoreDepartment, Department } from '@hospital/shared';

const StorePage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingStore, setEditingStore] = useState<Store | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [currentStore, setCurrentStore] = useState<Store | null>(null);
  const [storeDepartments, setStoreDepartments] = useState<StoreDepartment[]>([]);
  const [deptModalVisible, setDeptModalVisible] = useState(false);
  const [departments, setDepartments] = useState<Department[]>([]);

  const handleAdd = () => {
    setEditingStore(null);
    setModalVisible(true);
  };

  const handleEdit = (record: Store) => {
    setEditingStore(record);
    setModalVisible(true);
  };

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
      const data = {
        ...values,
        openingTime: values.openingTime?.format?.('HH:mm:ss') || values.openingTime,
        closingTime: values.closingTime?.format?.('HH:mm:ss') || values.closingTime,
      };
      
      if (editingStore) {
        await storeApi.update(editingStore.id, data);
        message.success('更新成功');
      } else {
        await storeApi.create(data);
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

  const handleViewDetail = async (record: Store) => {
    setCurrentStore(record);
    setDetailVisible(true);
    // 加载门店科室
    try {
      const depts = await storeApi.getDepartments(record.id);
      setStoreDepartments(depts);
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

  const handleStatusChange = async (id: string, status: number) => {
    try {
      await storeApi.updateStatus(id, status);
      message.success('状态更新成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleAddDepartment = async () => {
    // 加载科室列表
    try {
      const result = await departmentApi.getList({ status: 1, pageSize: 100 });
      setDepartments(result.data);
      setDeptModalVisible(true);
    } catch (error) {
      message.error('加载科室列表失败');
    }
  };

  const handleDeptSubmit = async (values: any) => {
    if (!currentStore) return;
    try {
      await storeApi.addDepartment(currentStore.id, values.departmentId, values.floor, values.room);
      message.success('添加成功');
      setDeptModalVisible(false);
      // 刷新科室列表
      const depts = await storeApi.getDepartments(currentStore.id);
      setStoreDepartments(depts);
    } catch (error: any) {
      message.error(error.message || '添加失败');
    }
  };

  const handleRemoveDepartment = async (relationId: string) => {
    try {
      await storeApi.removeDepartment(relationId);
      message.success('移除成功');
      if (currentStore) {
        const depts = await storeApi.getDepartments(currentStore.id);
        setStoreDepartments(depts);
      }
    } catch (error: any) {
      message.error(error.message || '移除失败');
    }
  };

  const columns: ProColumns<Store>[] = [
    { title: '门店名称', dataIndex: 'name', width: 150 },
    { title: '门店编码', dataIndex: 'code', width: 100 },
    { title: '地址', dataIndex: 'address', width: 200, ellipsis: true, search: false },
    { title: '联系电话', dataIndex: 'phone', width: 120, search: false },
    { 
      title: '科室数', 
      dataIndex: 'departmentCount', 
      width: 80, 
      search: false,
      render: (_, r) => <Tag color="blue">{r.departmentCount || 0}</Tag>
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 80,
      valueEnum: { 
        0: { text: '停业', status: 'Default' }, 
        1: { text: '营业', status: 'Success' } 
      }
    },
    { title: '创建时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { 
      title: '操作', 
      valueType: 'option',
      width: 200,
      render: (_, record) => (
        <Space>
          <a onClick={() => handleViewDetail(record)}>详情</a>
          <a onClick={() => handleEdit(record)}>编辑</a>
          {record.status === 1 ? (
            <Popconfirm title="确定停业该门店吗？" onConfirm={() => handleStatusChange(record.id, 0)}>
              <a style={{ color: 'orange' }}>停业</a>
            </Popconfirm>
          ) : (
            <a onClick={() => handleStatusChange(record.id, 1)} style={{ color: 'green' }}>营业</a>
          )}
          <Popconfirm title="确定删除该门店吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      )
    },
  ];

  const deptColumns = [
    { title: '科室名称', dataIndex: 'departmentName', key: 'departmentName' },
    { title: '楼层', dataIndex: 'floor', key: 'floor' },
    { title: '诊室', dataIndex: 'room', key: 'room' },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: number) => status === 1 ? <Tag color="green">正常</Tag> : <Tag>停诊</Tag>
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: StoreDepartment) => (
        <Popconfirm title="确定移除该科室吗？" onConfirm={() => handleRemoveDepartment(record.id)}>
          <a style={{ color: 'red' }}>移除</a>
        </Popconfirm>
      )
    }
  ];

  return (
    <PageContainer>
      <ProTable<Store>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增门店
          </Button>
        ]}
        request={async (params) => {
          const { current, pageSize, name, code, status } = params;
          const result = await storeApi.getList({ 
            keyword: name || code, 
            status, 
            page: current, 
            pageSize 
          });
          return { data: result.data, success: true, total: result.total };
        }}
      />

      {/* 新增/编辑弹窗 */}
      <ModalForm
        title={editingStore ? '编辑门店' : '新增门店'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        onFinish={handleSubmit}
        initialValues={editingStore || { sortOrder: 0, status: 1, workingDays: '1,2,3,4,5,6,7' }}
        modalProps={{ destroyOnClose: true }}
        width={600}
      >
        <ProFormText 
          name="name" 
          label="门店名称" 
          rules={[{ required: true, message: '请输入门店名称' }]} 
        />
        <ProFormText name="code" label="门店编码" placeholder="可选，用于唯一标识" />
        <Space style={{ display: 'flex' }}>
          <ProFormText name="province" label="省份" width="sm" />
          <ProFormText name="city" label="城市" width="sm" />
          <ProFormText name="district" label="区县" width="sm" />
        </Space>
        <ProFormText name="address" label="详细地址" />
        <Space style={{ display: 'flex' }}>
          <ProFormText name="phone" label="联系电话" width="md" />
          <ProFormText name="contactPerson" label="联系人" width="md" />
        </Space>
        <Space style={{ display: 'flex' }}>
          <ProFormTimePicker name="openingTime" label="营业开始" width="sm" />
          <ProFormTimePicker name="closingTime" label="营业结束" width="sm" />
        </Space>
        <ProFormText name="workingDays" label="工作日" placeholder="1,2,3,4,5,6,7 表示周一到周日" />
        <ProFormTextArea name="description" label="门店简介" fieldProps={{ rows: 3 }} />
        <Space style={{ display: 'flex' }}>
          <ProFormDigit name="sortOrder" label="排序" min={0} max={999} fieldProps={{ precision: 0 }} />
          <ProFormSelect 
            name="status" 
            label="状态" 
            options={[
              { label: '营业', value: 1 },
              { label: '停业', value: 0 },
            ]} 
          />
        </Space>
      </ModalForm>

      {/* 详情抽屉 */}
      <Drawer
        title={<><ShopOutlined /> 门店详情</>}
        width={600}
        open={detailVisible}
        onClose={() => setDetailVisible(false)}
      >
        {currentStore && (
          <>
            <ProDescriptions column={2}>
              <ProDescriptions.Item label="门店名称">{currentStore.name}</ProDescriptions.Item>
              <ProDescriptions.Item label="门店编码">{currentStore.code || '-'}</ProDescriptions.Item>
              <ProDescriptions.Item label="联系电话">{currentStore.phone || '-'}</ProDescriptions.Item>
              <ProDescriptions.Item label="联系人">{currentStore.contactPerson || '-'}</ProDescriptions.Item>
              <ProDescriptions.Item label="地址" span={2}>
                {[currentStore.province, currentStore.city, currentStore.district, currentStore.address]
                  .filter(Boolean).join(' ') || '-'}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="营业时间">
                {currentStore.openingTime && currentStore.closingTime 
                  ? `${currentStore.openingTime} - ${currentStore.closingTime}` 
                  : '-'}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="状态">
                {currentStore.status === 1 ? <Tag color="green">营业</Tag> : <Tag>停业</Tag>}
              </ProDescriptions.Item>
              <ProDescriptions.Item label="简介" span={2}>
                {currentStore.description || '-'}
              </ProDescriptions.Item>
            </ProDescriptions>

            <div style={{ marginTop: 24 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
                <h4>关联科室</h4>
                <Button type="primary" size="small" icon={<PlusOutlined />} onClick={handleAddDepartment}>
                  添加科室
                </Button>
              </div>
              <Table 
                dataSource={storeDepartments} 
                columns={deptColumns} 
                rowKey="id" 
                size="small"
                pagination={false}
              />
            </div>
          </>
        )}
      </Drawer>

      {/* 添加科室弹窗 */}
      <ModalForm
        title="添加科室"
        open={deptModalVisible}
        onOpenChange={setDeptModalVisible}
        onFinish={handleDeptSubmit}
        modalProps={{ destroyOnClose: true }}
        width={400}
      >
        <ProFormSelect
          name="departmentId"
          label="选择科室"
          rules={[{ required: true, message: '请选择科室' }]}
          options={departments.map(d => ({ label: d.name, value: d.id }))}
          fieldProps={{ showSearch: true, optionFilterProp: 'label' }}
        />
        <ProFormText name="floor" label="楼层" placeholder="如：3F" />
        <ProFormText name="room" label="诊室" placeholder="如：301室" />
      </ModalForm>
    </PageContainer>
  );
};

export default StorePage;
