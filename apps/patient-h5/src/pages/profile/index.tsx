import { Image, Dialog, Toast, Badge } from 'antd-mobile';
import { history } from 'umi';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { userApi, messageApi } from '@hospital/api';
import { removeToken, removeStorage, STORAGE_KEYS } from '@hospital/shared';
import type { User } from '@hospital/shared';
import { Button, Card, InvertedSection } from '@/components/ui';
import { fadeInUp, stagger, viewportOptions } from '@/components/ui/animations';

// Menu items with icons
const menuItems = [
  {
    group: 'main',
    items: [
      {
        key: 'patient',
        title: '就诊人管理',
        icon: (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
          </svg>
        ),
        path: '/profile/patient',
      },
      {
        key: 'records',
        title: '就诊记录',
        icon: (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        ),
        path: '/records',
      },
      {
        key: 'message',
        title: '消息通知',
        icon: (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
        ),
        path: '/message',
        showBadge: true,
      },
    ],
  },
  {
    group: 'settings',
    items: [
      {
        key: 'feedback',
        title: '意见反馈',
        icon: (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        ),
        path: '/feedback',
      },
      {
        key: 'settings',
        title: '设置',
        icon: (
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        ),
        path: '/settings',
      },
    ],
  },
];

const ProfilePage: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const userId = localStorage.getItem('userId') || '';

  useEffect(() => {
    loadProfile();
    loadUnreadCount();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await userApi.getProfile();
      setUser(data);
    } catch (error) {
      console.error('加载用户信息失败', error);
    }
  };

  const loadUnreadCount = async () => {
    if (!userId) return;
    try {
      const count = await messageApi.getUnreadCount(userId, 'patient');
      setUnreadCount(count.total || 0);
    } catch (error) {
      console.error('获取未读消息数失败', error);
    }
  };

  const handleLogout = async () => {
    const result = await Dialog.confirm({
      content: '确定要退出登录吗？',
    });

    if (result) {
      removeToken();
      removeStorage(STORAGE_KEYS.USER_INFO);
      localStorage.removeItem('userId');
      Toast.show({ content: '已退出登录' });
      history.push('/login');
    }
  };

  const handleEditProfile = () => {
    history.push('/profile/edit');
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header with inverted section */}
      <InvertedSection 
        showDotPattern 
        showGlow 
        glowPosition="top-right"
        padding="lg"
      >
        <motion.div 
          className="flex items-center gap-4"
          variants={fadeInUp}
          initial="hidden"
          animate="visible"
          onClick={handleEditProfile}
        >
          <Image 
            src={user?.avatar || ''} 
            width={72} 
            height={72} 
            fit="cover" 
            className="rounded-full bg-white/10 border-2 border-white/20"
          />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-xl font-semibold text-white">
                {user?.nickname || user?.name || '未设置昵称'}
              </span>
              <svg 
                className="w-4 h-4 text-white/60" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </div>
            <p className="text-white/70 text-sm mt-1">
              {user?.phone?.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') || '未登录'}
            </p>
          </div>
        </motion.div>
      </InvertedSection>

      {/* Menu Groups */}
      <motion.div
        className="px-3 -mt-4 relative z-10"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {menuItems.map((group, groupIndex) => (
          <Card 
            key={group.group} 
            variant="elevated" 
            padding="none"
            className={groupIndex > 0 ? 'mt-3' : ''}
          >
            {group.items.map((item, index) => (
              <motion.div
                key={item.key}
                variants={fadeInUp}
                className={`
                  flex items-center gap-4 px-4 py-4 cursor-pointer
                  active:bg-muted transition-colors
                  ${index > 0 ? 'border-t border-border' : ''}
                `}
                onClick={() => history.push(item.path)}
              >
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                  {item.icon}
                </div>
                <span className="flex-1 text-foreground font-medium">{item.title}</span>
                {item.showBadge && unreadCount > 0 && (
                  <Badge content={unreadCount} />
                )}
                <svg 
                  className="w-5 h-5 text-muted-foreground" 
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </motion.div>
            ))}
          </Card>
        ))}
      </motion.div>

      {/* Logout Button */}
      <motion.div 
        className="px-3 py-6"
        variants={fadeInUp}
        initial="hidden"
        whileInView="visible"
        viewport={viewportOptions}
      >
        <Button 
          variant="outline" 
          block 
          onClick={handleLogout}
        >
          退出登录
        </Button>
      </motion.div>
    </div>
  );
};

export default ProfilePage;
