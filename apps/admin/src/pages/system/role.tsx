import { PlusOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormText, ProFormTextArea, ProFormSwitch } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Tag, Modal, Tree, Spin } from 'antd';
import type { TreeDataNode, TreeProps } from 'antd';
import { useRef, useState, useEffect, useCallback } from 'react';
import { adminApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Role, Permission } from '@hospital/api';
import { useAccess } from '@umijs/max';

/**
 * 将权限列表转换为 Tree 组件需要的数据结构
 */
const convertToTreeData = (permissions: Permission[]): TreeDataNode[] => {
  return permissions.map((p) => ({
    key: p.code,
    title: p.name,
    icon: p.type === 'menu' ? <SafetyCertificateOutlined /> : null,
    children: p.children ? convertToTreeData(p.children) : undefined,
  }));
};

/**
 * 获取所有叶子节点的 key
 */
const getAllLeafKeys = (permissions: Permission[]): string[] => {
  const keys: string[] = [];
  const traverse = (list: Permission[]) => {
    list.forEach((p) => {
      if (p.children && p.children.length > 0) {
        traverse(p.children);
      } else {
        keys.push(p.code);
      }
    });
  };
  traverse(permissions);
  return keys;
};

/**
 * 获取所有节点的 key
 */
const getAllKeys = (permissions: Permission[]): string[] => {
  const keys: string[] = [];
  const traverse = (list: Permission[]) => {
    list.forEach((p) => {
      keys.push(p.code);
      if (p.children && p.children.length > 0) {
        traverse(p.children);
      }
    });
  };
  traverse(permissions);
  return keys;
};

const RolePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Role | null>(null);
  
  // 权限分配相关状态
  const [permissionModalOpen, setPermissionModalOpen] = useState(false);
  const [currentRole, setCurrentRole] = useState<Role | null>(null);
  const [permissionsTree, setPermissionsTree] = useState<Permission[]>([]);
  const [checkedKeys, setCheckedKeys] = useState<string[]>([]);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [loadingPermissions, setLoadingPermissions] = useState(false);
  const [savingPermissions, setSavingPermissions] = useState(false);

  // 加载权限树
  const loadPermissionsTree = useCallback(async () => {
    setLoadingPermissions(true);
    try {
      const tree = await adminApi.getPermissionsTree();
      setPermissionsTree(tree);
      // 默认展开所有节点
      setExpandedKeys(getAllKeys(tree));
    } catch (error: any) {
      message.error(error.message || '加载权限列表失败');
    } finally {
      setLoadingPermissions(false);
    }
  }, [message]);

  // 打开权限分配弹窗
  const handleOpenPermissionModal = async (record: Role) => {
    setCurrentRole(record);
    setCheckedKeys(record.permissions || []);
    setPermissionModalOpen(true);
    
    // 如果还没加载过权限树，则加载
    if (permissionsTree.length === 0) {
      await loadPermissionsTree();
    }
  };

  // 保存权限
  const handleSavePermissions = async () => {
    if (!currentRole) return;
    
    setSavingPermissions(true);
    try {
      await adminApi.updateRolePermissions(currentRole.id, checkedKeys);
      message.success('权限保存成功');
      setPermissionModalOpen(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '保存失败');
    } finally {
      setSavingPermissions(false);
    }
  };

  // 树选中变化
  const onCheck: TreeProps['onCheck'] = (checked, info) => {
    // checked 包含所有选中的节点（包括半选状态的父节点不在这里）
    const checkedKeysValue = Array.isArray(checked) ? checked : checked.checked;
    setCheckedKeys(checkedKeysValue as string[]);
  };

  const handleDelete = async (id: string) => {
    try {
      await adminApi.deleteRole(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const data = { ...values, status: values.status ? 1 : 0 };
      if (editingRecord) {
        await adminApi.updateRole(editingRecord.id, data);
        message.success('更新成功');
      } else {
        await adminApi.createRole(data);
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

  const columns: ProColumns<Role>[] = [
    { title: '角色名称', dataIndex: 'name', width: 150 },
    { title: '角色编码', dataIndex: 'code', width: 120 },
    { title: '描述', dataIndex: 'description', ellipsis: true, search: false },
    {
      title: '权限数量',
      dataIndex: 'permissions',
      width: 100,
      search: false,
      render: (_, record) => (
        <Tag color="blue">{record.permissions?.length || 0} 个权限</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: { 1: { text: '启用', status: 'Success' }, 0: { text: '禁用', status: 'Default' } },
    },
    { title: '创建时间', dataIndex: 'createdAt', valueType: 'dateTime', width: 160, search: false },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      render: (_, record) => (
        <Space>
          {access.hasPermission('system:role:permission') && record.code !== 'SUPER_ADMIN' && (
            <a onClick={() => handleOpenPermissionModal(record)}>
              <SafetyCertificateOutlined /> 分配权限
            </a>
          )}
          {access.hasPermission('system:role:update') && (
            <a onClick={() => { setEditingRecord(record); setModalOpen(true); }}>编辑</a>
          )}
          {access.hasPermission('system:role:delete') && record.code !== 'SUPER_ADMIN' && (
            <Popconfirm title="确定删除该角色吗？" onConfirm={() => handleDelete(record.id)}>
              <a style={{ color: '#ff4d4f' }}>删除</a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Role>
        headerTitle="角色列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await adminApi.getRoles({ ...rest, page: current, pageSize }));
        }}
        toolBarRender={() => [
          access.hasPermission('system:role:create') && (
            <Button key="add" type="primary" icon={<PlusOutlined />} onClick={() => { setEditingRecord(null); setModalOpen(true); }}>
              新增角色
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      {/* 新增/编辑角色弹窗 */}
      <ModalForm
        title={editingRecord ? '编辑角色' : '新增角色'}
        open={modalOpen}
        onOpenChange={setModalOpen}
        onFinish={handleSubmit}
        initialValues={editingRecord ? { ...editingRecord, status: editingRecord.status === 1 } : { status: true }}
        modalProps={{ destroyOnClose: true }}
      >
        <ProFormText name="name" label="角色名称" rules={[{ required: true }]} />
        <ProFormText name="code" label="角色编码" rules={[{ required: true }]} disabled={!!editingRecord} />
        <ProFormTextArea name="description" label="描述" />
        <ProFormSwitch name="status" label="启用状态" />
      </ModalForm>

      {/* 权限分配弹窗 */}
      <Modal
        title={`分配权限 - ${currentRole?.name || ''}`}
        open={permissionModalOpen}
        onCancel={() => setPermissionModalOpen(false)}
        onOk={handleSavePermissions}
        confirmLoading={savingPermissions}
        width={600}
        styles={{ body: { maxHeight: '60vh', overflow: 'auto' } }}
      >
        {loadingPermissions ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin tip="加载权限列表中..." />
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button 
                  size="small" 
                  onClick={() => setExpandedKeys(getAllKeys(permissionsTree))}
                >
                  展开全部
                </Button>
                <Button 
                  size="small" 
                  onClick={() => setExpandedKeys([])}
                >
                  收起全部
                </Button>
                <Button 
                  size="small" 
                  type="primary"
                  onClick={() => setCheckedKeys(getAllLeafKeys(permissionsTree))}
                >
                  全选
                </Button>
                <Button 
                  size="small" 
                  onClick={() => setCheckedKeys([])}
                >
                  清空
                </Button>
              </Space>
            </div>
            <Tree
              checkable
              checkStrictly={false}
              checkedKeys={checkedKeys}
              expandedKeys={expandedKeys}
              onExpand={(keys) => setExpandedKeys(keys as string[])}
              onCheck={onCheck}
              treeData={convertToTreeData(permissionsTree)}
              height={400}
            />
            <div style={{ marginTop: 16, color: '#999' }}>
              已选择 {checkedKeys.length} 个权限
            </div>
          </>
        )}
      </Modal>
    </PageContainer>
  );
};

export default RolePage;
