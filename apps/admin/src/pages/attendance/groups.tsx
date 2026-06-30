import { PageContainer, ProTable, ProColumns } from '@ant-design/pro-components';
import { Tag, Drawer, App, Select, Button, Space, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { useState, useRef } from 'react';
import type { ActionType } from '@ant-design/pro-components';
import { attendanceApi, userManageApi } from '@hospital/api';
import type { AttendanceGroup, GroupMember } from '@hospital/api';
import { createListRequest } from '@/utils/proTable';
import { useListPage } from '@/hooks/useListPage';
import { CreateButton, OperationButton, OperationGroup } from '@/components/ListOperations';

/** 签到方式映射 */
const CHECK_METHOD_MAP: Record<string, { text: string; color: string }> = {
  gps: { text: 'GPS', color: 'blue' },
  wifi: { text: 'WiFi', color: 'cyan' },
  device: { text: '设备', color: 'purple' },
};

/**
 * 签到组管理列表页
 */
const GroupListPage: React.FC = () => {
  const { actionRef, message, handleDelete, reload } = useListPage({
    deleteFn: attendanceApi.deleteGroup,
  });

  // 成员管理 Drawer 状态
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [currentGroup, setCurrentGroup] = useState<AttendanceGroup | null>(null);
  const memberActionRef = useRef<ActionType>();
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([]);
  const [addingMembers, setAddingMembers] = useState(false);
  const [accountOptions, setAccountOptions] = useState<{ label: string; value: string }[]>([]);
  const [accountSearching, setAccountSearching] = useState(false);

  /** 打开成员管理 Drawer */
  const handleManageMembers = (record: AttendanceGroup) => {
    setCurrentGroup(record);
    setDrawerVisible(true);
    setSelectedAccountIds([]);
  };

  /** 搜索账号 */
  const handleSearchAccounts = async (keyword: string) => {
    if (!keyword || keyword.length < 2) return;
    setAccountSearching(true);
    try {
      const res = await userManageApi.getList({ keyword, page: 1, pageSize: 20 });
      const items = (res as any).items || (res as any).data || [];
      setAccountOptions(
        items.map((item: any) => ({
          label: `${item.name || item.username} (${item.username || item.phone || ''})`,
          value: item.id,
        }))
      );
    } catch {
      // 搜索失败静默处理
    } finally {
      setAccountSearching(false);
    }
  };

  /** 添加成员 */
  const handleAddMembers = async () => {
    if (!currentGroup || selectedAccountIds.length === 0) return;
    setAddingMembers(true);
    try {
      await attendanceApi.addGroupMembers(currentGroup.id, selectedAccountIds);
      message.success('添加成员成功');
      setSelectedAccountIds([]);
      memberActionRef.current?.reload();
      // 刷新主列表（成员数量变化）
      reload();
    } catch (error: any) {
      message.error(error.message || '添加成员失败');
    } finally {
      setAddingMembers(false);
    }
  };

  /** 移除成员 */
  const handleRemoveMember = async (accountId: string) => {
    if (!currentGroup) return;
    try {
      await attendanceApi.removeGroupMember(currentGroup.id, accountId);
      message.success('移除成员成功');
      memberActionRef.current?.reload();
      reload();
    } catch (error: any) {
      message.error(error.message || '移除成员失败');
    }
  };

  /** 成员列表列定义 */
  const memberColumns: ProColumns<GroupMember>[] = [
    {
      title: '成员姓名',
      dataIndex: 'accountName',
      width: 200,
      render: (_, record) => record.accountName || record.accountId,
    },
    {
      title: '添加时间',
      dataIndex: 'createdAt',
      width: 180,
      valueType: 'dateTime',
    },
    {
      title: '操作',
      valueType: 'option',
      width: 100,
      render: (_, record) => (
        <Popconfirm
          title="确认移除该成员？"
          onConfirm={() => handleRemoveMember(record.accountId)}
        >
          <a style={{ color: 'var(--color-error)' }}>
            <DeleteOutlined /> 移除
          </a>
        </Popconfirm>
      ),
    },
  ];

  /** 主表列定义 */
  const columns: ProColumns<AttendanceGroup>[] = [
    {
      title: '组名称',
      dataIndex: 'name',
      width: 200,
      fixed: 'left',
    },
    {
      title: '关键词',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '搜索签到组名称',
      },
      search: {
        transform: (value: string) => ({ keyword: value }),
      },
    },
    {
      title: '签到方式',
      dataIndex: 'checkMethod',
      width: 100,
      search: false,
      render: (_, record) => {
        const m = CHECK_METHOD_MAP[record.checkMethod] || { text: record.checkMethod, color: 'default' };
        return <Tag color={m.color}>{m.text}</Tag>;
      },
    },
    {
      title: '签到半径(米)',
      dataIndex: 'locationRadius',
      width: 120,
      search: false,
    },
    {
      title: '成员数',
      dataIndex: 'memberCount',
      width: 90,
      search: false,
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      width: 80,
      search: false,
      render: (_, record) => (
        <Tag color={record.enabled ? 'success' : 'default'}>
          {record.enabled ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      valueType: 'option',
      width: 220,
      fixed: 'right',
      render: (_, record) => (
        <OperationGroup>
          <OperationButton
            type="edit"
            url={`/attendance/groups/${record.id}/edit`}
          />
          <OperationButton
            type="custom"
            label="成员"
            onClick={() => handleManageMembers(record)}
          />
          <OperationButton
            type="delete"
            confirmText="确认删除"
            confirmDescription="删除后无法恢复，确定要删除吗？"
            onClick={() => handleDelete(record.id)}
          />
        </OperationGroup>
      ),
    },
  ];

  return (
    <PageContainer
      title="签到组管理"
      content="管理签到组及其成员，用于考勤签到的地理位置或设备验证"
    >
      <ProTable<AttendanceGroup>
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={createListRequest(attendanceApi.getGroupList)}
        columnsState={{
          persistenceKey: 'attendance-group-list-table',
          persistenceType: 'localStorage',
        }}
        search={{
          labelWidth: 'auto',
        }}
        options={{
          density: false,
          fullScreen: false,
          reload: true,
          setting: true,
        }}
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
        }}
        dateFormatter="string"
        headerTitle="签到组列表"
        toolBarRender={() => [
          <CreateButton
            key="create"
            url="/attendance/groups/create"
            label="新增签到组"
          />,
        ]}
      />

      {/* 成员管理 Drawer */}
      <Drawer
        title={`成员管理 - ${currentGroup?.name || ''}`}
        width={600}
        open={drawerVisible}
        onClose={() => {
          setDrawerVisible(false);
          setCurrentGroup(null);
          setSelectedAccountIds([]);
          setAccountOptions([]);
        }}
      >
        {currentGroup && (
          <>
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Select
                  mode="multiple"
                  placeholder="搜索并选择账号添加成员"
                  showSearch
                  filterOption={false}
                  onSearch={handleSearchAccounts}
                  options={accountOptions}
                  loading={accountSearching}
                  value={selectedAccountIds}
                  onChange={setSelectedAccountIds}
                  style={{ minWidth: 350 }}
                />
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleAddMembers}
                  loading={addingMembers}
                  disabled={selectedAccountIds.length === 0}
                >
                  添加
                </Button>
              </Space>
            </div>

            <ProTable<GroupMember>
              actionRef={memberActionRef}
              rowKey="id"
              columns={memberColumns}
              request={createListRequest((params) =>
                attendanceApi.getGroupMembers(currentGroup.id, params)
              )}
              search={false}
              options={false}
              pagination={{
                defaultPageSize: 10,
                showSizeChanger: true,
              }}
              dateFormatter="string"
              headerTitle="成员列表"
            />
          </>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default GroupListPage;
