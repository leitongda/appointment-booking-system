import { NavBar, Dialog, Toast, Skeleton, Empty } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { waitlistApi } from '@hospital/api';
import type { WaitlistEntry, WaitlistStatus } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import { Card, Button, InvertedSection } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

/** 状态配置 */
const STATUS_CONFIG: Record<WaitlistStatus, {
  label: string;
  gradient: string;
  description: string;
}> = {
  WAITING: {
    label: '排队中',
    gradient: 'from-orange-500 to-amber-500',
    description: '您正在候补队列中，当有号源释放时系统会按顺序通知',
  },
  PROMOTED: {
    label: '已转预约',
    gradient: 'from-green-500 to-emerald-500',
    description: '已成功转为预约，请按时就诊',
  },
  CANCELLED: {
    label: '已取消',
    gradient: 'from-gray-500 to-gray-600',
    description: '您已主动取消候补',
  },
  EXPIRED: {
    label: '已过期',
    gradient: 'from-gray-500 to-gray-600',
    description: '排班已结束，候补自动过期',
  },
};

const WaitlistDetailPage: React.FC = () => {
  const { id } = useParams() as { id: string };
  const [loading, setLoading] = useState(true);
  const [entry, setEntry] = useState<WaitlistEntry | null>(null);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    try {
      const data = await waitlistApi.getDetail(id!);
      setEntry(data);
    } catch (error: any) {
      Toast.show({ content: error.message || '加载失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    const result = await Dialog.confirm({
      content: '确定要取消候补吗？取消后需要重新排队。',
      confirmText: '确定取消',
      cancelText: '再想想',
    });
    if (!result) return;

    try {
      await waitlistApi.leave(id!);
      Toast.show({ content: '已取消候补', icon: 'success' });
      loadData();
    } catch (error: any) {
      Toast.show({ content: error.message || '取消失败', icon: 'fail' });
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return dateStr.substring(0, 10);
  };

  const formatTime = (dateStr?: string) => {
    if (!dateStr) return '-';
    return dateStr.substring(0, 16).replace('T', ' ');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          候补详情
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={10} animated />
        </div>
      </div>
    );
  }

  if (!entry) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          候补详情
        </NavBar>
        <div className="flex items-center justify-center h-64">
          <Empty description="候补记录不存在" />
        </div>
      </div>
    );
  }

  const statusConfig = STATUS_CONFIG[entry.status];
  const schedule = entry.schedule;
  const isWaiting = entry.status === 'WAITING';
  const isPromoted = entry.status === 'PROMOTED';

  return (
    <div className="min-h-screen bg-background pb-24">
      <NavBar
        onBack={() => history.back()}
        className="!bg-transparent absolute top-0 left-0 right-0 z-20 text-white"
      >
        候补详情
      </NavBar>

      {/* Status Header */}
      <div className={`bg-gradient-to-r ${statusConfig.gradient} pt-16 pb-8 px-4`}>
        <div className="text-center text-white">
          <h2 className="text-2xl font-display mb-2">{statusConfig.label}</h2>
          <p className="text-white/80">{statusConfig.description}</p>
        </div>
      </div>

      <motion.div
        className="px-4 -mt-4 relative z-10 space-y-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Position Card */}
        {isWaiting && (
          <motion.div variants={fadeInUp}>
            <Card variant="elevated" padding="lg">
              <div className="text-center py-2">
                <p className="text-muted-foreground text-sm mb-2">当前排队位置</p>
                <p className="text-4xl font-bold text-accent">第 {entry.position} 位</p>
                <p className="text-muted-foreground text-sm mt-2">
                  前方有 {Math.max(entry.position - 1, 0)} 人等待，请耐心等候通知
                </p>
              </div>
            </Card>
          </motion.div>
        )}

        {/* Schedule Info */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="lg">
            <h3 className="font-semibold text-foreground mb-4">排班信息</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">医生</span>
                <span className="text-foreground font-medium">
                  {schedule?.doctorName || '-'}
                  {schedule?.doctorTitle ? ` - ${schedule.doctorTitle}` : ''}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">科室</span>
                <span className="text-foreground">{schedule?.departmentName || '-'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">就诊日期</span>
                <span className="text-foreground">
                  {schedule?.scheduleDate ? formatDate(schedule.scheduleDate) : '-'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">就诊时段</span>
                <span className="text-foreground">
                  {schedule?.timeSlot ? TIME_SLOT_MAP[schedule.timeSlot] || schedule.timeSlot : '-'}
                </span>
              </div>
              {schedule?.storeName && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">就诊机构</span>
                  <span className="text-foreground">{schedule.storeName}</span>
                </div>
              )}
            </div>
          </Card>
        </motion.div>

        {/* Waitlist Info */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="lg">
            <h3 className="font-semibold text-foreground mb-4">候补信息</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">加入时间</span>
                <span className="text-foreground">{formatTime(entry.createdAt)}</span>
              </div>
              {entry.promotedAt && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">转预约时间</span>
                  <span className="text-foreground">{formatTime(entry.promotedAt)}</span>
                </div>
              )}
              {entry.cancelledAt && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">取消时间</span>
                  <span className="text-foreground">{formatTime(entry.cancelledAt)}</span>
                </div>
              )}
              {entry.symptomDescription && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">病情描述</span>
                  <span className="text-foreground text-right max-w-[60%]">
                    {entry.symptomDescription}
                  </span>
                </div>
              )}
            </div>
          </Card>
        </motion.div>

        {/* Tip */}
        {isWaiting && (
          <motion.div variants={fadeInUp}>
            <InvertedSection>
              <h3>候补说明</h3>
              <p>候补排队按照先到先得原则，当有号源释放时系统会自动按顺序递补。您也可以随时取消候补。</p>
            </InvertedSection>
          </motion.div>
        )}
      </motion.div>

      {/* Footer Actions */}
      {isWaiting && (
        <div className="fixed bottom-0 left-0 right-0 bg-card border-t border-border p-4 flex gap-3 safe-area-inset-bottom">
          <Button variant="outline" block onClick={handleCancel}>
            取消候补
          </Button>
        </div>
      )}

      {isPromoted && (
        <div className="fixed bottom-0 left-0 right-0 bg-card border-t border-border p-4 flex gap-3 safe-area-inset-bottom">
          <Button
            block
            onClick={() => history.push('/appointment')}
          >
            查看预约
          </Button>
        </div>
      )}
    </div>
  );
};

export default WaitlistDetailPage;
