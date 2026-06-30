import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import { App, Space, Tag, Popconfirm, Descriptions, Drawer, Spin, Card, Row, Col, Statistic } from 'antd';
import { EyeOutlined, CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined, SyncOutlined } from '@ant-design/icons';
import { useRef, useState, useCallback, useEffect } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { waitlistApi, storeApi, doctorApi, departmentApi } from '@hospital/api';
import type { WaitlistEntry, WaitlistStatus, WaitlistStats } from '@hospital/api';
import type { Store, Department, Doctor } from '@hospital/shared';
import { createListRequest } from '@/utils/proTable';
import { fetchAllData } from '@/utils/fetchAllData';
import { rrwebMaskTextCell } from '@/utils/tableCellProps';
import { PAGINATION_CONFIG } from '@/constants/pagination';
import ListPageSkeleton from '@/components/ListPageSkeleton';
import dayjs from 'dayjs';

const STATUS_MAP: Record<WaitlistStatus, { text: string; color: string }> = {
  WAITING: { text: '等待中', color: 'orange' },
  PROMOTED: { text: '已递补', color: 'green' },
  CANCELLED: { text: '已取消', color: 'default' },
  EXPIRED: { text: '已过期', color: 'red' },
};

const WaitlistPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const actionRef = useRef<ActionType>();
  const [initialLoading, setInitialLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [currentEntry, setCurrentEntry] = useState<WaitlistEntry | null>(null);
  const [stats, setStats] = useState<WaitlistStats | null>(null);

  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;

  // 加载统计
  useEffect(() => {
    const loadStats = async () => {
      try {
        const data = await waitlistApi.getStats();
        setStats(data);
      } catch {
        // 统计加载失败不影响页面使用
      }
    };
    loadStats();
  }, []);

  // 预加载门店数据
  useEffect(() => {
    const prefetch = async () => {
      setInitialLoading(false);
    };
    prefetch();
  }, []);

  const handleView = useCallback(async (id: string) => {
    setDetailLoading(true);
    setDrawerOpen(true);
    try {
      const result = await waitlistApi.getDetail(id);
      setCurrentEntry(result);
    } catch (error: any) {
      message.error(error.message || '加载候补详情失败');
      setDrawerOpen(false);
    } finally {
      setDetailLoading(false);
    }
  }, [message]);

  const handlePromote = useCallback(async (id: string) => {
    try {
      await waitlistApi.adminPromote(id);
      message.success('递补成功');
      actionRef.current?.reload();
      // 刷新统计
      const data = await waitlistApi.getStats();
      setStats(data);
    } catch (error: any) {
      message.error(error.message || '递补失败');
    }
  }, [message]);

  const handleCancel = useCallback(async (id: string) => {
    try {
      await waitlistApi.adminCancel(id);
      message.success('取消成功');
      actionRef.current?.reload();
      // 刷新统计
      const data = await waitlistApi.getStats();
      setStats(data);
    } catch (error: any) {
      message.error(error.message || '取消失败');
    }
  }, [message]);

  // 日期快捷选项
  const datePresets: { label: string; value: [dayjs.Dayjs, dayjs.Dayjs] }[] = [
    { label: '今天', value: [dayjs(), dayjs()] },
    { label: '本周', value: [dayjs().startOf('week'), dayjs().endOf('week')] },
    { label: '本月', value: [dayjs().startOf('month'), dayjs().endOf('month')] },
    { label: '近7天', value: [dayjs().subtract(6, 'day'), dayjs()] },
    { label: '近30天', value: [dayjs().subtract(29, 'day'), dayjs()] },
  ];

  const columns: ProColumns<WaitlistEntry>[] = [
    {
      title: '关键字',
      dataIndex: 'keyword',
      hideInTable: true,
      fieldProps: {
        placeholder: '患者姓名/手机号',
      },
    },
    // 超级管理员和多门店管理员可以按门店筛选
    ...(showStoreFilter
      ? [
          {
            title: '门店',
            dataIndex: 'storeId',
            hideInTable: true,
            valueType: 'select',
            request: async () => {
              try {
                const stores = await storeApi.getAll();
                let storeList = stores ?? [];
                if (!isSuperAdmin && currentUser?.storeIds?.length) {
                  storeList = storeList.filter((s: Store) =>
                    currentUser.storeIds?.includes(s.id)
                  );
                }
                return [
                  { label: '全部门店', value: '' },
                  ...storeList.map((s: Store) => ({
                    label: s.name,
                    value: s.id,
                  })),
                ];
              } catch {
                return [];
              }
            },
          } as ProColumns<WaitlistEntry>,
        ]
      : []),
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
          const departments = await fetchAllData((page, pageSize) =>
            departmentApi.getList({ page, pageSize })
          );
          return [
            { label: '全部科室', value: '' },
            ...departments.map((d: Department) => ({
              label: d.name,
              value: d.id,
            })),
          ];
        } catch {
          return [];
        }
      },
    },
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
          const doctors = await fetchAllData((page, pageSize) =>
            doctorApi.getList({ page, pageSize })
          );
          return [
            { label: '全部医生', value: '' },
            ...doctors.map((d: Doctor) => ({
              label: `${d.name}（${d.departmentName || '无科室'}）`,
              value: d.id,
            })),
          ];
        } catch {
          return [];
        }
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      hideInTable: true,
      valueType: 'select',
      valueEnum: Object.fromEntries(
        Object.entries(STATUS_MAP).map(([key, value]) => [
          key,
          { text: value.text },
        ])
      ),
    },
    {
      title: '候补日期',
      dataIndex: 'dateRange',
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
    // 表格展示列
    {
      title: '序号',
      dataIndex: 'position',
      width: 70,
      search: false,
      render: (_, __, index) => index + 1,
    },
    {
      title: '排班日期',
      dataIndex: ['schedule', 'scheduleDate'],
      width: 110,
      valueType: 'date',
      search: false,
    },
    {
      title: '时段',
      dataIndex: ['schedule', 'timeSlot'],
      width: 70,
      search: false,
      valueEnum: {
        morning: '上午',
        afternoon: '下午',
        evening: '晚上',
      },
    },
    {
      title: '门店',
      dataIndex: ['schedule', 'storeName'],
      width: 120,
      search: false,
      ellipsis: true,
    },
    {
      title: '科室',
      dataIndex: ['schedule', 'departmentName'],
      width: 100,
      search: false,
    },
    {
      title: '医生',
      dataIndex: ['schedule', 'doctorName'],
      width: 80,
      search: false,
    },
    {
      title: '患者',
      dataIndex: 'patientName',
      width: 80,
      search: false,
      onCell: rrwebMaskTextCell,
    },
    {
      title: '排队位置',
      dataIndex: 'position',
      width: 80,
      search: false,
      render: (pos) => (pos != null ? `第 ${pos} 位` : '-'),
    },
    {
      title: '症状描述',
      dataIndex: 'symptomDescription',
      ellipsis: true,
      search: false,
      onCell: rrwebMaskTextCell,
      render: (val) => val || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      search: false,
      render: (_, record) => {
        const statusInfo = STATUS_MAP[record.status] || {
          text: '未知',
          color: 'default',
        };
        return <Tag color={statusInfo.color}>{statusInfo.text}</Tag>;
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
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4}>
          <a
            onClick={() => handleView(record.id)}
            style={{ fontSize: 13 }}
          >
            <EyeOutlined /> 详情
          </a>
          {record.status === 'WAITING' && (
            <>
              <Popconfirm
                title="确定递补该候补用户吗？将自动创建预约。"
                onConfirm={() => handlePromote(record.id)}
              >
                <a style={{ color: '#52c41a', fontSize: 13 }}>
                  <CheckCircleOutlined /> 递补
                </a>
              </Popconfirm>
              <Popconfirm
                title="确定取消该候补吗？"
                onConfirm={() => handleCancel(record.id)}
              >
                <a style={{ color: '#ff4d4f', fontSize: 13 }}>
                  <CloseCircleOutlined /> 取消
                </a>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      {/* 统计卡片 */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="等待中"
                value={stats.totalWaiting}
                prefix={<ClockCircleOutlined />}
                valueStyle={{ color: '#fa8c16' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已递补"
                value={stats.totalPromoted}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已取消"
                value={stats.totalCancelled}
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: '#999' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="已过期"
                value={stats.totalExpired}
                prefix={<SyncOutlined />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      {initialLoading && <ListPageSkeleton filterCount={5} rowCount={6} />}
      {!initialLoading && (
        <ProTable<WaitlistEntry>
          headerTitle="候补队列"
          actionRef={actionRef}
          rowKey="id"
          columns={columns}
          request={createListRequest(waitlistApi.adminList, ({ keyword, storeId, departmentId, doctorId, status, startDate, endDate, ...params }) => ({
            ...params,
            keyword: keyword || undefined,
            storeId: storeId || undefined,
            departmentId: departmentId || undefined,
            doctorId: doctorId || undefined,
            status: (status as WaitlistStatus) || undefined,
            startDate: startDate || undefined,
            endDate: endDate || undefined,
          }))}
          pagination={{
            defaultPageSize: PAGINATION_CONFIG.DEFAULT_PAGE_SIZE,
          }}
          search={{ labelWidth: 'auto' }}
          scroll={{ x: 1200 }}
        />
      )}

      <Drawer
        title="候补详情"
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setCurrentEntry(null);
        }}
        width={640}
      >
        <Spin spinning={detailLoading}>
          {currentEntry ? (
            <Descriptions column={2} bordered size="small" items={[
              { key: 'id', label: '候补ID', children: currentEntry.id },
              { key: 'status', label: '状态', children: (
                <Tag color={STATUS_MAP[currentEntry.status]?.color || 'default'}>
                  {STATUS_MAP[currentEntry.status]?.text || '未知'}
                </Tag>
              ) },
              { key: 'position', label: '排队位置', children: currentEntry.position != null ? `第 ${currentEntry.position} 位` : '-' },
              { key: 'priority', label: '优先级', children: currentEntry.priority ?? '-' },
              { key: 'patientName', label: '患者', children: <span data-rrweb-mask-text>{currentEntry.patientName || '-'}</span> },
              { key: 'storeName', label: '门店', children: currentEntry.schedule?.storeName || '-' },
              { key: 'departmentName', label: '科室', children: currentEntry.schedule?.departmentName || '-' },
              { key: 'doctorName', label: '医生', children: currentEntry.schedule?.doctorName || '-' },
              { key: 'scheduleDate', label: '排班日期', children: currentEntry.schedule?.scheduleDate ? dayjs(currentEntry.schedule.scheduleDate).format('YYYY-MM-DD') : '-' },
              { key: 'timeSlot', label: '时段', children: currentEntry.schedule?.timeSlot === 'morning' ? '上午' : currentEntry.schedule?.timeSlot === 'afternoon' ? '下午' : currentEntry.schedule?.timeSlot === 'evening' ? '晚上' : '-' },
              { key: 'slotInfo', label: '号源', children: currentEntry.schedule ? `${currentEntry.schedule.bookedSlots}/${currentEntry.schedule.totalSlots}` : '-' },
              { key: 'symptom', label: '症状描述', span: 2, children: <div className="rrweb-block">{currentEntry.symptomDescription || '-'}</div> },
              { key: 'createdAt', label: '创建时间', children: currentEntry.createdAt ? dayjs(currentEntry.createdAt).format('YYYY-MM-DD HH:mm:ss') : '-' },
              { key: 'promotedAt', label: '递补时间', children: currentEntry.promotedAt ? dayjs(currentEntry.promotedAt).format('YYYY-MM-DD HH:mm:ss') : '-' },
              { key: 'cancelledAt', label: '取消时间', children: currentEntry.cancelledAt ? dayjs(currentEntry.cancelledAt).format('YYYY-MM-DD HH:mm:ss') : '-' },
            ]} />
          ) : null}
        </Spin>
      </Drawer>
    </PageContainer>
  );
};

export default WaitlistPage;
