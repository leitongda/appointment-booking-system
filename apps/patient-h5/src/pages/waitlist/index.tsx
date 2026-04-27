import { NavBar, Empty, Dialog, Toast, PullToRefresh, Tabs } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { waitlistApi } from '@hospital/api';
import type { WaitlistEntry, WaitlistStatus } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import { Card, Button } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

/** 状态标签配置 */
const STATUS_MAP: Record<WaitlistStatus, { label: string; color: string }> = {
  WAITING: { label: '排队中', color: 'bg-orange-100 text-orange-600' },
  PROMOTED: { label: '已转预约', color: 'bg-green-100 text-green-600' },
  CANCELLED: { label: '已取消', color: 'bg-gray-100 text-gray-500' },
  EXPIRED: { label: '已过期', color: 'bg-gray-100 text-gray-500' },
};

const WaitlistPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('WAITING');
  const [entries, setEntries] = useState<WaitlistEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadList(true);
  }, [activeTab]);

  const loadList = async (reset = false) => {
    setLoading(true);
    try {
      const status = activeTab === 'all' ? undefined : (activeTab as WaitlistStatus);
      const result = await waitlistApi.getMyList({ status, page: 1, pageSize: 50 });
      setEntries(result.items || []);
    } catch (error) {
      console.error('加载候补列表失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (entry: WaitlistEntry) => {
    const result = await Dialog.confirm({
      content: '确定要取消候补吗？取消后需要重新排队。',
      confirmText: '确定取消',
      cancelText: '再想想',
    });
    if (!result) return;

    try {
      await waitlistApi.leave(entry.id);
      Toast.show({ content: '已取消候补', icon: 'success' });
      loadList(true);
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

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-gradient-to-r from-accent to-accent-secondary px-4 pt-12 pb-4">
        <h1 className="text-white text-xl font-display">候补排队</h1>
      </div>

      {/* Tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        className="!bg-card"
        style={{
          '--active-line-color': '#0052FF',
          '--active-title-color': '#0052FF',
        } as React.CSSProperties}
      >
        <Tabs.Tab title="排队中" key="WAITING" />
        <Tabs.Tab title="已转预约" key="PROMOTED" />
        <Tabs.Tab title="全部" key="all" />
      </Tabs>

      <PullToRefresh onRefresh={() => loadList(true)}>
        <div className="p-4">
          {entries.length === 0 && !loading ? (
            <div className="flex items-center justify-center h-64">
              <Empty description="暂无候补记录" />
            </div>
          ) : (
            <motion.div
              className="space-y-3"
              variants={stagger}
              initial="hidden"
              animate="visible"
            >
              {entries.map((entry) => {
                const schedule = entry.schedule;
                const statusConfig = STATUS_MAP[entry.status];
                return (
                  <motion.div
                    key={entry.id}
                    variants={fadeInUp}
                    whileTap={{ scale: 0.98 }}
                  >
                    <Card
                      variant="default"
                      padding="md"
                      hoverable
                      animated={false}
                      className="cursor-pointer"
                      onClick={() => history.push(`/waitlist/${entry.id}`)}
                    >
                      {/* Header */}
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm text-muted-foreground">
                          {formatDate(entry.createdAt)}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded-full ${statusConfig.color}`}>
                          {statusConfig.label}
                        </span>
                      </div>

                      {/* Body */}
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="font-semibold text-foreground text-lg">
                            {schedule?.doctorName || '医生'}
                          </h3>
                          <p className="text-muted-foreground text-sm mt-1">
                            {schedule?.departmentName}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-medium text-foreground">
                            {schedule?.scheduleDate ? formatDate(schedule.scheduleDate) : '-'}
                          </p>
                          <p className="text-sm text-muted-foreground mt-1">
                            {schedule?.timeSlot ? TIME_SLOT_MAP[schedule.timeSlot] || schedule.timeSlot : '-'}
                          </p>
                        </div>
                      </div>

                      {/* Position */}
                      {entry.status === 'WAITING' && (
                        <div className="mt-3 flex justify-between items-center rounded-xl bg-orange-50 px-3 py-2 text-sm">
                          <span className="text-orange-700">排队位置</span>
                          <span className="font-semibold text-orange-700">第 {entry.position} 位</span>
                        </div>
                      )}

                      {/* Actions */}
                      {entry.status === 'WAITING' && (
                        <div className="flex gap-2 mt-4 pt-4 border-t border-border">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCancel(entry);
                            }}
                          >
                            取消候补
                          </Button>
                        </div>
                      )}

                      {/* Promoted action */}
                      {entry.status === 'PROMOTED' && (
                        <div className="flex gap-2 mt-4 pt-4 border-t border-border">
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              history.push('/appointment');
                            }}
                          >
                            查看预约
                          </Button>
                        </div>
                      )}
                    </Card>
                  </motion.div>
                );
              })}
            </motion.div>
          )}
        </div>
      </PullToRefresh>
    </div>
  );
};

export default WaitlistPage;
