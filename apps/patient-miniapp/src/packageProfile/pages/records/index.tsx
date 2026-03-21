import { View, Text } from '@tarojs/components';
import Taro, { usePullDownRefresh, useReachBottom } from '@tarojs/taro';
import { Empty, Loading } from '@nutui/nutui-react-taro';
import { useState, useCallback } from 'react';
import { medicalRecordApi } from '@hospital/api';
import { getToken } from '../../../utils/auth';
import { useProtectedPage } from '../../../hooks/useProtectedPage';
import LoginPopup from '../../../components/LoginPopup';
import type { MedicalRecordListItem } from '@hospital/api';
import './index.less';

const PAGE_SIZE = 20;

const RecordsPage = () => {
  const [loading, setLoading] = useState(true);
  const [records, setRecords] = useState<MedicalRecordListItem[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  // 上拉加载更多
  useReachBottom(() => {
    if (!loadingMore && hasMore) {
      loadMoreRecords();
    }
  });

  // 下拉刷新
  usePullDownRefresh(() => {
    resetAndLoad().finally(() => {
      Taro.stopPullDownRefresh();
    });
  });

  const loadRecords = useCallback(async () => {
    try {
      const result = await medicalRecordApi.getList({ page: 1, pageSize: PAGE_SIZE });
      setRecords(result.data || []);
      setHasMore((result.data?.length || 0) < (result.total || 0));
    } catch (error) {
      console.error('加载就诊记录失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
    }
  }, []);

  // 重置并加载
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

  // 页面显示时刷新数据
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
      const result = await medicalRecordApi.getList({ page: nextPage, pageSize: PAGE_SIZE });
      const newRecords = result.data || [];
      setRecords(prev => [...prev, ...newRecords]);
      setPage(nextPage);
      setHasMore(newRecords.length < (result.total || 0) && newRecords.length > 0);
    } catch (error) {
      console.error('加载更多就诊记录失败', error);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleViewDetail = (id: string) => {
    Taro.navigateTo({ url: `/packageProfile/pages/records/detail?id=${id}` });
  };

  const formatDate = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 10);
  };

  if (loading) {
    return (
      <View className="records-page loading-container">
        <Loading type="spinner">加载中...</Loading>
      </View>
    );
  }

  return (
    <View className="records-page">
      {records.length === 0 ? (
        <Empty description="暂无就诊记录" />
      ) : (
        <View className="list">
          {records.map((record) => (
            <View
              key={record.id}
              className="record-card"
              onClick={() => handleViewDetail(record.id)}
            >
              <View className="card-header">
                <Text className="date">{formatDate(record.visitDate)}</Text>
                <Text className="dept">{record.departmentName}</Text>
              </View>
              <View className="card-body">
                <View className="info-row">
                  <Text className="label">病历号</Text>
                  <Text className="value">{record.recordNo}</Text>
                </View>
                <View className="info-row">
                  <Text className="label">就诊医生</Text>
                  <Text className="value">{record.doctorName || '-'}</Text>
                </View>
                <View className="info-row">
                  <Text className="label">诊断</Text>
                  <Text className="value diagnosis">{record.diagnosis || '-'}</Text>
                </View>
              </View>
              <View className="card-footer">
                <Text className="link">查看详情 ›</Text>
              </View>
            </View>
          ))}
        </View>
      )}

      {/* 加载状态 */}
      {loadingMore && (
        <View className="loading-more">
          <Text>加载中...</Text>
        </View>
      )}

      {/* 没有更多数据 */}
      {!hasMore && records.length > 0 && (
        <View className="no-more">
          <Text>没有更多了</Text>
        </View>
      )}

      {/* 登录弹窗 */}
      <LoginPopup
        visible={showLoginPopup}
        onClose={handleLoginClose}
        onSuccess={handleLoginSuccess}
      />
    </View>
  );
};

export default RecordsPage;
