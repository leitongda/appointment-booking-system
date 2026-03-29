import { FooterToolbar, PageContainer } from '@ant-design/pro-components';
import { SafetyCertificateOutlined, LayoutOutlined, ThunderboltOutlined, CarryOutOutlined } from '@ant-design/icons';
import { Card, App, Button, Space, Tree, Spin, Tag, Typography, Alert } from 'antd';
import './role-permissions.less';
import type { TreeDataNode, TreeProps } from 'antd';
import { useEffect, useState, useCallback } from 'react';
import { history, useParams } from '@umijs/max';
import { adminApi } from '@hospital/api';
import type { Role, Permission } from '@hospital/api';

const { Text } = Typography;

/**
 * 将权限列表转换为 Tree 组件需要的数据结构
 */
const convertToTreeData = (permissions: Permission[]): TreeDataNode[] => {
  return permissions.map((p) => ({
    key: p.code,
    title: (
      <div className={`permission-node node-type-${p.type}`}>
        <div className="node-left">
          <span className={`type-tag type-tag-${p.type}`}>
            {p.type === 'menu' ? '页面' : '按钮'}
          </span>
          <span className="node-title">{p.name}</span>
        </div>
        <div className="node-right">
          <span style={{ fontFamily: 'monospace' }}>{p.code}</span>
        </div>
      </div>
    ),
    // icon: p.type === 'menu' ? <LayoutOutlined style={{ color: '#1890ff' }} /> : <ThunderboltOutlined style={{ color: '#fa8c16' }} />,
    icon: p.type === 'menu' ? <LayoutOutlined style={{ color: '#1890ff' }} /> : <ThunderboltOutlined style={{ color: '#fa8c16' }} />,
    children: p.children && p.children.length > 0 ? convertToTreeData(p.children) : undefined,
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

/**
 * 将 checkedKeys 展开成包含所有选中节点的集合
 * checkStrictly=false 模式下，选中父节点时 checkedKeys 只包含父节点 key，不包含子节点
 */
const expandCheckedKeys = (permissions: Permission[], checkedKeys: string[]): Set<string> => {
  const checkedSet = new Set(checkedKeys);
  const result = new Set<string>();

  // 首先找出所有被选中的父节点
  const getParentKeys = (list: Permission[]): string[] => {
    const parents: string[] = [];
    const traverse = (nodes: Permission[]) => {
      nodes.forEach((p) => {
        if (checkedSet.has(p.code) && p.children && p.children.length > 0) {
          parents.push(p.code);
        }
        if (p.children && p.children.length > 0) {
          traverse(p.children);
        }
      });
    };
    traverse(list);
    return parents;
  };

  const parentKeys = getParentKeys(permissions);

  // 遍历所有节点，如果节点本身被选中或其祖先被选中，则加入结果
  const traverse = (list: Permission[], hasSelectedAncestor: boolean) => {
    list.forEach((p) => {
      const isThisNodeSelected = checkedSet.has(p.code);
      const shouldSelect = hasSelectedAncestor || isThisNodeSelected;

      if (shouldSelect) {
        result.add(p.code);
      }

      // 如果当前节点被选中且有子节点，子节点也有选中祖先
      const nextHasSelectedAncestor = shouldSelect;
      if (p.children && p.children.length > 0) {
        traverse(p.children, nextHasSelectedAncestor);
      }
    });
  };

  traverse(permissions, false);
  return result;
};

/**
 * 统计选中的叶子节点数量（实际权限数量）
 */
const countCheckedLeafKeys = (permissions: Permission[], checkedKeys: string[]): number => {
  const expandedChecked = expandCheckedKeys(permissions, checkedKeys);
  let count = 0;

  const traverse = (list: Permission[]) => {
    list.forEach((p) => {
      // 只统计叶子节点
      if (!p.children || p.children.length === 0) {
        if (expandedChecked.has(p.code)) {
          count++;
        }
      }
      if (p.children && p.children.length > 0) {
        traverse(p.children);
      }
    });
  };

  traverse(permissions);
  return count;
};

const RolePermissionsPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams();
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
      const data = await adminApi.getRole(id);
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
      history.push('/organization/system/role');
    } catch (error: any) {
      message.error(error.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const onCheck: TreeProps['onCheck'] = (checked) => {
    // checkStrictly=false 时，checked 是对象 { checked: string[], halfCheckedKeys: string[] }
    // checked.checked 包含所有被勾选的节点（包括自动勾选的子节点）
    const checkedKeysValue = Array.isArray(checked) ? checked : checked.checked;
    setCheckedKeys(checkedKeysValue as string[]);
  };

  // 计算实际选中的节点数量（checkStrictly=false 模式下，checkedKeys 已包含所有选中节点）
  const actualCheckedCount = checkedKeys.length;

  return (
    <PageContainer title={`分配权限 - ${role?.name || ''}`}>
      <Card
        loading={loading}
        bordered={false}
        extra={
          permissionsTree.length > 0 && (
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
          )
        }
      >
        {permissionsTree.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin tip="加载权限列表中..."><span /></Spin>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 16 }}>
              <Alert
                type="info"
                showIcon
                message={
                  <Space>
                    <span>已选择 <span style={{ fontWeight: 'bold', color: '#1890ff' }}>{countCheckedLeafKeys(permissionsTree, checkedKeys)}</span> 个权限</span>
                  </Space>
                }
              />
            </div>

            <div className="permission-tree-container">
              <Tree
                checkable
                showIcon
                showLine={{ showLeafIcon: false }}
                blockNode
                checkStrictly={false}
                checkedKeys={checkedKeys}
                expandedKeys={expandedKeys}
                onExpand={(keys) => setExpandedKeys(keys as string[])}
                onCheck={onCheck}
                treeData={convertToTreeData(permissionsTree)}
                height={600}
                itemHeight={36}
              />
            </div>

            <FooterToolbar>
              <Button onClick={() => history.push('/organization/system/role')}>取消</Button>
              <Button type="primary" loading={saving} onClick={handleSave}>
                保存权限
              </Button>
            </FooterToolbar>
          </>
        )}
      </Card>
    </PageContainer>
  );
};

export default RolePermissionsPage;

