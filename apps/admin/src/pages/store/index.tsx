import { PlusOutlined, ApartmentOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Avatar, Modal, Tree, Spin, Empty } from 'antd';
import type { TreeDataNode, TreeProps } from 'antd';
import { useRef, useState, useCallback } from 'react';
import { history, useAccess } from '@umijs/max';
import { storeApi, departmentApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Store, DepartmentTreeNode } from '@hospital/shared';

// 将科室树转换为 Antd Tree 数据格式
const convertToTreeData = (nodes: DepartmentTreeNode[]): TreeDataNode[] => {
  return nodes.map((node) => ({
    key: node.id,
    title: node.name,
    children: node.children?.length ? convertToTreeData(node.children) : undefined,
  }));
};

// 获取树中所有节点的 key
const getAllKeys = (nodes: DepartmentTreeNode[]): string[] => {
  const keys: string[] = [];
  const traverse = (items: DepartmentTreeNode[]) => {
    items.forEach((item) => {
      keys.push(item.id);
      if (item.children?.length) {
        traverse(item.children);
      }
    });
  };
  traverse(nodes);
  return keys;
};

const StorePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  
  // 科室绑定弹窗状态
  const [bindModalVisible, setBindModalVisible] = useState(false);
  const [bindingStore, setBindingStore] = useState<Store | null>(null);
  const [treeData, setTreeData] = useState<TreeDataNode[]>([]);
  const [checkedKeys, setCheckedKeys] = useState<string[]>([]);
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleDelete = async (id: string) => {
    try {
      await storeApi.delete(id);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '删除失败');
    }
  };

  // 打开绑定科室弹窗
  const handleOpenBindModal = useCallback(async (store: Store) => {
    setBindingStore(store);
    setBindModalVisible(true);
    setLoading(true);
    
    try {
      // 并行获取科室树和已绑定的科室
      const [tree, boundDepartments] = await Promise.all([
        departmentApi.getTree(),
        storeApi.getDepartments(store.id),
      ]);
      
      const treeNodes = convertToTreeData(tree || []);
      setTreeData(treeNodes);
      setExpandedKeys(getAllKeys(tree || []));
      
      // 设置已绑定的科室为选中状态
      const boundIds = (boundDepartments || []).map((d) => d.id);
      setCheckedKeys(boundIds);
    } catch (error: any) {
      message.error('加载科室数据失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [message]);

  // 处理树节点选中变化
  const handleCheck: TreeProps['onCheck'] = (checked) => {
    const keys = Array.isArray(checked) ? checked : checked.checked;
    setCheckedKeys(keys as string[]);
  };

  // 提交绑定
  const handleBindSubmit = async () => {
    if (!bindingStore) return;
    
    setSubmitting(true);
    try {
      await storeApi.batchBindDepartments(bindingStore.id, checkedKeys);
      message.success('绑定成功');
      setBindModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '绑定失败');
    } finally {
      setSubmitting(false);
    }
  };

  // 关闭弹窗
  const handleCloseBindModal = () => {
    setBindModalVisible(false);
    setBindingStore(null);
    setTreeData([]);
    setCheckedKeys([]);
    setExpandedKeys([]);
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
      width: 180,
      render: (_, record) => (
        <Space>
          {access.hasPermission('store:update') && (
            <a onClick={() => handleOpenBindModal(record)}>
              <ApartmentOutlined /> 科室
            </a>
          )}
          {access.hasPermission('store:update') && (
            <a onClick={() => history.push(`/store/${record.id}/edit`)}>编辑</a>
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
            <Button
              key="add"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => history.push('/store/create')}
            >
              新增门店
            </Button>
          ),
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      {/* 科室绑定弹窗 */}
      <Modal
        title={`绑定科室 - ${bindingStore?.name || ''}`}
        open={bindModalVisible}
        onCancel={handleCloseBindModal}
        onOk={handleBindSubmit}
        confirmLoading={submitting}
        okText="确定"
        cancelText="取消"
        width={500}
        destroyOnClose
      >
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin tip="加载中..." />
          </div>
        ) : treeData.length === 0 ? (
          <Empty description="暂无科室数据" />
        ) : (
          <div style={{ maxHeight: 400, overflow: 'auto', border: '1px solid #f0f0f0', borderRadius: 6, padding: 12 }}>
            <Tree
              checkable
              checkStrictly
              treeData={treeData}
              checkedKeys={checkedKeys}
              expandedKeys={expandedKeys}
              onExpand={(keys) => setExpandedKeys(keys as string[])}
              onCheck={handleCheck}
              selectable={false}
            />
          </div>
        )}
      </Modal>
    </PageContainer>
  );
};

export default StorePage;
