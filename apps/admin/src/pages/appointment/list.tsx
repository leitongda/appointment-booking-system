import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { App, Space, Tag, Popconfirm, Divider } from 'antd';
import { EyeOutlined, CloseCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { useRef, useMemo, useCallback } from 'react';
import { history, useAccess, useModel } from '@umijs/max';
import { appointmentApi, storeApi, dataApi, doctorApi, departmentApi } from '@hospital/api';
import { toProTableResult } from '@/utils/proTable';
import { fetchAllData } from '@/utils/fetchAllData';
import { PAGINATION_CONFIG } from '@/constants/pagination';
import type { Appointment } from '@hospital/shared';
import ImportExport from '@/components/ImportExport';
import dayjs from 'dayjs';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  0: { text: '待支付', color: 'orange' },
  1: { text: '已预约', color: 'blue' },
  2: { text: '已签到', color: 'cyan' },
  3: { text: '候诊中', color: 'purple' },
  4: { text: '就诊中', color: 'processing' },
  5: { text: '已完成', color: 'green' },
  6: { text: '已取消', color: 'default' },
  7: { text: '已过期', color: 'default' },
  8: { text: '已爽约', color: 'red' },
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

  const handleCancel = useCallback(async (id: string) => {
    try {
      await appointmentApi.cancel(id, '管理员取消');
      message.success('取消成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  }, [message, actionRef]);

  const handleMarkNoShow = useCallback(async (id: string) => {
    try {
      await appointmentApi.markNoShow(id);
      message.success('标记成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  }, [message, actionRef]);

  const handleCancelSignIn = useCallback(async (id: string) => {
    try {
      await appointmentApi.cancelSignIn(id);
      message.success('取消签到成功');
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  }, [message, actionRef]);

  // 日期快捷选项
  const datePresets: { label: string; value: [dayjs.Dayjs, dayjs.Dayjs] }[] = [
    { label: '今天', value: [dayjs(), dayjs()] },
    { label: '本周', value: [dayjs().startOf('week'), dayjs().endOf('week')] },
    { label: '本月', value: [dayjs().startOf('month'), dayjs().endOf('month')] },
    { label: '近7天', value: [dayjs().subtract(6, 'day'), dayjs()] },
    { label: '近30天', value: [dayjs().subtract(29, 'day'), dayjs()] },
  ];

  // 使用 useMemo 优化 columns 配置
  const columns = useMemo<ProColumns<Appointment>[]>(() => [
    // 关键字搜索（仅搜索，不在表格中显示）
    {
      title: '关键字',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '预约编号/患者姓名/手机号',
      },
    },
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
      search: false,
    },
    {
      title: '患者',
      dataIndex: 'patientName',
      width: 80,
      search: false,
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
      search: false,
    },
    // 医生下拉选择器（仅搜索，不在表格中显示）
    {
      title: '医生',
      dataIndex: 'doctorId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择医生',
      },
      request: async () => {
        try {
          // 获取所有医生（使用分页加载）
          const doctors = await fetchAllData((page, pageSize) =>
            doctorApi.getList({ page, pageSize })
          );
          return [
            { label: '全部医生', value: '' },
            ...doctors.map((d: any) => ({ label: `${d.name}（${d.departmentName || '无科室'}）`, value: d.id })),
          ];
        } catch {
          return [];
        }
      },
    },
    {
      title: '科室',
      dataIndex: 'departmentName',
      width: 100,
      search: false,
    },
    // 科室下拉选择器（仅搜索，不在表格中显示）
    {
      title: '科室',
      dataIndex: 'departmentId',
      hideInTable: true,
      valueType: 'select',
      fieldProps: {
        showSearch: true,
        optionFilterProp: 'label',
        placeholder: '请选择科室',
      },
      request: async () => {
        try {
          // 获取所有科室（使用分页加载）
          const departments = await fetchAllData((page, pageSize) =>
            departmentApi.getList({ page, pageSize })
          );
          return [
            { label: '全部科室', value: '' },
            ...departments.map((d: any) => ({ label: d.name, value: d.id })),
          ];
        } catch {
          return [];
        }
      },
    },
    // 预约日期范围选择器（仅搜索，不在表格中显示）
    {
      title: '预约日期',
      dataIndex: 'scheduleDateRange',
      hideInTable: true,
      valueType: 'dateRange',
      fieldProps: {
        presets: datePresets,
      },
      search: {
        transform: (value) => {
          if (!value) return {};
          return {
            startDate: value[0],
            endDate: value[1],
          };
        },
      },
    },
    {
      title: '预约日期',
      dataIndex: 'scheduleDate',
      width: 110,
      valueType: 'date',
      search: false,
    },
    {
      title: '时段',
      dataIndex: 'timeSlot',
      width: 70,
      search: false,
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
    // 创建时间范围选择器（仅搜索，不在表格中显示）
    {
      title: '创建时间',
      dataIndex: 'createdAtRange',
      hideInTable: true,
      valueType: 'dateTimeRange',
      fieldProps: {
        presets: datePresets,
      },
      search: {
        transform: (value) => {
          if (!value) return {};
          return {
            createdStart: value[0],
            createdEnd: value[1],
          };
        },
      },
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      width: 160,
      valueType: 'dateTime',
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4} split={<Divider type="vertical" style={{ margin: 0 }} />}>
          {access.hasPermission('appointment:detail') && (
            <a onClick={() => history.push(`/medical-services/appointment/${record.id}`)} style={{ fontSize: 13 }}>
              <EyeOutlined /> 详情
            </a>
          )}
          {record.status === 0 && access.hasPermission('appointment:cancel') && (
            <Popconfirm title="确定取消该预约吗？" onConfirm={() => handleCancel(record.id)}>
              <a style={{ color: '#ff4d4f', fontSize: 13 }}>
                <CloseCircleOutlined /> 取消
              </a>
            </Popconfirm>
          )}
          {record.status === 1 && access.hasPermission('appointment:update') && (
            <Popconfirm title="确定标记为爽约吗？" onConfirm={() => handleMarkNoShow(record.id)}>
              <a style={{ color: '#fa8c16', fontSize: 13 }}>
                <ExclamationCircleOutlined /> 爽约
              </a>
            </Popconfirm>
          )}
          {record.status === 2 && isSuperAdmin && (
            <Popconfirm title="确定取消签到吗？状态将恢复为已预约" onConfirm={() => handleCancelSignIn(record.id)}>
              <a style={{ color: '#ff4d4f', fontSize: 13 }}>
                <CloseCircleOutlined /> 取消签到
              </a>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ], [showStoreFilter, access, handleCancel, handleMarkNoShow, handleCancelSignIn]);

  return (
    <PageContainer>
      <ProTable<Appointment>
        headerTitle="预约列表"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { 
            current, 
            pageSize, 
            keyword,
            storeId,
            doctorId,
            departmentId,
            startDate,
            endDate,
            createdStart,
            createdEnd,
            status,
          } = params;
          return toProTableResult(await appointmentApi.getList({
            keyword: keyword || undefined,
            storeId: storeId || undefined,
            doctorId: doctorId || undefined,
            departmentId: departmentId || undefined,
            startDate: startDate || undefined,
            endDate: endDate || undefined,
            createdStart: createdStart || undefined,
            createdEnd: createdEnd || undefined,
            status: status !== undefined && status !== '' ? Number(status) : undefined,
            page: current,
            pageSize,
          }));
        }}
        pagination={{ defaultPageSize: 10 }}
        search={{ labelWidth: 'auto' }}
        toolBarRender={() => [
          <ImportExport
            key="export"
            moduleName="预约"
            exportUrl={dataApi.getExportAppointmentsUrl()}
            showImport={false}
          />,
        ]}
      />
    </PageContainer>
  );
};

export default AppointmentListPage;
