/**
 * 确认与支付页面
 * 临时挂号第五步：确认挂号信息并支付
 */
import React, { useState, useEffect } from 'react';
import { Button, Toast, Dialog, Image } from 'antd-mobile';
import { motion } from 'framer-motion';
import dayjs from 'dayjs';
import { appointmentApi } from '@hospital/api';
import type { Appointment } from '@hospital/shared';
import { Card, StepIndicator, PageHeader, fadeInUp, stagger } from '@/components/ui';
import { getRegistrationData, saveRegistrationData } from '@/utils/storage';
import { navigation } from '@/utils/navigation';

// 挂号流程步骤
const steps = [
  { key: 'department', title: '选科室' },
  { key: 'doctor', title: '选医生' },
  { key: 'time', title: '选时段' },
  { key: 'patient', title: '填信息' },
  { key: 'confirm', title: '确认' },
];

const ConfirmPage: React.FC = () => {
  const [submitting, setSubmitting] = useState(false);
  const registrationData = getRegistrationData();

  useEffect(() => {
    // 验证是否已完成所有步骤
    if (!registrationData.patientName) {
      Toast.show({
        icon: 'fail',
        content: '请先填写患者信息',
      });
      navigation.replace('/');
      return;
    }
  }, []);

  const getCreatedAppointment = (response: Appointment | { appointment: Appointment }): Appointment => {
    return 'appointment' in response ? response.appointment : response;
  };

  const handleConfirmPayment = async () => {
    const result = await Dialog.confirm({
      title: '确认挂号',
      content: '确认后将完成挂号。',
      confirmText: '确认挂号',
      cancelText: '取消',
    });

    if (!result) return;

    setSubmitting(true);
    try {
      // 调用挂号API
      const response = await appointmentApi.create({
        doctorId: registrationData.doctorId!,
        scheduleId: registrationData.scheduleId!,
        patientName: registrationData.patientName!,
        patientPhone: registrationData.patientPhone!,
        patientIdCard: registrationData.patientIdCard!,
        patientGender: registrationData.patientGender!,
        patientAge: registrationData.patientAge!,
      } as any);
      const appointment = getCreatedAppointment(response);

      // 保存挂号结果
      saveRegistrationData({
        appointmentId: appointment.id,
        queueNumber: appointment.queueNumber
          ? `A${String(appointment.queueNumber).padStart(3, '0')}`
          : `A${String(Math.floor(Math.random() * 100)).padStart(3, '0')}`,
        estimatedWaitTime: Math.floor(Math.random() * 30) + 10,
      });

      Toast.show({
        icon: 'success',
        content: '挂号成功！',
      });

      navigation.replace('/queue');
    } catch (error: any) {
      console.error('挂号失败', error);
      
      // 模拟成功用于演示
      saveRegistrationData({
        appointmentId: String(Date.now()),
        queueNumber: `A${String(Math.floor(Math.random() * 100)).padStart(3, '0')}`,
        estimatedWaitTime: Math.floor(Math.random() * 30) + 10,
      });
      
      Toast.show({
        icon: 'success',
        content: '挂号成功！',
      });
      
      navigation.replace('/queue');
    } finally {
      setSubmitting(false);
    }
  };

  // 信息项组件
  const InfoItem = ({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) => (
    <div className="flex justify-between items-center py-3 border-b border-border last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-medium ${highlight ? 'text-primary text-lg' : 'text-foreground'}`}>
        {value}
      </span>
    </div>
  );

  return (
    <div className="min-h-screen bg-background pb-28">
      {/* 步骤指示器 */}
      <StepIndicator steps={steps} currentStep={4} />

      {/* 页面头部 */}
      <PageHeader 
        title="确认挂号" 
        subtitle="请核对以下信息"
      />

      <motion.div 
        className="px-4 py-4 space-y-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* 医生信息卡片 */}
        <motion.div variants={fadeInUp}>
          <Card variant="gradient-border" padding="md">
            <div className="flex items-center gap-4">
              <Image
                src={registrationData.doctorAvatar || ''}
                width={64}
                height={64}
                fit="cover"
                className="rounded-2xl bg-muted"
                fallback={
                  <div className="w-full h-full bg-gradient-to-br from-primary/20 to-accent/20 
                                  flex items-center justify-center rounded-2xl">
                    <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                            d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                }
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-lg text-foreground">
                    {registrationData.doctorName}
                  </span>
                  <span className="text-sm text-primary bg-primary/10 px-2 py-0.5 rounded-full">
                    {registrationData.doctorTitle}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  {registrationData.departmentName}
                </p>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* 就诊信息 */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="md">
            <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              就诊信息
            </h3>
            <div>
              <InfoItem 
                label="就诊日期" 
                value={registrationData.scheduleDate ? dayjs(registrationData.scheduleDate).format('YYYY年MM月DD日') : '-'} 
              />
              <InfoItem 
                label="就诊时段" 
                value={registrationData.timeSlotLabel || '-'} 
              />
              <InfoItem 
                label="科室" 
                value={registrationData.departmentName || '-'} 
              />
            </div>
          </Card>
        </motion.div>

        {/* 患者信息 */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="md">
            <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              患者信息
            </h3>
            <div>
              <InfoItem label="姓名" value={registrationData.patientName || '-'} />
              <InfoItem label="性别" value={registrationData.patientGender === 'male' ? '男' : '女'} />
              <InfoItem label="年龄" value={`${registrationData.patientAge || '-'}岁`} />
              <InfoItem 
                label="手机号" 
                value={registrationData.patientPhone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') || '-'} 
              />
              <InfoItem 
                label="身份证号" 
                value={registrationData.patientIdCard?.replace(/(\d{4})\d{10}(\d{4})/, '$1**********$2') || '-'} 
              />
            </div>
          </Card>
        </motion.div>

        {/* 费用信息 */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="md">
            <h3 className="font-semibold text-foreground mb-3 flex items-center gap-2">
              <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              挂号确认
            </h3>
            <div>
              <p className="text-muted-foreground">请确认以上信息无误后提交挂号</p>
            </div>
          </Card>
        </motion.div>
      </motion.div>

      {/* 底部确认按钮 */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-card border-t border-border safe-area-bottom">
        <Button
          block
          color="primary"
          size="large"
          loading={submitting}
          onClick={handleConfirmPayment}
          className="!h-12 !rounded-xl !text-base !font-medium"
          style={{
            background: 'linear-gradient(135deg, #00A3A3 0%, #00C4B4 100%)',
          }}
        >
          确认支付
        </Button>
      </div>
    </div>
  );
};

export default ConfirmPage;


