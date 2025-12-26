import { NavBar, Skeleton, Toast, Empty } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { medicalRecordApi } from '@hospital/api';
import type { MedicalRecord } from '@hospital/api';
import { Card, SectionLabel } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

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
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          病历详情
        </NavBar>
        <div className="p-4">
          <Skeleton.Paragraph lineCount={10} animated />
        </div>
      </div>
    );
  }

  if (!record) {
    return (
      <div className="min-h-screen bg-background">
        <NavBar 
          onBack={() => history.back()}
          className="!bg-card border-b border-border"
        >
          病历详情
        </NavBar>
        <div className="flex items-center justify-center h-64">
          <Empty description="病历不存在" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-6">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        病历详情
      </NavBar>
      
      <motion.div
        className="p-4 space-y-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Visit Info */}
        <motion.div variants={fadeInUp}>
          <Card variant="elevated" padding="lg">
            <h3 className="font-semibold text-foreground mb-4">就诊信息</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">病历号</span>
                <span className="font-mono text-foreground">{record.recordNo}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">就诊日期</span>
                <span className="text-foreground">{formatDate(record.visitDate)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">医生</span>
                <span className="text-foreground">{record.doctorName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">科室</span>
                <span className="text-foreground">{record.departmentName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">患者</span>
                <span className="text-foreground">{record.patientName}</span>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Diagnosis Info */}
        <motion.div variants={fadeInUp}>
          <Card variant="default" padding="lg">
            <h3 className="font-semibold text-foreground mb-4">诊断信息</h3>
            <div className="space-y-4">
              {record.chiefComplaint && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">主诉</p>
                  <p className="text-foreground">{record.chiefComplaint}</p>
                </div>
              )}
              {record.presentIllness && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">现病史</p>
                  <p className="text-foreground">{record.presentIllness}</p>
                </div>
              )}
              {record.pastHistory && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">既往史</p>
                  <p className="text-foreground">{record.pastHistory}</p>
                </div>
              )}
              {record.allergyHistory && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">过敏史</p>
                  <p className="text-foreground">{record.allergyHistory}</p>
                </div>
              )}
              {record.physicalExam && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">体格检查</p>
                  <p className="text-foreground">{record.physicalExam}</p>
                </div>
              )}
              {record.auxiliaryExam && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">辅助检查</p>
                  <p className="text-foreground">{record.auxiliaryExam}</p>
                </div>
              )}
              <div>
                <p className="text-sm text-muted-foreground mb-2">诊断</p>
                <span className="inline-block text-sm text-accent bg-accent/10 px-3 py-1.5 rounded-full">
                  {record.diagnosis}
                </span>
              </div>
              {record.treatment && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">治疗方案</p>
                  <p className="text-foreground">{record.treatment}</p>
                </div>
              )}
            </div>
          </Card>
        </motion.div>

        {/* Prescription */}
        {record.prescription && (
          <motion.div variants={fadeInUp}>
            <Card variant="default" padding="lg">
              <h3 className="font-semibold text-foreground mb-4">处方信息</h3>
              <div className="bg-muted rounded-xl p-4">
                {record.prescription.split('\n').map((line, index) => (
                  <p key={index} className="text-foreground text-sm leading-relaxed">
                    {line}
                  </p>
                ))}
              </div>
            </Card>
          </motion.div>
        )}

        {/* Advice */}
        {record.advice && (
          <motion.div variants={fadeInUp}>
            <Card variant="default" padding="lg">
              <h3 className="font-semibold text-foreground mb-4">医嘱</h3>
              <p className="text-foreground leading-relaxed">{record.advice}</p>
            </Card>
          </motion.div>
        )}

        {/* Fee Info */}
        {record.totalFee !== undefined && record.totalFee > 0 && (
          <motion.div variants={fadeInUp}>
            <Card variant="gradient-border" padding="lg">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">总费用</span>
                <span className="text-accent font-semibold text-xl">
                  ¥{record.totalFee.toFixed(2)}
                </span>
              </div>
            </Card>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};

export default RecordDetailPage;
