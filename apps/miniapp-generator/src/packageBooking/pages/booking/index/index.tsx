import { View, Text, Image, Textarea } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button, Radio } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { doctorApi, userApi, appointmentApi, bookingNoticeApi, settingsApi } from '@hospital/api';
import type { BookingNotice, TimePeriodConfig } from '@hospital/api';
import { TIME_SLOT_MAP, getPeriodNameFromTime } from '@hospital/shared';
import { useProtectedPage } from '../../../../hooks/useProtectedPage';
import { useSubscribeMessage } from '../../../../hooks/useSubscribeMessage';
import { useTenantGuard } from '../../../../hooks/useTenantGuard';
import { useApplyThemeNavigationBar, useThemePrimaryColor } from '../../../../utils/theme';
import {
  buildBookingResultUrl,
  getPaymentPreparationFailure,
  getPaymentRequestFailure,
  verifyPaymentResult,
} from '../../../../utils/payment';
import LoginPopup from '../../../../components/LoginPopup';
import type { Doctor, Patient } from '@hospital/shared';
import { DoctorIcon, UserIcon } from '../../../../components/Icons';
import { getImageUrl } from '../../../../utils/url';
import { useTemplate } from '../../../../contexts/TemplateContext';
import './index.less';

interface ConsultationFeeResponse {
  amount: number; // 分
}

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

/** 「预约注意事项」默认文案（对齐竞品确认页），可被模板 tone.custom（bookingNotice1~3）覆盖 */
const DEFAULT_BOOKING_NOTICES = [
  '由于医生接诊量较大，每天看诊量有限，请提前挂号；挂号后医助助理会与您联系，确认具体到店时间与就诊地点，避免排队等候或跑空；',
  '就诊前12小时可在小程序内自行取消预约；就诊当日12小时内的预约无法自行取消，如遇特殊情况需取消，请联系在线客服；',
  '如咨询代煎进度、现场排队情况，请添加医助微信咨询。',
];

const BookingPage = () => {
  const primaryColor = useThemePrimaryColor();
  const { tone } = useTemplate();
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { doctorId, scheduleId, date, timeSlot, storeId, departmentId } = router.params;
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

  // 诊费
  const [consultationFee, setConsultationFee] = useState<number | null>(null);

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

      // 获取诊费
      if (storeId && departmentId) {
        try {
          const feeData = await appointmentApi.getConsultationFee({
            doctorId: doctorId!,
            storeId,
            departmentId,
          }) as ConsultationFeeResponse;
          setConsultationFee(feeData.amount || null);
        } catch (error) {
          // 无诊费设置
          setConsultationFee(null);
        }
      }
    } catch (error) {
      console.error('加载数据失败', error);
    } finally {
      setLoading(false);
    }
  }, [doctorId, storeId, departmentId]);

  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: loadData,
    clear: () => {
      setDoctor(null);
      setPatients([]);
      setSelectedPatientId('');
      setBookingNotices([]);
      setConsultationFee(null);
      setLoading(false);
    },
  });

  // 获取选中的就诊人
  const selectedPatient = patients.find(p => p.id === selectedPatientId);
  const { requireWritable } = useTenantGuard();
  const { subscribeAppointment } = useSubscribeMessage();

  // 病情主诉是否已填写（必填校验）
  const hasSymptom = symptomDescription.trim().length > 0;

  // 预约时间展示用星期（如 2026-10-23 周五）
  const bookingWeekday = date && !Number.isNaN(new Date(date).getTime())
    ? WEEKDAY_NAMES[new Date(date).getDay()]
    : '';

  // 预约注意事项：机构后台配置的须知优先，其次模板 tone.custom（bookingNotice1~3）覆盖，最后用默认三条
  const noticeOverride = [1, 2, 3]
    .map((i) => tone.custom?.[`bookingNotice${i}`])
    .filter((text): text is string => Boolean(text && text.trim()));
  const remoteNotices = bookingNotices
    .map((notice) => ({ title: notice.title, content: notice.content || '' }))
    .filter((notice) => notice.content.trim().length > 0);
  const displayNotices: Array<{ title?: string; content: string }> =
    remoteNotices.length > 0
      ? remoteNotices
      : noticeOverride.length > 0
        ? noticeOverride.map((content) => ({ content }))
        : DEFAULT_BOOKING_NOTICES.map((content) => ({ content }));

  const handleSubmit = async () => {
    // 租户状态守卫：暂停时阻断写操作
    try {
      requireWritable();
    } catch {
      return;
    }

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
        const confirmText = consultationFee
          ? `确认支付 ¥${(consultationFee / 100).toFixed(2)} 并预约？`
          : '确定要预约吗？';

        const result = await Taro.showModal({
          title: '确认预约',
          content: confirmText,
        });

        if (!result.confirm) {
          setSubmitting(false);
          return;
        }
      }

      // 创建预约
      const createResult = await appointmentApi.create({
        scheduleId: validScheduleId,
        patientId: validPatientId,
        symptomDescription: symptomDescription.trim() || undefined,
      });

      // 判断返回值类型
      const appointment = 'appointment' in createResult ? createResult.appointment : createResult;
      const paymentParams = 'payment_params' in createResult ? createResult.payment_params : undefined;
      const paymentRequired =
        'payment_required' in createResult ? Boolean(createResult.payment_required) : appointment.status === 0;

      subscribeAppointment();

      if (paymentRequired && paymentParams) {
        // 需要支付，调用微信支付
        try {
          await Taro.requestPayment({
            timeStamp: paymentParams.timeStamp,
            nonceStr: paymentParams.nonceStr,
            package: paymentParams.package,
            signType: paymentParams.signType as any,
            paySign: paymentParams.paySign,
          });

          Taro.redirectTo({
            url: buildBookingResultUrl(appointment.appointmentNo, 'success'),
          });
        } catch (paymentError: any) {
          console.error('支付失败', paymentError);

          // 二次确认：微信支付可能实际成功但本地 Promise reject
          const actuallyPaid = await verifyPaymentResult(appointmentApi.getPaymentStatus, appointment.id);
          if (actuallyPaid) {
            Taro.redirectTo({
              url: buildBookingResultUrl(appointment.appointmentNo, 'success'),
            });
            return;
          }

          const result = getPaymentRequestFailure(paymentError);
          Taro.redirectTo({
            url: buildBookingResultUrl(appointment.appointmentNo, result.status, result.message),
          });
        }
      } else if (paymentRequired) {
        const paymentParamError = 'payment_param_error' in createResult ? createResult.payment_param_error : undefined;
        const result = getPaymentPreparationFailure(
          paymentParamError ? { message: paymentParamError } : null,
          '订单已创建，但当前无法直接拉起支付，请前往预约详情重新支付。'
        );
        Taro.redirectTo({
          url: buildBookingResultUrl(appointment.appointmentNo, result.status, result.message),
        });
      } else {
        Taro.redirectTo({
          url: buildBookingResultUrl(appointment.appointmentNo, 'confirmed', '预约已提交成功。'),
        });
      }
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
            <Text className="label">就诊科室</Text>
            <Text className="value">{doctor?.departmentName || '-'}</Text>
          </View>
          <View className="info-row">
            <Text className="label">预约时间</Text>
            <Text className="value">
              {date}
              {bookingWeekday ? ` ${bookingWeekday}` : ''}
              {` ${startTime ? getPeriodNameFromTime(startTime, timePeriods) : TIME_SLOT_MAP[timeSlot || 'morning']}`}
              {startTime && endTime && ` ${startTime}-${endTime}`}
            </Text>
          </View>
          {/* 诊费展示（后端 /consultation-fees/amount 返回的是初诊金额） */}
          {consultationFee && consultationFee > 0 && (
            <View className="info-row">
              <Text className="label">挂号费用</Text>
              <Text className="value fee">
                ¥{(consultationFee / 100).toFixed(2)}
                <Text className="fee-tag">（初诊）</Text>
              </Text>
            </View>
          )}
          {hospitalName && (
            <View className="info-row">
              <Text className="label">机构名称</Text>
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

        {/* 病情主诉输入（必填） */}
        <View className="symptom-section">
          <Text className="symptom-label">
            <Text className="symptom-required">*</Text>
            病情主诉
          </Text>
          <Textarea
            className="symptom-input"
            placeholder="为了提供更好的诊疗效果，请填写病情主诉"
            maxlength={500}
            value={symptomDescription}
            onInput={(e) => setSymptomDescription(e.detail.value)}
          />
          {!hasSymptom && (
            <Text className="symptom-required-tip">病情主诉为必填项，请填写后再提交预约</Text>
          )}
          <Text className="symptom-count">{symptomDescription.length}/500</Text>
        </View>
      </View>

      {/* 底部：预约注意事项 */}
      <View className="notice-card">
        <Text className="notice-title">预约注意事项</Text>
        <View className="notice-list">
          {displayNotices.map((notice, index) => (
            <View key={`${index}-${notice.content.slice(0, 12)}`} className="notice-item">
              {notice.title && <Text className="notice-item-title">{notice.title}</Text>}
              <Text className="notice-content">{`${index + 1}、${notice.content}`}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* 底部提交 */}
      <View className="footer">
        <Button
          className="submit-btn"
          type="primary"
          loading={submitting}
          disabled={!selectedPatientId || !hasSymptom}
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
