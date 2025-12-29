/**
 * 时段选择页面
 * 临时挂号第三步：选择就诊时段
 */
import React, { useState, useEffect } from 'react';
import { Skeleton, Toast, Tag } from 'antd-mobile';
import { history, useSearchParams } from 'umi';
import { motion } from 'framer-motion';
import dayjs from 'dayjs';
import { scheduleApi } from '@hospital/api';
import { Card, StepIndicator, PageHeader, fadeInUp, stagger } from '@/components/ui';
import { saveRegistrationData, getRegistrationData } from '@/utils/storage';

// 挂号流程步骤
const steps = [
  { key: 'department', title: '选科室' },
  { key: 'doctor', title: '选医生' },
  { key: 'time', title: '选时段' },
  { key: 'patient', title: '填信息' },
  { key: 'confirm', title: '确认' },
];

interface Schedule {
  id: number;
  doctorId: number;
  date: string;
  timeSlot: 'morning' | 'afternoon';
  maxPatients: number;
  currentPatients: number;
  status: number;
}

const TimeSlotPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const doctorId = searchParams.get('doctorId');

  const [loading, setLoading] = useState(true);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>(dayjs().format('YYYY-MM-DD'));
  const registrationData = getRegistrationData();

  // 生成未来7天的日期
  const dates = Array.from({ length: 7 }, (_, i) => {
    const date = dayjs().add(i, 'day');
    return {
      date: date.format('YYYY-MM-DD'),
      label: i === 0 ? '今天' : i === 1 ? '明天' : date.format('MM/DD'),
      weekday: date.format('ddd'),
    };
  });

  useEffect(() => {
    if (!doctorId) {
      Toast.show({
        icon: 'fail',
        content: '请先选择医生',
      });
      history.replace('/');
      return;
    }
    loadSchedules();
  }, [doctorId, selectedDate]);

  const loadSchedules = async () => {
    setLoading(true);
    try {
      // 获取医生在选定日期的排班
      const data = await scheduleApi.getByDoctor(Number(doctorId), {
        startDate: selectedDate,
        endDate: selectedDate,
      });
      setSchedules(data || []);
    } catch (error) {
      console.error('加载排班失败', error);
      // 模拟数据用于演示
      setSchedules([
        {
          id: 1,
          doctorId: Number(doctorId),
          date: selectedDate,
          timeSlot: 'morning',
          maxPatients: 30,
          currentPatients: 15,
          status: 1,
        },
        {
          id: 2,
          doctorId: Number(doctorId),
          date: selectedDate,
          timeSlot: 'afternoon',
          maxPatients: 25,
          currentPatients: 20,
          status: 1,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectTimeSlot = (schedule: Schedule) => {
    const remaining = schedule.maxPatients - schedule.currentPatients;
    if (remaining <= 0) {
      Toast.show({
        icon: 'fail',
        content: '该时段号源已满',
      });
      return;
    }

    saveRegistrationData({
      scheduleId: schedule.id,
      scheduleDate: schedule.date,
      timeSlot: schedule.timeSlot,
      timeSlotLabel: schedule.timeSlot === 'morning' ? '上午' : '下午',
    });
    history.push('/patient-info');
  };

  const getTimeSlotInfo = (slot: 'morning' | 'afternoon') => {
    return slot === 'morning'
      ? { label: '上午', time: '08:00 - 12:00', icon: '🌅' }
      : { label: '下午', time: '14:00 - 17:30', icon: '🌆' };
  };

  return (
    <div className="min-h-screen bg-background">
      {/* 步骤指示器 */}
      <StepIndicator steps={steps} currentStep={2} />

      {/* 页面头部 */}
      <PageHeader 
        title="选择时段" 
        subtitle={registrationData.doctorName ? `${registrationData.doctorName} ${registrationData.doctorTitle || ''}` : ''}
      />

      {/* 日期选择 */}
      <div className="px-4 py-4">
        <Card variant="default" padding="sm">
          <div className="flex gap-2 overflow-x-auto pb-2 -mx-1 px-1 scrollbar-hide">
            {dates.map((item) => (
              <motion.button
                key={item.date}
                className={`
                  flex-shrink-0 flex flex-col items-center justify-center
                  w-16 h-20 rounded-xl transition-all duration-200
                  ${selectedDate === item.date
                    ? 'bg-gradient-to-br from-primary to-accent text-white shadow-primary'
                    : 'bg-muted text-foreground hover:bg-muted/80'
                  }
                `}
                onClick={() => setSelectedDate(item.date)}
                whileTap={{ scale: 0.95 }}
              >
                <span className="text-xs opacity-80">{item.weekday}</span>
                <span className="text-lg font-semibold mt-1">{item.label}</span>
              </motion.button>
            ))}
          </div>
        </Card>
      </div>

      {/* 时段列表 */}
      <div className="px-4 pb-6">
        <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
          <span className="w-1 h-5 bg-gradient-to-b from-primary to-accent rounded-full" />
          可选时段
        </h2>

        {loading ? (
          <div className="space-y-4">
            {[1, 2].map((i) => (
              <Card key={i} variant="default" padding="md">
                <Skeleton.Paragraph lineCount={2} animated />
              </Card>
            ))}
          </div>
        ) : schedules.length === 0 ? (
          <Card variant="flat" padding="lg">
            <div className="text-center py-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
                <svg className="w-8 h-8 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} 
                        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-muted-foreground mb-2">该日期暂无排班</p>
              <p className="text-sm text-muted-foreground">请选择其他日期</p>
            </div>
          </Card>
        ) : (
          <motion.div
            variants={stagger}
            initial="hidden"
            animate="visible"
            className="space-y-4"
          >
            {schedules.map((schedule) => {
              const slotInfo = getTimeSlotInfo(schedule.timeSlot);
              const remaining = schedule.maxPatients - schedule.currentPatients;
              const isFull = remaining <= 0;
              const isLow = remaining > 0 && remaining <= 5;

              return (
                <motion.div key={schedule.id} variants={fadeInUp}>
                  <Card
                    variant={isFull ? 'flat' : 'default'}
                    padding="md"
                    hoverable={!isFull}
                    className={`
                      ${isFull ? 'opacity-60' : 'cursor-pointer active:scale-[0.99]'}
                      transition-all duration-200
                    `}
                    onClick={() => !isFull && handleSelectTimeSlot(schedule)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`
                          w-14 h-14 rounded-2xl flex items-center justify-center text-2xl
                          ${isFull 
                            ? 'bg-muted' 
                            : 'bg-gradient-to-br from-primary/10 to-accent/10'
                          }
                        `}>
                          {slotInfo.icon}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-lg text-foreground">
                              {slotInfo.label}
                            </span>
                            {isLow && !isFull && (
                              <Tag color="warning" className="!text-xs">紧张</Tag>
                            )}
                            {isFull && (
                              <Tag color="default" className="!text-xs">已满</Tag>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">{slotInfo.time}</p>
                        </div>
                      </div>

                      <div className="text-right">
                        <div className={`text-lg font-semibold ${isFull ? 'text-muted-foreground' : 'text-primary'}`}>
                          {isFull ? '已约满' : `余${remaining}号`}
                        </div>
                        <p className="text-xs text-muted-foreground">
                          已预约 {schedule.currentPatients}/{schedule.maxPatients}
                        </p>
                      </div>
                    </div>

                    {/* 进度条 */}
                    <div className="mt-4 h-2 bg-muted rounded-full overflow-hidden">
                      <motion.div
                        className={`h-full rounded-full ${isFull ? 'bg-muted-foreground' : 'bg-gradient-to-r from-primary to-accent'}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${(schedule.currentPatients / schedule.maxPatients) * 100}%` }}
                        transition={{ duration: 0.5, ease: 'easeOut' }}
                      />
                    </div>
                  </Card>
                </motion.div>
              );
            })}
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default TimeSlotPage;

