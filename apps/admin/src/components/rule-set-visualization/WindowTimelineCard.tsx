/**
 * 时间窗时间轴卡片组件
 * 用于直观显示"提前7天开放、班次开始前1小时截止"等时间关系
 */

import React, { useMemo } from 'react';
import { Card, Space, Typography, Row, Col, Tag, Divider, Tooltip, theme } from 'antd';
import { ClockCircleOutlined, ArrowRightOutlined, MinusOutlined } from '@ant-design/icons';
import type { RuleWindow } from '@hospital/shared';
import { formatOffset, calculateWindowTime } from '@/utils/ruleSetFormatter';
import { ACTION_COLORS, REFERENCE_POINT_LABELS } from '@/constants/rule-set';
import dayjs from 'dayjs';

const { Text } = Typography;

// ==================== 类型定义 ====================

export interface WindowTimelineCardProps {
  window: RuleWindow;
  shiftStart: Date;
  shiftEnd?: Date;
  compact?: boolean;
  highlightOnHover?: boolean;
}

// ==================== 辅助函数 ====================

/**
 * 计算并格式化实际时间点
 */
const formatActualTime = (window: RuleWindow, shiftStart: Date, shiftEnd?: Date): string => {
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

  const openStr = openTime ? dayjs(openTime).format('MM-DD HH:mm') : '不限制';
  const closeStr = closeTime ? dayjs(closeTime).format('MM-DD HH:mm') : '不限制';

  return `${openStr} ~ ${closeStr}`;
};

/**
 * 生成友好的时间描述
 */
const generateFriendlyDescription = (window: RuleWindow): string[] => {
  const descriptions: string[] = [];
  const refPoint = REFERENCE_POINT_LABELS[window.referencePoint] || window.referencePoint;
  const openOffset = formatOffset(window.openOffsetSec);
  const closeOffset = formatOffset(window.closeOffsetSec);

  // 开放时间描述
  if (window.openOffsetSec === null) {
    descriptions.push('无最早开放时间限制');
  } else if (window.openOffsetSec < 0) {
    descriptions.push(`${refPoint}${openOffset}可开始操作`);
  } else {
    descriptions.push(`${refPoint}${openOffset}可开始操作`);
  }

  // 截止时间描述
  if (window.closeOffsetSec === null) {
    descriptions.push('无最晚截止时间限制');
  } else if (window.closeOffsetSec < 0) {
    descriptions.push(`${refPoint}${closeOffset}前必须操作`);
  } else {
    descriptions.push(`${refPoint}${closeOffset}前必须操作`);
  }

  return descriptions;
};

// ==================== 主组件 ====================

/**
 * 时间窗时间轴卡片组件
 */
const WindowTimelineCard: React.FC<WindowTimelineCardProps> = ({
  window,
  shiftStart,
  shiftEnd,
  compact = false,
  highlightOnHover = true,
}) => {
  const { token } = theme.useToken();
  const colorConfig = ACTION_COLORS[window.action] || ACTION_COLORS.BOOK;
  const refPointLabel = REFERENCE_POINT_LABELS[window.referencePoint] || window.referencePoint;

  // 计算实际时间
  const actualTimeRange = useMemo(() => {
    return formatActualTime(window, shiftStart, shiftEnd);
  }, [window, shiftStart, shiftEnd]);

  // 生成友好描述
  const friendlyDescriptions = useMemo(() => {
    return generateFriendlyDescription(window);
  }, [window]);

  // 开放和截止偏移
  const openOffset = formatOffset(window.openOffsetSec);
  const closeOffset = formatOffset(window.closeOffsetSec);

  return (
    <Card
      size="small"
      style={{
        backgroundColor: colorConfig.light,
        borderLeft: `4px solid ${colorConfig.primary}`,
        marginBottom: compact ? 8 : 12,
        transition: highlightOnHover ? 'all 0.3s' : 'none',
        cursor: highlightOnHover ? 'pointer' : 'default',
      }}
      bodyStyle={{ padding: compact ? '12px' : '16px' }}
      onMouseEnter={highlightOnHover ? (e) => {
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
        e.currentTarget.style.transform = 'translateY(-2px)';
      } : undefined}
      onMouseLeave={highlightOnHover ? (e) => {
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.transform = 'translateY(0)';
      } : undefined}
    >
      <Space direction="vertical" size={compact ? 'small' : 'middle'} style={{ width: '100%' }}>
        {/* 标题行：动作类型 + 参考点 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Tag color={colorConfig.primary}>{colorConfig.label}</Tag>
            <Text type="secondary" style={{ fontSize: compact ? 12 : 13 }}>
              基于 {refPointLabel}
            </Text>
          </Space>
          {!window.enabled && <Tag color="default">已禁用</Tag>}
        </div>

        {/* 时间轴可视化 */}
        {!compact && (
          <div style={{
            padding: '12px',
            backgroundColor: 'white',
            borderRadius: '6px',
            border: '1px solid #d9d9d9',
          }}>
            <Row gutter={[16, 8]} align="middle">
              {/* 开放时间 */}
              <Col xs={24} sm={11}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: token.colorTextTertiary, marginBottom: 4 }}>开放时间</div>
                  <div style={{
                    padding: '6px 12px',
                    backgroundColor: token.colorSuccessBg,
                    border: `1px solid ${token.colorSuccessBorder}`,
                    borderRadius: '4px',
                    color: token.colorSuccess,
                    fontWeight: 500,
                  }}>
                    {window.openOffsetSec === null ? (
                      <span style={{ color: token.colorTextTertiary }}>∞ 不限制</span>
                    ) : (
                      <>
                        <ClockCircleOutlined style={{ marginRight: 4 }} />
                        {openOffset}
                      </>
                    )}
                  </div>
                </div>
              </Col>

              {/* 分隔符 */}
              <Col xs={24} sm={2} style={{ textAlign: 'center' }}>
                <ArrowRightOutlined style={{ color: token.colorBorderSecondary, fontSize: 16 }} />
              </Col>

              {/* 参考点 */}
              <Col xs={24} sm={11}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: token.colorTextTertiary, marginBottom: 4 }}>参考点</div>
                  <div style={{
                    padding: '6px 12px',
                    backgroundColor: token.colorInfoBg,
                    border: `1px solid ${token.colorInfoBorder}`,
                    borderRadius: '4px',
                    color: token.colorInfo,
                    fontWeight: 500,
                  }}>
                    {refPointLabel}
                  </div>
                </div>
              </Col>

              {/* 截止时间 */}
              <Col xs={24} sm={11}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: token.colorTextTertiary, marginBottom: 4 }}>截止时间</div>
                  <div style={{
                    padding: '6px 12px',
                    backgroundColor: token.colorWarningBg,
                    border: `1px solid ${token.colorWarningBorder}`,
                    borderRadius: '4px',
                    color: token.colorWarning,
                    fontWeight: 500,
                  }}>
                    {window.closeOffsetSec === null ? (
                      <span style={{ color: token.colorTextTertiary }}>∞ 不限制</span>
                    ) : (
                      <>
                        <ClockCircleOutlined style={{ marginRight: 4 }} />
                        {closeOffset}
                      </>
                    )}
                  </div>
                </div>
              </Col>
            </Row>

            {/* 实际时间范围 */}
            <Divider style={{ margin: '12px 0' }} />
            <div style={{ textAlign: 'center' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                实际时间范围（以班次 8:00 为基准）
              </Text>
              <div style={{ marginTop: 4, fontSize: 13, fontWeight: 500, color: token.colorText }}>
                {actualTimeRange}
              </div>
            </div>
          </div>
        )}

        {/* 紧凑模式的时间显示 */}
        {compact && (
          <Row gutter={8}>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 11 }}>开放：</Text>
              <Text style={{ fontSize: 12, color: token.colorSuccess }}>{openOffset}</Text>
            </Col>
            <Col span={12}>
              <Text type="secondary" style={{ fontSize: 11 }}>截止：</Text>
              <Text style={{ fontSize: 12, color: token.colorWarning }}>{closeOffset}</Text>
            </Col>
          </Row>
        )}

        {/* 友好描述 */}
        {!compact && friendlyDescriptions.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {friendlyDescriptions.map((desc, index) => (
              <div key={index} style={{ fontSize: 13, color: token.colorTextSecondary, marginBottom: 4 }}>
                • {desc}
              </div>
            ))}
          </div>
        )}

        {/* 失败策略 */}
        {!compact && (
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>
              失败策略：
              {window.failPolicy === 'REJECT' && '拒绝操作'}
              {window.failPolicy === 'ALLOW_WITH_TAG' && `允许并打标签: ${window.failTag || '无'}`}
              {window.failPolicy === 'AUTO_TO_WAITLIST' && '自动进入候补'}
            </Text>
          </div>
        )}
      </Space>
    </Card>
  );
};

export default React.memo(WindowTimelineCard);
