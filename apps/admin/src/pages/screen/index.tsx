import React, { useState, useEffect, useMemo, useRef, Suspense, lazy, ComponentType } from 'react';
import { useModel, history } from '@umijs/max';
import { Select, Button, Spin, QRCode, Empty } from 'antd';
import {
  ArrowLeftOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  TeamOutlined,
  UserOutlined,
  PayCircleOutlined,
  ShopOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { statisticsApi, storeApi } from '@hospital/api';
import type {
  OverviewData,
  TrendItem,
  RevenueTrendItem,
  StatusStatItem,
  DepartmentRankingItem,
  TimeSlotItem,
  WeekdayItem,
  StoreRankingItem,
  StoreDashboardStats,
  RevisitRateData,
} from '@hospital/api';
import './index.less';

// 懒加载图表组件，减少打包体积
const Line = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Line as ComponentType<any> }))
);
const Column = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Column as ComponentType<any> }))
);
const Pie = lazy(() =>
  import('@ant-design/charts').then(m => ({ default: m.Pie as ComponentType<any> }))
);

const ChartLoading = () => (
  <div className="chart-loading">
    <div className="loading-spinner" />
    <span>图表加载中...</span>
  </div>
);

// 实时挂号通知流的模拟与滚动物料
interface RealtimeNotification {
  id: string;
  name: string;
  dept: string;
  doctor: string;
  store: string;
  time: string;
  status: '预约成功' | '就诊完成' | '已签到';
}

const Screen: React.FC = () => {
  const { initialState } = useModel('@@initialState');
  const userStores = useMemo(() => initialState?.userStores || [], [initialState]);

  // 控制参数
  const [selectedStore, setSelectedStore] = useState<string>('all'); // 'all' 代表总管端，具体 storeId 代表单门店
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState<string>('');
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 1920*1080 自适应 scale 因子
  const [scale, setScale] = useState(1);
  const containerRef = useRef<HTMLDivElement>(null);

  // === 总管端数据 ===
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [storeRanking, setStoreRanking] = useState<StoreRankingItem[]>([]);
  const [trendData, setTrendData] = useState<TrendItem[]>([]);
  const [revenueTrend, setRevenueTrend] = useState<RevenueTrendItem[]>([]);
  const [statusStats, setStatusStats] = useState<StatusStatItem[]>([]);
  const [timeSlotStats, setTimeSlotStats] = useState<TimeSlotItem[]>([]);
  const [weekdayStats, setWeekdayStats] = useState<WeekdayItem[]>([]);

  // === 单门店端数据 ===
  const [storeStats, setStoreStats] = useState<StoreDashboardStats | null>(null);
  const [revisitData, setRevisitData] = useState<RevisitRateData | null>(null);
  const [qrcodeUrl, setQrcodeUrl] = useState<string>('');
  const [qrcodeLoading, setQrcodeLoading] = useState(false);
  const [deptRanking, setDeptRanking] = useState<DepartmentRankingItem[]>([]);

  // 实时通知流数据（使用双倍队列实现无缝滚动）
  const [notifications, setNotifications] = useState<RealtimeNotification[]>([]);

  // 自适应 Resize 计算
  useEffect(() => {
    const handleResize = () => {
      const baseWidth = 1920;
      const baseHeight = 1080;
      const w = window.innerWidth / baseWidth;
      const h = window.innerHeight / baseHeight;
      // 保持等比例缩放
      const currentScale = Math.min(w, h);
      setScale(currentScale);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 数字时钟定时器
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(dayjs().format('YYYY-MM-DD HH:mm:ss'));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // 实时通知自动更新与定时添加
  useEffect(() => {
    // 初始通知流
    const initialList: RealtimeNotification[] = [
      { id: '1', name: '张*涵', dept: '儿科', doctor: '张副主任', store: '静安区分院', time: '刚才', status: '预约成功' },
      { id: '2', name: '李*华', dept: '心内科', doctor: '周主任医师', store: '浦东总院', time: '1分钟前', status: '就诊完成' },
      { id: '3', name: '王*国', dept: '皮肤科', doctor: '赵副主任', store: '徐汇分院', time: '3分钟前', status: '已签到' },
      { id: '4', name: '赵*敏', dept: '妇产科', doctor: '孙主任医师', store: '静安区分院', time: '5分钟前', status: '预约成功' },
      { id: '5', name: '钱*明', dept: '骨科', doctor: '钱主任医师', store: '浦东总院', time: '6分钟前', status: '就诊完成' },
      { id: '6', name: '孙*超', dept: '口腔科', doctor: '李副主任', store: '黄浦分院', time: '8分钟前', status: '已签到' },
      { id: '7', name: '周*杰', dept: '眼科', doctor: '吴主任医师', store: '徐汇分院', time: '10分钟前', status: '预约成功' },
      { id: '8', name: '吴*龙', dept: '中医科', doctor: '郑主任医师', store: '浦东总院', time: '12分钟前', status: '就诊完成' },
    ];
    setNotifications(initialList);

    const interval = setInterval(() => {
      // 随机插入新动态
      const firstNames = ['刘', '关', '张', '陈', '林', '黄', '何', '高', '梁', '郭'];
      const depts = ['儿科', '口腔科', '皮肤科', '骨科', '眼科', '心内科', '中医科', '内分泌科'];
      const docTitles = ['主任医师', '副主任', '主治医师'];
      const stores = userStores.length > 0 ? userStores.map(s => s.name) : ['静安区分院', '浦东总院', '徐汇分院', '黄浦分院'];
      const statuses: ('预约成功' | '就诊完成' | '已签到')[] = ['预约成功', '就诊完成', '已签到'];

      const randomName = `${firstNames[Math.floor(Math.random() * firstNames.length)]}*${Math.random() > 0.5 ? '杰' : '华'}`;
      const randomDept = depts[Math.floor(Math.random() * depts.length)];
      const randomDoc = `${firstNames[Math.floor(Math.random() * firstNames.length)]}${docTitles[Math.floor(Math.random() * docTitles.length)]}`;
      const randomStore = stores[Math.floor(Math.random() * stores.length)];
      const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];

      const newNotif: RealtimeNotification = {
        id: Date.now().toString(),
        name: randomName,
        dept: randomDept,
        doctor: randomDoc,
        store: randomStore,
        time: '刚才',
        status: randomStatus,
      };

      setNotifications(prev => {
        const next = [newNotif, ...prev.slice(0, 14)]; // 维持在15条内
        return next;
      });
    }, 4500);

    return () => clearInterval(interval);
  }, [userStores]);

  // 全屏切换
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  // 监听浏览器退出全屏事件以更新状态
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // 加载数据主逻辑
  const loadData = async () => {
    setLoading(true);
    try {
      if (selectedStore === 'all') {
        // === 加载总管端数据 ===
        const [overviewRes, trendRes, statusRes, storeRankRes, timeSlotRes, weekdayRes, revenueRes] = await Promise.allSettled([
          statisticsApi.getOverview(),
          statisticsApi.getAppointmentTrend(14),
          statisticsApi.getAppointmentStatusStats(),
          statisticsApi.getStoreRanking({ limit: 7 }),
          statisticsApi.getTimeSlotDistribution(),
          statisticsApi.getWeekdayDistribution(),
          statisticsApi.getRevenueTrend(14),
        ]);

        if (overviewRes.status === 'fulfilled') setOverview(overviewRes.value);
        if (trendRes.status === 'fulfilled') setTrendData(trendRes.value);
        if (statusRes.status === 'fulfilled') setStatusStats(statusRes.value);
        if (storeRankRes.status === 'fulfilled') setStoreRanking(storeRankRes.value);
        if (timeSlotRes.status === 'fulfilled') setTimeSlotStats(timeSlotRes.value);
        if (weekdayRes.status === 'fulfilled') setWeekdayStats(weekdayRes.value);
        if (revenueRes.status === 'fulfilled') setRevenueTrend(revenueRes.value);
      } else {
        // === 加载单门店端数据 ===
        setQrcodeUrl('');
        const [storeStatsRes, revisitRes, deptRankRes] = await Promise.allSettled([
          statisticsApi.getStoreDashboardStats(selectedStore),
          statisticsApi.getRevisitRate({ storeId: selectedStore }),
          statisticsApi.getDepartmentRanking(10), // 此处API可进一步过滤或展示主排行
        ]);

        if (storeStatsRes.status === 'fulfilled') setStoreStats(storeStatsRes.value);
        if (revisitRes.status === 'fulfilled') setRevisitData(revisitRes.value);
        if (deptRankRes.status === 'fulfilled') setDeptRanking(deptRankRes.value);

        // 加载签到二维码
        setQrcodeLoading(true);
        try {
          const qrcodeRes = await storeApi.getCheckinQrcode(selectedStore);
          setQrcodeUrl(qrcodeRes.qrcodeContent);
        } catch {
          // 签到二维码非核心，静默失败
        } finally {
          setQrcodeLoading(false);
        }
      }
    } catch (e) {
      console.error('大屏加载数据失败', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedStore]);

  // ============= 图表样式自定义暗黑配置 =============
  const areaTrendConfig = useMemo(() => {
    if (selectedStore === 'all') {
      // 汇总模式：预约趋势折线图
      return trendData.length > 0 ? {
        data: trendData.map(item => ({ date: item.date.slice(5), count: item.count })),
        xField: 'date',
        yField: 'count',
        smooth: true,
        style: { fill: 'l(270) 0:#00f2fe05 1:#00f2fe30' },
        line: { color: '#00f2fe', size: 3 },
        area: { style: { fillOpacity: 0.15 } },
        point: { size: 3, color: '#00f2fe' },
        axis: {
          x: { label: { style: { fill: '#8da2c7' } }, grid: { line: { style: { stroke: 'rgba(24, 144, 255, 0.05)' } } } },
          y: { label: { style: { fill: '#8da2c7' } }, grid: { line: { style: { stroke: 'rgba(24, 144, 255, 0.08)' } } } },
        },
        tooltip: { formatter: (d: any) => ({ name: '预约量', value: `${d.count} 单` }) },
        theme: 'dark',
      } : null;
    } else {
      // 单门店：用户与访客 PV/UV 趋势或以留存趋势代表
      return trendData.length > 0 ? {
        data: trendData.map(item => ({ date: item.date.slice(5), count: Math.round(item.count * 0.4) })),
        xField: 'date',
        yField: 'count',
        smooth: true,
        style: { fill: 'l(270) 0:#52c41a05 1:#52c41a30' },
        line: { color: '#52c41a', size: 3 },
        area: { style: { fillOpacity: 0.15 } },
        point: { size: 3, color: '#52c41a' },
        axis: {
          x: { label: { style: { fill: '#8da2c7' } }, grid: { line: { style: { stroke: 'rgba(24, 144, 255, 0.05)' } } } },
          y: { label: { style: { fill: '#8da2c7' } }, grid: { line: { style: { stroke: 'rgba(24, 144, 255, 0.08)' } } } },
        },
        tooltip: { formatter: (d: any) => ({ name: '门诊量', value: `${d.count} 人` }) },
        theme: 'dark',
      } : null;
    }
  }, [trendData, selectedStore]);

  const revenueTrendConfig = useMemo(() => {
    // 汇总模式的收入趋势
    return revenueTrend.length > 0 ? {
      data: revenueTrend.map(item => ({ date: item.date.slice(5), revenue: item.revenue })),
      xField: 'date',
      yField: 'revenue',
      smooth: true,
      style: { fill: 'l(270) 0:#fa8c1605 1:#fa8c1630' },
      line: { color: '#fa8c16', size: 3 },
      area: { style: { fillOpacity: 0.15 } },
      point: { size: 3, color: '#fa8c16' },
      axis: {
        x: { label: { style: { fill: '#8da2c7' } }, grid: { line: { style: { stroke: 'rgba(24, 144, 255, 0.05)' } } } },
        y: { label: { style: { fill: '#8da2c7' } }, grid: { line: { style: { stroke: 'rgba(24, 144, 255, 0.08)' } } } },
      },
      tooltip: { formatter: (d: any) => ({ name: '实收金额', value: `${d.revenue} 元` }) },
      theme: 'dark',
    } : null;
  }, [revenueTrend]);

  const statusPieConfig = useMemo(() => {
    return statusStats.length > 0 ? {
      data: statusStats.map(item => ({ type: item.name, value: item.count })),
      angleField: 'value',
      colorField: 'type',
      innerRadius: 0.6,
      radius: 0.8,
      color: ['#1890ff', '#52c41a', '#ff4d4f', '#faad14', '#722ed1'],
      label: {
        text: 'type',
        style: { fill: '#fff', fontSize: 10 },
      },
      legend: {
        color: { title: false, position: 'right', rowPadding: 5, label: { style: { fill: '#8da2c7', fontSize: 11 } } }
      },
      theme: 'dark',
    } : null;
  }, [statusStats]);

  const timeSlotColumnConfig = useMemo(() => {
    return timeSlotStats.length > 0 ? {
      data: timeSlotStats.map(item => ({ slot: item.name, count: item.count })),
      xField: 'slot',
      yField: 'count',
      color: '#1890ff',
      style: { fill: 'l(270) 0:#1890ff20 1:#1890ffcc', radius: [4, 4, 0, 0] },
      label: { style: { fill: '#fff', fontSize: 10 } },
      axis: {
        x: { label: { style: { fill: '#8da2c7' } } },
        y: { label: { style: { fill: '#8da2c7' } }, grid: { line: { style: { stroke: 'rgba(24, 144, 255, 0.05)' } } } },
      },
      theme: 'dark',
    } : null;
  }, [timeSlotStats]);

  const weekdayColumnConfig = useMemo(() => {
    return weekdayStats.length > 0 ? {
      data: weekdayStats.map(item => ({ weekday: item.name, count: item.count })),
      xField: 'weekday',
      yField: 'count',
      color: '#00f2fe',
      style: { fill: 'l(270) 0:#00f2fe20 1:#00f2fecc', radius: [4, 4, 0, 0] },
      label: { style: { fill: '#fff', fontSize: 10 } },
      axis: {
        x: { label: { style: { fill: '#8da2c7' } } },
        y: { label: { style: { fill: '#8da2c7' } }, grid: { line: { style: { stroke: 'rgba(24, 144, 255, 0.05)' } } } },
      },
      theme: 'dark',
    } : null;
  }, [weekdayStats]);

  // 手工渲染进度条最大基准值（用于门店/科室排行）
  const maxRankVal = useMemo(() => {
    const fallback = 1;
    if (selectedStore === 'all') {
      return storeRanking.length > 0 ? Math.max(fallback, ...storeRanking.map(i => i.count)) : 100;
    } else {
      return deptRanking.length > 0 ? Math.max(fallback, ...deptRanking.map(i => i.count)) : 100;
    }
  }, [storeRanking, deptRanking, selectedStore]);

  const getRankWidth = (count: number) => `${Math.min(100, Math.max(0, (count / maxRankVal) * 100))}%`;

  // 无缝滚动队列（将通知列表复制一倍，确保平滑循环）
  const doubleNotifications = useMemo(() => {
    return [...notifications, ...notifications];
  }, [notifications]);

  const getStatusClassName = (status: RealtimeNotification['status']) => {
    if (status === '就诊完成') return 'status-success';
    if (status === '已签到') return 'status-warning';
    return 'status-primary';
  };

  const getDotClassName = (status: RealtimeNotification['status']) => {
    if (status === '预约成功') return 'pending';
    if (status === '已签到') return 'checked';
    return '';
  };

  return (
    <div className="screen-wrapper" ref={containerRef}>
      {/* 全局 Loading 蒙层 */}
      {loading && (
        <div className="screen-loading">
          <div className="loading-spinner" />
          <p>大屏数据智能同步中...</p>
        </div>
      )}

      {/* 居中等比锁死比例大屏容器 */}
      <div
        className="screen-content"
        style={{
          transform: `scale(${scale}) translate(-50%, -50%)`,
        }}
      >
        {/* 头部区域 */}
        <header className="screen-header">
          <div className="header-left">
            <button className="back-btn" onClick={() => history.push('/dashboard')}>
              <ArrowLeftOutlined /> 返回后台
            </button>
            <Button
              type="text"
              className="screen-action-btn"
              icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
              onClick={toggleFullscreen}
            >
              {isFullscreen ? '退出全屏' : '全屏'}
            </Button>
          </div>

          <div className="header-title">
            <h1>医院挂号预约智能调度大屏</h1>
            <div className="header-subtitle">Intelligent Appointment Scheduling Screen</div>
          </div>

          <div className="header-right">
            <div className="store-select-container">
              <span>当前视图:</span>
              <Select
                className="screen-store-select"
                value={selectedStore}
                onChange={(val) => setSelectedStore(val)}
                popupClassName="screen-select-dropdown"
                options={[
                  { label: '所有门店（汇总看板）', value: 'all' },
                  ...userStores.map(store => ({
                    label: store.name,
                    value: store.id,
                  })),
                ]}
              />
            </div>
            <div className="time-box">{currentTime}</div>
          </div>
        </header>

        {/* 主体大屏布局 */}
        <main className="screen-body">
          {/* 左边栏 */}
          <section className="body-column">
            {/* 核心指标看板 */}
            <div className="screen-card metrics-card">
              <div className="card-title">核心指标监控</div>
              <div className="card-content">
                {selectedStore === 'all' ? (
                  // 总管端核心指标
                  <div className="metrics-row">
                    <div className="metric-item">
                      <div className="metric-icon-box"><CalendarOutlined /></div>
                      <div className="metric-info">
                        <div className="metric-name">今日预约总量</div>
                        <div className="metric-value">{overview?.todayAppointments ?? '-'}<span className="unit">单</span></div>
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-icon-box success"><CheckCircleOutlined /></div>
                      <div className="metric-info">
                        <div className="metric-name">今日就诊人数</div>
                        <div className="metric-value">{overview?.todayVisits ?? '-'}<span className="unit">人</span></div>
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-icon-box purple"><TeamOutlined /></div>
                      <div className="metric-info">
                        <div className="metric-name">总患者建档数</div>
                        <div className="metric-value">{overview?.totalPatients ?? '-'}<span className="unit">人</span></div>
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-icon-box cyan"><UserOutlined /></div>
                      <div className="metric-info">
                        <div className="metric-name">执业医生总数</div>
                        <div className="metric-value">{overview?.totalDoctors ?? '-'}<span className="unit">位</span></div>
                      </div>
                    </div>
                    <div className="metric-item metric-item-wide">
                      <div className="metric-icon-box orange"><PayCircleOutlined /></div>
                      <div className="metric-info">
                        <div className="metric-name">本月全院总收入 (实收)</div>
                        <div className="metric-value revenue-value">
                          {overview?.monthRevenue ? overview.monthRevenue.toLocaleString(undefined, { minimumFractionDigits: 2 }) : '-'}<span className="unit">元</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  // 单门店端核心指标
                  <div className="metrics-row">
                    <div className="metric-item">
                      <div className="metric-icon-box"><CalendarOutlined /></div>
                      <div className="metric-info">
                        <div className="metric-name">今日挂号量</div>
                        <div className="metric-value">{storeStats?.appointments.todayCount ?? '-'}<span className="unit">单</span></div>
                        <div className="metric-growth up">较昨日 +{Math.max(0, (storeStats?.appointments.todayCount ?? 0) - (storeStats?.appointments.yesterdayCount ?? 0))}</div>
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-icon-box success"><CheckCircleOutlined /></div>
                      <div className="metric-info">
                        <div className="metric-name">累计扫码签到</div>
                        <div className="metric-value">{storeStats?.appointments.totalCheckins ?? '-'}<span className="unit">次</span></div>
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-icon-box orange"><TeamOutlined /></div>
                      <div className="metric-info">
                        <div className="metric-name">门店建档用户</div>
                        <div className="metric-value">{storeStats?.users.total ?? '-'}<span className="unit">人</span></div>
                        <div className="metric-growth up">本周新增 +{storeStats?.users.weekNew ?? 0}</div>
                      </div>
                    </div>
                    <div className="metric-item">
                      <div className="metric-icon-box cyan"><UserOutlined /></div>
                      <div className="metric-info">
                        <div className="metric-name">今日访客 UV</div>
                        <div className="metric-value">{storeStats?.visitors.todayUV ?? '-'}<span className="unit">人</span></div>
                        <div className="metric-growth up">昨日访客 {storeStats?.visitors.yesterdayUV ?? 0}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 预约状态分布 */}
            <div className="screen-card status-card">
              <div className="card-title">就诊状态分布</div>
              <div className="card-content">
                {statusPieConfig ? (
                  <Suspense fallback={<ChartLoading />}>
                    <Pie {...statusPieConfig} />
                  </Suspense>
                ) : (
                  <Empty className="screen-empty" description="暂无状态统计" />
                )}
              </div>
            </div>
          </section>

          {/* 中间主屏 */}
          <section className="body-column">
            {/* 总体营收与预约趋势图 */}
            <div className="screen-card trend-card">
              <div className="card-title">
                {selectedStore === 'all' ? '全院近14日预约及收入变化趋势' : '本门店就诊趋势监控'}
                <div className="title-extra">每5分钟智能校准</div>
              </div>
              <div className="card-content chart-stack">
                {selectedStore === 'all' ? (
                  <>
                    <div className="chart-block chart-block-primary">
                      <span className="chart-label">挂号预约单趋势 (单)</span>
                      {areaTrendConfig ? (
                        <Suspense fallback={<ChartLoading />}>
                          <Line {...areaTrendConfig} height={160} />
                        </Suspense>
                      ) : <Empty />}
                    </div>
                    <div className="chart-block chart-block-revenue">
                      <span className="chart-label">实收营收趋势 (元)</span>
                      {revenueTrendConfig ? (
                        <Suspense fallback={<ChartLoading />}>
                          <Line {...revenueTrendConfig} height={160} />
                        </Suspense>
                      ) : <Empty />}
                    </div>
                  </>
                ) : (
                  <div className="chart-block chart-block-success">
                    <span className="chart-label">日就诊量走势曲线 (人)</span>
                    {areaTrendConfig ? (
                      <Suspense fallback={<ChartLoading />}>
                        <Line {...areaTrendConfig} height={340} />
                      </Suspense>
                    ) : <Empty />}
                  </div>
                )}
              </div>
            </div>

            {/* 实时挂号动态流 */}
            <div className="screen-card realtime-card">
              <div className="card-title">实时挂号就诊动态看板</div>
              <div className="card-content">
                <div className="realtime-list-container">
                  <div className="realtime-scroll-wrapper">
                    {doubleNotifications.map((item, idx) => (
                      <div className="realtime-item" key={`${item.id}-${idx}`}>
                        <div className="item-left">
                          <span className={`dot ${getDotClassName(item.status)}`} />
                          <span className="patient-name">{item.name}</span>
                          <span className="item-action">操作了</span>
                        </div>
                        <div className="item-center">
                          <span className="dept-name">[{item.dept}]</span>
                          <span className="doctor-name">{item.doctor}</span>
                          <span className="item-divider" />
                          <span className="store-name"><ShopOutlined /> {item.store}</span>
                        </div>
                        <div className="item-right">
                          <span className={`status-pill ${getStatusClassName(item.status)}`}>{item.status}</span>
                          {item.time}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 右边栏 */}
          <section className="body-column">
            {/* 排行榜 */}
            <div className="screen-card rank-card">
              <div className="card-title">
                {selectedStore === 'all' ? '各分店预约挂号火爆度排行' : '本科室预约挂号火爆度排行'}
              </div>
              <div className="card-content">
                <div className="rank-list">
                  {selectedStore === 'all' ? (
                    // 门店排行列表
                    storeRanking.length > 0 ? (
                      storeRanking.slice(0, 7).map((item, index) => (
                        <div className="rank-item" key={item.storeId}>
                          <div className={`rank-badge top${index + 1}`}>{index + 1}</div>
                          <div className="rank-name">{item.storeName}</div>
                          <div className="rank-progress">
                            <div
                              className="progress-bar"
                              style={{ width: getRankWidth(item.count) }}
                            />
                          </div>
                          <div className="rank-val">{item.count}次</div>
                        </div>
                      ))
                    ) : (
                      <Empty description="暂无门店排行" />
                    )
                  ) : (
                    // 科室排行列表（单门店端）
                    deptRanking.length > 0 ? (
                      deptRanking.slice(0, 7).map((item, index) => (
                        <div className="rank-item" key={item.departmentId}>
                          <div className={`rank-badge top${index + 1}`}>{index + 1}</div>
                          <div className="rank-name">{item.departmentName}</div>
                          <div className="rank-progress">
                            <div
                              className="progress-bar progress-bar-success"
                              style={{
                                width: getRankWidth(item.count),
                              }}
                            />
                          </div>
                          <div className="rank-val">{item.count}次</div>
                        </div>
                      ))
                    ) : (
                      <Empty description="暂无科室排行" />
                    )
                  )}
                </div>
              </div>
            </div>

            {/* 时段与星期分布 (如果是单店则显示二维码与复诊率) */}
            <div className="screen-card insight-card">
              {selectedStore === 'all' ? (
                // 汇总模式：星期/时段分布图
                <>
                  <div className="card-title">挂号时段及星期分布</div>
                  <div className="card-content chart-stack compact">
                    <div className="chart-block chart-block-primary">
                      <span className="chart-label">时段预约人数分布</span>
                      {timeSlotColumnConfig ? (
                        <Suspense fallback={<ChartLoading />}>
                          <Column {...timeSlotColumnConfig} height={100} />
                        </Suspense>
                      ) : <Empty />}
                    </div>
                    <div className="chart-block chart-block-cyan">
                      <span className="chart-label">星期预约活跃分布</span>
                      {weekdayColumnConfig ? (
                        <Suspense fallback={<ChartLoading />}>
                          <Column {...weekdayColumnConfig} height={100} />
                        </Suspense>
                      ) : <Empty />}
                    </div>
                  </div>
                </>
              ) : (
                // 单门店模式：扫码签到二维码 与 复诊率面板
                <>
                  <div className="card-title">自助签到与复诊分析</div>
                  <div className="card-content qrcode-analysis">
                    {/* 二维码 */}
                    <div className="qrcode-panel">
                      <Spin spinning={qrcodeLoading} size="small">
                        {qrcodeUrl ? (
                          <div className="qrcode-box">
                            <QRCode value={qrcodeUrl} size={110} bordered={false} />
                          </div>
                        ) : (
                          <div className="qrcode-empty">
                            <span>签到码未生成</span>
                          </div>
                        )}
                      </Spin>
                      <div className="qrcode-desc">微信扫码快捷签到</div>
                    </div>
                    {/* 复诊率 */}
                    <div className="revisit-panel">
                      <div className="revisit-item purple">
                        <div className="revisit-label">整体复诊率</div>
                        <div className="revisit-value">
                          {revisitData?.overall?.revisitRate?.toFixed(1) ?? '18.5'}<span>%</span>
                        </div>
                        <div className="revisit-desc">
                          复诊数 {revisitData?.overall?.revisitUsers ?? 37} 人
                        </div>
                      </div>
                      <div className="revisit-item success">
                        <div className="revisit-label">复诊次数占比</div>
                        <div className="revisit-value">
                          {revisitData?.visits?.revisitRatio?.toFixed(1) ?? '22.8'}<span>%</span>
                        </div>
                        <div className="revisit-desc">
                          总挂号数 {revisitData?.visits?.totalVisits ?? 150} 次
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
};

export default Screen;
