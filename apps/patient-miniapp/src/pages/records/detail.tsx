import { View, Text } from '@tarojs/components';
import { useRouter } from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { appointmentApi } from '@hospital/api';
import type { MedicalRecord } from '@hospital/shared';
import './detail.less';

const RecordDetailPage = () => {
  const router = useRouter();
  const { id } = router.params;

  const [loading, setLoading] = useState(true);
  const [record, setRecord] = useState<MedicalRecord | null>(null);

  useEffect(() => {
    if (id) {
      loadRecord();
    }
  }, [id]);

  const loadRecord = async () => {
    try {
      const data = await appointmentApi.getMedicalRecordDetail(id!);
      setRecord(data);
    } catch (error) {
      console.error('加载就诊记录详情失败', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !record) {
    return <View className="loading">加载中...</View>;
  }

  return (
    <View className="record-detail-page">
      <View className="header">
        <Text className="date">{record.visitDate}</Text>
        <Text className="dept">{record.departmentName}</Text>
      </View>

      <View className="section">
        <Text className="section-title">就诊信息</Text>
        <View className="info-row">
          <Text className="label">就诊医生</Text>
          <Text className="value">{record.doctorName}</Text>
        </View>
        <View className="info-row">
          <Text className="label">患者姓名</Text>
          <Text className="value">{record.patientName}</Text>
        </View>
      </View>

      <View className="section">
        <Text className="section-title">诊疗信息</Text>
        <View className="info-block">
          <Text className="block-label">主诉</Text>
          <Text className="block-value">{record.chiefComplaint || '无'}</Text>
        </View>
        <View className="info-block">
          <Text className="block-label">现病史</Text>
          <Text className="block-value">{record.presentIllness || '无'}</Text>
        </View>
        <View className="info-block">
          <Text className="block-label">诊断</Text>
          <Text className="block-value">{record.diagnosis || '无'}</Text>
        </View>
        <View className="info-block">
          <Text className="block-label">处置方案</Text>
          <Text className="block-value">{record.treatment || '无'}</Text>
        </View>
      </View>

      {record.prescription && (
        <View className="section">
          <Text className="section-title">处方信息</Text>
          <Text className="prescription">{record.prescription}</Text>
        </View>
      )}

      {record.advice && (
        <View className="section">
          <Text className="section-title">医嘱</Text>
          <Text className="advice">{record.advice}</Text>
        </View>
      )}
    </View>
  );
};

export default RecordDetailPage;

