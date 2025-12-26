import { NavBar, Image, Skeleton, Toast } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { doctorApi, scheduleApi } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import type { Doctor, AvailableSchedule } from '@hospital/shared';
import dayjs from 'dayjs';
import { Card, Button, SectionLabel } from '@/components/ui';
import { fadeInUp, stagger, viewportOptions } from '@/components/ui/animations';

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

const DoctorDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [schedules, setSchedules] = useState<AvailableSchedule[]>([]);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    try {
      const [doctorData, scheduleData] = await Promise.all([
        doctorApi.getDetail(id!),
        scheduleApi.getAvailable(id!, 14),
      ]);
      setDoctor(doctorData);
      setSchedules(scheduleData);
    } catch (error) {
      console.error('加载数据失败', error);
      Toast.show({ content: '加载失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const handleBook = (schedule: AvailableSchedule) => {
    if (schedule.availableSlots <= 0) {
      Toast.show({ content: '该时段已约满' });
      return;
    }
    history.push(`/booking/${id}?scheduleId=${schedule.id}&date=${schedule.scheduleDate}&timeSlot=${schedule.timeSlot}`);
  };

  // Group schedules by date
  const groupedSchedules = schedules.reduce((acc, schedule) => {
    const date = schedule.scheduleDate;
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(schedule);
    return acc;
  }, {} as Record<string, AvailableSchedule[]>);

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          医生详情
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={10} animated />
        </div>
      </div>
    );
  }

  if (!doctor) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          医生详情
        </NavBar>
        <div className="flex items-center justify-center h-64 text-muted-foreground">
          医生信息不存在
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-6">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        医生详情
      </NavBar>
      
      {/* Doctor Info Card */}
      <motion.div
        className="p-4"
        variants={fadeInUp}
        initial="hidden"
        animate="visible"
      >
        <Card variant="elevated" padding="lg">
          <div className="flex gap-4 mb-6">
            <Image 
              src={doctor.avatar || ''} 
              width={88} 
              height={88} 
              fit="cover" 
              className="rounded-2xl bg-muted flex-shrink-0"
            />
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-semibold text-xl text-foreground">
                  {doctor.name}
                </span>
                {doctor.title && (
                  <span className="text-xs text-accent bg-accent/10 px-2 py-1 rounded-full">
                    {doctor.title}
                  </span>
                )}
              </div>
              <p className="text-muted-foreground mb-2">{doctor.departmentName}</p>
              <p className="text-accent font-semibold text-lg">
                挂号费：¥{doctor.registrationFee}
              </p>
            </div>
          </div>

          {/* Specialty */}
          <div className="mb-4">
            <h4 className="font-medium text-foreground mb-2">擅长</h4>
            <p className="text-muted-foreground text-sm leading-relaxed">
              {doctor.specialty || '暂无信息'}
            </p>
          </div>

          {/* Introduction */}
          <div>
            <h4 className="font-medium text-foreground mb-2">简介</h4>
            <p className="text-muted-foreground text-sm leading-relaxed">
              {doctor.introduction || '暂无简介'}
            </p>
          </div>
        </Card>
      </motion.div>

      {/* Schedule Card */}
      <motion.div
        className="px-4"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={viewportOptions}
      >
        <Card variant="default" padding="lg">
          <div className="mb-4">
            <SectionLabel animated={false}>选择就诊时间</SectionLabel>
          </div>

          {Object.keys(groupedSchedules).length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              暂无可预约时段
            </div>
          ) : (
            <motion.div 
              className="space-y-4"
              variants={stagger}
              initial="hidden"
              animate="visible"
            >
              {Object.entries(groupedSchedules).map(([date, daySchedules]) => (
                <motion.div 
                  key={date} 
                  className="border-b border-border pb-4 last:border-0 last:pb-0"
                  variants={fadeInUp}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <span className="font-medium text-foreground">
                      {dayjs(date).format('MM-DD')}
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {WEEKDAY_NAMES[dayjs(date).day()]}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {daySchedules.map((schedule) => (
                      <Button
                        key={schedule.id}
                        variant={schedule.availableSlots > 0 ? 'primary' : 'outline'}
                        size="sm"
                        disabled={schedule.availableSlots === 0}
                        onClick={() => handleBook(schedule)}
                        className="min-w-[80px] !py-3"
                      >
                        <div className="text-center">
                          <div className="text-sm">
                            {TIME_SLOT_MAP[schedule.timeSlot]}
                          </div>
                          <div className="text-xs opacity-80 mt-1">
                            {schedule.availableSlots > 0 ? `余${schedule.availableSlots}` : '约满'}
                          </div>
                        </div>
                      </Button>
                    ))}
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </Card>
      </motion.div>
    </div>
  );
};

export default DoctorDetailPage;
