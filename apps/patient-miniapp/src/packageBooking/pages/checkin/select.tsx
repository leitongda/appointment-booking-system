import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { Button, Empty } from '@nutui/nutui-react-taro';
import { appointmentApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { PendingAppointment } from '@hospital/api';
import { DoctorIcon, CheckCircleIcon } from '../../../components/Icons';
import { getToken } from '../../../utils/auth';
import LoginPopup from '../../../components/LoginPopup';
import './select.less';

const CheckinSelectPage = () => {
  const router = useRouter();
  const { storeId } = router.params;

  const [loading, setLoading] = useState(true);
  const [appointments, setAppointments] = useState<PendingAppointment[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showLoginPopup, setShowLoginPopup] = useState(false);

  useEffect(() => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      setShowLoginPopup(true);
      setLoading(false);
      return;
    }
    if (storeId) {
      loadAppointments();
    }
  }, [storeId]);

  // 登录成功后加载数据
  const handleLoginSuccess = () => {
    setShowLoginPopup(false);
    if (storeId) {
      loadAppointments();
    }
  };

  const loadAppointments = async () => {
    try {
      const data = await appointmentApi.getTodayPending(storeId!);
      setAppointments(data);
      // 如果只有一个预约，自动选中
      if (data.length === 1) {
        setSelectedId(data[0].id);
      }
    } catch (error: any) {
      console.error('[选择预约] 加载失败:', error);
      Taro.showToast({
        title: error.message || '加载失败',
        icon: 'none',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (id: string, signInStatus?: string) => {
    // 只允许选择可签到的预约
    if (signInStatus === 'early' || signInStatus === 'late') {
      return;
    }
    setSelectedId(id);
  };

  const handleSignIn = async () => {
    if (!selectedId) {
      Taro.showToast({
        title: '请选择要签到的预约',
        icon: 'none',
      });
      return;
    }

    setSubmitting(true);

    try {
      const result = await appointmentApi.signIn(selectedId);
      
      Taro.showModal({
        title: '签到成功',
        content: `您的排队号码是 ${result.queueNumber}，请在候诊区等待叫号。`,
        showCancel: false,
        confirmText: '知道了',
        success: () => {
          // 返回首页
          Taro.switchTab({ url: '/pages/appointment/index' });
        },
      });
    } catch (error: any) {
      console.error('[签到] 失败:', error);
      Taro.showToast({
        title: error.message || '签到失败',
        icon: 'none',
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <View className="checkin-select-page">
        <View className="loading-state">加载中...</View>
      </View>
    );
  }

  return (
    <View className="checkin-select-page">
      {appointments.length === 0 ? (
        <View className="empty-state">
          <Empty description="暂无待签到的预约" />
          <Text className="empty-tip">
            您在该门店今日没有待签到的预约，请确认预约信息
          </Text>
        </View>
      ) : (
        <>
          <View className="page-header">
            <Text className="header-title">选择要签到的预约</Text>
            <Text className="header-desc">
              您有 {appointments.length} 个待签到的预约
            </Text>
          </View>

          <View className="appointment-list">
            {appointments.map((item) => {
              const isDisabled = item.signInStatus === 'early' || item.signInStatus === 'late';
              return (
                <View
                  key={item.id}
                  className={`appointment-card ${selectedId === item.id ? 'selected' : ''} ${isDisabled ? 'disabled' : ''}`}
                  onClick={() => handleSelect(item.id, item.signInStatus)}
                >
                  <View className="card-icon">
                    <DoctorIcon size={40} color="#C41E3A" />
                  </View>
                  <View className="card-content">
                    <View className="card-header">
                      <Text className="doctor-name">{item.doctorName || '医生'}</Text>
                      <Text className="dept-name">{item.departmentName}</Text>
                    </View>
                    <Text className="patient-name">就诊人：{item.patientName}</Text>
                    <View className="schedule-info">
                      <Text className="schedule-date">{item.scheduleDate}</Text>
                      <Text className="schedule-time">
                        {item.startTime ? item.startTime.substring(0, 5) : (item.timeSlot !== null ? TIME_SLOT_MAP[item.timeSlot] : '')}
                        {item.endTime ? ` ~ ${item.endTime.substring(0, 5)}` : ''}
                      </Text>
                    </View>
                    {item.signInMessage && (
                      <View className={`signin-status ${item.signInStatus}`}>
                        <Text className="status-text">{item.signInMessage}</Text>
                      </View>
                    )}
                  </View>
                  {selectedId === item.id && !isDisabled && (
                    <View className="selected-icon">
                      <CheckCircleIcon size={24} color="#10B981" />
                    </View>
                  )}
                </View>
              );
            })}
          </View>

          <View className="action-bar">
            <Button
              type="primary"
              block
              loading={submitting}
              disabled={!selectedId}
              onClick={handleSignIn}
            >
              确认签到
            </Button>
          </View>
        </>
      )}

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={() => {
          setShowLoginPopup(false);
          if (!getToken()) {
            Taro.navigateBack();
          }
        }}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default CheckinSelectPage;

