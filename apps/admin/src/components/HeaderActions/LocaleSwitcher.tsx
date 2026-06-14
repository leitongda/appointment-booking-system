/**
 * LocaleSwitcher - 语言切换按钮
 *
 * 在中英文之间切换，偏好持久化到 localStorage。
 */
import { useState, useEffect } from 'react';
import { Button, Dropdown } from 'antd';
import { GlobalOutlined } from '@ant-design/icons';
import { getLocale, setLocale, type Locale } from '@/utils/locale';

const LOCALE_LABELS: Record<Locale, string> = {
  zh: '中文',
  en: 'English',
};

export const LocaleSwitcher: React.FC = () => {
  const [locale, setCurrentLocale] = useState<Locale>(getLocale);

  useEffect(() => {
    const handler = (e: CustomEvent<Locale>) => {
      setCurrentLocale(e.detail);
    };
    window.addEventListener('locale-change', handler as EventListener);
    return () => window.removeEventListener('locale-change', handler as EventListener);
  }, []);

  const handleChange = (newLocale: Locale) => {
    setLocale(newLocale);
    setCurrentLocale(newLocale);
    // 刷新页面以应用语言变更
    window.location.reload();
  };

  return (
    <Dropdown
      menu={{
        items: [
          { key: 'zh', label: '中文', onClick: () => handleChange('zh') },
          { key: 'en', label: 'English', onClick: () => handleChange('en') },
        ],
        selectedKeys: [locale],
      }}
      trigger={['click']}
    >
      <Button type="text" icon={<GlobalOutlined />} style={{ color: '#666' }}>
        {LOCALE_LABELS[locale]}
      </Button>
    </Dropdown>
  );
};

export default LocaleSwitcher;
