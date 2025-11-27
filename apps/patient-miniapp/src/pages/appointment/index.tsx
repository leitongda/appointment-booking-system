import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Tabs, Button, Empty } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';
import './index.less';

const statusColorMap: Record<number, string> = {
  1: '#1890ff',
  2: '#52c41a',
  3: '#faad14',
  5: '#52c41a',
  6: '#999',
  7: '#ff4d4f',
};

const AppointmentPage = () => {
  const [activeTab, setActiveTab] = useState('0');
  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<Appointment[]>([]);

  useEffect(() => {
    loadAppointments();
  }, [activeTab]);

  const loadAppointments = async () => {
    setLoading(true);
    try {
      const statusMap: Record<string, number | undefined> = {
        '0': undefined,
        '1': 1,
        '2': 5,
        '3': 6,
      };

      const result = await appointmentApi.getList({
        status: statusMap[activeTab],
        page: 1,
        pageSize: 20,
      });
      setAppointments(result.data);
    } catch (error) {
      console.error('加载预约列表失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (id: string) => {
    const result = await Taro.showModal({
      title: '取消预约',
      content: '确定要取消预约吗？',
    });

    if (!result.confirm) return;

    try {
      await appointmentApi.cancel(id);
      Taro.showToast({ title: '取消成功', icon: 'success' });
      loadAppointments();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '取消失败', icon: 'none' });
    }
  };

  const handleSignIn = async (id: string) => {
    try {
      const result = await appointmentApi.signIn(id);
      Taro.showToast({ title: `签到成功，您是第${result.queueNumber}号`, icon: 'success' });
      loadAppointments();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '签到失败', icon: 'none' });
    }
  };

  const handleViewDetail = (id: string) => {
    Taro.navigateTo({ url: `/pages/appointment/detail?id=${id}` });
  };

  return (
    <View className="appointment-page">
      <Tabs
        value={activeTab}
        onChange={(value) => setActiveTab(value as string)}
      >
        <Tabs.TabPane title="全部" value="0" />
        <Tabs.TabPane title="待就诊" value="1" />
        <Tabs.TabPane title="已完成" value="2" />
        <Tabs.TabPane title="已取消" value="3" />
      </Tabs>

      <View className="list">
        {appointments.length === 0 && !loading ? (
          <Empty description="暂无预约记录" />
        ) : (
          appointments.map((item) => (
            <View key={item.id} className="card" onClick={() => handleViewDetail(item.id)}>
              <View className="card-header">
                <Text className="appointment-no">预约单号：{item.appointmentNo}</Text>
                <Text 
                  className="status" 
                  style={{ color: statusColorMap[item.status] }}
                >
                  {APPOINTMENT_STATUS_MAP[item.status]}
                </Text>
              </View>

              <View className="card-body">
                <View className="info">
                  <Text className="doctor-name">{item.doctorName}</Text>
                  <Text className="dept-name">{item.departmentName}</Text>
                </View>
                <View className="time">
                  <Text className="date">{item.scheduleDate}</Text>
                  <Text className="slot">
                    {TIME_SLOT_MAP[item.timeSlot || 'AM']}
                    {item.queueNumber && ` 第${item.queueNumber}号`}
                  </Text>
                </View>
              </View>

              {item.status === 1 && (
                <View className="card-footer">
                  <Button 
                    size="small" 
                    onClick={(e) => { e.stopPropagation(); handleCancel(item.id); }}
                  >
                    取消预约
                  </Button>
                  <Button 
                    type="primary" 
                    size="small"
                    onClick={(e) => { e.stopPropagation(); handleSignIn(item.id); }}
                  >
                    签到
                  </Button>
                </View>
              )}
            </View>
          ))
        )}
      </View>
    </View>
  );
};

export default AppointmentPage;

