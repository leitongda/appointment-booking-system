import { useState, useEffect } from 'react';
import { NavBar, Form, Input, TextArea, Button, Selector, ImageUploader, Toast, List, Tag, Empty } from 'antd-mobile';
import { history } from 'umi';
import { feedbackApi } from '@hospital/api';
import type { Feedback } from '@hospital/shared';
import styles from './index.less';

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

  const getStatusTag = (status: string) => {
    const map: Record<string, { color: string; text: string }> = {
      pending: { color: '#faad14', text: '待处理' },
      processing: { color: '#1890ff', text: '处理中' },
      resolved: { color: '#52c41a', text: '已解决' },
      closed: { color: '#999', text: '已关闭' },
    };
    const config = map[status] || { color: '#999', text: status };
    return <Tag color={config.color}>{config.text}</Tag>;
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
    <div className={styles.container}>
      <NavBar onBack={() => history.goBack()}>意见反馈</NavBar>
      
      <div className={styles.tabs}>
        <div 
          className={`${styles.tab} ${showForm ? styles.active : ''}`}
          onClick={() => setShowForm(true)}
        >
          提交反馈
        </div>
        <div 
          className={`${styles.tab} ${!showForm ? styles.active : ''}`}
          onClick={() => setShowForm(false)}
        >
          我的反馈
        </div>
      </div>

      {showForm ? (
        <div className={styles.formWrapper}>
          <Form form={form} layout="vertical">
            <Form.Item name="feedbackType" label="反馈类型">
              <Selector options={feedbackTypes} />
            </Form.Item>
            
            <Form.Item 
              name="title" 
              label="标题" 
              rules={[{ required: true, message: '请输入标题' }]}
            >
              <Input placeholder="请简要描述您的问题或建议" maxLength={50} />
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
              />
            </Form.Item>
            
            <Form.Item name="contact" label="联系方式（选填）">
              <Input placeholder="方便我们与您联系" />
            </Form.Item>
          </Form>
          
          <Button 
            block 
            color="primary" 
            size="large"
            loading={loading}
            onClick={handleSubmit}
            className={styles.submitBtn}
          >
            提交反馈
          </Button>
        </div>
      ) : (
        <div className={styles.listWrapper}>
          {myFeedbacks.length === 0 ? (
            <Empty description="暂无反馈记录" />
          ) : (
            <List>
              {myFeedbacks.map(item => (
                <List.Item
                  key={item.id}
                  description={
                    <div className={styles.feedbackItem}>
                      <div className={styles.content}>{item.content}</div>
                      <div className={styles.meta}>
                        <span>{getTypeText(item.feedbackType)}</span>
                        <span>{new Date(item.createdAt).toLocaleDateString()}</span>
                      </div>
                      {item.reply && (
                        <div className={styles.reply}>
                          <div className={styles.replyLabel}>官方回复：</div>
                          <div>{item.reply}</div>
                        </div>
                      )}
                    </div>
                  }
                  extra={getStatusTag(item.status)}
                >
                  {item.title}
                </List.Item>
              ))}
            </List>
          )}
        </div>
      )}
    </div>
  );
};

export default FeedbackPage;
