import { NavBar, List, Button, Tag, SwipeAction, Dialog, Toast, Empty, Skeleton } from 'antd-mobile';
import { history } from 'umi';
import { AddOutline } from 'antd-mobile-icons';
import { useState, useEffect } from 'react';
import { userApi } from '@hospital/api';
import { GENDER_MAP } from '@hospital/shared';
import type { Patient } from '@hospital/shared';
import styles from './index.less';

const PatientListPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [patients, setPatients] = useState<Patient[]>([]);

  useEffect(() => {
    loadPatients();
  }, []);

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
    const result = await Dialog.confirm({ 
      content: '确定要删除该就诊人吗？删除后无法恢复。' 
    });
    
    if (!result) return;

    try {
      await userApi.deletePatient(id);
      Toast.show({ content: '删除成功', icon: 'success' });
      loadPatients();
    } catch (error: any) {
      Toast.show({ content: error.message || '删除失败', icon: 'fail' });
    }
  };

  const handleSetDefault = async (patient: Patient) => {
    if (patient.isDefault) return;

    try {
      await userApi.updatePatient(patient.id, { isDefault: true });
      Toast.show({ content: '设置成功', icon: 'success' });
      loadPatients();
    } catch (error: any) {
      Toast.show({ content: error.message || '设置失败', icon: 'fail' });
    }
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>就诊人管理</NavBar>
        <Skeleton.Paragraph lineCount={5} animated />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>就诊人管理</NavBar>
      
      {patients.length === 0 ? (
        <Empty description="暂无就诊人，请添加" style={{ marginTop: 100 }} />
      ) : (
        <List>
          {patients.map((patient) => (
            <SwipeAction
              key={patient.id}
              rightActions={[
                {
                  key: 'default',
                  text: '设为默认',
                  color: 'primary',
                  onClick: () => handleSetDefault(patient),
                },
                {
                  key: 'delete',
                  text: '删除',
                  color: 'danger',
                  onClick: () => handleDelete(patient.id),
                },
              ]}
            >
              <List.Item
                description={
                  <div className={styles.patientInfo}>
                    <span>{GENDER_MAP[patient.gender || 0]}</span>
                    <span>{patient.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}</span>
                    {patient.idCard && (
                      <span>{patient.idCard.replace(/(\d{4})\d{10}(\d{4})/, '$1**********$2')}</span>
                    )}
                  </div>
                }
                extra={patient.isDefault && <Tag color="primary">默认</Tag>}
                onClick={() => history.push(`/profile/patient/edit?id=${patient.id}`)}
                arrow
              >
                <div className={styles.patientName}>
                  {patient.name}
                  {patient.relationship && (
                    <Tag fill="outline" style={{ marginLeft: 8 }}>{patient.relationship}</Tag>
                  )}
                </div>
              </List.Item>
            </SwipeAction>
          ))}
        </List>
      )}

      <div className={styles.addBtn}>
        <Button 
          block 
          color="primary" 
          size="large"
          onClick={() => history.push('/profile/patient/edit')}
        >
          <AddOutline /> 添加就诊人
        </Button>
      </div>
    </div>
  );
};

export default PatientListPage;
