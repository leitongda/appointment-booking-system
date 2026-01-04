import { PlusOutlined, ApartmentOutlined, UserOutlined, MoneyCollectOutlined, QrcodeOutlined, ClockCircleOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Button, App, Popconfirm, Space, Avatar, Modal, Tree, Spin, Empty, Transfer, Tag, QRCode } from 'antd';
import type { TreeDataNode, TreeProps, TransferProps } from 'antd';
import { useRef, useState, useCallback } from 'react';
import { history, useAccess } from '@umijs/max';
import { storeApi, departmentApi, adminApi, dataApi } from '@hospital/api';
import type { StoreAdmin } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Store, DepartmentTreeNode } from '@hospital/shared';
import ImportExport from '@/components/ImportExport';

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

interface AdminItem {
  key: string;
  title: string;
  description: string;
  disabled?: boolean;
}

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

  // 用户绑定弹窗状态
  const [userBindModalVisible, setUserBindModalVisible] = useState(false);
  const [userBindingStore, setUserBindingStore] = useState<Store | null>(null);
  const [allAdmins, setAllAdmins] = useState<AdminItem[]>([]);
  const [selectedAdminKeys, setSelectedAdminKeys] = useState<string[]>([]);
  const [userLoading, setUserLoading] = useState(false);
  const [userSubmitting, setUserSubmitting] = useState(false);

  // 签到二维码弹窗状态
  const [qrcodeModalVisible, setQrcodeModalVisible] = useState(false);
  const [qrcodeStore, setQrcodeStore] = useState<Store | null>(null);
  const [qrcodeContent, setQrcodeContent] = useState<string>('');

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

  // 提交绑定科室
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

  // 关闭科室弹窗
  const handleCloseBindModal = () => {
    setBindModalVisible(false);
    setBindingStore(null);
    setTreeData([]);
    setCheckedKeys([]);
    setExpandedKeys([]);
  };

  // 打开用户绑定弹窗
  const handleOpenUserBindModal = useCallback(async (store: Store) => {
    setUserBindingStore(store);
    setUserBindModalVisible(true);
    setUserLoading(true);
    
    try {
      // 并行获取所有用户和已绑定的用户
      const [adminsResult, boundAdmins] = await Promise.all([
        adminApi.getAdmins({ pageSize: 100, status: 1 }),
        storeApi.getAdmins(store.id),
      ]);
      
      // 转换为 Transfer 数据格式
      const adminItems: AdminItem[] = (adminsResult.data ?? []).map((admin) => ({
        key: admin.id,
        title: admin.name || admin.username,
        description: admin.phone || admin.email || '',
      }));
      setAllAdmins(adminItems);
      
      // 设置已绑定的用户为选中状态
      const boundIds = (boundAdmins || []).map((a) => a.id);
      setSelectedAdminKeys(boundIds);
    } catch (error: any) {
      message.error('加载用户数据失败');
      console.error(error);
    } finally {
      setUserLoading(false);
    }
  }, [message]);

  // 处理用户选择变化
  const handleUserChange: TransferProps['onChange'] = (targetKeys) => {
    setSelectedAdminKeys(targetKeys as string[]);
  };

  // 提交用户绑定
  const handleUserBindSubmit = async () => {
    if (!userBindingStore) return;
    
    setUserSubmitting(true);
    try {
      await storeApi.batchBindAdmins(userBindingStore.id, selectedAdminKeys);
      message.success('分配成功');
      setUserBindModalVisible(false);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '分配失败');
    } finally {
      setUserSubmitting(false);
    }
  };

  // 关闭用户弹窗
  const handleCloseUserBindModal = () => {
    setUserBindModalVisible(false);
    setUserBindingStore(null);
    setAllAdmins([]);
    setSelectedAdminKeys([]);
  };

  // Transfer 过滤搜索
  const filterOption = (inputValue: string, option: AdminItem) =>
    option.title.indexOf(inputValue) > -1 || option.description.indexOf(inputValue) > -1;

  // 打开签到二维码弹窗
  const handleOpenQrcodeModal = async (store: Store) => {
    setQrcodeStore(store);
    setQrcodeModalVisible(true);
    
    try {
      const result = await storeApi.getCheckinQrcode(store.id);
      setQrcodeContent(result.qrcodeContent);
    } catch (error: any) {
      message.error(error.message || '获取二维码失败');
    }
  };

  // 关闭签到二维码弹窗
  const handleCloseQrcodeModal = () => {
    setQrcodeModalVisible(false);
    setQrcodeStore(null);
    setQrcodeContent('');
  };

  // 下载二维码
  const handleDownloadQrcode = () => {
    const canvas = document.querySelector('#store-checkin-qrcode canvas') as HTMLCanvasElement;
    if (canvas) {
      const link = document.createElement('a');
      link.download = `签到二维码-${qrcodeStore?.name || '门店'}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  };

  const columns: ProColumns<Store>[] = [
    {
      title: 'Logo',
      dataIndex: 'logo',
      width: 64,
      search: false,
      render: (_, record) => record.logo ? <Avatar src={record.logo} size={40} /> : '-',
    },
    { title: '门店名称', dataIndex: 'name', width: 140, ellipsis: true },
    { title: '门店编码', dataIndex: 'code', width: 100, search: false },
    { title: '城市', dataIndex: 'city', width: 80, search: false },
    { title: '地址', dataIndex: 'address', width: 180, ellipsis: true, search: false },
    { title: '联系电话', dataIndex: 'phone', width: 120, search: false },
    { title: '风格', dataIndex: 'themeStyle', width: 70, search: false },
    {
      title: '状态',
      dataIndex: 'status',
      width: 70,
      search: false,
      valueEnum: { 1: { text: '营业', status: 'Success' }, 0: { text: '停业', status: 'Default' } },
    },
    {
      title: '操作',
      valueType: 'option',
      width: 360,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4} wrap>
          {access.hasPermission('store:update') && (
            <a onClick={() => handleOpenBindModal(record)}>
              <ApartmentOutlined /> 科室
            </a>
          )}
          {access.hasPermission('store:update') && (
            <a onClick={() => history.push(`/store/${record.id}/fee-templates`)}>
              <MoneyCollectOutlined /> 诊费
            </a>
          )}
          {access.hasPermission('store:update') && (
            <a onClick={() => history.push(`/store/${record.id}/visit-type-config`)}>
              <ClockCircleOutlined /> 复诊
            </a>
          )}
          {access.hasPermission('store:read') && (
            <a onClick={() => handleOpenQrcodeModal(record)}>
              <QrcodeOutlined /> 签到
            </a>
          )}
          {access.canSuperAdmin && (
            <a onClick={() => handleOpenUserBindModal(record)}>
              <UserOutlined /> 用户
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
        scroll={{ x: 1200 }}
        request={async (params) => {
          const { current, pageSize, name, ...rest } = params;
          return toProTableResult(await storeApi.getList({ ...rest, keyword: name, page: current, pageSize }));
        }}
        toolBarRender={() => [
          <ImportExport
            key="import-export"
            moduleName="门店"
            exportUrl={dataApi.getExportStoresUrl()}
            importUrl={dataApi.getImportStoresUrl()}
            templateUrl={dataApi.getStoreTemplateUrl()}
            onImportSuccess={() => actionRef.current?.reload()}
          />,
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

      {/* 用户绑定弹窗 */}
      <Modal
        title={`分配用户 - ${userBindingStore?.name || ''}`}
        open={userBindModalVisible}
        onCancel={handleCloseUserBindModal}
        onOk={handleUserBindSubmit}
        confirmLoading={userSubmitting}
        okText="确定"
        cancelText="取消"
        width={700}
        destroyOnClose
      >
        {userLoading ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin tip="加载中..." />
          </div>
        ) : allAdmins.length === 0 ? (
          <Empty description="暂无用户数据" />
        ) : (
          <div>
            <div style={{ marginBottom: 12 }}>
              <Tag color="blue">已选择 {selectedAdminKeys.length} 个用户</Tag>
            </div>
            <Transfer
              dataSource={allAdmins}
              targetKeys={selectedAdminKeys}
              onChange={handleUserChange}
              filterOption={filterOption}
              showSearch
              listStyle={{
                width: 280,
                height: 350,
              }}
              titles={['可选用户', '已分配用户']}
              render={(item) => (
                <span>
                  {item.title}
                  {item.description && (
                    <span style={{ color: '#999', marginLeft: 8, fontSize: 12 }}>
                      {item.description}
                    </span>
                  )}
                </span>
              )}
            />
          </div>
        )}
      </Modal>

      {/* 签到二维码弹窗 */}
      <Modal
        title={`签到二维码 - ${qrcodeStore?.name || ''}`}
        open={qrcodeModalVisible}
        onCancel={handleCloseQrcodeModal}
        footer={[
          <Button key="close" onClick={handleCloseQrcodeModal}>
            关闭
          </Button>,
          <Button key="download" type="primary" onClick={handleDownloadQrcode}>
            下载二维码
          </Button>,
        ]}
        width={400}
        destroyOnClose
      >
        <div style={{ textAlign: 'center', padding: '24px 0' }} id="store-checkin-qrcode">
          {qrcodeContent ? (
            <>
              <QRCode
                value={qrcodeContent}
                size={256}
                style={{ margin: '0 auto' }}
              />
              <div style={{ marginTop: 16, color: '#666' }}>
                请使用微信扫描此二维码进行签到
              </div>
              <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
                二维码内容: {qrcodeContent}
              </div>
            </>
          ) : (
            <Spin tip="加载中..." />
          )}
        </div>
      </Modal>
    </PageContainer>
  );
};

export default StorePage;
