import { useState, useEffect } from 'react';
import { Popup, List, CheckList } from 'antd-mobile';
import type { CheckListValue } from 'antd-mobile/es/components/check-list';
import { userApi } from '@hospital/api';
import type { Patient } from '@hospital/shared';

interface PatientPickerProps {
  /** 当前选中的就诊人 ID */
  value?: string;
  /** 选中回调 */
  onChange?: (patientId: string | undefined) => void;
  /** 是否显示"全部"选项（默认 false，即默认就诊人模式） */
  showAll?: boolean;
}

/**
 * 就诊人选择器
 * - 默认选中默认就诊人（is_default=true）
 * - 支持切换到家庭成员
 * - 不暴露 patient_id 给 URL，仅通过回调传递
 */
export const PatientPicker: React.FC<PatientPickerProps> = ({
  value,
  onChange,
  showAll = false,
}) => {
  const [visible, setVisible] = useState(false);
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
        // 默认选中默认就诊人
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

  const handleSelect = (val: CheckListValue[]) => {
    const selectedId = val[0] as string;
    if (selectedId === '__default__') {
      // 选择默认就诊人，不传 patient_id
      setCurrentPatient(patients.find((p) => p.isDefault) || null);
      onChange?.(undefined);
    } else {
      const found = patients.find((p) => p.id === selectedId);
      setCurrentPatient(found || null);
      onChange?.(selectedId);
    }
    setVisible(false);
  };

  // 只有一个就诊人时不显示切换
  if (patients.length <= 1 && !showAll) {
    return currentPatient ? (
      <span className="text-sm text-white/90">{currentPatient.name}</span>
    ) : null;
  }

  const displayText = currentPatient?.name || '选择就诊人';
  const selectedKeys = currentPatient ? [currentPatient.id] : [];

  return (
    <>
      <div
        className="flex items-center gap-1 cursor-pointer"
        onClick={() => setVisible(true)}
      >
        <span className="text-sm text-white/90">{displayText}</span>
        <span className="text-xs text-white/60">切换 ▾</span>
      </div>

      <Popup
        visible={visible}
        onMaskClick={() => setVisible(false)}
        bodyStyle={{ borderTopLeftRadius: 12, borderTopRightRadius: 12 }}
      >
        <div className="p-4">
          <h3 className="text-base font-medium mb-3">选择就诊人</h3>
          <CheckList
            multiple={false}
            value={selectedKeys}
            onChange={handleSelect}
          >
            {showAll && (
              <CheckList.Item value="__default__">
                <div>
                  <div className="text-sm font-medium">默认就诊人</div>
                  <div className="text-xs text-muted-foreground">
                    {patients.find((p) => p.isDefault)?.name || '-'}
                  </div>
                </div>
              </CheckList.Item>
            )}
            {patients.map((patient) => (
              <CheckList.Item key={patient.id} value={patient.id}>
                <div className="flex items-center justify-between w-full">
                  <div>
                    <div className="text-sm font-medium">
                      {patient.name}
                      {patient.isDefault && (
                        <span className="ml-2 text-xs text-primary">默认</span>
                      )}
                    </div>
                    {patient.relationship && (
                      <div className="text-xs text-muted-foreground">
                        {patient.relationship}
                      </div>
                    )}
                  </div>
                </div>
              </CheckList.Item>
            ))}
          </CheckList>
        </div>
      </Popup>
    </>
  );
};
