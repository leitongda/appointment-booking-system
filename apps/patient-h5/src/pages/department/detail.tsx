import { NavBar, Card } from 'antd-mobile';
import { history, useParams } from 'umi';
import styles from './detail.less';

const DepartmentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>科室详情</NavBar>
      <div className={styles.content}>
        <Card title="科室简介">
          <p>内科是研究人体内部器官疾病的临床医学学科，主要诊治心、肺、肝、肾等内脏器官的疾病。</p>
        </Card>
      </div>
    </div>
  );
};

export default DepartmentDetailPage;

