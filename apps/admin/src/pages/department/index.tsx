import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect, ProFormSwitch } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, TreeSelect } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';
import { departmentApi } from '@hospital/api';
import type { Department, DepartmentTreeNode } from '@hospital/shared';

const DepartmentPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [editingDept, setEditingDept] = useState<Department | null>(null);
  const [treeData, setTreeData] = useState<DepartmentTreeNode[]>([]);

  const loadTreeData = async () => {
    try {
      const data = await departmentApi.getTree();
      setTreeData(data);
    } catch (error) {
      console.error('加载科室树失败', error);
    }
  };

  const handleAdd = () => {
    setEditingDept(null);
    loadTreeData();
    setModalVisible(true);
  };

  const handleEdit = (record: Department) => {
    setEditingDept(record);
    loadTreeData();
    setModalVisible(true);
  };

  const handleDelete = async (id: string) => {
    try {
      await departmentApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingDept) {
        await departmentApi.update(editingDept.id, values);
        message.success('更新成功');
      } else {
        await departmentApi.create(values);
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

  const convertToTreeSelect = (nodes: DepartmentTreeNode[]): any[] => {
    return nodes.map((node) => ({
      value: node.id,
      title: node.name,
      children: node.children ? convertToTreeSelect(node.children) : [],
    }));
  };

  const columns: ProColumns<Department>[] = [
    { title: '科室名称', dataIndex: 'name', width: 200 },
    { title: '描述', dataIndex: 'description', width: 300, ellipsis: true, search: false },
    { title: '排序', dataIndex: 'sortOrder', width: 80, search: false },
    { 
      title: '热门', 
      dataIndex: 'isHot', 
      width: 80, 
      search: false,
      render: (_, r) => r.isHot ? <Tag color="red">是</Tag> : <Tag>否</Tag>
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 80,
      valueEnum: { 0: { text: '禁用', status: 'Default' }, 1: { text: '启用', status: 'Success' } }
    },
    { title: '创建时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { 
      title: '操作', 
      valueType: 'option',
      width: 150,
      render: (_, record) => (
        <Space>
          <a onClick={() => handleEdit(record)}>编辑</a>
          <Popconfirm title="确定删除该科室吗？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: 'red' }}>删除</a>
          </Popconfirm>
        </Space>
      )
    },
  ];

  return (
    <PageContainer>
      <ProTable<Department>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增科室
          </Button>
        ]}
        request={async (params) => {
          const { current, pageSize, name, status } = params;
          const result = await departmentApi.getList({ name, status, page: current, pageSize });
          return { data: result.data, success: true, total: result.total };
        }}
      />

      <ModalForm
        title={editingDept ? '编辑科室' : '新增科室'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        onFinish={handleSubmit}
        initialValues={editingDept || { sortOrder: 0, isHot: 0, status: 1 }}
        modalProps={{ destroyOnClose: true }}
      >
        <ProFormText name="name" label="科室名称" rules={[{ required: true, message: '请输入科室名称' }]} />
        <ProFormSelect
          name="parentId"
          label="上级科室"
          fieldProps={{
            allowClear: true,
            placeholder: '无上级科室',
            treeData: convertToTreeSelect(treeData),
            showSearch: true,
            treeNodeFilterProp: 'title',
          }}
          valueEnum={{}}
          request={async () => {
            const data = await departmentApi.getTree();
            return convertToTreeSelect(data);
          }}
        />
        <ProFormTextArea name="description" label="描述" fieldProps={{ rows: 3 }} />
        <ProFormDigit name="sortOrder" label="排序" min={0} max={999} fieldProps={{ precision: 0 }} />
        <ProFormSwitch name="isHot" label="热门科室" checkedChildren="是" unCheckedChildren="否" />
        <ProFormSwitch name="status" label="状态" checkedChildren="启用" unCheckedChildren="禁用" initialValue={true} />
      </ModalForm>
    </PageContainer>
  );
};

export default DepartmentPage;
