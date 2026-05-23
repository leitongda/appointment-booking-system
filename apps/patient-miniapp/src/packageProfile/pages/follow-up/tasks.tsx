import { View, Text } from '@tarojs/components';
import Taro, { usePullDownRefresh, useReachBottom } from '@tarojs/taro';
import { Empty, Loading, Tag } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { followUpApi } from '@hospital/api';
import { getToken } from '../../../utils/auth';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import { useApplyThemeNavigationBar } from '../../../utils/theme';
import LoginPopup from '../../../components/LoginPopup';
import PatientPicker from '../../../components/PatientPicker';
import type { FollowUpTaskListItem } from '@hospital/api';
import './tasks.less';

const PAGE_SIZE = 20;

const STATUS_MAP: Record<string, { text: string; type: string }> = {
  pending: { text: '待随访', type: 'primary' },
  completed: { text: '已完成', type: 'success' },
  overdue: { text: '已逾期', type: 'danger' },
  skipped: { text: '已跳过', type: 'default' },
};

const FollowUpTasksPage = () => {
  useApplyThemeNavigationBar();
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<FollowUpTaskListItem[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [patientId, setPatientId] = useState<string | undefined>();

  useReachBottom(() => {
    if (!loadingMore && hasMore) {
      loadMoreTasks();
    }
  });

  usePullDownRefresh(() => {
    resetAndLoad().finally(() => {
      Taro.stopPullDownRefresh();
    });
  });

  const loadTasks = useCallback(async () => {
    try {
      const params: any = { page: 1, pageSize: PAGE_SIZE };
      if (patientId) params.patientId = patientId;
      const result = await followUpApi.getMyPatientTasks(params);
      setTasks(result.data || []);
      setHasMore((result.data?.length || 0) < (result.total || 0));
    } catch (error) {
      console.error('加载随访任务失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  const resetAndLoad = useCallback(async () => {
    setPage(1);
    setHasMore(true);
    return loadTasks();
  }, [loadTasks]);

  const {
    showLoginPopup,
    handleLoginSuccess,
    handleLoginClose,
  } = useProtectedPage({
    load: resetAndLoad,
    clear: () => {
      setTasks([]);
      setPage(1);
      setHasMore(true);
      setLoading(false);
    },
  });

  Taro.useDidShow(() => {
    if (getToken()) {
      void resetAndLoad();
    }
  });

  const loadMoreTasks = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const params: any = { page: nextPage, pageSize: PAGE_SIZE };
      if (patientId) params.patientId = patientId;
      const result = await followUpApi.getMyPatientTasks(params);
      const newTasks = result.data || [];
      setTasks(prev => [...prev, ...newTasks]);
      setPage(nextPage);
      setHasMore(newTasks.length < (result.total || 0) && newTasks.length > 0);
    } catch (error) {
      console.error('加载更多随访任务失败', error);
    } finally {
      setLoadingMore(false);
    }
  };

  const handlePatientChange = (id: string | undefined) => {
    setPatientId(id);
  };

  const handleViewDetail = (id: string) => {
    Taro.navigateTo({ url: `/packageProfile/pages/follow-up/detail?id=${id}` });
  };

  const formatDate = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 10);
  };

  if (loading) {
    return (
      <View className="follow-up-tasks-page loading-container">
        <Loading type="spinner">加载中...</Loading>
      </View>
    );
  }

  return (
    <View className="follow-up-tasks-page">
      <View className="patient-picker-bar">
        <Text className="picker-label">就诊人：</Text>
        <PatientPicker value={patientId} onChange={handlePatientChange} />
      </View>

      {tasks.length === 0 ? (
        <Empty description="暂无随访任务" />
      ) : (
        <View className="list">
          {tasks.map((task) => {
            const statusInfo = STATUS_MAP[task.status || ''] || { text: task.status || '-', type: 'default' };
            return (
              <View
                key={task.id}
                className="task-card"
                onClick={() => handleViewDetail(task.id)}
              >
                <View className="card-header">
                  <Text className="task-no">{task.taskNo || '随访任务'}</Text>
                  <Tag type={statusInfo.type as any} plain>{statusInfo.text}</Tag>
                </View>
                <View className="card-body">
                  {task.planName && (
                    <View className="info-row">
                      <Text className="label">随访计划</Text>
                      <Text className="value">
                        {task.planName}{task.stepOrder != null ? ` · 第${task.stepOrder}步` : ''}
                      </Text>
                    </View>
                  )}
                  <View className="info-row">
                    <Text className="label">计划日期</Text>
                    <Text className="value">{formatDate(task.scheduledDate)}</Text>
                  </View>
                  <View className="info-row">
                    <Text className="label">负责医生</Text>
                    <Text className="value">{task.doctorName || '-'}</Text>
                  </View>
                  <View className="info-row">
                    <Text className="label">科室</Text>
                    <Text className="value">{task.departmentName || '-'}</Text>
                  </View>
                </View>
                <View className="card-footer">
                  <Text className="link">查看详情 ›</Text>
                </View>
              </View>
            );
          })}
        </View>
      )}

      {loadingMore && (
        <View className="loading-more">
          <Text>加载中...</Text>
        </View>
      )}

      {!hasMore && tasks.length > 0 && (
        <View className="no-more">
          <Text>没有更多了</Text>
        </View>
      )}

      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default FollowUpTasksPage;
