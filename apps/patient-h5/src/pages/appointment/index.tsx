import { Tabs, Tag, Empty, Dialog, Toast, PullToRefresh, InfiniteScroll } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';
import { Card, Button } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';
import { announce } from '@/components/ui/toast-live';

const AppointmentPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);

  useEffect(() => {
    loadAppointments(true);
  }, [activeTab]);

  const loadAppointments = async (reset = false) => {
    const currentPage = reset ? 1 : page;
    
    try {
      const statusMap: Record<string, number | undefined> = {
        'all': undefined,
        'pending': 1,
        'completed': 5,
        'cancelled': 6,
      };
      
      const result = await appointmentApi.getList({
        status: statusMap[activeTab],
        page: currentPage,
        pageSize: 10,
      });
      
      if (reset) {
        setAppointments(result.data);
      } else {
        setAppointments((prev) => [...prev, ...result.data]);
      }
      
      setHasMore(result.data.length === 10);
      setPage(currentPage + 1);
    } catch (error) {
      console.error('加载预约列表失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (id: string) => {
    const result = await Dialog.confirm({
      content: '确定要取消预约吗？',
    });
    
    if (!result) return;

    try {
      await appointmentApi.cancel(id);
      Toast.show({ content: '取消成功', icon: 'success' });
      announce('取消预约成功');
      loadAppointments(true);
    } catch (error: any) {
      const msg = error.message || '取消失败';
      Toast.show({ content: msg, icon: 'fail' });
      announce(msg);
    }
  };

  const handleSignIn = async (id: string) => {
    try {
      const result = await appointmentApi.signIn(id, { checkin_method: 'PHONE' });
      const msg = `签到成功，您是第${result.queueNumber}号`;
      Toast.show({ content: msg, icon: 'success' });
      announce(msg);
      loadAppointments(true);
    } catch (error: any) {
      const msg = error.message || '签到失败';
      Toast.show({ content: msg, icon: 'fail' });
      announce(msg);
    }
  };

  // Map status colors to our design system
  const getStatusColor = (status: number) => {
    const colorMap: Record<string, string> = {
      'primary': 'bg-accent/10 text-accent',
      'success': 'bg-green-100 text-green-600',
      'warning': 'bg-yellow-100 text-yellow-600',
      'danger': 'bg-red-100 text-red-600',
      'default': 'bg-muted text-muted-foreground',
    };
    return colorMap[APPOINTMENT_STATUS_COLOR[status]] || colorMap.default;
  };

  return (
    <div className="min-h-screen bg-background" role="main">
      {/* Header */}
      <div className="bg-gradient-to-r from-accent to-accent-secondary px-4 pt-12 pb-4">
        <h1 className="text-white text-xl font-display">我的预约</h1>
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
        <Tabs.Tab title="全部" key="all" />
        <Tabs.Tab title="待就诊" key="pending" />
        <Tabs.Tab title="已完成" key="completed" />
        <Tabs.Tab title="已取消" key="cancelled" />
      </Tabs>
      
      <PullToRefresh onRefresh={() => loadAppointments(true)}>
        <div className="p-4">
          {appointments.length === 0 && !loading ? (
            <div className="flex items-center justify-center h-64" role="status">
              <Empty description="暂无预约记录" />
            </div>
          ) : (
            <motion.div
              className="space-y-3"
              variants={stagger}
              initial="hidden"
              animate="visible"
              role="list"
              aria-label="预约列表"
            >
              {appointments.map((item) => (
                <motion.div
                  key={item.id}
                  variants={fadeInUp}
                  whileTap={{ scale: 0.98 }}
                  role="listitem"
                >
                  <Card
                    variant="default"
                    padding="md"
                    hoverable
                    animated={false}
                    className="cursor-pointer"
                    onClick={() => history.push(`/appointment/${item.id}`)}
                    aria-label={`${item.doctorName} ${item.departmentName} ${APPOINTMENT_STATUS_MAP[item.status]} ${item.scheduleDate}`}
                  >
                    {/* Header */}
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm text-muted-foreground">
                        预约单号：{item.appointmentNo}
                      </span>
                      <span
                        className={`text-xs px-2 py-1 rounded-full ${getStatusColor(item.status)}`}
                        aria-label={`状态：${APPOINTMENT_STATUS_MAP[item.status]}`}
                      >
                        {APPOINTMENT_STATUS_MAP[item.status]}
                      </span>
                    </div>

                    {/* Body */}
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-semibold text-foreground text-lg">
                          {item.doctorName}
                        </h3>
                        <p className="text-muted-foreground text-sm mt-1">
                          {item.departmentName}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-medium text-foreground">{item.scheduleDate}</p>
                        <p className="text-sm text-muted-foreground mt-1">
                          {TIME_SLOT_MAP[item.timeSlot || 'morning']}
                          {item.queueNumber && (
                            <span className="ml-2 text-accent">第{item.queueNumber}号</span>
                          )}
                        </p>
                      </div>
                    </div>

                    {item.status === 0 && item.paymentAmount !== undefined && item.paymentAmount > 0 && (
                      <div className="mt-3 flex justify-between items-center rounded-xl bg-yellow-50 px-3 py-2 text-sm">
                        <span className="text-yellow-700">待支付金额</span>
                        <span className="font-semibold text-yellow-700">¥{item.paymentAmount.toFixed(2)}</span>
                      </div>
                    )}

                    {/* Actions */}
                    {(item.status === 0 || item.status === 1) && (
                      <div className="flex gap-2 mt-4 pt-4 border-t border-border">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => { e.stopPropagation(); handleCancel(item.id); }}
                          aria-label={`取消${item.doctorName}的预约`}
                        >
                          {item.status === 0 ? '取消订单' : '取消预约'}
                        </Button>
                        {item.status === 1 && (
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={(e) => { e.stopPropagation(); handleSignIn(item.id); }}
                            aria-label={`签到${item.doctorName}的预约`}
                          >
                            签到
                          </Button>
                        )}
                      </div>
                    )}
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          )}
          <InfiniteScroll loadMore={() => loadAppointments()} hasMore={hasMore} />
        </div>
      </PullToRefresh>
    </div>
  );
};

export default AppointmentPage;
