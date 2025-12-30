import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button, Radio } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { doctorApi, userApi, appointmentApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import { getToken } from '../../../utils/auth';
import type { Doctor, Patient } from '@hospital/shared';
import { DoctorIcon } from '../../../components/Icons';
import './index.less';

const BookingPage = () => {
  const router = useRouter();
  const { doctorId, scheduleId, date, timeSlot } = router.params;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');

  useEffect(() => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      Taro.navigateTo({ url: '/pages/login/index' });
      return;
    }
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [doctorData, patientsData] = await Promise.all([
        doctorApi.getDetail(doctorId!),
        userApi.getPatients(),
      ]);
      setDoctor(doctorData);
      setPatients(patientsData);

      const defaultPatient = patientsData.find((p) => p.isDefault) || patientsData[0];
      if (defaultPatient) {
        setSelectedPatientId(defaultPatient.id);
      }
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedPatientId) {
      Taro.showToast({ title: '请选择就诊人', icon: 'none' });
      return;
    }

    const result = await Taro.showModal({
      title: '确认预约',
      content: '确定要预约吗？',
    });

    if (!result.confirm) return;

    setSubmitting(true);
    try {
      const appointment = await appointmentApi.create({
        scheduleId: scheduleId!,
        patientId: selectedPatientId,
      });

      Taro.showToast({ title: '预约成功', icon: 'success' });
      Taro.redirectTo({
        url: `/packageBooking/pages/booking/result?appointmentNo=${appointment.appointmentNo}`,
      });
    } catch (error: any) {
      Taro.showToast({ title: error.message || '预约失败', icon: 'none' });
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddPatient = () => {
    Taro.navigateTo({ url: '/packageProfile/pages/patient/edit' });
  };

  if (loading) {
    return (
      <View className="booking-page">
        <View className="loading">加载中...</View>
      </View>
    );
  }

  return (
    <View className="booking-page">
      {/* 医生信息摘要 */}
      <View className="doctor-summary">
        <View className="doctor-avatar">
          <DoctorIcon size={36} color="#4F46E5" />
        </View>
        <View className="doctor-info">
          <Text className="doctor-name">{doctor?.name} · {doctor?.title}</Text>
          <Text className="doctor-dept">{doctor?.departmentName}</Text>
        </View>
      </View>

      {/* 预约信息 */}
      <View className="card">
        <Text className="card-title">预约信息</Text>
        <View className="info-row">
          <Text className="label">就诊日期</Text>
          <Text className="value">{date}</Text>
        </View>
        <View className="info-row">
          <Text className="label">就诊时段</Text>
          <Text className="value">{TIME_SLOT_MAP[timeSlot || 'AM']}</Text>
        </View>
        <View className="info-row">
          <Text className="label">挂号费用</Text>
          <Text className="value fee">¥{doctor?.registrationFee || 0}</Text>
        </View>
      </View>

      {/* 选择就诊人 */}
      <View className="card">
        <View className="card-header">
          <Text className="card-title">选择就诊人</Text>
          <Text className="add-btn" onClick={handleAddPatient}>+ 新增</Text>
        </View>

        {patients.length === 0 ? (
          <View className="empty-patient">
            <Text>请先添加就诊人</Text>
            <Button type="primary" size="small" onClick={handleAddPatient}>
              添加就诊人
            </Button>
          </View>
        ) : (
          <Radio.Group
            value={selectedPatientId}
            onChange={(value) => setSelectedPatientId(value as string)}
          >
            {patients.map((patient) => (
              <View key={patient.id} className="patient-item">
                <Radio value={patient.id}>
                  <View className="patient-info">
                    <Text className="patient-name">{patient.name}</Text>
                    <Text className="patient-phone">
                      {patient.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
                    </Text>
                    {patient.isDefault && <Text className="default-tag">默认</Text>}
                  </View>
                </Radio>
              </View>
            ))}
          </Radio.Group>
        )}
      </View>

      {/* 预约须知 */}
      <View className="notice-card">
        <Text className="notice-title">预约须知</Text>
        <View className="notice-list">
          <View className="notice-item">
            <Text>请按预约时间提前15分钟到达医院</Text>
          </View>
          <View className="notice-item">
            <Text>就诊时请携带有效身份证件</Text>
          </View>
          <View className="notice-item">
            <Text>如需取消预约，请提前24小时操作</Text>
          </View>
        </View>
      </View>

      {/* 底部提交 */}
      <View className="footer">
        <View className="total">
          <Text className="total-label">合计：</Text>
          <Text className="total-price">¥{doctor?.registrationFee || 0}</Text>
        </View>
        <Button
          className="submit-btn"
          type="primary"
          loading={submitting}
          disabled={!selectedPatientId}
          onClick={handleSubmit}
        >
          确认预约
        </Button>
      </View>
    </View>
  );
};

export default BookingPage;
