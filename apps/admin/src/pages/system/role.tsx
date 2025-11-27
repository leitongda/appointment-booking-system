import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSwitch } from '@ant-design/pro-components';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, Tag, Space, message, Popconfirm, Modal, Tree, Checkbox } from 'antd';
import { PlusOutlined, SettingOutlined } from '@ant-design/icons';
import { useRef, useState } from 'react';

interface RoleRecord {
  id: string;
  name: string;
  code: string;
  description: string;
  status: number;
  createdAt: string;
}

// 菜单权限树
const menuTree = [
  {
    title: '工作台',
    key: 'dashboard',
    children: [],
  },
  {
    title: '科室管理',
    key: 'department',
    children: [
      { title: '科室列表', key: 'department:list' },
      { title: '新增科室', key: 'department:create' },
      { title: '编辑科室', key: 'department:update' },
      { title: '删除科室', key: 'department:delete' },
    ],
  },
  {
    title: '医生管理',
    key: 'doctor',
    children: [
      { title: '医生列表', key: 'doctor:list' },
      { title: '新增医生', key: 'doctor:create' },
      { title: '编辑医生', key: 'doctor:update' },
      { title: '删除医生', key: 'doctor:delete' },
    ],
  },
  {
    title: '排班管理',
    key: 'schedule',
    children: [
      { title: '排班列表', key: 'schedule:list' },
      { title: '新增排班', key: 'schedule:create' },
      { title: '停诊操作', key: 'schedule:suspend' },
    ],
  },
  {
    title: '预约管理',
    key: 'appointment',
    children: [
      { title: '预约列表', key: 'appointment:list' },
      { title: '预约详情', key: 'appointment:detail' },
    ],
  },
  {
    title: '患者管理',
    key: 'patient',
    children: [
      { title: '患者列表', key: 'patient:list' },
      { title: '黑名单管理', key: 'patient:blacklist' },
    ],
  },
  {
    title: '内容管理',
    key: 'content',
    children: [
      { title: '新闻管理', key: 'content:news' },
      { title: '公告管理', key: 'content:notice' },
      { title: '轮播图管理', key: 'content:banner' },
    ],
  },
  {
    title: '系统管理',
    key: 'system',
    children: [
      { title: '角色管理', key: 'system:role' },
      { title: '管理员管理', key: 'system:admin' },
      { title: '系统设置', key: 'system:settings' },
      { title: '操作日志', key: 'system:log' },
    ],
  },
];

const RolePage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState(false);
  const [permissionVisible, setPermissionVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleRecord | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);
  const [checkedKeys, setCheckedKeys] = useState<string[]>([]);

  const handleAdd = () => {
    setEditingRole(null);
    setModalVisible(true);
  };

  const handleEdit = (record: RoleRecord) => {
    setEditingRole(record);
    setModalVisible(true);
  };

  const handlePermission = (record: RoleRecord) => {
    setEditingRole(record);
    // 加载角色已有权限
    setCheckedKeys(['dashboard', 'department:list', 'doctor:list']);
    setPermissionVisible(true);
  };

  const handleDelete = async (id: string) => {
    message.success('删除成功');
    actionRef.current?.reload();
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingRole) {
        message.success('更新成功');
      } else {
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

  const handlePermissionSave = () => {
    console.log('保存权限:', checkedKeys);
    message.success('权限配置成功');
    setPermissionVisible(false);
  };

  const columns: ProColumns<RoleRecord>[] = [
    { title: '角色名称', dataIndex: 'name', width: 150 },
    { title: '角色编码', dataIndex: 'code', width: 150 },
    { title: '描述', dataIndex: 'description', width: 250, search: false, ellipsis: true },
    { 
      title: '状态', 
      dataIndex: 'status', 
      width: 100, 
      valueEnum: { 0: { text: '禁用' }, 1: { text: '启用', status: 'Success' } } 
    },
    { title: '创建时间', dataIndex: 'createdAt', width: 180, valueType: 'dateTime', search: false },
    { 
      title: '操作', 
      valueType: 'option', 
      width: 200, 
      render: (_, record) => (
        <Space>
          <a onClick={() => handlePermission(record)}><SettingOutlined /> 权限</a>
          <a onClick={() => handleEdit(record)}>编辑</a>
          {record.code !== 'super_admin' && (
            <Popconfirm title="确定删除吗？" onConfirm={() => handleDelete(record.id)}>
              <a style={{ color: 'red' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      )
    },
  ];

  const mockData: RoleRecord[] = [
    { id: '1', name: '超级管理员', code: 'super_admin', description: '拥有所有权限', status: 1, createdAt: '2024-01-01 00:00:00' },
    { id: '2', name: '科室管理员', code: 'dept_admin', description: '负责科室和医生管理', status: 1, createdAt: '2024-11-01 10:00:00' },
    { id: '3', name: '内容管理员', code: 'content_admin', description: '负责新闻公告管理', status: 1, createdAt: '2024-11-15 14:00:00' },
  ];

  return (
    <PageContainer>
      <ProTable<RoleRecord>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        toolBarRender={() => [
          <Button key="add" type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            新增角色
          </Button>
        ]}
        request={async () => ({ data: mockData, success: true, total: mockData.length })}
      />

      <ModalForm
        title={editingRole ? '编辑角色' : '新增角色'}
        open={modalVisible}
        onOpenChange={setModalVisible}
        onFinish={handleSubmit}
        initialValues={editingRole || { status: true }}
        modalProps={{ destroyOnClose: true }}
      >
        <ProFormText name="name" label="角色名称" rules={[{ required: true }]} />
        <ProFormText name="code" label="角色编码" rules={[{ required: true }]} disabled={!!editingRole} tooltip="创建后不可修改" />
        <ProFormTextArea name="description" label="描述" fieldProps={{ rows: 2 }} />
        <ProFormSwitch name="status" label="状态" checkedChildren="启用" unCheckedChildren="禁用" initialValue={true} />
      </ModalForm>

      <Modal
        title={`权限配置 - ${editingRole?.name}`}
        open={permissionVisible}
        onCancel={() => setPermissionVisible(false)}
        onOk={handlePermissionSave}
        width={600}
      >
        <Tree
          checkable
          defaultExpandAll
          checkedKeys={checkedKeys}
          onCheck={(keys) => setCheckedKeys(keys as string[])}
          treeData={menuTree}
        />
      </Modal>
    </PageContainer>
  );
};

export default RolePage;
