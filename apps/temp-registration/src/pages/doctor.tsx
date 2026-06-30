/**
 * 医生选择页面
 * 临时挂号第二步：选择就诊医生
 */
import React, { useState, useEffect } from 'react';
import { Image, Skeleton, Toast, Tag } from 'antd-mobile';
import { motion } from 'framer-motion';
import { doctorApi } from '@hospital/api';
import type { Doctor } from '@hospital/shared';
import { Card, StepIndicator, PageHeader, fadeInUp, stagger } from '@/components/ui';
import { saveRegistrationData } from '@/utils/storage';
import { navigation } from '@/utils/navigation';

// 挂号流程步骤
const steps = [
  { key: 'department', title: '选科室' },
  { key: 'doctor', title: '选医生' },
  { key: 'time', title: '选时段' },
  { key: 'patient', title: '填信息' },
  { key: 'confirm', title: '确认' },
];

const DoctorPage: React.FC = () => {
  const searchParams = new URLSearchParams(window.location.search);
  const departmentId = searchParams.get('departmentId');
  const departmentName = searchParams.get('departmentName') || '';

  const [loading, setLoading] = useState(true);
  const [doctors, setDoctors] = useState<Doctor[]>([]);

  useEffect(() => {
    if (!departmentId) {
      Toast.show({
        icon: 'fail',
        content: '请先选择科室',
      });
      navigation.replace('/');
      return;
    }
    loadDoctors();
  }, [departmentId]);

  const loadDoctors = async () => {
    if (!departmentId) return;

    try {
      const data = await doctorApi.getByDepartment(departmentId);
      setDoctors(data);
    } catch (error) {
      console.error('加载医生列表失败', error);
      Toast.show({
        icon: 'fail',
        content: '加载医生失败，请重试',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDoctor = (doctor: Doctor) => {
    saveRegistrationData({
      doctorId: doctor.id,
      doctorName: doctor.name,
      doctorTitle: doctor.title,
      doctorAvatar: doctor.avatar,
    });
    navigation.push(`/time-slot?doctorId=${doctor.id}`);
  };

  // 获取职称颜色
  const getTitleColor = (title: string) => {
    if (title?.includes('主任')) return 'primary';
    if (title?.includes('副主任')) return 'success';
    if (title?.includes('主治')) return 'warning';
    return 'default';
  };

  return (
    <div className="min-h-screen bg-background">
      {/* 步骤指示器 */}
      <StepIndicator steps={steps} currentStep={1} />

      {/* 页面头部 */}
      <PageHeader 
        title="选择医生" 
        subtitle={departmentName ? decodeURIComponent(departmentName) : ''}
      />

      {/* 医生列表 */}
      <div className="px-4 py-4">
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} variant="default" padding="md">
                <div className="flex gap-4">
                  <Skeleton.Paragraph lineCount={1} animated className="w-16" />
                  <div className="flex-1">
                    <Skeleton.Paragraph lineCount={3} animated />
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : doctors.length === 0 ? (
          <div className="py-16 text-center">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
              <svg className="w-10 h-10 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                      d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <p className="text-muted-foreground">该科室暂无出诊医生</p>
            <button 
              onClick={() => navigation.back()}
              className="mt-4 text-primary font-medium"
            >
              返回选择其他科室
            </button>
          </div>
        ) : (
          <motion.div
            variants={stagger}
            initial="hidden"
            animate="visible"
            className="space-y-4"
          >
            {doctors.map((doctor) => (
              <motion.div key={doctor.id} variants={fadeInUp}>
                <Card 
                  variant="default" 
                  padding="md" 
                  hoverable
                  className="cursor-pointer active:scale-[0.99] transition-transform"
                  onClick={() => handleSelectDoctor(doctor)}
                >
                  <div className="flex gap-4">
                    {/* 医生头像 */}
                    <div className="flex-shrink-0">
                      <Image
                        src={doctor.avatar || ''}
                        width={72}
                        height={72}
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
                    </div>

                    {/* 医生信息 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-lg text-foreground">{doctor.name}</span>
                        {doctor.title && (
                          <Tag color={getTitleColor(doctor.title)} className="!text-xs">
                            {doctor.title}
                          </Tag>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{doctor.departmentName}</p>
                      {doctor.specialty && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          <span className="text-foreground font-medium">擅长：</span>
                          {doctor.specialty}
                        </p>
                      )}
                    </div>

                    {/* 选择按钮 */}
                    <div className="flex flex-col items-end justify-center">
                      <div className="flex items-center gap-1 text-primary text-sm">
                        <span>选择</span>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </div>
                  </div>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default DoctorPage;

