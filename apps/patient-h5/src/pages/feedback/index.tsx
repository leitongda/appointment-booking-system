import { useState, useEffect } from 'react';
import { NavBar, Form, Input, TextArea, Selector, Toast, Empty } from 'antd-mobile';
import { history } from 'umi';
import { motion } from 'framer-motion';
import { feedbackApi } from '@hospital/api';
import type { Feedback } from '@hospital/shared';
import { Card, Button } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const feedbackTypes = [
  { label: '建议', value: 'suggestion' },
  { label: '投诉', value: 'complaint' },
  { label: '问题', value: 'bug' },
  { label: '其他', value: 'other' },
];

const FeedbackPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [myFeedbacks, setMyFeedbacks] = useState<Feedback[]>([]);
  const [showForm, setShowForm] = useState(true);
  
  const userId = localStorage.getItem('userId') || '';

  useEffect(() => {
    loadMyFeedbacks();
  }, []);

  const loadMyFeedbacks = async () => {
    try {
      const data = await feedbackApi.getMyList(userId);
      setMyFeedbacks(data);
    } catch (error) {
      console.error('加载反馈列表失败', error);
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      
      await feedbackApi.create({
        userId,
        userType: 'patient',
        feedbackType: values.feedbackType?.[0] || 'suggestion',
        title: values.title,
        content: values.content,
        contact: values.contact,
      });
      
      Toast.show({ content: '提交成功，感谢您的反馈！', icon: 'success' });
      form.resetFields();
      loadMyFeedbacks();
      setShowForm(false);
    } catch (error: any) {
      Toast.show({ content: error.message || '提交失败', icon: 'fail' });
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const map: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-600',
      processing: 'bg-accent/10 text-accent',
      resolved: 'bg-green-100 text-green-600',
      closed: 'bg-muted text-muted-foreground',
    };
    return map[status] || 'bg-muted text-muted-foreground';
  };

  const getStatusText = (status: string) => {
    const map: Record<string, string> = {
      pending: '待处理',
      processing: '处理中',
      resolved: '已解决',
      closed: '已关闭',
    };
    return map[status] || status;
  };

  const getTypeText = (type: string) => {
    const map: Record<string, string> = {
      suggestion: '建议',
      complaint: '投诉',
      bug: '问题',
      other: '其他',
    };
    return map[type] || type;
  };

  return (
    <div className="min-h-screen bg-background">
      <NavBar 
        onBack={() => history.goBack()}
        className="!bg-card border-b border-border"
      >
        意见反馈
      </NavBar>
      
      {/* Tab Switcher */}
      <div className="flex bg-card border-b border-border">
        <button
          className={`flex-1 py-4 text-center font-medium transition-colors relative ${
            showForm ? 'text-accent' : 'text-muted-foreground'
          }`}
          onClick={() => setShowForm(true)}
        >
          提交反馈
          {showForm && (
            <motion.div 
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent"
              layoutId="tab-indicator"
            />
          )}
        </button>
        <button
          className={`flex-1 py-4 text-center font-medium transition-colors relative ${
            !showForm ? 'text-accent' : 'text-muted-foreground'
          }`}
          onClick={() => setShowForm(false)}
        >
          我的反馈
          {!showForm && (
            <motion.div 
              className="absolute bottom-0 left-0 right-0 h-0.5 bg-accent"
              layoutId="tab-indicator"
            />
          )}
        </button>
      </div>

      {showForm ? (
        <motion.div 
          className="p-4"
          variants={fadeInUp}
          initial="hidden"
          animate="visible"
        >
          <Card variant="default" padding="lg">
            <Form form={form} layout="vertical">
              <Form.Item name="feedbackType" label="反馈类型">
                <Selector 
                  options={feedbackTypes}
                  style={{
                    '--checked-color': '#0052FF',
                    '--checked-text-color': '#FFFFFF',
                  } as React.CSSProperties}
                />
              </Form.Item>
              
              <Form.Item 
                name="title" 
                label="标题" 
                rules={[{ required: true, message: '请输入标题' }]}
              >
                <Input 
                  placeholder="请简要描述您的问题或建议" 
                  maxLength={50}
                  className="!h-12 !rounded-xl"
                />
              </Form.Item>
              
              <Form.Item 
                name="content" 
                label="详细内容" 
                rules={[
                  { required: true, message: '请输入详细内容' },
                  { min: 10, message: '内容至少10个字符' }
                ]}
              >
                <TextArea 
                  placeholder="请详细描述您遇到的问题或建议..." 
                  rows={5}
                  maxLength={500}
                  showCount
                  className="!rounded-xl"
                />
              </Form.Item>
              
              <Form.Item name="contact" label="联系方式（选填）">
                <Input 
                  placeholder="方便我们与您联系"
                  className="!h-12 !rounded-xl"
                />
              </Form.Item>
            </Form>
            
            <Button 
              block 
              size="lg"
              loading={loading}
              onClick={handleSubmit}
              className="mt-4"
            >
              提交反馈
            </Button>
          </Card>
        </motion.div>
      ) : (
        <div className="p-4">
          {myFeedbacks.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <Empty description="暂无反馈记录" />
            </div>
          ) : (
            <motion.div
              className="space-y-3"
              variants={stagger}
              initial="hidden"
              animate="visible"
            >
              {myFeedbacks.map(item => (
                <motion.div key={item.id} variants={fadeInUp}>
                  <Card variant="default" padding="md" animated={false}>
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-medium text-foreground flex-1">{item.title}</h3>
                      <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(item.status)}`}>
                        {getStatusText(item.status)}
                      </span>
                    </div>
                    
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                      {item.content}
                    </p>
                    
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{getTypeText(item.feedbackType)}</span>
                      <span>{new Date(item.createdAt).toLocaleDateString()}</span>
                    </div>
                    
                    {item.reply && (
                      <div className="mt-3 pt-3 border-t border-border">
                        <p className="text-xs text-accent mb-1">官方回复：</p>
                        <p className="text-sm text-foreground">{item.reply}</p>
                      </div>
                    )}
                  </Card>
                </motion.div>
              ))}
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
};

export default FeedbackPage;
