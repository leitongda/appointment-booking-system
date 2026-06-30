/**
 * 会话回放 - 回放页
 *
 * 对应后端：GET /api/v1/session-events/{sessionId}/replay
 * 流程：取 sessionId -> 拉 segments -> 按顺序 fetch 各 eventsUrl(presigned)
 *      -> 拼接 events 数组 -> 喂给 rrweb-player 渲染。
 *
 * rrweb-player 是 Svelte 组件（非原生 React 组件），通过 ref + useEffect
 * 实例化到容器 div，卸载时 $destroy() 释放。
 */
import { PageContainer } from '@ant-design/pro-components';
import { Alert, Button, Descriptions, Result, Spin, Tag, Typography } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { history, useParams } from '@umijs/max';
import { useEffect, useRef, useState } from 'react';
import dayjs from 'dayjs';
import { sessionReplayApi, type SessionReplayData } from '@/services/sessionReplay';

// rrweb-player 2.x 为 Svelte 组件，默认导出构造器
// @ts-ignore — @types/rrweb-player 可能未提供完整类型，按构造器方式调用
import rrwebPlayer from 'rrweb-player';
// 必须引入样式，否则播放器无 UI
// @ts-ignore
import 'rrweb-player/dist/style.css';

type LoadState = 'loading' | 'success' | 'empty' | 'error';

interface ReplayMeta {
  segments: number;
  totalEvents: number;
}

const SessionReplayPage: React.FC = () => {
  const params = useParams() as { sessionId?: string };
  const sessionId = params.sessionId;

  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const playerRef = useRef<any>(null);

  const [state, setState] = useState<LoadState>('loading');
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [meta, setMeta] = useState<ReplayMeta>({ segments: 0, totalEvents: 0 });
  const [viewport, setViewport] = useState<{ w?: number; h?: number }>({});

  useEffect(() => {
    if (!sessionId) {
      setState('error');
      setErrorMsg('缺少会话ID');
      return;
    }
    let cancelled = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let playerInstance: any = null;

    const loadAndPlay = async () => {
      try {
        setState('loading');
        const data: SessionReplayData = await sessionReplayApi.getReplay(sessionId);
        if (cancelled) return;

        setViewport({ w: data.viewportW || undefined, h: data.viewportH || undefined });

        // 按顺序拉取各 eventsUrl（presigned 对象存储直链，直接 fetch）
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const allEvents: any[] = [];
        let totalEvents = 0;
        for (const seg of data.segments) {
          if (cancelled) return;
          if (!seg.eventsUrl) continue;
          const resp = await fetch(seg.eventsUrl);
          if (!resp.ok) {
            throw new Error(`批次段 ${seg.segmentId} 数据加载失败 (HTTP ${resp.status})`);
          }
          const segEvents = await resp.json();
          if (Array.isArray(segEvents)) {
            allEvents.push(...segEvents);
            totalEvents += segEvents.length;
          }
        }

        if (cancelled) return;

        if (allEvents.length === 0) {
          setMeta({ segments: data.segments.length, totalEvents: 0 });
          setState('empty');
          return;
        }

        // 按 timestamp 排序，确保跨批次段顺序正确
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        allEvents.sort((a: any, b: any) => (a.timestamp || 0) - (b.timestamp || 0));
        setMeta({ segments: data.segments.length, totalEvents });

        if (!containerRef.current) return;

        // 实例化 rrweb-player
        playerInstance = new rrwebPlayer({
          target: containerRef.current,
          props: {
            events: allEvents,
            width: data.viewportW || 1024,
            height: data.viewportH || 768,
            autoPlay: false,
            showController: true,
          },
        });
        playerRef.current = playerInstance;
        if (!cancelled) setState('success');
      } catch (err: any) {
        if (cancelled) return;
        setErrorMsg(err?.message || '回放数据加载失败');
        setState('error');
      }
    };

    loadAndPlay();

    return () => {
      cancelled = true;
      // 卸载时销毁播放器实例，避免 Svelte 组件泄漏
      try {
        playerRef.current?.$destroy?.();
      } catch {
        /* noop */
      }
      playerRef.current = null;
    };
  }, [sessionId]);

  const renderBody = () => {
    if (state === 'loading') {
      return (
        <div style={{ textAlign: 'center', padding: '80px 0' }}>
          <Spin size="large" tip="正在加载会话回放数据..." />
        </div>
      );
    }

    if (state === 'error') {
      return (
        <Result
          status="error"
          title="回放加载失败"
          subTitle={errorMsg}
          extra={
            <Button type="primary" onClick={() => history.push('/session-replay')}>
              返回列表
            </Button>
          }
        />
      );
    }

    if (state === 'empty') {
      return (
        <Result
          status="info"
          title="该会话暂无可回放的事件数据"
          subTitle={`共 ${meta.segments} 个批次段，0 个事件`}
          extra={
            <Button onClick={() => history.push('/session-replay')}>返回列表</Button>
          }
        />
      );
    }

    return (
      <>
        {viewport.w && viewport.h ? (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message={
              <>
                录制视口：<Tag color="blue">{viewport.w}×{viewport.h}</Tag>
                批次段数：<Tag>{meta.segments}</Tag>
                事件总数：<Tag color="green">{meta.totalEvents}</Tag>
              </>
            }
          />
        ) : null}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            padding: 16,
            background: '#fafafa',
            borderRadius: 8,
            overflow: 'auto',
          }}
        >
          {/* rrweb-player 挂载点 */}
          <div ref={containerRef} />
        </div>
      </>
    );
  };

  return (
    <PageContainer
      header={{
        title: '会话回放',
        breadcrumb: {},
        onBack: () => history.push('/session-replay'),
      }}
    >
      <div style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => history.push('/session-replay')}>
          返回列表
        </Button>
      </div>
      <Descriptions size="small" column={3} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="会话ID">
          <Typography.Text code copyable={{ text: sessionId || '' }}>
            {sessionId}
          </Typography.Text>
        </Descriptions.Item>
        <Descriptions.Item label="加载状态">
          <Tag color={state === 'success' ? 'green' : state === 'loading' ? 'blue' : 'red'}>
            {state === 'success' ? '就绪' : state === 'loading' ? '加载中' : state === 'empty' ? '空数据' : '失败'}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="时间">
          {dayjs().format('YYYY-MM-DD HH:mm:ss')}
        </Descriptions.Item>
      </Descriptions>
      {renderBody()}
    </PageContainer>
  );
};

export default SessionReplayPage;
