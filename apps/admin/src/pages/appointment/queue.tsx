import { PageContainer } from '@ant-design/pro-components';
import { App, Card, Table, Tag, Space, Button, Select, DatePicker, Empty, Spin } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useState, useEffect, useCallback } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { appointmentApi, storeApi, doctorApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { CheckinQueueItem } from '@hospital/api';
import dayjs from 'dayjs';

const STATUS_MAP: Record<number, { text: string; color: string }> = {
  2: { text: '已签到', color: 'cyan' },
  3: { text: '候诊中', color: 'purple' },
  4: { text: '就诊中', color: 'processing' },
  5: { text: '已完成', color: 'green' },
};

const AppointmentQueuePage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser, currentStore } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const showStoreFilter = isSuperAdmin || (currentUser?.storeIds?.length ?? 0) > 1;

  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<CheckinQueueItem[]>([]);
  const [stores, setStores] = useState<{ id: string; name: string }[]>([]);
  const [doctors, setDoctors] = useState<{ id: string; name: string }[]>([]);
  
  // 筛选条件
  const [selectedStoreId, setSelectedStoreId] = useState<string | undefined>(
    currentStore?.id || undefined
  );
  const [selectedDoctorId, setSelectedDoctorId] = useState<string | undefined>(undefined);
  const [selectedDate, setSelectedDate] = useState<dayjs.Dayjs>(dayjs());

  // 加载门店列表
  useEffect(() => {
    const loadStores = async () => {
      try {
        const result = await storeApi.getAll();
        let storeList = result ?? [];
        if (!isSuperAdmin && currentUser?.storeIds?.length) {
          storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
        }
        setStores(storeList.map((s) => ({ id: s.id, name: s.name })));
      } catch (error) {
        console.error('加载门店失败', error);
      }
    };

    if (showStoreFilter) {
      loadStores();
    }
  }, [isSuperAdmin, showStoreFilter, currentUser?.storeIds]);

  // 加载医生列表
  useEffect(() => {
    const loadDoctors = async () => {
      try {
        const result = await doctorApi.getAll();
        setDoctors((result ?? []).map((d) => ({ id: d.id, name: d.name })));
      } catch (error) {
        console.error('加载医生失败', error);
      }
    };
    loadDoctors();
  }, []);

  // 加载签到队列
  const loadQueue = useCallback(async () => {
    setLoading(true);
    try {
      const result = await appointmentApi.getCheckinQueue({
        storeId: selectedStoreId,
        doctorId: selectedDoctorId,
        targetDate: selectedDate.format('YYYY-MM-DD'),
      });
      setData(result ?? []);
    } catch (error: any) {
      message.error(error.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [selectedStoreId, selectedDoctorId, selectedDate, message]);

  useEffect(() => {
    loadQueue();
    // 每30秒自动刷新
    const timer = setInterval(loadQueue, 30000);
    return () => clearInterval(timer);
  }, [loadQueue]);

  // 叫号
  const handleCall = async (id: string) => {
    try {
      await appointmentApi.call(id);
      message.success('叫号成功');
      loadQueue();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 过号
  const handlePass = async (id: string) => {
    try {
      await appointmentApi.pass(id);
      message.success('已过号');
      loadQueue();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 重新叫号
  const handleRecall = async (id: string) => {
    try {
      await appointmentApi.recall(id);
      message.success('已重新叫号');
      loadQueue();
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 完成就诊
  const handleComplete = async (id: string) => {
    try {
      await appointmentApi.complete(id);
      message.success('就诊完成');
      loadQueue();
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
            {status === 7 && (  /* 7=已过期(过号) */
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
        <div style={{ marginBottom: 16, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          {showStoreFilter && (
            <Select
              placeholder="选择门店"
              allowClear
              style={{ width: 200 }}
              value={selectedStoreId}
              onChange={setSelectedStoreId}
              options={stores.map((s) => ({ label: s.name, value: s.id }))}
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
          <Button onClick={loadQueue}>刷新</Button>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin tip="加载中..." />
          </div>
        ) : data.length === 0 ? (
          <Empty description="暂无签到患者" />
        ) : (
          <Table
            rowKey="id"
            columns={columns}
            dataSource={data}
            pagination={false}
            scroll={{ x: 900 }}
          />
        )}
      </Card>
    </PageContainer>
  );
};

export default AppointmentQueuePage;

