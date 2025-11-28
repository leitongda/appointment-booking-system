import { PageContainer } from '@ant-design/pro-components';
import { Tabs, List, Badge, Tag, Empty, Button, Spin, message as antMessage, Modal } from 'antd';
import { BellOutlined, CalendarOutlined, MedicineBoxOutlined, NotificationOutlined, CheckOutlined } from '@ant-design/icons';
import { useState, useEffect } from 'react';
import { messageApi } from '@hospital/api';
import type { Message, UnreadCount } from '@hospital/shared';

const MessagePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [messages, setMessages] = useState<Message[]>([]);
  const [unreadCount, setUnreadCount] = useState<UnreadCount | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  
  // 模拟医生ID，实际应从登录状态获取
  const doctorId = localStorage.getItem('doctorId') || '';
  const userType = 'doctor';

  useEffect(() => {
    loadUnreadCount();
  }, []);

  useEffect(() => {
    loadMessages(1);
  }, [activeTab]);

  const loadUnreadCount = async () => {
    try {
      const count = await messageApi.getUnreadCount(doctorId, userType);
      setUnreadCount(count);
    } catch (error) {
      console.error('获取未读数失败', error);
    }
  };

  const loadMessages = async (pageNum: number) => {
    setLoading(true);
    try {
      const messageType = activeTab === 'all' ? undefined : activeTab;
      const result = await messageApi.getList({
        userId: doctorId,
        userType,
        messageType,
        page: pageNum,
        pageSize: 20,
      });
      
      setMessages(result.data);
      setTotal(result.total);
      setPage(pageNum);
    } catch (error) {
      console.error('加载消息失败', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRead = async (msg: Message) => {
    if (msg.isRead === 0) {
      try {
        await messageApi.markAsRead(msg.id, doctorId);
        setMessages(prev => 
          prev.map(m => m.id === msg.id ? { ...m, isRead: 1 } : m)
        );
        loadUnreadCount();
      } catch (error) {
        console.error('标记已读失败', error);
      }
    }
  };

  const handleReadAll = async () => {
    Modal.confirm({
      title: '确认',
      content: '确定将所有消息标记为已读吗？',
      onOk: async () => {
        try {
          const messageType = activeTab === 'all' ? undefined : activeTab;
          await messageApi.markAllAsRead(doctorId, userType, messageType);
          setMessages(prev => prev.map(m => ({ ...m, isRead: 1 })));
          loadUnreadCount();
          antMessage.success('已全部标记为已读');
        } catch (error) {
          antMessage.error('操作失败');
        }
      }
    });
  };

  const handleDelete = async (messageId: string) => {
    try {
      await messageApi.delete(messageId, doctorId);
      setMessages(prev => prev.filter(m => m.id !== messageId));
      antMessage.success('删除成功');
    } catch (error) {
      antMessage.error('删除失败');
    }
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'appointment': return <CalendarOutlined style={{ color: '#1890ff' }} />;
      case 'schedule': return <CalendarOutlined style={{ color: '#52c41a' }} />;
      case 'consultation': return <MedicineBoxOutlined style={{ color: '#722ed1' }} />;
      case 'stop_clinic': return <NotificationOutlined style={{ color: '#faad14' }} />;
      default: return <BellOutlined style={{ color: '#666' }} />;
    }
  };

  const getMessageTypeTag = (type: string) => {
    const typeMap: Record<string, { color: string; text: string }> = {
      appointment: { color: 'blue', text: '预约' },
      schedule: { color: 'green', text: '排班' },
      consultation: { color: 'purple', text: '就诊' },
      stop_clinic: { color: 'orange', text: '停诊' },
      system: { color: 'default', text: '系统' },
    };
    const config = typeMap[type] || { color: 'default', text: '通知' };
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const formatTime = (time: string) => {
    const date = new Date(time);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    
    return `${date.getMonth() + 1}月${date.getDate()}日 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
  };

  const tabItems = [
    { key: 'all', label: <Badge count={unreadCount?.total} size="small" offset={[8, 0]}>全部</Badge> },
    { key: 'schedule', label: <Badge count={unreadCount?.schedule} size="small" offset={[8, 0]}>排班</Badge> },
    { key: 'appointment', label: <Badge count={unreadCount?.appointment} size="small" offset={[8, 0]}>预约</Badge> },
    { key: 'system', label: <Badge count={unreadCount?.system} size="small" offset={[8, 0]}>系统</Badge> },
  ];

  return (
    <PageContainer
      extra={
        unreadCount && unreadCount.total > 0 ? (
          <Button icon={<CheckOutlined />} onClick={handleReadAll}>
            全部已读
          </Button>
        ) : null
      }
    >
      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        items={tabItems}
      />
      
      <Spin spinning={loading}>
        {messages.length === 0 ? (
          <Empty description="暂无消息" style={{ padding: '60px 0' }} />
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={messages}
            pagination={{
              current: page,
              total,
              pageSize: 20,
              onChange: loadMessages,
              showSizeChanger: false,
            }}
            renderItem={(item) => (
              <List.Item
                style={{ 
                  background: item.isRead === 0 ? '#fafafa' : '#fff',
                  padding: '16px',
                  cursor: 'pointer',
                }}
                onClick={() => handleRead(item)}
                actions={[
                  <a key="delete" style={{ color: '#ff4d4f' }} onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(item.id);
                  }}>删除</a>
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <Badge dot={item.isRead === 0}>
                      <div style={{ 
                        width: 40, 
                        height: 40, 
                        borderRadius: '50%', 
                        background: '#f5f5f5',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 18,
                      }}>
                        {getMessageIcon(item.messageType)}
                      </div>
                    </Badge>
                  }
                  title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontWeight: item.isRead === 0 ? 600 : 400 }}>{item.title}</span>
                      {getMessageTypeTag(item.messageType)}
                    </div>
                  }
                  description={
                    <div>
                      <div style={{ color: '#666', marginBottom: 4 }}>{item.content}</div>
                      <div style={{ color: '#999', fontSize: 12 }}>{formatTime(item.createdAt)}</div>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Spin>
    </PageContainer>
  );
};

export default MessagePage;
