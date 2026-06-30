import { NavBar, Toast, Skeleton, TextArea, Switch } from 'antd-mobile';
import { history, useParams } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { appointmentApi, doctorApi } from '@hospital/api';
import type { Appointment } from '@hospital/shared';
import { Card, Button } from '@/components/ui';
import { fadeInUp } from '@/components/ui/animations';

/** 评价标签选项 */
const REVIEW_TAGS = [
  '医术精湛', '态度亲切', '耐心细致', '讲解清晰',
  '经验丰富', '诊断准确', '用药合理', '值得信赖',
];

/**
 * 医生评价页面
 *
 * 就诊完成后，患者可以对医生进行评价。
 * 路由：/review/:appointmentId
 * 后端：apps/server/app/modules/doctor_reviews/router.py
 */
const ReviewPage: React.FC = () => {
  const { appointmentId } = useParams() as { appointmentId: string };
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [rating, setRating] = useState(0);
  const [content, setContent] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [isAnonymous, setIsAnonymous] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (appointmentId) loadData();
  }, [appointmentId]);

  const loadData = async () => {
    try {
      const data = await appointmentApi.getDetail(appointmentId!);
      setAppointment(data);
      // 检查是否已提交过评价
      try {
        const reviews = await doctorApi.getDoctorReviews(data.doctorId, { page: 1, pageSize: 100 });
        const existing = reviews.data.find((review) => review.appointmentId === appointmentId);
        if (existing) {
          setSubmitted(true);
          setRating(existing.rating || 0);
          setContent(existing.content || '');
          setSelectedTags(existing.tags || []);
          setIsAnonymous(existing.isAnonymous || false);
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
    if (rating === 0) {
      Toast.show({ icon: 'fail', content: '请选择评分' });
      return;
    }
    if (!appointment?.doctorId) {
      Toast.show({ icon: 'fail', content: '医生信息不存在' });
      return;
    }
    setSubmitting(true);
    try {
      await doctorApi.createReview({
        appointmentId: appointmentId!,
        doctorId: appointment.doctorId,
        rating,
        content: content || undefined,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
        isAnonymous,
      });
      Toast.show({ icon: 'success', content: '评价提交成功，感谢您的反馈！' });
      setSubmitted(true);
    } catch (error: any) {
      Toast.show({ icon: 'fail', content: error.message || '提交失败，请稍后重试' });
    } finally {
      setSubmitting(false);
    }
  };

  const renderStars = (value: number, onChange: (v: number) => void) => (
    <div style={{ display: 'flex', gap: 8, justifyContent: 'center', marginBottom: 16 }}>
      {[1, 2, 3, 4, 5].map((star) => (
        <div
          key={star}
          onClick={() => !submitted && onChange(star)}
          style={{
            fontSize: 40,
            cursor: submitted ? 'default' : 'pointer',
            color: star <= value ? '#FFD700' : '#E0E0E0',
            transition: 'color 0.2s',
          }}
        >
          ★
        </div>
      ))}
    </div>
  );

  if (loading) {
    return (
      <div>
        <NavBar onBack={() => history.back()}>医生评价</NavBar>
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
        <NavBar onBack={() => history.back()}>医生评价</NavBar>
        <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
          预约信息不存在
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <NavBar onBack={() => history.back()}>医生评价</NavBar>

      <motion.div variants={fadeInUp} initial="hidden" animate="visible" style={{ padding: 16 }}>
        {/* 医生信息卡片 */}
        <Card style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 48, height: 48, borderRadius: 24, background: '#1677ff', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 20 }}>
              {appointment.doctorName?.[0] || '医'}
            </div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600 }}>{appointment.doctorName}</div>
              <div style={{ fontSize: 14, color: '#666' }}>{appointment.departmentName}</div>
            </div>
          </div>
          <div style={{ marginTop: 12, fontSize: 14, color: '#666' }}>
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
                感谢您的反馈，您的评价将帮助其他患者
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
                {selectedTags.map((tag) => (
                  <span key={tag} style={{ padding: '4px 12px', background: '#E6F7FF', color: '#1677ff', borderRadius: 12, fontSize: 12 }}>
                    {tag}
                  </span>
                ))}
              </div>
              {content && (
                <div style={{ marginTop: 16, padding: 12, background: '#FAFAFA', borderRadius: 8, textAlign: 'left', fontSize: 14, color: '#333' }}>
                  {content}
                </div>
              )}
            </div>
          </Card>
        ) : (
          /* 评价表单 */
          <>
            {/* 评分 */}
            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, textAlign: 'center' }}>
                请为医生评分
              </div>
              {renderStars(rating, setRating)}
              <div style={{ textAlign: 'center', fontSize: 14, color: '#666' }}>
                {rating === 0 ? '点击星星评分' : ['', '非常差', '较差', '一般', '较好', '非常好'][rating]}
              </div>
            </Card>

            {/* 评价标签 */}
            <Card style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>选择标签（可多选）</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {REVIEW_TAGS.map((tag) => {
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
                placeholder="请分享您的就诊体验，帮助其他患者选择医生..."
                value={content}
                onChange={setContent}
                rows={4}
                maxLength={1000}
                showCount
              />
            </Card>

            {/* 匿名选项 */}
            <Card style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 600 }}>匿名评价</div>
                  <div style={{ fontSize: 14, color: '#666' }}>开启后您的姓名将不会显示</div>
                </div>
                <Switch
                  checked={isAnonymous}
                  onChange={setIsAnonymous}
                />
              </div>
            </Card>

            {/* 提交按钮 */}
            <Button
              variant="primary"
              size="lg"
              onClick={handleSubmit}
              disabled={submitting || rating === 0}
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

export default ReviewPage;
