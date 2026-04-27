import { NavBar } from 'antd-mobile';
import { history, useSearchParams } from 'umi';
import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import { Card, Button, GradientText } from '@/components/ui';
import { fadeInUp, stagger, scaleIn } from '@/components/ui/animations';
import { settingsApi } from '@hospital/api';
import type { BookingRules } from '@hospital/api';

const BookingConfirmPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const appointmentNo = searchParams.get('appointmentNo');
  const storeId = searchParams.get('storeId');
  const [rules, setRules] = useState<BookingRules | null>(null);

  useEffect(() => {
    settingsApi.getBookingRules(storeId || undefined).then(setRules).catch(() => {});
  }, [storeId]);

  const checkinText = rules
    ? `就诊当天请提前${rules.signInAdvanceMinutes}分钟到达医院签到`
    : '就诊当天请提前到达医院签到';

  const cancelText = rules
    ? `如需取消预约，请至少提前${rules.cancelHours}小时操作`
    : '如需取消预约，请提前操作';

  return (
    <div className="min-h-screen bg-background">
      <NavBar
        onBack={() => history.push('/home')}
        backArrow={false}
        className="!bg-card border-b border-border"
      >
        预约结果
      </NavBar>

      {/* Success Icon & Message */}
      <motion.div
        className="flex flex-col items-center pt-12 pb-8 px-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        <motion.div
          variants={scaleIn}
          className="w-20 h-20 rounded-full bg-gradient-to-br from-green-400 to-green-600 flex items-center justify-center shadow-lg mb-6"
        >
          <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </motion.div>

        <motion.h1
          variants={fadeInUp}
          className="font-display text-2xl text-foreground mb-2"
        >
          预约<GradientText>成功</GradientText>
        </motion.h1>

        <motion.p
          variants={fadeInUp}
          className="text-muted-foreground text-center"
        >
          请按时到院就诊，提前到达进行签到
        </motion.p>
      </motion.div>

      {/* Info Card */}
      <motion.div
        className="px-4"
        variants={fadeInUp}
        initial="hidden"
        animate="visible"
      >
        <Card variant="elevated" padding="lg">
          <div className="flex items-center justify-between mb-6 pb-4 border-b border-border">
            <span className="text-muted-foreground">预约单号</span>
            <span className="font-mono text-accent font-semibold">
              {appointmentNo}
            </span>
          </div>

          <div>
            <h4 className="font-medium text-foreground mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              温馨提示
            </h4>
            <ul className="space-y-3 text-sm text-muted-foreground">
              <li className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-accent/10 text-accent text-xs flex items-center justify-center flex-shrink-0 mt-0.5">1</span>
                <span>请携带本人有效身份证件</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-accent/10 text-accent text-xs flex items-center justify-center flex-shrink-0 mt-0.5">2</span>
                <span>{checkinText}</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-accent/10 text-accent text-xs flex items-center justify-center flex-shrink-0 mt-0.5">3</span>
                <span>{cancelText}</span>
              </li>
            </ul>
          </div>
        </Card>
      </motion.div>

      {/* Actions */}
      <motion.div
        className="px-4 py-6 space-y-3"
        variants={fadeInUp}
        initial="hidden"
        animate="visible"
      >
        <Button
          variant="outline"
          block
          onClick={() => history.push('/appointment')}
        >
          查看预约
        </Button>
        <Button
          block
          onClick={() => history.push('/home')}
        >
          返回首页
        </Button>
      </motion.div>
    </div>
  );
};

export default BookingConfirmPage;
