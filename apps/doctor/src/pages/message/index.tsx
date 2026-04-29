import { PageContainer } from '@ant-design/pro-components';
import { Tabs, List, Badge, Tag, Empty, Button, Spin, message as antMessage, Modal, Tooltip } from 'antd';
import { BellOutlined, CalendarOutlined, MedicineBoxOutlined, NotificationOutlined, CheckOutlined, WifiOutlined, DisconnectOutlined, CheckCircleOutlined, LoadingOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { messageApi } from '@hospital/api';
import type { Message, UnreadCount } from '@hospital/shared';
import { DOCTOR_MESSAGE_TABS } from '@hospital/shared';
import { useWebSocket, ConnectionStatus } from '@/hooks';

const MessagePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('all');
  const [messages, setMessages] = useState<Message[]>([]);
  const [unreadCount, setUnreadCount] = useState<UnreadCount | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  
  // 获取医生 ID
  const doctorId = useMemo(() => {
    try {
      const doctorStr = localStorage.getItem('doctor');
      if (doctorStr) {
        const doctor = JSON.parse(doctorStr);
        return doctor.id || doctor.doctorId || '';
      }
    } catch (e) {
      console.error('解析医生信息失败:', e);
    }
    return '';
  }, []);
  const userType = 'doctor';

  const loadUnreadCount = useCallback(async () => {
    try {
      const count = await messageApi.getUnreadCount(doctorId, userType);
      setUnreadCount(count);
    } catch (error) {
      console.error('获取未读数失败', error);
    }
  }, [doctorId]);

  const loadMessages = useCallback(async (pageNum: number) => {
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
  }, [activeTab, doctorId]);

  // WebSocket 连接
  const { status: wsStatus, reconnect } = useWebSocket({
    doctorId,
    onSystemMessage: () => {
      // 收到新系统消息时刷新列表
      loadMessages(1);
      loadUnreadCount();
    },
    onLeaveRequestReviewed: () => {
      // 收到审核结果时刷新列表
      loadMessages(1);
      loadUnreadCount();
    },
    showNotifications: false, // 消息中心自己显示，不需要额外通知
  });

  useEffect(() => {
    loadUnreadCount();
  }, [loadUnreadCount]);

  useEffect(() => {
    loadMessages(1);
  }, [activeTab, loadMessages]);

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
      okButtonProps: { 'aria-label': '确认将所有消息标记为已读' },
      cancelButtonProps: { 'aria-label': '取消操作' },
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

  const tabItems = DOCTOR_MESSAGE_TABS.map(tab => {
    const count = tab.key === 'all' ? unreadCount?.total :
      tab.key === 'schedule' ? unreadCount?.schedule :
      tab.key === 'appointment' ? unreadCount?.appointment :
      unreadCount?.system;
    return {
      key: tab.key,
      label: (
        <Badge count={count} size="small" offset={[8, 0]}>
          {tab.label}
        </Badge>
      ),
      'aria-label': count > 0 ? `${tab.label}, ${count}条未读` : tab.label,
    };
  });

  // 连接状态指示器
  const connectionIndicator = useMemo(() => {
    if (wsStatus === ConnectionStatus.CONNECTED) {
      return (
        <Tooltip title="实时连接正常">
          <Tag
            color="success"
            icon={<CheckCircleOutlined />}
            aria-label="WebSocket 已连接"
            role="status"
            aria-live="polite"
          >
            实时
          </Tag>
        </Tooltip>
      );
    }
    if (wsStatus === ConnectionStatus.CONNECTING || wsStatus === ConnectionStatus.RECONNECTING) {
      return (
        <Tooltip title="正在连接...">
          <Tag
            color="processing"
            icon={<LoadingOutlined />}
            aria-label="WebSocket 正在连接"
            role="status"
            aria-live="polite"
          >
            连接中
          </Tag>
        </Tooltip>
      );
    }
    return (
      <Tooltip title="实时连接已断开，点击重连">
        <Tag
          color="error"
          icon={<CloseCircleOutlined />}
          style={{ cursor: 'pointer' }}
          onClick={reconnect}
          aria-label="WebSocket 连接已断开，点击重连"
          role="status"
          aria-live="assertive"
        >
          离线
        </Tag>
      </Tooltip>
    );
  }, [wsStatus, reconnect]);

  return (
    <PageContainer
      extra={
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {connectionIndicator}
          {unreadCount && unreadCount.total > 0 && (
            <Button
              icon={<CheckOutlined />}
              onClick={handleReadAll}
              aria-label={`标记全部${unreadCount.total}条消息为已读`}
            >
              全部已读
            </Button>
          )}
        </div>
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
            role="list"
            aria-label="消息列表"
            renderItem={(item) => (
              <List.Item
                style={{
                  background: item.isRead === 0 ? '#fafafa' : '#fff',
                  padding: '16px',
                  cursor: 'pointer',
                }}
                onClick={() => handleRead(item)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    handleRead(item);
                  }
                }}
                role="listitem"
                aria-label={
                  item.isRead === 0
                    ? `未读消息: ${item.title}, ${item.content}, ${formatTime(item.createdAt)}`
                    : `消息: ${item.title}, ${item.content}, ${formatTime(item.createdAt)}`
                }
                actions={[
                  <a
                    key="delete"
                    style={{ color: '#ff4d4f' }}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(item.id);
                    }}
                    aria-label={`删除消息: ${item.title}`}
                  >
                    删除
                  </a>
                ]}
              >
                <List.Item.Meta
                  avatar={
                    <Badge dot={item.isRead === 0} aria-hidden="true">
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
                      <span style={{ fontWeight: item.isRead === 0 ? 600 : 400 }}>
                        {item.title}
                        {item.isRead === 0 && <span style={{ position: 'absolute', width: 1, height: 1, padding: 0, margin: '-1px', overflow: 'hidden', clip: 'rect(0,0,0,0)', whiteSpace: 'nowrap', borderWidth: 0 }}>（未读）</span>}
                      </span>
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
