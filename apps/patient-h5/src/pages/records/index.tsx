import { NavBar, List, Empty } from 'antd-mobile';
import { history } from 'umi';
import styles from './index.less';

const mockRecords = [
  { id: '1', doctorName: '张医生', deptName: '心内科', diagnosis: '高血压', visitDate: '2024-11-20' },
  { id: '2', doctorName: '李医生', deptName: '消化内科', diagnosis: '胃炎', visitDate: '2024-10-15' },
];

const RecordsPage: React.FC = () => {
  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>就诊记录</NavBar>
      {mockRecords.length === 0 ? (
        <Empty description="暂无就诊记录" />
      ) : (
        <List>
          {mockRecords.map((record) => (
            <List.Item
              key={record.id}
              description={<div className={styles.diagnosis}>诊断：{record.diagnosis}</div>}
              extra={record.visitDate}
              onClick={() => history.push(`/records/${record.id}`)}
              arrow
            >
              {record.doctorName} - {record.deptName}
            </List.Item>
          ))}
        </List>
      )}
    </div>
  );
};

export default RecordsPage;

