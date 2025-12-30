/**
 * 排队状态页面
 * 临时挂号完成后显示排队信息
 */
import React, { useState, useEffect } from 'react';
import { Button, Toast } from 'antd-mobile';
import { history } from 'umi';
import { motion } from 'framer-motion';
import dayjs from 'dayjs';
import { Card, fadeInUp, stagger, pulseAnimation } from '@/components/ui';
import { getRegistrationData, resetRegistration } from '@/utils/storage';

const QueuePage: React.FC = () => {
  const registrationData = getRegistrationData();
  const [currentTime, setCurrentTime] = useState(dayjs());

  useEffect(() => {
    // 验证是否已完成挂号
    if (!registrationData.queueNumber) {
      Toast.show({
        icon: 'fail',
        content: '未找到挂号信息',
      });
      history.replace('/');
      return;
    }

    // 更新当前时间
    const timer = setInterval(() => {
      setCurrentTime(dayjs());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const handleNewRegistration = () => {
    resetRegistration();
    history.replace('/');
  };

  const handleViewDetail = () => {
    Toast.show({
      content: '功能开发中...',
    });
  };

  return (
    <div className="min-h-screen bg-background">
      {/* 成功头部 */}
      <motion.div 
        className="bg-gradient-to-br from-primary via-accent to-primary-light px-6 pt-12 pb-20 text-center relative overflow-hidden"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        {/* 装饰圆圈 */}
        <div className="absolute top-0 left-0 w-40 h-40 bg-white/10 rounded-full -translate-x-1/2 -translate-y-1/2" />
        <div className="absolute bottom-0 right-0 w-60 h-60 bg-white/10 rounded-full translate-x-1/3 translate-y-1/3" />
        
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.2 }}
          className="relative z-10"
        >
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-white/20 flex items-center justify-center">
            <motion.svg 
              className="w-10 h-10 text-white" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.5, delay: 0.5 }}
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2.5} 
                d="M5 13l4 4L19 7" 
              />
            </motion.svg>
          </div>
          <h1 className="text-2xl font-semibold text-white mb-2">挂号成功</h1>
          <p className="text-white/80">请凭排队号到相应诊室等候</p>
        </motion.div>
      </motion.div>

      <motion.div 
        className="px-4 -mt-10 pb-8 space-y-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* 排队号卡片 */}
        <motion.div variants={fadeInUp}>
          <Card variant="elevated" padding="lg" className="text-center relative overflow-hidden">
            {/* 背景装饰 */}
            <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-accent/5" />
            
            <div className="relative z-10">
              <p className="text-muted-foreground mb-2">您的排队号</p>
              <motion.div 
                className="text-6xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent"
                animate={pulseAnimation}
              >
                {registrationData.queueNumber}
              </motion.div>
              <div className="mt-4 flex items-center justify-center gap-4 text-sm">
                <div className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-warning animate-pulse" />
                  <span className="text-muted-foreground">
                    前方约 <span className="text-foreground font-medium">{Math.floor(Math.random() * 10) + 1}</span> 人
                  </span>
                </div>
                <div className="w-px h-4 bg-border" />
                <div className="text-muted-foreground">
                  预计等待 <span className="text-foreground font-medium">{registrationData.estimatedWaitTime}</span> 分钟
                </div>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* 就诊信息 */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="md">
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 rounded-xl bg-muted">
                <p className="text-xs text-muted-foreground mb-1">就诊日期</p>
                <p className="font-medium text-foreground">
                  {registrationData.scheduleDate ? dayjs(registrationData.scheduleDate).format('MM月DD日') : '-'}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-muted">
                <p className="text-xs text-muted-foreground mb-1">就诊时段</p>
                <p className="font-medium text-foreground">
                  {registrationData.timeSlotLabel || '-'}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-muted">
                <p className="text-xs text-muted-foreground mb-1">就诊科室</p>
                <p className="font-medium text-foreground">
                  {registrationData.departmentName || '-'}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-muted">
                <p className="text-xs text-muted-foreground mb-1">就诊医生</p>
                <p className="font-medium text-foreground">
                  {registrationData.doctorName || '-'}
                </p>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* 患者信息 */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="md">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div>
                <p className="font-semibold text-foreground">{registrationData.patientName}</p>
                <p className="text-sm text-muted-foreground">
                  {registrationData.patientGender === 'male' ? '男' : '女'} · {registrationData.patientAge}岁
                </p>
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              手机号：{registrationData.patientPhone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}
            </div>
          </Card>
        </motion.div>

        {/* 温馨提示 */}
        <motion.div variants={fadeInUp}>
          <Card variant="flat" padding="md">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="font-medium text-foreground mb-2">就诊提示</h3>
                <ul className="text-sm text-muted-foreground space-y-1.5">
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>请携带有效身份证件到相应诊室候诊</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>叫号时请及时就诊，过号需重新排队</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-primary mt-1">•</span>
                    <span>如需取消挂号，请提前告知导诊台</span>
                  </li>
                </ul>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* 当前时间 */}
        <motion.div 
          variants={fadeInUp}
          className="text-center text-sm text-muted-foreground"
        >
          当前时间：{currentTime.format('HH:mm:ss')}
        </motion.div>

        {/* 操作按钮 */}
        <motion.div variants={fadeInUp} className="space-y-3 pt-4">
          <Button
            block
            color="primary"
            size="large"
            onClick={handleViewDetail}
            className="!h-12 !rounded-xl !text-base !font-medium"
            style={{
              background: 'linear-gradient(135deg, #00A3A3 0%, #00C4B4 100%)',
            }}
          >
            查看详情
          </Button>
          <Button
            block
            size="large"
            onClick={handleNewRegistration}
            className="!h-12 !rounded-xl !text-base !font-medium !bg-muted !text-foreground"
          >
            再次挂号
          </Button>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default QueuePage;



