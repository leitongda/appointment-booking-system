import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { Button } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { waitlistApi } from '@hospital/api';
import type { WaitlistEntry, WaitlistStatus } from '@hospital/api';
import { TIME_SLOT_MAP } from '@hospital/shared';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import { useApplyThemeNavigationBar } from '../../../utils/theme';
import LoginPopup from '../../../components/LoginPopup';
import './detail.less';

const STATUS_CONFIG: Record<WaitlistStatus, {
  label: string;
  desc: string;
}> = {
  WAITING: { label: '排队中', desc: '您正在候补队列中，当有号源释放时系统会按顺序通知' },
  PROMOTED: { label: '已转预约', desc: '已成功转为预约，请按时就诊' },
  CANCELLED: { label: '已取消', desc: '您已主动取消候补' },
  EXPIRED: { label: '已过期', desc: '排班已结束，候补自动过期' },
};

const WaitlistDetailPage = () => {
  useApplyThemeNavigationBar();
  const router = useRouter();
  const { id } = router.params;

  const [loading, setLoading] = useState(true);
  const [entry, setEntry] = useState<WaitlistEntry | null>(null);

  const loadDetail = useCallback(async () => {
    if (!id) return;
    try {
      const data = await waitlistApi.getDetail(id);
      setEntry(data);
    } catch {
      // 静默处理
    } finally {
      setLoading(false);
    }
  }, [id]);

  const noop = useCallback(async () => {}, []);
  const { showLoginPopup, handleLoginSuccess, handleLoginClose } = useProtectedPage({
    load: loadDetail,
    deps: [id],
  });

  const handleCancel = async () => {
    const result = await Taro.showModal({
      title: '取消候补',
      content: '确定要取消候补吗？取消后需要重新排队。',
      confirmText: '确定取消',
      cancelText: '再想想',
    });
    if (!result.confirm) return;

    try {
      await waitlistApi.leave(id!);
      Taro.showToast({ title: '已取消候补', icon: 'success' });
      loadDetail();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '取消失败', icon: 'error' });
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
    return <View className="waitlist-detail loading"><Text>加载中...</Text></View>;
  }

  if (!entry) {
    return (
      <View className="waitlist-detail">
        <Text>候补记录不存在</Text>
        <LoginPopup visible={showLoginPopup} onClose={handleLoginClose} onSuccess={handleLoginSuccess} />
      </View>
    );
  }

  const statusConfig = STATUS_CONFIG[entry.status];
  const schedule = entry.schedule;

  return (
    <View className="waitlist-detail">
      {/* 状态头部 */}
      <View className="detail-header">
        <Text className="detail-status">{statusConfig.label}</Text>
        <Text className="detail-desc">{statusConfig.desc}</Text>
      </View>

      {/* 排队位置 */}
      {entry.status === 'WAITING' && (
        <View className="detail-position">
          <Text className="position-label">当前排队位置</Text>
          <Text className="position-number">第 {entry.position} 位</Text>
          <Text className="position-hint">前方有 {Math.max(entry.position - 1, 0)} 人等待</Text>
        </View>
      )}

      {/* 排班信息 */}
      <View className="detail-section">
        <Text className="section-title">排班信息</Text>
        <View className="section-row">
          <Text className="row-label">医生</Text>
          <Text className="row-value">{schedule?.doctorName || '-'}{schedule?.doctorTitle ? ` - ${schedule.doctorTitle}` : ''}</Text>
        </View>
        <View className="section-row">
          <Text className="row-label">科室</Text>
          <Text className="row-value">{schedule?.departmentName || '-'}</Text>
        </View>
        <View className="section-row">
          <Text className="row-label">就诊日期</Text>
          <Text className="row-value">{schedule?.scheduleDate ? formatDate(schedule.scheduleDate) : '-'}</Text>
        </View>
        <View className="section-row">
          <Text className="row-label">就诊时段</Text>
          <Text className="row-value">{schedule?.timeSlot ? TIME_SLOT_MAP[schedule.timeSlot] || schedule.timeSlot : '-'}</Text>
        </View>
      </View>

      {/* 候补信息 */}
      <View className="detail-section">
        <Text className="section-title">候补信息</Text>
        <View className="section-row">
          <Text className="row-label">加入时间</Text>
          <Text className="row-value">{formatTime(entry.createdAt)}</Text>
        </View>
        {entry.promotedAt && (
          <View className="section-row">
            <Text className="row-label">转预约时间</Text>
            <Text className="row-value">{formatTime(entry.promotedAt)}</Text>
          </View>
        )}
        {entry.cancelledAt && (
          <View className="section-row">
            <Text className="row-label">取消时间</Text>
            <Text className="row-value">{formatTime(entry.cancelledAt)}</Text>
          </View>
        )}
      </View>

      {/* 候补说明 */}
      {entry.status === 'WAITING' && (
        <View className="detail-notice">
          <Text className="notice-text">
            候补排队按照先到先得原则，当有号源释放时系统会自动按顺序递补。您也可以随时取消候补。
          </Text>
        </View>
      )}

      {/* 底部操作 */}
      {entry.status === 'WAITING' && (
        <View className="detail-footer">
          <Button block onClick={handleCancel}>取消候补</Button>
        </View>
      )}
      {entry.status === 'PROMOTED' && (
        <View className="detail-footer">
          <Button block type="primary" onClick={() => Taro.switchTab({ url: '/pages/appointment/index' })}>
            查看预约
          </Button>
        </View>
      )}

      <LoginPopup visible={showLoginPopup} onClose={handleLoginClose} onSuccess={handleLoginSuccess} />
    </View>
  );
};

export default WaitlistDetailPage;
