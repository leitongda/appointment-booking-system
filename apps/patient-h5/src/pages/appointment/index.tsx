import { Tabs, Empty, Dialog, Toast, PullToRefresh, InfiniteScroll } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { appointmentApi } from '@hospital/api';
import type { Appointment } from '@hospital/shared';
import { fadeInUp, stagger } from '@/components/ui/animations';
import { announce } from '@/components/ui/toast-live';
import { AppointmentStatusCard } from '@/components/AppointmentStatusCard';

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
      // tab 状态映射。注意：'signed'/'seeing' 后端为单一 status 值（2/4），
      // 无法一次筛多个状态，故分别单列。'invalid' 类目（爽约/过期）同理单列以覆盖最常见的查询。
      const statusMap: Record<string, number | undefined> = {
        'all': undefined,
        'pending': 1,
        'signed': 2,
        'seeing': 4,
        'completed': 5,
        'cancelled': 6,
        'expired': 7,
        'no_show': 8,
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
        <Tabs.Tab title="已签到" key="signed" />
        <Tabs.Tab title="就诊中" key="seeing" />
        <Tabs.Tab title="已完成" key="completed" />
        <Tabs.Tab title="已取消" key="cancelled" />
        <Tabs.Tab title="已过期" key="expired" />
        <Tabs.Tab title="已爽约" key="no_show" />
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
                  <AppointmentStatusCard
                    appointment={item}
                    onClick={(apt) => history.push(`/appointment/${apt.id}`)}
                    onCancel={handleCancel}
                    onSignIn={handleSignIn}
                  />
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
