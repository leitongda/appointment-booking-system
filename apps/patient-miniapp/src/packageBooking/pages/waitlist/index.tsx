import { View, Text } from '@tarojs/components';
import Taro, { useDidShow } from '@tarojs/taro';
import { Button, Empty, Tabs } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { waitlistApi } from '@hospital/api';
import type { WaitlistEntry, WaitlistStatus } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import { useApplyThemeNavigationBar } from '../../../utils/theme';
import LoginPopup from '../../../components/LoginPopup';
import './index.less';

const STATUS_MAP: Record<WaitlistStatus, { label: string; className: string }> = {
  WAITING: { label: '排队中', className: 'status-waiting' },
  PROMOTED: { label: '已转预约', className: 'status-promoted' },
  CANCELLED: { label: '已取消', className: 'status-cancelled' },
  EXPIRED: { label: '已过期', className: 'status-expired' },
};

const WaitlistPage = () => {
  useApplyThemeNavigationBar();
  const [activeTab, setActiveTab] = useState('WAITING');
  const [entries, setEntries] = useState<WaitlistEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const loadList = useCallback(async () => {
    setLoading(true);
    try {
      const status = activeTab === 'all' ? undefined : (activeTab as WaitlistStatus);
      const result = await waitlistApi.getMyList({ status, page: 1, pageSize: 50 });
      setEntries(result.items || []);
    } catch {
      // 静默处理
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  const noop = useCallback(async () => {}, []);
  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: loadList,
    deps: [activeTab],
  });

  useDidShow(() => {
    loadList();
  });

  const handleCancel = async (entry: WaitlistEntry) => {
    const result = await Taro.showModal({
      title: '取消候补',
      content: '确定要取消候补吗？取消后需要重新排队。',
      confirmText: '确定取消',
      cancelText: '再想想',
    });
    if (!result.confirm) return;

    try {
      await waitlistApi.leave(entry.id);
      Taro.showToast({ title: '已取消候补', icon: 'success' });
      loadList();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '取消失败', icon: 'error' });
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return dateStr.substring(0, 10);
  };

  return (
    <View className="waitlist-page">
      <Tabs
        value={activeTab}
        onChange={(val) => setActiveTab(String(val))}
        activeType="smile"
      >
        <Tabs.TabPane title="排队中" value="WAITING" />
        <Tabs.TabPane title="已转预约" value="PROMOTED" />
        <Tabs.TabPane title="全部" value="all" />
      </Tabs>

      <View className="waitlist-content">
        {entries.length === 0 && !loading ? (
          <Empty description="暂无候补记录" />
        ) : (
          entries.map((entry) => {
            const schedule = entry.schedule;
            const statusConfig = STATUS_MAP[entry.status];
            return (
              <View
                key={entry.id}
                className="waitlist-card"
                onClick={() => Taro.navigateTo({
                  url: `/packageBooking/pages/waitlist/detail?id=${entry.id}`,
                })}
              >
                <View className="card-header">
                  <Text className="card-date">{formatDate(entry.createdAt)}</Text>
                  <Text className={`card-status ${statusConfig.className}`}>
                    {statusConfig.label}
                  </Text>
                </View>

                <View className="card-body">
                  <View className="card-info">
                    <Text className="card-doctor">{schedule?.doctorName || '医生'}</Text>
                    <Text className="card-dept">{schedule?.departmentName}</Text>
                  </View>
                  <View className="card-schedule">
                    <Text className="card-date-text">
                      {schedule?.scheduleDate ? formatDate(schedule.scheduleDate) : '-'}
                    </Text>
                    <Text className="card-slot">
                      {schedule?.timeSlot ? TIME_SLOT_MAP[schedule.timeSlot] || schedule.timeSlot : '-'}
                    </Text>
                  </View>
                </View>

                {entry.status === 'WAITING' && (
                  <View className="card-position">
                    <Text className="position-label">排队位置</Text>
                    <Text className="position-value">第 {entry.position} 位</Text>
                  </View>
                )}

                {entry.status === 'WAITING' && (
                  <View className="card-actions">
                    <Button
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation?.();
                        handleCancel(entry);
                      }}
                    >
                      取消候补
                    </Button>
                  </View>
                )}

                {entry.status === 'PROMOTED' && (
                  <View className="card-actions">
                    <Button
                      size="small"
                      type="primary"
                      onClick={(e) => {
                        e.stopPropagation?.();
                        Taro.switchTab({ url: '/pages/appointment/index' });
                      }}
                    >
                      查看预约
                    </Button>
                  </View>
                )}
              </View>
            );
          })
        )}
      </View>

      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default WaitlistPage;
