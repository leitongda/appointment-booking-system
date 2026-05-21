/**
 * 规则组时间轴可视化组件
 * 将时间窗配置转换为直观的时间轴展示
 */

import React, { useMemo } from 'react';
import { Timeline, Space, Tag, Card, Typography, Row, Col, theme } from 'antd';
import type { TimelineItemProps } from 'antd';
import type { RuleWindow } from '@hospital/shared';
import { formatOffset, groupWindowsByAction, calculateWindowTime } from '@/utils/ruleSetFormatter';
import { ACTION_COLORS, REFERENCE_POINT_LABELS } from '@/constants/rule-set';
import dayjs from 'dayjs';

const { Text } = Typography;

// ==================== 类型定义 ====================

export interface RuleSetTimelineProps {
  windows: RuleWindow[];
  direction?: 'horizontal' | 'vertical';
  showReferenceLine?: boolean;
  compact?: boolean;
  shiftStart?: Date;
  shiftEnd?: Date;
}

// ==================== 子组件 ====================

/**
 * 单个时间窗的时间轴项
 */
interface WindowTimelineItemProps {
  window: RuleWindow;
  compact?: boolean;
  shiftStart?: Date;
  shiftEnd?: Date;
}

const WindowTimelineItem: React.FC<WindowTimelineItemProps> = ({
  window,
  compact,
  shiftStart,
  shiftEnd
}) => {
  const { token } = theme.useToken();
  const colorConfig = ACTION_COLORS[window.action] || ACTION_COLORS.BOOK;
  const refPointLabel = REFERENCE_POINT_LABELS[window.referencePoint] || window.referencePoint;
  const openOffset = formatOffset(window.openOffsetSec);
  const closeOffset = formatOffset(window.closeOffsetSec);

  // 计算实际时间（如果提供了班次时间）
  const actualTimeRange = useMemo(() => {
    if (!shiftStart) return null;

    const openTime = calculateWindowTime(
      window.referencePoint,
      window.openOffsetSec,
      shiftStart,
      shiftEnd || shiftStart
    );
    const closeTime = calculateWindowTime(
      window.referencePoint,
      window.closeOffsetSec,
      shiftStart,
      shiftEnd || shiftStart
    );

    const openStr = openTime ? dayjs(openTime).format('HH:mm') : '∞';
    const closeStr = closeTime ? dayjs(closeTime).format('HH:mm') : '∞';

    return { openStr, closeStr, openTime, closeTime };
  }, [window, shiftStart, shiftEnd]);

  // 生成友好描述
  const friendlyDescription = useMemo(() => {
    const parts: string[] = [];

    if (window.openOffsetSec !== null) {
      if (window.openOffsetSec < 0) {
        parts.push(`${refPointLabel}${openOffset}开放`);
      } else {
        parts.push(`${refPointLabel}${openOffset}开放`);
      }
    } else {
      parts.push('无最早开放时间');
    }

    if (window.closeOffsetSec !== null) {
      if (window.closeOffsetSec < 0) {
        parts.push(`${refPointLabel}${closeOffset}截止`);
      } else {
        parts.push(`${refPointLabel}${closeOffset}截止`);
      }
    } else {
      parts.push('无最晚截止时间');
    }

    return parts.join('，');
  }, [window, refPointLabel, openOffset, closeOffset]);

  return (
    <div
      style={{
        padding: compact ? '8px 12px' : '12px 16px',
        backgroundColor: colorConfig.light,
        borderRadius: '6px',
        borderLeft: `3px solid ${colorConfig.primary}`,
      }}
    >
      <Space size={compact ? 'small' : 'middle'} style={{ width: '100%' }}>
        {/* 动作类型与参考点 */}
        <div>
          <Tag color={colorConfig.primary}>{colorConfig.label}</Tag>
          <Text type="secondary" style={{ fontSize: compact ? 12 : 13 }}>
            基于 {refPointLabel}
          </Text>
        </div>

        {/* 时间偏移 */}
        {!compact && (
          <Row gutter={16}>
            <Col span={12}>
              <div>
                <Text type="secondary">开放：</Text>
                <Text style={{ color: token.colorSuccess, fontWeight: 500 }}>{openOffset}</Text>
              </div>
              {actualTimeRange && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  实际时间: {actualTimeRange.openStr}
                </Text>
              )}
            </Col>
            <Col span={12}>
              <div>
                <Text type="secondary">截止：</Text>
                <Text style={{ color: token.colorWarning, fontWeight: 500 }}>{closeOffset}</Text>
              </div>
              {actualTimeRange && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  实际时间: {actualTimeRange.closeStr}
                </Text>
              )}
            </Col>
          </Row>
        )}

        {compact && (
          <>
            <Text type="secondary" style={{ fontSize: 11 }}>
              {openOffset} / {closeOffset}
            </Text>
            {actualTimeRange && (
              <Text type="secondary" style={{ fontSize: 10 }}>
                ({actualTimeRange.openStr} ~ {actualTimeRange.closeStr})
              </Text>
            )}
          </>
        )}

        {/* 友好描述 */}
        {!compact && (
          <div>
            <Text style={{ fontSize: 12, color: token.colorTextSecondary }}>
              {friendlyDescription}
            </Text>
          </div>
        )}

        {/* 失败策略 */}
        {!compact && (
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              失败策略：{window.failPolicy === 'REJECT' ? '拒绝操作' : null}
              {window.failPolicy === 'ALLOW_WITH_TAG' ? `允许并打标签: ${window.failTag || '无'}` : null}
              {window.failPolicy === 'AUTO_TO_WAITLIST' ? '自动进入候补' : null}
            </Text>
          </div>
        )}
      </Space>
    </div>
  );
};

// ==================== 主组件 ====================

/**
 * 规则组时间轴组件
 */
const RuleSetTimeline: React.FC<RuleSetTimelineProps> = ({
  windows,
  direction = 'vertical',
  showReferenceLine: _showReferenceLine = true,
  compact = false,
  shiftStart,
  shiftEnd,
}) => {
  // 按动作类型分组时间窗
  const groupedWindows = useMemo(() => groupWindowsByAction(windows), [windows]);

  // 如果没有时间窗，显示提示
  const allWindows = [
    ...groupedWindows.book,
    ...groupedWindows.checkin,
    ...groupedWindows.cancel,
    ...groupedWindows.holdRelease,
  ];

  if (allWindows.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '32px 0' }}>
        <Text type="secondary">暂无时间窗配置</Text>
      </div>
    );
  }

  // 垂直时间轴模式
  if (direction === 'vertical') {
    return (
      <Timeline
        mode="left"
        items={[
          groupedWindows.book.length > 0 ? {
            key: '0',
            color: ACTION_COLORS.BOOK.primary,
            label: <Text strong>{ACTION_COLORS.BOOK.label}</Text>,
            children: (
              <Space style={{ width: '100%' }} size="small">
                {groupedWindows.book.map((window) => (
                  <WindowTimelineItem
                    key={window.id}
                    window={window}
                    compact={compact}
                    shiftStart={shiftStart}
                    shiftEnd={shiftEnd}
                  />
                ))}
              </Space>
            ),
          } : null,
          groupedWindows.checkin.length > 0 ? {
            key: '1',
            color: ACTION_COLORS.CHECKIN.primary,
            label: <Text strong>{ACTION_COLORS.CHECKIN.label}</Text>,
            children: (
              <Space style={{ width: '100%' }} size="small">
                {groupedWindows.checkin.map((window) => (
                  <WindowTimelineItem
                    key={window.id}
                    window={window}
                    compact={compact}
                    shiftStart={shiftStart}
                    shiftEnd={shiftEnd}
                  />
                ))}
              </Space>
            ),
          } : null,
          groupedWindows.cancel.length > 0 ? {
            key: '2',
            color: ACTION_COLORS.CANCEL.primary,
            label: <Text strong>{ACTION_COLORS.CANCEL.label}</Text>,
            children: (
              <Space style={{ width: '100%' }} size="small">
                {groupedWindows.cancel.map((window) => (
                  <WindowTimelineItem
                    key={window.id}
                    window={window}
                    compact={compact}
                    shiftStart={shiftStart}
                    shiftEnd={shiftEnd}
                  />
                ))}
              </Space>
            ),
          } : null,
          groupedWindows.holdRelease.length > 0 ? {
            key: '3',
            color: ACTION_COLORS.HOLD_RELEASE.primary,
            label: <Text strong>{ACTION_COLORS.HOLD_RELEASE.label}</Text>,
            children: (
              <Space style={{ width: '100%' }} size="small">
                {groupedWindows.holdRelease.map((window) => (
                  <WindowTimelineItem
                    key={window.id}
                    window={window}
                    compact={compact}
                    shiftStart={shiftStart}
                    shiftEnd={shiftEnd}
                  />
                ))}
              </Space>
            ),
          } : null,
        ].filter(Boolean) as TimelineItemProps[]}
      />
    );
  }

  // 水平时间轴模式（用于紧凑展示）
  return (
    <Space style={{ width: '100%' }} size="middle">
      {groupedWindows.book.length > 0 && (
        <Card
          size="small"
          title={<Tag color={ACTION_COLORS.BOOK.primary}>{ACTION_COLORS.BOOK.label}</Tag>}
          styles={{ body: { padding: (compact ? '8px' : '12px') } }}
        >
          <Space style={{ width: '100%' }} size="small">
            {groupedWindows.book.map((window) => (
              <WindowTimelineItem
                key={window.id}
                window={window}
                compact={compact}
                shiftStart={shiftStart}
                shiftEnd={shiftEnd}
              />
            ))}
          </Space>
        </Card>
      )}

      {groupedWindows.checkin.length > 0 && (
        <Card
          size="small"
          title={<Tag color={ACTION_COLORS.CHECKIN.primary}>{ACTION_COLORS.CHECKIN.label}</Tag>}
          styles={{ body: { padding: (compact ? '8px' : '12px') } }}
        >
          <Space style={{ width: '100%' }} size="small">
            {groupedWindows.checkin.map((window) => (
              <WindowTimelineItem
                key={window.id}
                window={window}
                compact={compact}
                shiftStart={shiftStart}
                shiftEnd={shiftEnd}
              />
            ))}
          </Space>
        </Card>
      )}

      {groupedWindows.cancel.length > 0 && (
        <Card
          size="small"
          title={<Tag color={ACTION_COLORS.CANCEL.primary}>{ACTION_COLORS.CANCEL.label}</Tag>}
          styles={{ body: { padding: (compact ? '8px' : '12px') } }}
        >
          <Space style={{ width: '100%' }} size="small">
            {groupedWindows.cancel.map((window) => (
              <WindowTimelineItem
                key={window.id}
                window={window}
                compact={compact}
                shiftStart={shiftStart}
                shiftEnd={shiftEnd}
              />
            ))}
          </Space>
        </Card>
      )}

      {groupedWindows.holdRelease.length > 0 && (
        <Card
          size="small"
          title={<Tag color={ACTION_COLORS.HOLD_RELEASE.primary}>{ACTION_COLORS.HOLD_RELEASE.label}</Tag>}
          styles={{ body: { padding: (compact ? '8px' : '12px') } }}
        >
          <Space style={{ width: '100%' }} size="small">
            {groupedWindows.holdRelease.map((window) => (
              <WindowTimelineItem
                key={window.id}
                window={window}
                compact={compact}
                shiftStart={shiftStart}
                shiftEnd={shiftEnd}
              />
            ))}
          </Space>
        </Card>
      )}
    </Space>
  );
};

export default React.memo(RuleSetTimeline);
