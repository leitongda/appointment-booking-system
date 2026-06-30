import { NavBar, Toast, Skeleton, TextArea } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { appointmentApi } from '@hospital/api';
import type { Appointment } from '@hospital/shared';
import { Card, Button } from '@/components/ui';
import { fadeInUp } from '@/components/ui/animations';

/** 评分标签选项 */
const RATING_TAGS = [
  '医术精湛', '态度亲切', '耐心细致', '讲解清晰',
  '环境整洁', '等候时间短', '流程顺畅', '值得推荐',
];

/**
 * 满意度评价页面
 *
 * 就诊完成后，患者点击站内信通知进入此页面填写满意度。
 * 路由：/satisfaction/:appointmentId
 * 后端：apps/server/app/modules/appointment_satisfactions/router.py
 */
const SatisfactionPage: React.FC = () => {
  const { appointmentId } = useParams() as { appointmentId: string };
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [overallScore, setOverallScore] = useState(0);
  const [serviceScore, setServiceScore] = useState(0);
  const [environmentScore, setEnvironmentScore] = useState(0);
  const [comment, setComment] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (appointmentId) loadData();
  }, [appointmentId]);

  const loadData = async () => {
    try {
      const data = await appointmentApi.getDetail(appointmentId!);
      setAppointment(data);
      // 检查是否已提交过满意度
      try {
        const existing = await appointmentApi.getSatisfaction(appointmentId!);
        if (existing?.id) {
          setSubmitted(true);
          setOverallScore(existing.overallScore || 0);
          setServiceScore(existing.serviceScore || 0);
          setEnvironmentScore(existing.environmentScore || 0);
          setComment(existing.comment || '');
          setSelectedTags(existing.tags || []);
        }
      } catch {
        // 未提交过，正常
      }
    } catch (error: any) {
      Toast.show({ icon: 'fail', content: error.message || '加载预约信息失败' });
    } finally {
      setLoading(false);
    }
  };

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSubmit = async () => {
    if (overallScore === 0) {
      Toast.show({ icon: 'fail', content: '请选择综合评分' });
      return;
    }
    setSubmitting(true);
    try {
      await appointmentApi.createSatisfaction(appointmentId!, {
        overallScore,
        serviceScore: serviceScore || undefined,
        environmentScore: environmentScore || undefined,
        comment: comment || undefined,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
      });
      Toast.show({ icon: 'success', content: '评价提交成功，感谢您的反馈！' });
      setSubmitted(true);
    } catch (error: any) {
      Toast.show({ icon: 'fail', content: error.message || '提交失败，请稍后重试' });
    } finally {
      setSubmitting(false);
    }
  };

  const renderStars = (value: number, onChange: (v: number) => void, label: string) => (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 14, color: '#666', marginBottom: 8 }}>{label}</div>
      <div style={{ display: 'flex', gap: 8 }}>
        {[1, 2, 3, 4, 5].map((star) => (
          <div
            key={star}
            onClick={() => !submitted && onChange(star)}
            style={{
              fontSize: 32,
              cursor: submitted ? 'default' : 'pointer',
              color: star <= value ? '#FFD700' : '#E0E0E0',
              transition: 'color 0.2s',
            }}
          >
            ★
          </div>
        ))}
      </div>
    </div>
  );

  if (loading) {
    return (
      <div>
        <NavBar onBack={() => history.back()}>满意度评价</NavBar>
        <div style={{ padding: 16 }}>
          <Skeleton.Title animated />
          <Skeleton.Paragraph lineCount={5} animated />
        </div>
      </div>
    );
  }

  if (!appointment) {
    return (
      <div>
        <NavBar onBack={() => history.back()}>满意度评价</NavBar>
        <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
          预约信息不存在
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <NavBar onBack={() => history.back()}>满意度评价</NavBar>

      <motion.div variants={fadeInUp} initial="hidden" animate="visible" style={{ padding: 16 }}>
        {/* 预约信息卡片 */}
        <Card style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
            {appointment.doctorName} · {appointment.departmentName}
          </div>
          <div style={{ fontSize: 14, color: '#666' }}>
            {appointment.scheduleDate} {appointment.timeSlot === 'morning' ? '上午' : appointment.timeSlot === 'afternoon' ? '下午' : '晚间'}
          </div>
        </Card>

        {submitted ? (
          /* 已提交状态 */
          <Card>
            <div style={{ textAlign: 'center', padding: 24 }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
              <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>评价已提交</div>
              <div style={{ fontSize: 14, color: '#666', marginBottom: 16 }}>
                感谢您的反馈，我们会持续改进服务
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
                {selectedTags.map((tag) => (
                  <span key={tag} style={{ padding: '4px 12px', background: '#E6F7FF', color: '#1677ff', borderRadius: 12, fontSize: 12 }}>
                    {tag}
                  </span>
                ))}
              </div>
              {comment && (
                <div style={{ marginTop: 16, padding: 12, background: '#FAFAFA', borderRadius: 8, textAlign: 'left', fontSize: 14, color: '#333' }}>
                  {comment}
                </div>
              )}
            </div>
          </Card>
        ) : (
          /* 评价表单 */
          <>
            {/* 综合评分 */}
            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>请为本次就诊评分</div>
              {renderStars(overallScore, setOverallScore, '综合评分 *')}
              {renderStars(serviceScore, setServiceScore, '服务态度')}
              {renderStars(environmentScore, setEnvironmentScore, '就诊环境')}
            </Card>

            {/* 评价标签 */}
            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>选择标签（可多选）</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {RATING_TAGS.map((tag) => {
                  const isSelected = selectedTags.includes(tag);
                  return (
                    <div
                      key={tag}
                      onClick={() => toggleTag(tag)}
                      style={{
                        padding: '6px 16px',
                        borderRadius: 20,
                        fontSize: 14,
                        cursor: 'pointer',
                        background: isSelected ? '#1677ff' : '#F5F5F5',
                        color: isSelected ? '#fff' : '#333',
                        border: isSelected ? '1px solid #1677ff' : '1px solid #E0E0E0',
                        transition: 'all 0.2s',
                      }}
                    >
                      {tag}
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* 评价内容 */}
            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>详细评价（可选）</div>
              <TextArea
                placeholder="请分享您的就诊体验，帮助我们改进服务..."
                value={comment}
                onChange={setComment}
                rows={4}
                maxLength={500}
                showCount
              />
            </Card>

            {/* 提交按钮 */}
            <Button
              variant="primary"
              size="lg"
              onClick={handleSubmit}
              disabled={submitting || overallScore === 0}
              style={{ width: '100%' }}
            >
              {submitting ? '提交中...' : '提交评价'}
            </Button>
          </>
        )}
      </motion.div>
    </div>
  );
};

export default SatisfactionPage;
