import { View, Text } from '@tarojs/components';
import Taro from '@tarojs/taro';
import { useState, useEffect } from 'react';
import { userApi } from '@hospital/api';
import type { Patient } from '@hospital/shared';

interface PatientPickerProps {
  /** 当前选中的就诊人 ID */
  value?: string;
  /** 选中回调 */
  onChange?: (patientId: string | undefined) => void;
}

/**
 * 就诊人选择器（小程序版）
 * - 默认选中默认就诊人（is_default=true）
 * - 支持切换到家庭成员
 */
const PatientPicker: React.FC<PatientPickerProps> = ({ value, onChange }) => {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [currentPatient, setCurrentPatient] = useState<Patient | null>(null);

  useEffect(() => {
    loadPatients();
  }, []);

  useEffect(() => {
    if (patients.length > 0) {
      if (value) {
        const found = patients.find((p) => p.id === value);
        setCurrentPatient(found || null);
      } else {
        const defaultP = patients.find((p) => p.isDefault);
        setCurrentPatient(defaultP || patients[0] || null);
      }
    }
  }, [patients, value]);

  const loadPatients = async () => {
    try {
      const list = await userApi.getPatients();
      setPatients(list || []);
    } catch (error) {
      console.error('加载就诊人列表失败', error);
    }
  };

  const handlePress = async () => {
    if (patients.length <= 1) return;

    // 构建选项列表：默认就诊人 + 所有就诊人
    const defaultPatient = patients.find((p) => p.isDefault);
    const itemList = [
      `默认：${defaultPatient?.name || '-'}`,
      ...patients.map((p) =>
        `${p.name}${p.relationship ? ` (${p.relationship})` : ''}${p.isDefault ? ' [默认]' : ''}`
      ),
    ];

    try {
      const result = await Taro.showActionSheet({ itemList });
      const index = result.tapIndex;

      if (index === 0) {
        // 选择默认就诊人
        setCurrentPatient(defaultPatient || null);
        onChange?.(undefined);
      } else {
        const patient = patients[index - 1];
        setCurrentPatient(patient || null);
        onChange?.(patient?.id);
      }
    } catch (error: any) {
      // 用户取消选择
      if (error.errMsg !== 'showActionSheet:fail cancel') {
        console.error('选择就诊人失败', error);
      }
    }
  };

  // 只有一个就诊人时不显示切换
  if (patients.length <= 1) {
    return currentPatient ? (
      <Text className="patient-name">{currentPatient.name}</Text>
    ) : null;
  }

  const displayText = currentPatient?.name || '选择就诊人';

  return (
    <View className="patient-picker-trigger" onClick={handlePress}>
      <Text className="patient-name">{displayText}</Text>
      <Text className="patient-arrow">▾</Text>
    </View>
  );
};

export default PatientPicker;
