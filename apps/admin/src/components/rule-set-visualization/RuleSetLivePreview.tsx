/**
 * 规则组实时预览面板组件
 * 用于编辑页右侧实时显示当前配置效果
 */

import React, { useMemo, useState, useEffect, useRef } from 'react';
import { Card, Space, Typography, Divider, Spin, TimePicker } from 'antd';
import type { RuleSet, ShiftType } from '@hospital/shared';
import dayjs, { type Dayjs } from 'dayjs';
import { formatTime, calculateKeyTimes } from '@/utils/ruleSetFormatter';
import { trackLivePreviewOpen, trackLivePreviewUpdate, getTimestamp, type LivePreviewData } from '@/utils/analytics';
import RuleSetSummaryCard from './RuleSetSummaryCard';
import RuleSetTimeline from './RuleSetTimeline';
import GanttTimeline from './GanttTimeline';

const { Text, Title } = Typography;

// ==================== 类型定义 ====================

export interface RuleSetLivePreviewProps {
  formData: Partial<RuleSet>;
  shiftTypes: ShiftType[];
  exampleSchedule?: {
    date: string;
    startTime: string;
    endTime: string;
  };
  loading?: boolean;
}

// ==================== 常量定义 ====================

// 使用固定日期作为基准，避免每次渲染创建新的 dayjs 对象
const BASE_DATE = dayjs().startOf('day');

const DEFAULT_EXAMPLE_SCHEDULE = {
  date: BASE_DATE.format('YYYY-MM-DD'),
  startTime: '08:00:00',
  endTime: '12:00:00',
};

// 默认班次时间（Dayjs 格式）- 基于同一个基准日期
const DEFAULT_SHIFT_START = BASE_DATE.hour(8).minute(0).second(0);
const DEFAULT_SHIFT_END = BASE_DATE.hour(12).minute(0).second(0);

// ==================== 子组件 ====================

/**
 * 关键时间点列表组件
 */
interface KeyTimesListProps {
  keyTimes: ReturnType<typeof calculateKeyTimes>;
  baseDate: Date;
}

const KeyTimesList: React.FC<KeyTimesListProps> = ({ keyTimes, baseDate }) => {
  const formatKeyTime = (time?: Date) => {
    if (!time) return '不限制';
    return formatTime(time);
  };

  const items: { label: string; time?: Date; color?: string }[] = [
    { label: '预约开放', time: keyTimes.bookOpen, color: '#1890ff' },
    { label: '预约截止', time: keyTimes.bookClose, color: '#1890ff' },
    { label: '签到开放', time: keyTimes.checkinOpen, color: '#52c41a' },
    { label: '签到截止', time: keyTimes.checkinClose, color: '#52c41a' },
    { label: '取消开放', time: keyTimes.cancelOpen, color: '#fa8c16' },
    { label: '取消截止', time: keyTimes.cancelClose, color: '#fa8c16' },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="small">
      {items.map((item) => (
        <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary">{item.label}：</Text>
          <Text strong style={{ color: item.color }}>
            {formatKeyTime(item.time)}
          </Text>
        </div>
      ))}
    </Space>
  );
};

// ==================== 主组件 ====================

/**
 * 规则组实时预览面板组件
 */
const RuleSetLivePreview: React.FC<RuleSetLivePreviewProps> = ({
  formData,
  shiftTypes,
  exampleSchedule = DEFAULT_EXAMPLE_SCHEDULE,
  loading = false,
}) => {
  // 埋点：记录组件首次挂载
  const hasTrackedOpen = useRef(false);

  // 用户可配置的班次时间状态
  const [shiftStartTime, setShiftStartTime] = useState<Dayjs>(DEFAULT_SHIFT_START);
  const [shiftEndTime, setShiftEndTime] = useState<Dayjs>(DEFAULT_SHIFT_END);

  // 解析示例班次时间
  const scheduleDates = useMemo(() => {
    const baseDate = dayjs(exampleSchedule.date).toDate();
    const startTime = shiftStartTime.toDate();
    const endTime = shiftEndTime.toDate();

    return { baseDate, startTime, endTime };
  }, [exampleSchedule, shiftStartTime, shiftEndTime]);

  // 计算关键时间点
  const keyTimes = useMemo(() => {
    return calculateKeyTimes(formData, scheduleDates.startTime, scheduleDates.endTime);
  }, [formData, scheduleDates]);

  // 获取选中的班次类型名称
  const selectedShiftTypeNames = useMemo(() => {
    if (!formData.shiftTypes || shiftTypes.length === 0) return [];
    return shiftTypes
      .filter((st) => formData.shiftTypes?.some((fst) => fst.id === st.id))
      .map((st) => st.name);
  }, [formData.shiftTypes, shiftTypes]);

  // 埋点：追踪实时预览打开和更新
  useEffect(() => {
    // 首次打开埋点
    if (!hasTrackedOpen.current && formData.name) {
      const data: LivePreviewData = {
        ruleSetId: formData.id,
        ruleSetName: formData.name,
        hasWindows: !!(formData.windows && formData.windows.length > 0),
        hasShiftTypes: !!(formData.shiftTypes && formData.shiftTypes.length > 0),
        timestamp: getTimestamp(),
      };
      trackLivePreviewOpen(data);
      hasTrackedOpen.current = true;
    }
  }, [formData]);

  // 追踪表单数据变化（实时预览更新）
  useEffect(() => {
    if (!hasTrackedOpen.current) return;

    const data: LivePreviewData = {
      ruleSetId: formData.id,
      ruleSetName: formData.name,
      timestamp: getTimestamp(),
    };
    trackLivePreviewUpdate(data);
  }, [formData]);

  return (
    <Spin spinning={loading}>
      <Card
        title={
          <Space>
            <span>实时预览</span>
          </Space>
        }
        size="small"
        styles={{ body: { padding: '16px' } }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 班次时间配置 */}
          <div>
            <Text type="secondary">班次时间配置：</Text>
            <div style={{ marginTop: 8 }}>
              <Space.Compact style={{ width: '100%' }}>
                <TimePicker
                  value={shiftStartTime}
                  onChange={(value) => value && setShiftStartTime(value)}
                  format="HH:mm"
                  placeholder="开始时间"
                  style={{ width: '50%' }}
                />
                <TimePicker
                  value={shiftEndTime}
                  onChange={(value) => value && setShiftEndTime(value)}
                  format="HH:mm"
                  placeholder="结束时间"
                  style={{ width: '50%' }}
                />
              </Space.Compact>
            </div>
            {selectedShiftTypeNames.length > 0 && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                适用班次：{selectedShiftTypeNames.join('、')}
              </Text>
            )}
          </div>

          <Divider style={{ margin: '8px 0' }} />

          {/* 规则摘要 */}
          {formData.name && (
            <>
              <div>
                <Title level={5} style={{ margin: 0 }}>
                  规则摘要
                </Title>
                <div style={{ marginTop: 8 }}>
                  <RuleSetSummaryCard ruleSet={formData} variant="compact" />
                </div>
              </div>
              <Divider style={{ margin: '8px 0' }} />
            </>
          )}

          {/* 时间窗预览 */}
          {formData.windows && formData.windows.length > 0 && (
            <>
              <div>
                <Title level={5} style={{ margin: 0 }}>
                  时间窗预览（甘特图）
                </Title>
                {/* 甘特图形式展示时间窗 */}
                <div style={{ marginTop: 8 }}>
                  <GanttTimeline
                    windows={formData.windows}
                    shiftStart={scheduleDates.startTime}
                    shiftEnd={scheduleDates.endTime}
                    height={200}
                  />
                </div>
              </div>
              <Divider style={{ margin: '8px 0' }} />
            </>
          )}

          {/* 关键时间点 */}
          <div>
            <Title level={5} style={{ margin: 0 }}>
              关键时间点
            </Title>
            <div style={{ marginTop: 8, padding: '12px', backgroundColor: '#fafafa', borderRadius: '6px' }}>
              <KeyTimesList keyTimes={keyTimes} baseDate={scheduleDates.baseDate} />
            </div>
          </div>
        </Space>
      </Card>
    </Spin>
  );
};

export default React.memo(RuleSetLivePreview);
