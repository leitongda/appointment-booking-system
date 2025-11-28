import { NavBar, Card, Skeleton, Toast, Tag, Empty } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { medicalRecordApi } from '@hospital/api';
import type { MedicalRecord } from '@hospital/api';
import styles from './detail.less';

const RecordDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [record, setRecord] = useState<MedicalRecord | null>(null);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    try {
      const data = await medicalRecordApi.getDetail(id!);
      setRecord(data);
    } catch (error: any) {
      Toast.show({ content: error.message || '加载失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (date?: string) => {
    if (!date) return '-';
    return date.substring(0, 10);
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>病历详情</NavBar>
        <div style={{ padding: 16 }}>
          <Skeleton.Paragraph lineCount={10} animated />
        </div>
      </div>
    );
  }

  if (!record) {
    return (
      <div className={styles.container}>
        <NavBar onBack={() => history.back()}>病历详情</NavBar>
        <Empty description="病历不存在" style={{ marginTop: 100 }} />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <NavBar onBack={() => history.back()}>病历详情</NavBar>
      
      <Card title="就诊信息" className={styles.card}>
        <div className={styles.row}>
          <span>病历号</span>
          <span>{record.recordNo}</span>
        </div>
        <div className={styles.row}>
          <span>就诊日期</span>
          <span>{formatDate(record.visitDate)}</span>
        </div>
        <div className={styles.row}>
          <span>医生</span>
          <span>{record.doctorName}</span>
        </div>
        <div className={styles.row}>
          <span>科室</span>
          <span>{record.departmentName}</span>
        </div>
        <div className={styles.row}>
          <span>患者</span>
          <span>{record.patientName}</span>
        </div>
      </Card>

      <Card title="诊断信息" className={styles.card}>
        {record.chiefComplaint && (
          <div className={styles.section}>
            <div className={styles.label}>主诉</div>
            <div className={styles.content}>{record.chiefComplaint}</div>
          </div>
        )}
        {record.presentIllness && (
          <div className={styles.section}>
            <div className={styles.label}>现病史</div>
            <div className={styles.content}>{record.presentIllness}</div>
          </div>
        )}
        {record.pastHistory && (
          <div className={styles.section}>
            <div className={styles.label}>既往史</div>
            <div className={styles.content}>{record.pastHistory}</div>
          </div>
        )}
        {record.allergyHistory && (
          <div className={styles.section}>
            <div className={styles.label}>过敏史</div>
            <div className={styles.content}>{record.allergyHistory}</div>
          </div>
        )}
        {record.physicalExam && (
          <div className={styles.section}>
            <div className={styles.label}>体格检查</div>
            <div className={styles.content}>{record.physicalExam}</div>
          </div>
        )}
        {record.auxiliaryExam && (
          <div className={styles.section}>
            <div className={styles.label}>辅助检查</div>
            <div className={styles.content}>{record.auxiliaryExam}</div>
          </div>
        )}
        <div className={styles.section}>
          <div className={styles.label}>诊断</div>
          <div className={styles.content}>
            <Tag color="primary">{record.diagnosis}</Tag>
          </div>
        </div>
        {record.treatment && (
          <div className={styles.section}>
            <div className={styles.label}>治疗方案</div>
            <div className={styles.content}>{record.treatment}</div>
          </div>
        )}
      </Card>

      {record.prescription && (
        <Card title="处方信息" className={styles.card}>
          <div className={styles.prescription}>
            {record.prescription.split('\n').map((line, index) => (
              <div key={index}>{line}</div>
            ))}
          </div>
        </Card>
      )}

      {record.advice && (
        <Card title="医嘱" className={styles.card}>
          <div className={styles.content}>{record.advice}</div>
        </Card>
      )}

      {record.totalFee !== undefined && record.totalFee > 0 && (
        <Card title="费用信息" className={styles.card}>
          <div className={styles.row}>
            <span>总费用</span>
            <span className={styles.fee}>¥{record.totalFee.toFixed(2)}</span>
          </div>
        </Card>
      )}
    </div>
  );
};

export default RecordDetailPage;
