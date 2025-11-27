import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { Button, Empty, SwipeCell } from '@nutui/nutui-react-taro';
import { useState, useEffect } from 'react';
import { userApi } from '@hospital/api';
import { GENDER_MAP } from '@hospital/shared';
import type { Patient } from '@hospital/shared';
import './index.less';

const PatientListPage = () => {
  const [loading, setLoading] = useState(true);
  const [patients, setPatients] = useState<Patient[]>([]);

  useEffect(() => {
    loadPatients();
  }, []);

  // 页面显示时刷新
  Taro.useDidShow(() => {
    loadPatients();
  });

  const loadPatients = async () => {
    try {
      const data = await userApi.getPatients();
      setPatients(data);
    } catch (error) {
      console.error('加载就诊人失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    const result = await Taro.showModal({
      title: '删除就诊人',
      content: '确定要删除该就诊人吗？',
    });

    if (!result.confirm) return;

    try {
      await userApi.deletePatient(id);
      Taro.showToast({ title: '删除成功', icon: 'success' });
      loadPatients();
    } catch (error: any) {
      Taro.showToast({ title: error.message || '删除失败', icon: 'none' });
    }
  };

  const handleEdit = (id: string) => {
    Taro.navigateTo({ url: `/pages/profile/patient/edit?id=${id}` });
  };

  const handleAdd = () => {
    Taro.navigateTo({ url: '/pages/profile/patient/edit' });
  };

  return (
    <View className="patient-list-page">
      {patients.length === 0 && !loading ? (
        <Empty description="暂无就诊人，请添加" />
      ) : (
        <View className="list">
          {patients.map((patient) => (
            <SwipeCell
              key={patient.id}
              rightAction={
                <Button type="danger" onClick={() => handleDelete(patient.id)}>
                  删除
                </Button>
              }
            >
              <View className="patient-item" onClick={() => handleEdit(patient.id)}>
                <View className="patient-main">
                  <Text className="patient-name">{patient.name}</Text>
                  {patient.relationship && (
                    <Text className="relationship">{patient.relationship}</Text>
                  )}
                  {patient.isDefault && <Text className="default-tag">默认</Text>}
                </View>
                <View className="patient-info">
                  <Text>{GENDER_MAP[patient.gender || 0]}</Text>
                  <Text className="divider">|</Text>
                  <Text>{patient.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}</Text>
                </View>
                <Text className="arrow">›</Text>
              </View>
            </SwipeCell>
          ))}
        </View>
      )}

      <View className="footer">
        <Button type="primary" block onClick={handleAdd}>
          添加就诊人
        </Button>
      </View>
    </View>
  );
};

export default PatientListPage;

