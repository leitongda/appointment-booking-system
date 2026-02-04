import { PageContainer } from '@ant-design/pro-components';
import { App, Card, Table, Tag, Space, Button, Select, DatePicker, Empty, Spin, Switch, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState, useMemo } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { appointmentApi, storeApi, doctorApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { CheckinQueueItem } from '@hospital/api';
import { useListRequest } from '@/hooks/useListRequest';
import dayjs from 'dayjs';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  2: { text: '已签到', color: 'cyan' },
  3: { text: '候诊中', color: 'purple' },
  4: { text: '就诊中', color: 'processing' },
  5: { text: '已完成', color: 'green' },
};

const CHECKIN_METHOD_MAP: Record<string, { text: string; color: string }> = {
  QR_CODE: { text: '扫码', color: 'blue' },
  MANUAL: { text: '后台', color: 'default' },
  PHONE: { text: '手机端', color: 'green' },
};

const AppointmentQueuePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser, currentStore } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;

  // 筛选条件
  const [selectedStoreId, setSelectedStoreId] = useState<string | undefined>(
    currentStore?.id || undefined
  );
  const [selectedDoctorId, setSelectedDoctorId] = useState<string | undefined>(undefined);
  const [selectedDate, setSelectedDate] = useState<dayjs.Dayjs>(dayjs());

  // 轮询开关
  const [pollingEnabled, setPollingEnabled] = useState(true);

  // 使用 useListRequest 加载门店列表（带缓存）
  const { data: storesData } = useListRequest(
    () => storeApi.getAll(),
    {
      cacheKey: 'store-list-all',
      staleTime: 60000, // 1分钟缓存
      manual: !showStoreFilter,
    }
  );

  // 使用 useListRequest 加载医生列表（带缓存）
  const { data: doctorsData } = useListRequest(
    () => doctorApi.getAll(),
    {
      cacheKey: 'doctor-list-all',
      staleTime: 60000, // 1分钟缓存
    }
  );

  // 过滤门店列表
  const filteredStores = useMemo(() => {
    let storeList = storesData ?? [];
    if (!isSuperAdmin && currentUser?.storeIds?.length) {
      storeList = storeList.filter((s: any) => currentUser.storeIds?.includes(s.id));
    }
    return storeList.map((s: any) => ({ id: s.id, name: s.name }));
  }, [storesData, isSuperAdmin, currentUser?.storeIds]);

  // 医生列表
  const doctors = useMemo(() => {
    return (doctorsData ?? []).map((d: any) => ({ id: d.id, name: d.name }));
  }, [doctorsData]);

  // 使用 useListRequest 加载签到队列（带轮询）
  const {
    data: queueData,
    loading,
    refresh: refreshQueue,
  } = useListRequest(
    () =>
      appointmentApi.getCheckinQueue({
        storeId: selectedStoreId,
        doctorId: selectedDoctorId,
        targetDate: selectedDate.format('YYYY-MM-DD'),
      }),
    {
      // 轮询配置：每30秒自动刷新
      pollingInterval: pollingEnabled ? 30000 : undefined,
      // 页面隐藏时暂停轮询，节省资源
      pollingWhenHidden: false,
      // 错误重试
      retryCount: 2,
      retryInterval: 2000,
      // 错误回调
      onError: (error: any) => {
        message.error(error.message || '加载失败');
      },
      // 刷新依赖：筛选条件变化时重新请求
      refreshDeps: [selectedStoreId, selectedDoctorId, selectedDate],
    }
  );

  const data = queueData ?? [];

  // 叫号
  const handleCall = async (id: string) => {
    try {
      await appointmentApi.call(id);
      message.success('叫号成功');
      refreshQueue();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 过号
  const handlePass = async (id: string) => {
    try {
      await appointmentApi.pass(id);
      message.success('已过号');
      refreshQueue();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 重新叫号
  const handleRecall = async (id: string) => {
    try {
      await appointmentApi.recall(id);
      message.success('已重新叫号');
      refreshQueue();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 完成就诊
  const handleComplete = async (id: string) => {
    try {
      await appointmentApi.complete(id);
      message.success('就诊完成');
      refreshQueue();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  const columns: ColumnsType<CheckinQueueItem> = [
    {
      title: '队号',
      dataIndex: 'queueNumber',
      key: 'queueNumber',
      width: 80,
      render: (val) => (
        <span style={{ fontSize: 18, fontWeight: 600, color: '#4F46E5' }}>
          {val || '-'}
        </span>
      ),
    },
    {
      title: '患者姓名',
      dataIndex: 'patientName',
      key: 'patientName',
      width: 100,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      key: 'doctorName',
      width: 100,
    },
    {
      title: '科室',
      dataIndex: 'departmentName',
      key: 'departmentName',
      width: 120,
    },
    {
      title: '时段',
      dataIndex: 'timeSlot',
      key: 'timeSlot',
      width: 80,
      render: (val) => (val !== null ? TIME_SLOT_MAP[val] : '-'),
    },
    {
      title: '签到时间',
      dataIndex: 'signInTime',
      key: 'signInTime',
      width: 120,
      render: (val) => (val ? dayjs(val).format('HH:mm:ss') : '-'),
    },
    {
      title: '签到方式',
      dataIndex: 'checkinMethod',
      key: 'checkinMethod',
      width: 90,
      render: (val) => {
        const method = CHECKIN_METHOD_MAP[val];
        return method ? <Tag color={method.color}>{method.text}</Tag> : '-';
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (val) => {
        const status = STATUS_MAP[val];
        return status ? <Tag color={status.color}>{status.text}</Tag> : '-';
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => {
        const { status } = record;
        return (
          <Space size="small">
            {status === 2 && (
              <Button size="small" type="primary" onClick={() => handleCall(record.id)}>
                叫号
              </Button>
            )}
            {status === 3 && (
              <>
                <Button size="small" type="primary" onClick={() => handleComplete(record.id)}>
                  完成
                </Button>
                <Button size="small" onClick={() => handlePass(record.id)}>
                  过号
                </Button>
              </>
            )}
            {status === 7 && (
              /* 7=已过期(过号) */
              <Button size="small" onClick={() => handleRecall(record.id)}>
                重新叫号
              </Button>
            )}
          </Space>
        );
      },
    },
  ];

  return (
    <PageContainer>
      <Card>
        <div
          style={{
            marginBottom: 16,
            display: 'flex',
            gap: 16,
            flexWrap: 'wrap',
            alignItems: 'center',
          }}
        >
          {showStoreFilter && (
            <Select
              placeholder="选择门店"
              allowClear
              style={{ width: 200 }}
              value={selectedStoreId}
              onChange={setSelectedStoreId}
              options={filteredStores.map((s) => ({ label: s.name, value: s.id }))}
            />
          )}
          <Select
            placeholder="选择医生"
            allowClear
            style={{ width: 150 }}
            value={selectedDoctorId}
            onChange={setSelectedDoctorId}
            options={doctors.map((d) => ({ label: d.name, value: d.id }))}
          />
          <DatePicker
            value={selectedDate}
            onChange={(date) => date && setSelectedDate(date)}
            allowClear={false}
          />
          <Button onClick={refreshQueue}>刷新</Button>
          <Tooltip title={pollingEnabled ? '自动刷新已开启（30秒）' : '自动刷新已关闭'}>
            <Space>
              <span style={{ color: '#666', fontSize: 12 }}>自动刷新</span>
              <Switch size="small" checked={pollingEnabled} onChange={setPollingEnabled} />
            </Space>
          </Tooltip>
        </div>

        {loading && !data.length ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="加载中..." />
          </div>
        ) : !data.length ? (
          <Empty description="暂无签到患者" />
        ) : (
          <Table
            rowKey="id"
            columns={columns}
            dataSource={data}
            pagination={false}
            scroll={{ x: 900 }}
            loading={loading}
          />
        )}
      </Card>
    </PageContainer>
  );
};

export default AppointmentQueuePage;
