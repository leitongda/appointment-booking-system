/** 低代码动态页面入口 */

import React, { useEffect, useState } from 'react';
import { View, Text } from '@tarojs/components';
import Taro, { useRouter } from '@tarojs/taro';
import { LowCodeRenderer } from '../../components/LowCodeRenderer';
import { lowcodeApi } from '@hospital/api';
import type { LowCodeNode } from '@hospital/shared';

const LowCodePage: React.FC = () => {
  const router = useRouter();
  const pageId = router.params.id;
  const [schema, setSchema] = useState<LowCodeNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pageId) {
      setError('页面ID不存在');
      setLoading(false);
      return;
    }

    const loadPage = async () => {
      try {
        const page = await lowcodeApi.getPage(pageId);
        if (page.schemaData && Object.keys(page.schemaData).length > 0) {
          setSchema(page.schemaData as unknown as LowCodeNode);
        } else {
          setError('页面内容为空');
        }
      } catch (err) {
        console.error('加载低代码页面失败:', err);
        setError('页面加载失败');
      } finally {
        setLoading(false);
      }
    };

    loadPage();
  }, [pageId]);

  if (loading) {
    return (
      <View className="lowcode-loading">
        <Text>加载中...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View className="lowcode-error">
        <Text>{error}</Text>
      </View>
    );
  }

  if (!schema) {
    return (
      <View className="lowcode-empty">
        <Text>页面内容为空</Text>
      </View>
    );
  }

  return <LowCodeRenderer schema={schema} />;
};

export default LowCodePage;
