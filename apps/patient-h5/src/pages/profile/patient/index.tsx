import { NavBar, List, Tag, SwipeAction, Dialog, Toast, Empty, Skeleton } from 'antd-mobile';
import { history } from 'umi';
import { AddOutline } from 'antd-mobile-icons';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { userApi } from '@hospital/api';
import { GENDER_MAP } from '@hospital/shared';
import type { Patient } from '@hospital/shared';
import { Button } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

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
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          就诊人管理
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={5} animated />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-24">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        就诊人管理
      </NavBar>
      
      {patients.length === 0 ? (
        <Empty description="暂无就诊人，请添加" className="mt-24" />
      ) : (
        <motion.div
          variants={stagger}
          initial="hidden"
          animate="visible"
        >
          <List className="!bg-transparent">
            {patients.map((patient, index) => (
              <motion.div key={patient.id} variants={fadeInUp}>
                <SwipeAction
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
                    className="!bg-card !rounded-xl !mx-4 !mt-3 !shadow-sm"
                    description={
                      <div className="flex gap-3 text-sm text-muted-foreground mt-1">
                        <span>{GENDER_MAP[patient.gender || 0]}</span>
                        <span>{patient.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')}</span>
                        {patient.idCard && (
                          <span className="font-mono text-xs">
                            {patient.idCard.replace(/(\d{4})\d{10}(\d{4})/, '$1**********$2')}
                          </span>
                        )}
                      </div>
                    }
                    extra={
                      patient.isDefault && (
                        <span className="text-xs text-accent bg-accent/10 px-2 py-1 rounded-full">
                          默认
                        </span>
                      )
                    }
                    onClick={() => history.push(`/profile/patient/edit?id=${patient.id}`)}
                    arrow
                  >
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-foreground">{patient.name}</span>
                      {patient.relationship && (
                        <span className="text-xs text-muted-foreground border border-border px-2 py-0.5 rounded">
                          {patient.relationship}
                        </span>
                      )}
                    </div>
                  </List.Item>
                </SwipeAction>
              </motion.div>
            ))}
          </List>
        </motion.div>
      )}

      <div className="fixed bottom-0 left-0 right-0 p-4 bg-background/80 backdrop-blur-sm border-t border-border">
        <Button 
          variant="primary"
          className="w-full"
          onClick={() => history.push('/profile/patient/edit')}
        >
          <AddOutline className="mr-2" /> 添加就诊人
        </Button>
      </div>
    </div>
  );
};

export default PatientListPage;
