import { PageContainer } from '@ant-design/pro-components';
import { SafetyCertificateOutlined } from '@ant-design/icons';
import { Card, App, Button, Space, Tree, Spin } from 'antd';
import type { TreeDataNode, TreeProps } from 'antd';
import { useEffect, useState, useCallback } from 'react';
import { history, useParams } from '@umijs/max';
import { adminApi } from '@hospital/api';
import type { Role, Permission } from '@hospital/api';

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

const RolePermissionsPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [role, setRole] = useState<Role | null>(null);
  const [permissionsTree, setPermissionsTree] = useState<Permission[]>([]);
  const [checkedKeys, setCheckedKeys] = useState<string[]>([]);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);

  useEffect(() => {
    if (id) {
      loadRole();
      loadPermissionsTree();
    }
  }, [id]);

  const loadRole = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await adminApi.getRoleDetail(id);
      setRole(data);
      setCheckedKeys(data.permissions || []);
    } catch (error: any) {
      message.error('加载角色信息失败');
    } finally {
      setLoading(false);
    }
  };

  const loadPermissionsTree = useCallback(async () => {
    try {
      const tree = await adminApi.getPermissionsTree();
      setPermissionsTree(tree);
      setExpandedKeys(getAllKeys(tree));
    } catch (error: any) {
      message.error(error.message || '加载权限列表失败');
    }
  }, [message]);

  const handleSave = async () => {
    if (!id) return;
    setSaving(true);
    try {
      await adminApi.updateRolePermissions(id, checkedKeys);
      message.success('权限保存成功');
      history.push('/system/role');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const onCheck: TreeProps['onCheck'] = (checked) => {
    const checkedKeysValue = Array.isArray(checked) ? checked : checked.checked;
    setCheckedKeys(checkedKeysValue as string[]);
  };

  return (
    <PageContainer title={`分配权限 - ${role?.name || ''}`}>
      <Card loading={loading}>
        {permissionsTree.length === 0 ? (
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
              height={500}
            />
            <div style={{ marginTop: 16, marginBottom: 24, color: '#999' }}>
              已选择 {checkedKeys.length} 个权限
            </div>
            <div style={{ textAlign: 'center' }}>
              <Space>
                <Button onClick={() => history.push('/system/role')}>取消</Button>
                <Button type="primary" loading={saving} onClick={handleSave}>
                  保存权限
                </Button>
              </Space>
            </div>
          </>
        )}
      </Card>
    </PageContainer>
  );
};

export default RolePermissionsPage;

