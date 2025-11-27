import { NavBar, List, Button, Tag, SwipeAction, Dialog, Toast } from 'antd-mobile';
import { history } from 'umi';
import { AddOutline } from 'antd-mobile-icons';
import { GENDER_MAP } from '@hospital/shared';
import styles from './index.less';

const mockPatients = [
  { id: '1', name: '张三', phone: '13800138000', gender: 1, idCard: '310***********1234', relationship: '本人', isDefault: true },
  { id: '2', name: '李四', phone: '13800138001', gender: 2, idCard: '310***********5678', relationship: '父母', isDefault: false },
];

const PatientListPage: React.FC = () => {
  const handleDelete = async (id: string) => {
    const result = await Dialog.confirm({ content: '确定要删除该就诊人吗？' });
    if (result) {
      Toast.show('删除成功');
    }
  };

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>就诊人管理</NavBar>
      <List>
        {mockPatients.map((patient) => (
          <SwipeAction
            key={patient.id}
            rightActions={[
              { key: 'delete', text: '删除', color: 'danger', onClick: () => handleDelete(patient.id) },
            ]}
          >
            <List.Item
              description={
                <div className={styles.patientInfo}>
                  <span>{GENDER_MAP[patient.gender]}</span>
                  <span>{patient.phone}</span>
                  <span>{patient.idCard}</span>
                </div>
              }
              extra={patient.isDefault && <Tag color="primary">默认</Tag>}
              onClick={() => history.push(`/profile/patient/edit?id=${patient.id}`)}
              arrow
            >
              <div className={styles.patientName}>
                {patient.name}
                <Tag fill="outline">{patient.relationship}</Tag>
              </div>
            </List.Item>
          </SwipeAction>
        ))}
      </List>
      <div className={styles.addBtn}>
        <Button block color="primary" onClick={() => history.push('/profile/patient/edit')}>
          <AddOutline /> 添加就诊人
        </Button>
      </div>
    </div>
  );
};

export default PatientListPage;

