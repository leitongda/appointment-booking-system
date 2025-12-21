import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { App, Space, Tag, Popconfirm } from 'antd';
import { useRef } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { appointmentApi, storeApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import type { Appointment } from '@hospital/shared';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待签到', color: 'gold' },
  1: { text: '已签到', color: 'blue' },
  2: { text: '叫号中', color: 'processing' },
  3: { text: '就诊中', color: 'cyan' },
  4: { text: '已完成', color: 'green' },
  5: { text: '已取消', color: 'default' },
  6: { text: '已爽约', color: 'red' },
  7: { text: '已过号', color: 'orange' },
};

const AppointmentListPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  
  const { initialState } = useModel('@@initialState');
  const { currentUser, currentStore } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  // 多门店管理员也可以看到门店筛选
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;

  const handleCancel = async (id: string) => {
    try {
      await appointmentApi.cancel(id, '管理员取消');
      message.success('取消成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const handleMarkNoShow = async (id: string) => {
    try {
      await appointmentApi.markNoShow(id);
      message.success('标记成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ProColumns<Appointment>[] = [
    // 超级管理员和多门店管理员可以按门店筛选
    ...(showStoreFilter ? [{
      title: '门店',
      dataIndex: 'storeId',
      hideInTable: true,
      valueType: 'select',
      request: async () => {
        try {
          const stores = await storeApi.getAll();
          let storeList = stores ?? [];
          // 非超管只显示其关联的门店
          if (!isSuperAdmin && currentUser?.storeIds?.length) {
            storeList = storeList.filter((s: any) => currentUser.storeIds?.includes(s.id));
          }
          return [
            { label: '全部门店', value: '' },
            ...storeList.map((s: any) => ({ label: s.name, value: s.id })),
          ];
        } catch {
          return [];
        }
      },
    } as ProColumns<Appointment>] : []),
    {
      title: '预约编号',
      dataIndex: 'appointmentNo',
      width: 140,
      copyable: true,
    },
    {
      title: '患者',
      dataIndex: 'patientName',
      width: 80,
    },
    {
      title: '手机号',
      dataIndex: 'patientPhone',
      width: 120,
      search: false,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 80,
    },
    {
      title: '科室',
      dataIndex: 'departmentName',
      width: 100,
      search: false,
    },
    {
      title: '预约日期',
      dataIndex: 'scheduleDate',
      width: 110,
      valueType: 'date',
    },
    {
      title: '时段',
      dataIndex: 'timeSlot',
      width: 70,
      valueEnum: {
        morning: '上午',
        afternoon: '下午',
        evening: '晚上',
      },
    },
    {
      title: '排队号',
      dataIndex: 'queueNumber',
      width: 70,
      search: false,
      render: (val) => val || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      valueType: 'select',
      valueEnum: Object.fromEntries(
        Object.entries(STATUS_MAP).map(([k, v]) => [k, { text: v.text }])
      ),
      render: (_, record) => {
        const status = STATUS_MAP[record.status] || { text: '未知', color: 'default' };
        return <Tag color={status.color}>{status.text}</Tag>;
      },
    },
    {
      title: '预约时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 150,
      render: (_, record) => (
        <Space>
          {access.hasPermission('appointment:detail') && (
            <a onClick={() => history.push(`/appointment/${record.id}`)}>详情</a>
          )}
          {record.status === 0 && (
            <>
              {access.hasPermission('appointment:cancel') && (
                <Popconfirm title="确定取消该预约吗？" onConfirm={() => handleCancel(record.id)}>
                  <a style={{ color: '#ff4d4f' }}>取消</a>
                </Popconfirm>
              )}
              {access.hasPermission('appointment:update') && (
                <Popconfirm title="确定标记为爽约吗？" onConfirm={() => handleMarkNoShow(record.id)}>
                  <a style={{ color: '#fa8c16' }}>爽约</a>
                </Popconfirm>
              )}
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <ProTable<Appointment>
        headerTitle="预约列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, scheduleDate, ...rest } = params;
          return toProTableResult(await appointmentApi.getList({
            ...rest,
            startDate: scheduleDate,
            endDate: scheduleDate,
            page: current,
            pageSize,
          }));
        }}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
      />
    </PageContainer>
  );
};

export default AppointmentListPage;
