import { View, Text, Image, Textarea } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button, Radio } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { doctorApi, userApi, appointmentApi, bookingNoticeApi, settingsApi } from '@hospital/api';
import type { BookingNotice, TimePeriodConfig } from '@hospital/api';
import { TIME_SLOT_MAP, getPeriodNameFromTime } from '@hospital/shared';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import { useThemePrimaryColor } from '../../../utils/theme';
import LoginPopup from '../../../components/LoginPopup';
import type { Doctor, Patient } from '@hospital/shared';
import { DoctorIcon, UserIcon } from '../../../components/Icons';
import { getImageUrl } from '../../../utils/url';
import './index.less';

const BookingPage = () => {
  const primaryColor = useThemePrimaryColor();
  const router = useRouter();
  const { doctorId, scheduleId, date, timeSlot } = router.params;
  // 解码时间参数（URL 中的 %3A 需要解码为冒号）
  const startTime = router.params.startTime ? decodeURIComponent(router.params.startTime) : undefined;
  const endTime = router.params.endTime ? decodeURIComponent(router.params.endTime) : undefined;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string>('');
  
  // 病情描述
  const [symptomDescription, setSymptomDescription] = useState('');
  
  // 预约须知
  const [bookingNotices, setBookingNotices] = useState<BookingNotice[]>([]);
  
  // 医院信息
  const [hospitalName, setHospitalName] = useState('');
  const [hospitalAddress, setHospitalAddress] = useState('');
  
  // 时段配置
  const [timePeriods, setTimePeriods] = useState<TimePeriodConfig[]>([]);

  const loadData = useCallback(async () => {
    try {
      const [doctorData, patientsData, notices, hospitalInfo, timePeriodsRes] = await Promise.all([
        doctorApi.getDetail(doctorId!),
        userApi.getPatients(),
        bookingNoticeApi.getPublicList('BOOKING').catch(() => []),
        settingsApi.getHospitalInfo().catch(() => null),
        // 获取门店时段配置
        settingsApi.getTimePeriods().catch(() => ({ periods: [], isCustom: false })),
      ]);
      setDoctor(doctorData);
      setPatients(patientsData);
      setBookingNotices(notices);
      setTimePeriods(timePeriodsRes.periods || []);
      
      if (hospitalInfo) {
        setHospitalName(hospitalInfo.hospitalName || '');
        setHospitalAddress(hospitalInfo.address || '');
      }

      const defaultPatient = patientsData.find((p) => p.isDefault) || patientsData[0];
      if (defaultPatient) {
        setSelectedPatientId(defaultPatient.id);
      }
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  }, [doctorId]);

  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: loadData,
    clear: () => {
      setDoctor(null);
      setPatients([]);
      setSelectedPatientId('');
      setBookingNotices([]);
      setLoading(false);
    },
  });

  // 获取选中的就诊人
  const selectedPatient = patients.find(p => p.id === selectedPatientId);

  const handleSubmit = async () => {
    // 严格检查参数有效性（避免空字符串或 undefined）
    const validScheduleId = scheduleId?.trim();
    const validPatientId = selectedPatientId?.trim();
    
    if (!validScheduleId) {
      Taro.showToast({ title: '排班信息无效，请返回重新选择', icon: 'none' });
      return;
    }
    
    if (!validPatientId) {
      Taro.showToast({ title: '请选择就诊人', icon: 'none' });
      return;
    }

    setSubmitting(true);
    
    try {
      // 检查是否有同一天同一时段的重复预约
      const duplicateCheck = await appointmentApi.checkDuplicate(validScheduleId, validPatientId);
      
      if (duplicateCheck.hasDuplicate) {
        // 有重复预约，提示用户确认
        const existingAppts = duplicateCheck.appointments;
        const doctorNames = existingAppts.map(a => a.doctorName || '未知医生').join('、');
        
        const confirmResult = await Taro.showModal({
          title: '重复预约提醒',
          content: `您在同一天${timeSlot === 'morning' ? '上午' : '下午'}已预约了${doctorNames}的号，是否继续预约？`,
          confirmText: '继续预约',
          cancelText: '取消',
        });

        if (!confirmResult.confirm) {
          setSubmitting(false);
          return;
        }
      } else {
        // 没有重复预约，正常确认
        const result = await Taro.showModal({
          title: '确认预约',
          content: '确定要预约吗？',
        });

        if (!result.confirm) {
          setSubmitting(false);
          return;
        }
      }

      // 创建预约
      const appointment = await appointmentApi.create({
        scheduleId: validScheduleId,
        patientId: validPatientId,
        symptomDescription: symptomDescription.trim() || undefined,
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
      {/* 顶部：就诊人信息卡片 */}
      <View className="patient-card">
        <View className="patient-card-header">
          <Text className="patient-card-title">就诊人信息</Text>
          <Text className="change-btn" onClick={handleAddPatient}>+ 新增/切换</Text>
        </View>
        
        {patients.length === 0 ? (
          <View className="empty-patient">
            <Text>请先添加就诊人</Text>
            <Button type="primary" size="small" onClick={handleAddPatient}>
              添加就诊人
            </Button>
          </View>
        ) : (
          <>
            {selectedPatient ? (
              <View className="selected-patient">
                <View className="patient-avatar">
                  <UserIcon size={28} color={primaryColor} />
                </View>
                <View className="patient-details">
                  <Text className="patient-name">{selectedPatient.name}</Text>
                  <Text className="patient-phone">
                    {selectedPatient.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
                  </Text>
                </View>
                {selectedPatient.isDefault && <Text className="default-tag">默认</Text>}
              </View>
            ) : (
              <View className="select-patient-tip">
                <Text>请选择就诊人</Text>
              </View>
            )}
            
            {/* 就诊人选择列表（可折叠或直接显示） */}
            {patients.length > 1 && (
              <View className="patient-list">
                <Radio.Group
                  value={selectedPatientId}
                  onChange={(value) => setSelectedPatientId(value as string)}
                >
                  {patients.map((patient) => (
                    <View key={patient.id} className="patient-item">
                      <Radio value={patient.id}>
                        <View className="patient-info">
                          <Text className="name">{patient.name}</Text>
                          <Text className="phone">
                            {patient.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
                          </Text>
                        </View>
                      </Radio>
                    </View>
                  ))}
                </Radio.Group>
              </View>
            )}
          </>
        )}
      </View>

      {/* 中间：预约信息 */}
      <View className="appointment-card">
        <Text className="card-title">预约信息</Text>
        
        {/* 医生信息 */}
        <View className="doctor-row">
          <View className="doctor-avatar">
            {doctor?.avatar ? (
              <Image src={getImageUrl(doctor.avatar)} mode="aspectFill" />
            ) : (
              <DoctorIcon size={36} color={primaryColor} />
            )}
          </View>
          <View className="doctor-info">
            <View className="doctor-name-row">
              <Text className="doctor-name">{doctor?.name}</Text>
              {doctor?.title && <Text className="doctor-title">{doctor.title}</Text>}
            </View>
            <Text className="doctor-dept">{doctor?.departmentName}</Text>
          </View>
        </View>
        
        {/* 预约详情 */}
        <View className="info-list">
          <View className="info-row">
            <Text className="label">预约时间</Text>
            <Text className="value">
              {date} {startTime ? getPeriodNameFromTime(startTime, timePeriods) : TIME_SLOT_MAP[timeSlot || 'morning']}
              {startTime && endTime && ` (${startTime}-${endTime})`}
            </Text>
          </View>
          {hospitalName && (
            <View className="info-row">
              <Text className="label">就诊机构</Text>
              <Text className="value">{hospitalName}</Text>
            </View>
          )}
          {hospitalAddress && (
            <View className="info-row">
              <Text className="label">就诊地点</Text>
              <Text className="value address">{hospitalAddress}</Text>
            </View>
          )}
        </View>
        
        {/* 病情描述输入 */}
        <View className="symptom-section">
          <Text className="symptom-label">病情描述（选填）</Text>
          <Textarea
            className="symptom-input"
            placeholder="请简要描述您的症状，方便医生提前了解病情..."
            maxlength={500}
            value={symptomDescription}
            onInput={(e) => setSymptomDescription(e.detail.value)}
          />
          <Text className="symptom-count">{symptomDescription.length}/500</Text>
        </View>
      </View>

      {/* 底部：预约注意事项 */}
      {bookingNotices.length > 0 && (
        <View className="notice-card">
          <Text className="notice-title">预约注意事项</Text>
          <View className="notice-list">
            {bookingNotices.map((notice) => (
              <View key={notice.id} className="notice-item">
                {notice.title && <Text className="notice-item-title">{notice.title}</Text>}
                <Text className="notice-content">{notice.content}</Text>
              </View>
            ))}
          </View>
        </View>
      )}
      
      {/* 默认须知（如果没有配置的须知） */}
      {bookingNotices.length === 0 && (
        <View className="notice-card">
          <Text className="notice-title">预约须知</Text>
          <View className="notice-list">
            <View className="notice-item">
              <Text className="notice-content">请按预约时间提前15分钟到达医院</Text>
            </View>
            <View className="notice-item">
              <Text className="notice-content">就诊时请携带有效身份证件</Text>
            </View>
            <View className="notice-item">
              <Text className="notice-content">如需取消预约，请提前24小时操作</Text>
            </View>
          </View>
        </View>
      )}

      {/* 底部提交 */}
      <View className="footer">
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

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default BookingPage;
