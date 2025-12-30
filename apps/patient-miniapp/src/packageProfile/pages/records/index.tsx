import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Empty, Loading } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { medicalRecordApi } from '@hospital/api';
import { getToken } from '../../../utils/auth';
import type { MedicalRecordListItem } from '@hospital/api';
import './index.less';

const RecordsPage = () => {
  const [loading, setLoading] = useState(true);
  const [records, setRecords] = useState<MedicalRecordListItem[]>([]);

  useEffect(() => {
    // 检查登录状态
    const token = getToken();
    if (!token) {
      Taro.showToast({ title: '请先登录', icon: 'none' });
      Taro.navigateTo({ url: '/pages/login/index' });
      return;
    }
    loadRecords();
  }, []);

  const loadRecords = async () => {
    try {
      const result = await medicalRecordApi.getList({ pageSize: 50 });
      setRecords(result.data || []);
    } catch (error) {
      console.error('加载就诊记录失败', error);
      Taro.showToast({ title: '加载失败', icon: 'none' });
    } finally {
      setLoading(false);
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
    </View>
  );
};

export default RecordsPage;
