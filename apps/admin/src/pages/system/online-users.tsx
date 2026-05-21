import { PageContainer } from '@ant-design/pro-components';
import { Table, Card, App, Popconfirm, Button, Tag, Space, Tooltip, Typography, Drawer, Timeline, Segmented } from 'antd';
import {
  DesktopOutlined,
  MobileOutlined,
  WindowsOutlined,
  AppleOutlined,
  ReloadOutlined,
  DisconnectOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  LogoutOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useState, useEffect, useCallback } from 'react';
import { adminApi } from '@hospital/api';
import type { UserStatus, LoginHistory, DeviceInfo } from '@hospital/api';

const { Text } = Typography;

/**
 * 格式化时间间隔为可读字符串
 */
const formatDuration = (seconds: number | undefined | null): string => {
  if (seconds === undefined || seconds === null) return '-';
  if (seconds < 60) {
    return `${seconds}秒`;
  }
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs > 0 ? secs + '秒' : ''}`;
  }
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  return `${hours}小时${mins > 0 ? mins + '分' : ''}`;
};

/**
 * 计算在线时长（秒）
 */
const calculateOnlineDuration = (loginTime: string): number => {
  const loginDate = new Date(loginTime);
  const now = new Date();
  return Math.floor((now.getTime() - loginDate.getTime()) / 1000);
};

/**
 * 格式化时间
 */
const formatTime = (time: string | undefined | null): string => {
  if (!time) return '-';
  const date = new Date(time);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

/**
 * 获取设备类型图标
 */
const getDeviceIcon = (deviceType: string | undefined) => {
  switch (deviceType) {
    case 'mobile':
      return <MobileOutlined style={{ fontSize: 16, color: '#52c41a' }} />;
    case 'tablet':
      return <MobileOutlined style={{ fontSize: 16, color: '#1890ff' }} />;
    default:
      return <DesktopOutlined style={{ fontSize: 16, color: '#722ed1' }} />;
  }
};

/**
 * 获取操作系统图标
 */
const getOsIcon = (os: string | undefined) => {
  if (!os) return null;
  const osLower = os.toLowerCase();
  if (osLower.includes('windows')) {
    return <WindowsOutlined style={{ marginRight: 4 }} />;
  }
  if (osLower.includes('mac') || osLower.includes('ios')) {
    return <AppleOutlined style={{ marginRight: 4 }} />;
  }
  return null;
};

/**
 * 获取退出类型标签
 */
const getLogoutTypeTag = (logoutType: string | undefined) => {
  switch (logoutType) {
    case 'manual':
      return <Tag icon={<LogoutOutlined />} color="blue">主动退出</Tag>;
    case 'kicked':
      return <Tag icon={<StopOutlined />} color="red">强制下线</Tag>;
    case 'timeout':
      return <Tag icon={<ClockCircleOutlined />} color="orange">超时退出</Tag>;
    default:
      return <Tag color="default">未知</Tag>;
  }
};

const UserStatusPage: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [users, setUsers] = useState<UserStatus[]>([]);
  const [filter, setFilter] = useState<'all' | 'online' | 'offline'>('all');
  const [_tick, setTick] = useState(0);
  
  // 登录历史抽屉
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyList, setHistoryList] = useState<LoginHistory[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [currentUser, setCurrentUser] = useState<UserStatus | null>(null);

  // 加载用户状态列表
  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.getUserStatus();
      setUsers(data);
    } catch (error: any) {
      message.error(error.message || '加载失败');
    } finally {
      setLoading(false);
    }
  }, [message]);

  // 初始加载
  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  // 每秒更新一次（用于实时显示在线时长和倒计时）
  useEffect(() => {
    const timer = setInterval(() => {
      setTick((t) => t + 1);
      // 减少在线用户的 TTL
      setUsers((prev) =>
        prev.map((u) => {
          if (u.status === 'online' && u.ttl !== undefined) {
            const newTtl = Math.max(0, u.ttl - 1);
            // 如果 TTL 归零，变为离线状态
            if (newTtl === 0) {
              return {
                ...u,
                status: 'offline' as const,
                ttl: undefined,
                lastLoginAt: u.loginTime,
                lastLoginIp: u.loginIp,
              };
            }
            return { ...u, ttl: newTtl };
          }
          return u;
        })
      );
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // 每30秒刷新一次数据
  useEffect(() => {
    const refreshTimer = setInterval(() => {
      loadUsers();
    }, 30000);

    return () => clearInterval(refreshTimer);
  }, [loadUsers]);

  // 强制下线
  const handleKick = async (adminId: string) => {
    try {
      await adminApi.kickUser(adminId);
      message.success('已强制该用户下线');
      // 将用户状态改为离线
      setUsers((prev) =>
        prev.map((u) => {
          if (u.adminId === adminId) {
            return {
              ...u,
              status: 'offline' as const,
              ttl: undefined,
              lastLoginAt: u.loginTime,
              lastLoginIp: u.loginIp,
            };
          }
          return u;
        })
      );
    } catch (error: any) {
      message.error(error.message || '操作失败');
    }
  };

  // 加载登录历史
  const loadHistory = async (adminId: string, page: number) => {
    setHistoryLoading(true);
    try {
      const data = await adminApi.getLoginHistory(adminId, { page, pageSize: 20 });
      setHistoryList(data.list);
      setHistoryTotal(data.total);
    } catch (error: any) {
      message.error(error.message || '加载历史记录失败');
    } finally {
      setHistoryLoading(false);
    }
  };

  // 查看登录历史
  const handleViewHistory = async (user: UserStatus) => {
    setCurrentUser(user);
    setHistoryDrawerOpen(true);
    setHistoryPage(1);
    await loadHistory(user.adminId, 1);
  };

  // 过滤后的用户列表
  const filteredUsers = users.filter((u) => {
    if (filter === 'all') return true;
    return u.status === filter;
  });

  // 统计
  const onlineCount = users.filter((u) => u.status === 'online').length;
  const offlineCount = users.filter((u) => u.status === 'offline').length;

  const columns = [
    {
      title: '用户信息',
      key: 'user',
      width: 180,
      render: (_: any, record: UserStatus) => (
        <div>
          <div style={{ fontWeight: 500 }}>{record.name || record.username}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            @{record.username}
          </Text>
        </div>
      ),
    },
    {
      title: '角色',
      dataIndex: 'roleName',
      width: 100,
      render: (val: string) => val ? <Tag color="blue">{val}</Tag> : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string) => (
        status === 'online' 
          ? <Tag icon={<CheckCircleOutlined />} color="success">在线</Tag>
          : <Tag icon={<CloseCircleOutlined />} color="default">离线</Tag>
      ),
    },
    {
      title: '设备信息',
      key: 'device',
      width: 180,
      render: (_: any, record: UserStatus) => {
        if (record.status === 'offline') {
          return <Text type="secondary">-</Text>;
        }
        const device = (record.deviceInfo || {}) as DeviceInfo;
        return (
          <Space size={0}>
            <Space size={8}>
              <Tooltip title={device.deviceType === 'mobile' ? '移动设备' : device.deviceType === 'tablet' ? '平板设备' : '桌面设备'}>
                {getDeviceIcon(device.deviceType)}
              </Tooltip>
              <span>{device.browser || 'Unknown'}</span>
            </Space>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {getOsIcon(device.os)}
              {device.os || 'Unknown'}
            </Text>
          </Space>
        );
      },
    },
    {
      title: '登录IP',
      key: 'ip',
      width: 130,
      render: (_: any, record: UserStatus) => {
        const ip = record.status === 'online' ? record.loginIp : record.lastLoginIp;
        return ip ? <Text code>{ip}</Text> : '-';
      },
    },
    {
      title: (record: any) => record.status === 'online' ? '登录时间' : '上次登录',
      key: 'time',
      width: 160,
      render: (_: any, record: UserStatus) => {
        if (record.status === 'online') {
          return formatTime(record.loginTime);
        }
        return record.lastLoginAt ? (
          <Tooltip title={formatTime(record.lastLoginAt)}>
            <Text type="secondary">{formatTime(record.lastLoginAt)}</Text>
          </Tooltip>
        ) : '-';
      },
    },
    {
      title: '在线时长/TTL',
      key: 'duration',
      width: 140,
      render: (_: any, record: UserStatus) => {
        if (record.status !== 'online' || !record.loginTime) {
          return <Text type="secondary">-</Text>;
        }
        const duration = calculateOnlineDuration(record.loginTime);
        const ttl = record.ttl || 0;
        const ttlColor = ttl < 300 ? 'red' : ttl < 600 ? 'orange' : 'blue';
        return (
          <Space size={0}>
            <Tag color="green" icon={<DesktopOutlined />}>
              {formatDuration(duration)}
            </Tag>
            <Tag color={ttlColor} style={{ marginTop: 4 }}>
              TTL: {formatDuration(ttl)}
            </Tag>
          </Space>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: any, record: UserStatus) => (
        <Space>
          <Button
            type="link"
            icon={<HistoryOutlined />}
            size="small"
            onClick={() => handleViewHistory(record)}
          >
            历史
          </Button>
          {record.status === 'online' && (
            <Popconfirm
              title="确定强制该用户下线吗？"
              description="该用户的登录状态将立即失效"
              onConfirm={() => handleKick(record.adminId)}
              okText="确定"
              cancelText="取消"
              okButtonProps={{ danger: true }}
            >
              <Button
                type="link"
                danger
                icon={<DisconnectOutlined />}
                size="small"
              >
                下线
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <PageContainer>
      <Card
        title={
          <Space>
            <span>用户状态</span>
            <Tag color="green">{onlineCount} 在线</Tag>
            <Tag color="default">{offlineCount} 离线</Tag>
          </Space>
        }
        extra={
          <Space>
            <Segmented
              value={filter}
              onChange={(val) => setFilter(val as any)}
              options={[
                { label: '全部', value: 'all' },
                { label: '在线', value: 'online' },
                { label: '离线', value: 'offline' },
              ]}
            />
            <Button
              icon={<ReloadOutlined />}
              onClick={loadUsers}
              loading={loading}
            >
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          rowKey="adminId"
          columns={columns}
          dataSource={filteredUsers}
          loading={loading}
          pagination={false}
          size="middle"
          locale={{
            emptyText: '暂无用户',
          }}
        />
      </Card>

      {/* 登录历史抽屉 */}
      <Drawer
        title={
          <Space>
            <HistoryOutlined />
            <span>登录历史</span>
            {currentUser && (
              <Tag color="blue">{currentUser.name || currentUser.username}</Tag>
            )}
          </Space>
        }
        open={historyDrawerOpen}
        onClose={() => setHistoryDrawerOpen(false)}
        width={500}
      >
        {historyLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>加载中...</div>
        ) : historyList.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            暂无登录记录
          </div>
        ) : (
          <>
            <Timeline
              items={historyList.map((item) => ({
                color: item.logoutTime ? 'gray' : 'green',
                children: (
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ marginBottom: 8 }}>
                      <Space>
                        <Text strong>登录时间:</Text>
                        <Text>{formatTime(item.loginTime)}</Text>
                      </Space>
                    </div>
                    {item.logoutTime && (
                      <div style={{ marginBottom: 8 }}>
                        <Space>
                          <Text strong>退出时间:</Text>
                          <Text>{formatTime(item.logoutTime)}</Text>
                          {getLogoutTypeTag(item.logoutType)}
                        </Space>
                      </div>
                    )}
                    {!item.logoutTime && (
                      <div style={{ marginBottom: 8 }}>
                        <Tag color="green">当前会话</Tag>
                      </div>
                    )}
                    <div style={{ marginBottom: 8 }}>
                      <Space>
                        <Text strong>在线时长:</Text>
                        <Text>{formatDuration(item.duration)}</Text>
                      </Space>
                    </div>
                    <div style={{ marginBottom: 8 }}>
                      <Space>
                        {getDeviceIcon(item.deviceType)}
                        <Text type="secondary">
                          {item.browser || 'Unknown'} / {item.os || 'Unknown'}
                        </Text>
                      </Space>
                    </div>
                    <div>
                      <Space>
                        <Text strong>IP:</Text>
                        <Text code>{item.loginIp || '-'}</Text>
                      </Space>
                    </div>
                  </div>
                ),
              }))}
            />
            {historyTotal > 20 && (
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <Button
                  type="link"
                  onClick={() => {
                    const nextPage = historyPage + 1;
                    setHistoryPage(nextPage);
                    if (currentUser) {
                      loadHistory(currentUser.adminId, nextPage);
                    }
                  }}
                  disabled={historyList.length < 20}
                >
                  加载更多
                </Button>
              </div>
            )}
          </>
        )}
      </Drawer>
    </PageContainer>
  );
};

export default UserStatusPage;
