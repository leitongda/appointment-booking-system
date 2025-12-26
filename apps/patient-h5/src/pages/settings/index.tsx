import { NavBar, Switch, Dialog, Toast } from 'antd-mobile';
import { history } from 'umi';
import { useState } from 'react';
import { motion } from 'framer-motion';
import { removeToken, removeStorage, STORAGE_KEYS } from '@hospital/shared';
import { Card, Button } from '@/components/ui';
import { fadeInUp, stagger } from '@/components/ui/animations';

const SettingsPage: React.FC = () => {
  const [pushEnabled, setPushEnabled] = useState(true);

  const handleClearCache = async () => {
    const result = await Dialog.confirm({
      content: '确定要清除缓存吗？',
    });

    if (result) {
      const token = localStorage.getItem('token');
      const refreshToken = localStorage.getItem('refreshToken');
      const userId = localStorage.getItem('userId');
      
      localStorage.clear();
      
      if (token) localStorage.setItem('token', token);
      if (refreshToken) localStorage.setItem('refreshToken', refreshToken);
      if (userId) localStorage.setItem('userId', userId);
      
      Toast.show({ content: '缓存已清除', icon: 'success' });
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

  return (
    <div className="min-h-screen bg-background">
      <NavBar 
        onBack={() => history.back()}
        className="!bg-card border-b border-border"
      >
        设置
      </NavBar>

      <motion.div
        className="p-4 space-y-4"
        variants={stagger}
        initial="hidden"
        animate="visible"
      >
        {/* Notification Settings */}
        <motion.div variants={fadeInUp}>
          <div className="mb-2 px-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-mono">
              通知设置
            </span>
          </div>
          <Card variant="default" padding="none" animated={false}>
            <div className="flex items-center justify-between px-4 py-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                  </svg>
                </div>
                <span className="font-medium text-foreground">推送通知</span>
              </div>
              <Switch
                checked={pushEnabled}
                onChange={setPushEnabled}
                style={{
                  '--checked-color': '#0052FF',
                } as React.CSSProperties}
              />
            </div>
          </Card>
        </motion.div>

        {/* Other Settings */}
        <motion.div variants={fadeInUp}>
          <div className="mb-2 px-1">
            <span className="text-xs text-muted-foreground uppercase tracking-wider font-mono">
              其他
            </span>
          </div>
          <Card variant="default" padding="none" animated={false}>
            <div 
              className="flex items-center justify-between px-4 py-4 cursor-pointer active:bg-muted transition-colors"
              onClick={handleClearCache}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </div>
                <span className="font-medium text-foreground">清除缓存</span>
              </div>
              <svg className="w-5 h-5 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
            
            <div className="border-t border-border" />
            
            <div className="flex items-center justify-between px-4 py-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center text-accent">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <span className="font-medium text-foreground">版本号</span>
              </div>
              <span className="text-muted-foreground font-mono text-sm">v1.0.0</span>
            </div>
          </Card>
        </motion.div>

        {/* Logout Button */}
        <motion.div variants={fadeInUp} className="pt-4">
          <Button 
            variant="outline" 
            block 
            onClick={handleLogout}
            className="!text-red-500 !border-red-200 hover:!bg-red-50"
          >
            退出登录
          </Button>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default SettingsPage;
