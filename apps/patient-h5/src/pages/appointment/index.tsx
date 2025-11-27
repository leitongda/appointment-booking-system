import { Tabs, Card, Tag, Empty, Button, Dialog, Toast, PullToRefresh, InfiniteScroll } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { appointmentApi } from '@hospital/api';
import { APPOINTMENT_STATUS_MAP, APPOINTMENT_STATUS_COLOR, TIME_SLOT_MAP } from '@hospital/shared';
import type { Appointment } from '@hospital/shared';
import styles from './index.less';

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
      loadAppointments(true);
    } catch (error: any) {
      Toast.show({ content: error.message || '取消失败', icon: 'fail' });
    }
  };

  const handleSignIn = async (id: string) => {
    try {
      const result = await appointmentApi.signIn(id);
      Toast.show({ content: `签到成功，您是第${result.queueNumber}号`, icon: 'success' });
      loadAppointments(true);
    } catch (error: any) {
      Toast.show({ content: error.message || '签到失败', icon: 'fail' });
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>我的预约</div>
      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        className={styles.tabs}
      >
        <Tabs.Tab title="全部" key="all" />
        <Tabs.Tab title="待就诊" key="pending" />
        <Tabs.Tab title="已完成" key="completed" />
        <Tabs.Tab title="已取消" key="cancelled" />
      </Tabs>
      
      <PullToRefresh onRefresh={() => loadAppointments(true)}>
        <div className={styles.list}>
          {appointments.length === 0 && !loading ? (
            <Empty description="暂无预约记录" />
          ) : (
            appointments.map((item) => (
              <Card 
                key={item.id} 
                className={styles.card} 
                onClick={() => history.push(`/appointment/${item.id}`)}
              >
                <div className={styles.cardHeader}>
                  <span className={styles.appointmentNo}>预约单号：{item.appointmentNo}</span>
                  <Tag color={APPOINTMENT_STATUS_COLOR[item.status]}>
                    {APPOINTMENT_STATUS_MAP[item.status]}
                  </Tag>
                </div>
                <div className={styles.cardBody}>
                  <div className={styles.info}>
                    <div className={styles.doctorName}>{item.doctorName}</div>
                    <div className={styles.deptName}>{item.departmentName}</div>
                  </div>
                  <div className={styles.time}>
                    <div>{item.scheduleDate}</div>
                    <div>
                      {TIME_SLOT_MAP[item.timeSlot || 'AM']}
                      {item.queueNumber && ` 第${item.queueNumber}号`}
                    </div>
                  </div>
                </div>
                {item.status === 1 && (
                  <div className={styles.cardFooter}>
                    <Button 
                      size="small" 
                      onClick={(e) => { e.stopPropagation(); handleCancel(item.id); }}
                    >
                      取消预约
                    </Button>
                    <Button 
                      size="small" 
                      color="primary"
                      onClick={(e) => { e.stopPropagation(); handleSignIn(item.id); }}
                    >
                      签到
                    </Button>
                  </div>
                )}
              </Card>
            ))
          )}
          <InfiniteScroll loadMore={() => loadAppointments()} hasMore={hasMore} />
        </div>
      </PullToRefresh>
    </div>
  );
};

export default AppointmentPage;
