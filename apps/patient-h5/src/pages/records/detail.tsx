import { NavBar, Card } from 'antd-mobile';
import { history, useParams } from 'umi';
import styles from './detail.less';

const RecordDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>病历详情</NavBar>
      
      <Card title="就诊信息" className={styles.card}>
        <div className={styles.row}><span>就诊日期</span><span>2024-11-20</span></div>
        <div className={styles.row}><span>医生</span><span>张医生</span></div>
        <div className={styles.row}><span>科室</span><span>心内科</span></div>
      </Card>

      <Card title="诊断信息" className={styles.card}>
        <div className={styles.section}>
          <div className={styles.label}>主诉</div>
          <div>头晕、乏力3天</div>
        </div>
        <div className={styles.section}>
          <div className={styles.label}>诊断</div>
          <div>高血压</div>
        </div>
        <div className={styles.section}>
          <div className={styles.label}>治疗方案</div>
          <div>药物治疗，控制血压</div>
        </div>
      </Card>

      <Card title="处方信息" className={styles.card}>
        <div className={styles.prescription}>
          <div>1. 降压药 每日2次，每次1片</div>
          <div>2. 维生素B 每日1次，每次2片</div>
        </div>
      </Card>

      <Card title="医嘱" className={styles.card}>
        <div>注意休息，低盐低脂饮食，定期复查</div>
      </Card>
    </div>
  );
};

export default RecordDetailPage;

