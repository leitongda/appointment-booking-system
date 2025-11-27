import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Empty } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { appointmentApi } from '@hospital/api';
import type { MedicalRecord } from '@hospital/shared';
import './index.less';

const RecordsPage = () => {
  const [loading, setLoading] = useState(true);
  const [records, setRecords] = useState<MedicalRecord[]>([]);

  useEffect(() => {
    loadRecords();
  }, []);

  const loadRecords = async () => {
    try {
      const data = await appointmentApi.getMedicalRecords();
      setRecords(data);
    } catch (error) {
      console.error('加载就诊记录失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = (id: string) => {
    Taro.navigateTo({ url: `/pages/records/detail?id=${id}` });
  };

  return (
    <View className="records-page">
      {records.length === 0 && !loading ? (
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
                <Text className="date">{record.visitDate}</Text>
                <Text className="dept">{record.departmentName}</Text>
              </View>
              <View className="card-body">
                <View className="info-row">
                  <Text className="label">就诊医生</Text>
                  <Text className="value">{record.doctorName}</Text>
                </View>
                <View className="info-row">
                  <Text className="label">主诉</Text>
                  <Text className="value">{record.chiefComplaint || '无'}</Text>
                </View>
                <View className="info-row">
                  <Text className="label">诊断</Text>
                  <Text className="value">{record.diagnosis || '无'}</Text>
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

