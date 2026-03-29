import { PlusOutlined } from '@ant-design/icons';
import type { ActionType, ProColumns } from '@ant-design/pro-components';
import { PageContainer, ProTable, ModalForm, ProFormSelect, ProFormText, ProFormDatePicker } from '@ant-design/pro-components';
import { Button, App, Tag, Popconfirm, Checkbox, Space } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { useAccess, useModel } from '@umijs/max';
import { scheduleSuspensionApi, storeApi, doctorApi } from '@hospital/api';
import { fetchAllData } from '@/utils/fetchAllData';
import { toProTableResult } from '@/utils/proTable';
import type { ScheduleSuspension, AvailableScheduleForSuspension } from '@hospital/api';
import { ScheduleMessages } from './utils/message';

const SuspensionPage: React.FC = () => {
  const { message } = App.useApp();
  const access = useAccess();
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = access.canSuperAdmin;
  const actionRef = useRef<ActionType>();
  const [modalOpen, setModalOpen] = useState(false);
  const [stores, setStores] = useState<any[]>([]);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedStore, setSelectedStore] = useState<string>();
  const [selectedDoctor, setSelectedDoctor] = useState<string>();
  const [selectedDate, setSelectedDate] = useState<string>();
  const [availableSchedules, setAvailableSchedules] = useState<AvailableScheduleForSuspension[]>([]);
  const [selectedTimeSlots, setSelectedTimeSlots] = useState<string[]>([]);
  const [selectedScheduleIds, setSelectedScheduleIds] = useState<string[]>([]);

  useEffect(() => {
    loadStores();
  }, []);

  useEffect(() => {
    if (selectedStore) {
      loadDoctorsByStore(selectedStore);
    }
  }, [selectedStore]);

  useEffect(() => {
    if (selectedStore && selectedDoctor && selectedDate) {
      loadAvailableSchedules();
    }
  }, [selectedStore, selectedDoctor, selectedDate]);

  const loadStores = async () => {
    try {
      // 获取所有启用的门店
      const allStores = await fetchAllData((page, pageSize) =>
        storeApi.getList({ page, pageSize, status: 1 })
      );
      let storeList = allStores;
      // 非超管只显示其关联的门店
      if (!isSuperAdmin && currentUser?.storeIds?.length) {
        storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
      }
      setStores(storeList);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadDoctorsByStore = async (storeId: string) => {
    try {
      // 获取该门店所有在职医生
      const allDoctors = await fetchAllData((page, pageSize) =>
        doctorApi.getList({ storeId, page, pageSize, status: 1 })
      );
      setDoctors(allDoctors);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  };

  const loadAvailableSchedules = async () => {
    if (!selectedStore || !selectedDoctor || !selectedDate) return;
    try {
      const result = await scheduleSuspensionApi.getAvailableSchedules(
        selectedStore,
        selectedDoctor,
        selectedDate
      );
      setAvailableSchedules(result);
    } catch (error: any) {
      console.error('加载排班失败', error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await scheduleSuspensionApi.delete(id);
      message.success(ScheduleMessages.deleteSuccess);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.deleteFailed);
    }
  };

  const handleCancel = async (id: string) => {
    try {
      await scheduleSuspensionApi.cancel(id);
      message.success(ScheduleMessages.cancelSuccess);
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.operateFailed);
    }
  };

  const handleScheduleSelect = (schedule: AvailableScheduleForSuspension, checked: boolean) => {
    if (checked) {
      setSelectedTimeSlots([...selectedTimeSlots, schedule.timeSlot]);
      setSelectedScheduleIds([...selectedScheduleIds, schedule.scheduleId]);
    } else {
      setSelectedTimeSlots(selectedTimeSlots.filter(t => t !== schedule.timeSlot));
      setSelectedScheduleIds(selectedScheduleIds.filter(id => id !== schedule.scheduleId));
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      await scheduleSuspensionApi.create({
        storeId: values.storeId,
        doctorId: values.doctorId,
        title: values.title,
        suspensionDate: values.suspensionDate.format('YYYY-MM-DD'),
        scheduleIds: selectedScheduleIds.length > 0 ? selectedScheduleIds : undefined,
        timeSlots: selectedTimeSlots.length > 0 ? selectedTimeSlots : undefined,
      });
      message.success(ScheduleMessages.createSuccess);
      setModalOpen(false);
      setSelectedTimeSlots([]);
      setSelectedScheduleIds([]);
      setAvailableSchedules([]);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || ScheduleMessages.createFailed);
      return false;
    }
  };

  const columns: ProColumns<ScheduleSuspension>[] = [
    {
      title: '门店',
      dataIndex: 'storeName',
      width: 150,
    },
    {
      title: '医生',
      dataIndex: 'doctorName',
      width: 100,
    },
    {
      title: '停诊标题',
      dataIndex: 'title',
      width: 150,
      ellipsis: true,
    },
    {
      title: '停诊日期',
      dataIndex: 'suspensionDate',
      width: 110,
      valueType: 'date',
    },
    {
      title: '停诊时段',
      dataIndex: 'timeSlots',
      width: 250,
      search: false,
      render: (_, record) => {
        if (!record.timeSlots || record.timeSlots.length === 0) {
          return <Tag color="red">全天停诊</Tag>;
        }
        return (
          <Space wrap>
            {record.timeSlots.map((slot, index) => (
              <Tag key={index} color="orange">{slot}</Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      valueEnum: {
        1: { text: '生效中', status: 'Error' },
        0: { text: '已取消', status: 'Default' },
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
      width: 120,
      render: (_, record) => [
        record.status === 1 && (
          <Popconfirm 
            key="cancel"
            title="确定取消该停诊吗？" 
            onConfirm={() => handleCancel(record.id)}
          >
            <a>取消</a>
          </Popconfirm>
        ),
        <Popconfirm 
          key="delete"
          title="确定删除该记录吗？" 
          onConfirm={() => handleDelete(record.id)}
        >
          <a style={{ color: '#ff4d4f' }}>删除</a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <PageContainer>
      <ProTable<ScheduleSuspension>
        headerTitle="停诊管理"
        actionRef={actionRef}
        rowKey="id"
        columns={columns}
        request={async (params) => {
          const { current, pageSize, ...rest } = params;
          return toProTableResult(await scheduleSuspensionApi.getList({
            ...rest,
            page: current,
            pageSize,
          }));
        }}
        toolBarRender={() => [
          <Button
            key="add"
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setModalOpen(true)}
          >
            添加
          </Button>,
        ]}
        pagination={{ defaultPageSize: 10 }}
      />

      <ModalForm
        title="添加停诊"
        open={modalOpen}
        onOpenChange={(open) => {
          setModalOpen(open);
          if (!open) {
            setSelectedTimeSlots([]);
            setSelectedScheduleIds([]);
            setAvailableSchedules([]);
            setSelectedStore(undefined);
            setSelectedDoctor(undefined);
            setSelectedDate(undefined);
          }
        }}
        onFinish={handleSubmit}
        modalProps={{ destroyOnHidden: true }}
      >
        <ProFormSelect
          name="storeId"
          label="门店"
          options={stores.map(s => ({ label: s.name, value: s.id }))}
          rules={[{ required: true, message: '请选择门店' }]}
          fieldProps={{
            onChange: (val) => {
              setSelectedStore(val);
              setSelectedDoctor(undefined);
              setAvailableSchedules([]);
            },
          }}
        />
        <ProFormSelect
          name="doctorId"
          label="医生"
          options={doctors.map(d => ({ label: d.name, value: d.id }))}
          rules={[{ required: true, message: '请选择医生' }]}
          fieldProps={{
            onChange: (val) => {
              setSelectedDoctor(val);
              setAvailableSchedules([]);
            },
          }}
        />
        <ProFormText
          name="title"
          label="停诊标题"
          placeholder="请输入停诊标题"
          rules={[{ required: true, message: '请输入停诊标题' }]}
        />
        <ProFormDatePicker
          name="suspensionDate"
          label="停诊日期"
          rules={[{ required: true, message: '请选择停诊日期' }]}
          fieldProps={{
            onChange: (val) => {
              setSelectedDate(val?.format('YYYY-MM-DD'));
            },
          }}
        />

        {availableSchedules.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 500 }}>选择排班：</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {availableSchedules.map((schedule) => (
                <Checkbox
                  key={schedule.scheduleId}
                  checked={selectedScheduleIds.includes(schedule.scheduleId)}
                  onChange={(e) => handleScheduleSelect(schedule, e.target.checked)}
                >
                  <Tag color={schedule.scheduleType === 'custom' ? 'purple' : 'blue'}>
                    {schedule.timeSlot}
                  </Tag>
                  <span style={{ fontSize: 12, color: '#999' }}>
                    ({schedule.bookedCount}/{schedule.maxPatients})
                  </span>
                </Checkbox>
              ))}
            </div>
            <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
              不选择则全天停诊
            </div>
          </div>
        )}

        {selectedStore && selectedDoctor && selectedDate && availableSchedules.length === 0 && (
          <div style={{ marginTop: 16, color: '#999' }}>
            该日期暂无排班
          </div>
        )}
      </ModalForm>
    </PageContainer>
  );
};

export default SuspensionPage;
