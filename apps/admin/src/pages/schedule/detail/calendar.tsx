import { PageContainer } from '@ant-design/pro-components';
import { Calendar, Badge, Tooltip, Spin, Tag, Select, Space } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';
import { useEffect, useState, useCallback } from 'react';
import { scheduleApi, doctorApi, departmentApi, storeApi } from '@hospital/api';
import type { Schedule, Doctor, Department, Store } from '@hospital/shared';
import { APPOINTMENT_TYPE_MAP, TIME_SLOT_MAP } from '@hospital/shared';
import { useModel } from '@umijs/max';

interface DaySchedules {
  [date: string]: Schedule[];
}

const ScheduleDetailCalendarPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [scheduleData, setScheduleData] = useState<DaySchedules>({});
  const [currentMonth, setCurrentMonth] = useState<Dayjs>(dayjs());
  const [selectedDoctor, setSelectedDoctor] = useState<string>();
  const [selectedDepartment, setSelectedDepartment] = useState<string>();
  const [selectedStore, setSelectedStore] = useState<string>();
  
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [stores, setStores] = useState<Store[]>([]);
  
  const { initialState } = useModel('@@initialState');
  const { currentUser } = initialState ?? {};
  const isSuperAdmin = true; // 简化处理

  useEffect(() => {
    loadStores();
    loadDepartments();
  }, []);

  useEffect(() => {
    if (selectedDepartment) {
      loadDoctorsByDept(selectedDepartment);
    } else {
      setDoctors([]);
    }
  }, [selectedDepartment]);

  const loadStores = async () => {
    try {
      const data = await storeApi.getAll();
      let storeList = data ?? [];
      if (!isSuperAdmin && currentUser?.storeIds?.length) {
        storeList = storeList.filter((s) => currentUser.storeIds?.includes(s.id));
      }
      setStores(storeList);
    } catch (error) {
      console.error('加载门店失败', error);
    }
  };

  const loadDepartments = async () => {
    try {
      const res = await departmentApi.getList({ pageSize: 100, status: 1 });
      setDepartments(res.data ?? []);
    } catch (error) {
      console.error('加载科室失败', error);
    }
  };

  const loadDoctorsByDept = async (deptId: string) => {
    try {
      const data = await doctorApi.getByDepartment(deptId);
      setDoctors(data ?? []);
    } catch (error) {
      console.error('加载医生失败', error);
    }
  };

  const loadSchedules = useCallback(async (month: Dayjs) => {
    setLoading(true);
    try {
      const startDate = month.startOf('month').format('YYYY-MM-DD');
      const endDate = month.endOf('month').format('YYYY-MM-DD');
      
      const params: any = {
        startDate,
        endDate,
        pageSize: 1000,
      };
      
      if (selectedStore) {
        params.storeId = selectedStore;
      }
      if (selectedDoctor) {
        params.doctorId = selectedDoctor;
      }
      
      const result = await scheduleApi.getList(params);
      
      // 按日期分组
      const grouped: DaySchedules = {};
      (result.data ?? []).forEach((schedule) => {
        const date = schedule.scheduleDate;
        if (!grouped[date]) {
          grouped[date] = [];
        }
        grouped[date].push(schedule);
      });
      
      setScheduleData(grouped);
    } catch (error) {
      console.error('加载排班失败', error);
    } finally {
      setLoading(false);
    }
  }, [selectedStore, selectedDoctor]);

  useEffect(() => {
    loadSchedules(currentMonth);
  }, [loadSchedules, currentMonth]);

  const handlePanelChange = (date: Dayjs) => {
    setCurrentMonth(date);
  };

  const getStatusBadge = (schedule: Schedule) => {
    if (schedule.status === 0) {
      return 'default'; // 停诊
    }
    const available = schedule.totalSlots - schedule.bookedSlots;
    if (available <= 0) {
      return 'error'; // 已满
    }
    if (available <= schedule.totalSlots * 0.2) {
      return 'warning'; // 即将满
    }
    return 'success'; // 正常
  };

  const dateCellRender = (date: Dayjs) => {
    const dateStr = date.format('YYYY-MM-DD');
    const schedules = scheduleData[dateStr] || [];
    
    if (schedules.length === 0) {
      return null;
    }

    // 按时段和时间排序
    const sortOrder = { morning: 0, afternoon: 1, evening: 2 };
    const sortedSchedules = [...schedules].sort((a, b) => {
      const timeA = a.startTime || '00:00';
      const timeB = b.startTime || '00:00';
      return timeA.localeCompare(timeB);
    });

    return (
      <div style={{ fontSize: 11 }}>
        {sortedSchedules.map((schedule) => {
          const timeRange = schedule.startTime && schedule.endTime
            ? `${schedule.startTime}-${schedule.endTime}`
            : TIME_SLOT_MAP[schedule.timeSlot] || schedule.timeSlot;
          const available = schedule.totalSlots - schedule.bookedSlots;
          
          return (
            <Tooltip
              key={schedule.id}
              title={
                <div>
                  <div>医生：{schedule.doctorName || '-'}</div>
                  <div>科室：{schedule.departmentName || '-'}</div>
                  <div>时间：{timeRange}</div>
                  <div>预约类型：{APPOINTMENT_TYPE_MAP[schedule.appointmentType || 'normal']}</div>
                  <div>号源：{schedule.bookedSlots}/{schedule.totalSlots}</div>
                  <div>状态：{schedule.status === 1 ? '正常' : '停诊'}</div>
                </div>
              }
            >
              <div style={{ marginBottom: 2 }}>
                <Badge
                  status={getStatusBadge(schedule) as any}
                  text={
                    <span style={{ fontSize: 10 }}>
                      {timeRange} ({schedule.bookedSlots}/{schedule.totalSlots})
                    </span>
                  }
                />
              </div>
            </Tooltip>
          );
        })}
      </div>
    );
  };

  return (
    <PageContainer>
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="选择门店"
          style={{ width: 150 }}
          allowClear
          value={selectedStore}
          onChange={(val) => {
            setSelectedStore(val);
            setSelectedDoctor(undefined);
          }}
          options={stores.map((s) => ({ label: s.name, value: s.id }))}
        />
        <Select
          placeholder="选择科室"
          style={{ width: 150 }}
          allowClear
          value={selectedDepartment}
          onChange={(val) => {
            setSelectedDepartment(val);
            setSelectedDoctor(undefined);
          }}
          options={departments.map((d) => ({ label: d.name, value: d.id }))}
        />
        <Select
          placeholder="选择医生"
          style={{ width: 200 }}
          allowClear
          value={selectedDoctor}
          onChange={setSelectedDoctor}
          disabled={!selectedDepartment}
          options={doctors.map((d) => ({ label: `${d.name} - ${d.title || ''}`, value: d.id }))}
        />
      </Space>

      <Spin spinning={loading}>
        <Calendar
          onPanelChange={handlePanelChange}
          cellRender={(date, info) => {
            if (info.type === 'date') {
              return dateCellRender(date);
            }
            return null;
          }}
          style={{
            background: '#fff',
            borderRadius: 8,
            padding: 16,
          }}
        />
      </Spin>

      <div style={{ marginTop: 16, fontSize: 12, color: '#666' }}>
        <div>
          <Badge status="success" text="正常" /> - 可预约
        </div>
        <div>
          <Badge status="warning" text="即将满" /> - 剩余号源较少
        </div>
        <div>
          <Badge status="error" text="已满" /> - 无剩余号源
        </div>
        <div>
          <Badge status="default" text="停诊" /> - 已停诊
        </div>
      </div>
    </PageContainer>
  );
};

export default ScheduleDetailCalendarPage;

