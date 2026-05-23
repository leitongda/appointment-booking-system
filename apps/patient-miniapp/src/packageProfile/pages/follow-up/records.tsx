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
import type { FollowUpRecordListItem } from '@hospital/api';
import './records.less';

const PAGE_SIZE = 20;

const CONDITION_MAP: Record<string, { text: string; type: string }> = {
  improved: { text: '好转', type: 'success' },
  stable: { text: '稳定', type: 'primary' },
  worsened: { text: '加重', type: 'danger' },
};

const FollowUpRecordsPage = () => {
  useApplyThemeNavigationBar();
  const [loading, setLoading] = useState(true);
  const [records, setRecords] = useState<FollowUpRecordListItem[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [patientId, setPatientId] = useState<string | undefined>();

  useReachBottom(() => {
    if (!loadingMore && hasMore) {
      loadMoreRecords();
    }
  });

  usePullDownRefresh(() => {
    resetAndLoad().finally(() => {
      Taro.stopPullDownRefresh();
    });
  });

  const loadRecords = useCallback(async () => {
    try {
      const params: any = { page: 1, pageSize: PAGE_SIZE };
      if (patientId) params.patientId = patientId;
      const result = await followUpApi.getMyPatientRecords(params);
      setRecords(result.data || []);
      setHasMore((result.data?.length || 0) < (result.total || 0));
    } catch (error) {
      console.error('加载随访记录失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  const resetAndLoad = useCallback(async () => {
    setPage(1);
    setHasMore(true);
    return loadRecords();
  }, [loadRecords]);

  const {
    showLoginPopup,
    handleLoginSuccess,
    handleLoginClose,
  } = useProtectedPage({
    load: resetAndLoad,
    clear: () => {
      setRecords([]);
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

  const loadMoreRecords = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const nextPage = page + 1;
      const params: any = { page: nextPage, pageSize: PAGE_SIZE };
      if (patientId) params.patientId = patientId;
      const result = await followUpApi.getMyPatientRecords(params);
      const newRecords = result.data || [];
      setRecords(prev => [...prev, ...newRecords]);
      setPage(nextPage);
      setHasMore(newRecords.length < (result.total || 0) && newRecords.length > 0);
    } catch (error) {
      console.error('加载更多随访记录失败', error);
    } finally {
      setLoadingMore(false);
    }
  };

  const handlePatientChange = (id: string | undefined) => {
    setPatientId(id);
  };

  const handleViewTask = (taskId: string) => {
    Taro.navigateTo({ url: `/packageProfile/pages/follow-up/detail?id=${taskId}` });
  };

  const formatDate = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 10);
  };

  if (loading) {
    return (
      <View className="follow-up-records-page loading-container">
        <Loading type="spinner">加载中...</Loading>
      </View>
    );
  }

  return (
    <View className="follow-up-records-page">
      <View className="patient-picker-bar">
        <Text className="picker-label">就诊人：</Text>
        <PatientPicker value={patientId} onChange={handlePatientChange} />
      </View>

      {records.length === 0 ? (
        <Empty description="暂无随访记录" />
      ) : (
        <View className="list">
          {records.map((record) => {
            const conditionInfo = record.patientCondition
              ? CONDITION_MAP[record.patientCondition] || { text: record.patientCondition, type: 'default' }
              : null;
            return (
              <View key={record.id} className="record-card">
                <View className="card-header">
                  <Text className="doctor-name">{record.doctorName || '未知医生'}</Text>
                  <Text className="date">{formatDate(record.followUpDate || record.createdAt)}</Text>
                </View>
                <View className="card-body">
                  {conditionInfo && (
                    <View className="tag-row">
                      <Tag type={conditionInfo.type as any} plain>{conditionInfo.text}</Tag>
                    </View>
                  )}
                  {record.content && (
                    <Text className="content">{record.content}</Text>
                  )}
                </View>
                {record.taskId && (
                  <View className="card-footer">
                    <Text className="link" onClick={() => handleViewTask(record.taskId!)}>
                      查看关联任务 ›
                    </Text>
                  </View>
                )}
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

      {!hasMore && records.length > 0 && (
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

export default FollowUpRecordsPage;
