/**
 * 规则组摘要卡片组件
 * 生成易读的规则摘要展示
 */

import React, { useMemo } from 'react';
import { Card, Space, Typography, Tag, Descriptions, Collapse } from 'antd';
import type { RuleSet } from '@hospital/shared';
import { generateRuleSummary, generateShortSummary } from '@/utils/ruleSetFormatter';

const { Text, Paragraph } = Typography;

// ==================== 类型定义 ====================

export interface RuleSetSummaryCardProps {
  ruleSet: Partial<RuleSet>;
  variant?: 'default' | 'compact';
}

// ==================== 主组件 ====================

/**
 * 规则组摘要卡片组件
 */
const RuleSetSummaryCard: React.FC<RuleSetSummaryCardProps> = ({
  ruleSet,
  variant = 'default',
}) => {
  // 生成摘要数据
  const summary = useMemo(() => generateRuleSummary(ruleSet), [ruleSet]);
  const shortSummary = useMemo(() => generateShortSummary(ruleSet), [ruleSet]);

  // 紧凑模式：只显示一行摘要
  if (variant === 'compact') {
    return (
      <Card size="small" styles={{ body: { padding: '12px 16px' } }}>
        <Space size="small" style={{ width: '100%' }}>
          <div>
            <Text strong>{ruleSet.name}</Text>
            {ruleSet.priority && (
              <Tag color="blue" style={{ marginLeft: 8 }}>
                优先级 {ruleSet.priority}
              </Tag>
            )}
            {ruleSet.enabled !== undefined && (
              <Tag color={ruleSet.enabled ? 'success' : 'default'}>
                {ruleSet.enabled ? '启用' : '禁用'}
              </Tag>
            )}
          </div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {shortSummary}
          </Text>
        </Space>
      </Card>
    );
  }

  // 默认模式：完整摘要
  return (
    <Card
      title={
        <Space>
          <span>规则摘要</span>
          {ruleSet.enabled !== undefined && (
            <Tag color={ruleSet.enabled ? 'success' : 'default'}>
              {ruleSet.enabled ? '启用' : '禁用'}
            </Tag>
          )}
        </Space>
      }
      size="small"
    >
      <Space style={{ width: '100%' }} size="middle">
        {/* 短摘要 */}
        {shortSummary && (
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: '#f6ffed',
              borderLeft: '3px solid #52c41a',
              borderRadius: '4px',
            }}
          >
            <Text strong>核心规则：</Text>
            <Text>{shortSummary}</Text>
          </div>
        )}

        {/* 基础信息 */}
        {summary.basic.length > 0 && (
          <Descriptions size="small" column={1} items={summary.basic.map((item, index) => ({
            key: String(index),
            label: '',
            children: item,
          }))} />
        )}

        {/* 时间窗摘要 */}
        {summary.windows.length > 0 && (
          <Collapse
            size="small"
            ghost
            items={[
              {
                key: 'windows',
                label: <Text strong>时间窗配置</Text>,
                children: (
                  <Space size="small" style={{ width: '100%' }}>
                    {summary.windows.map((item, index) => (
                      <div key={index} style={{ paddingLeft: 12 }}>
                        <Text type="secondary">• </Text>
                        <Text>{item}</Text>
                      </div>
                    ))}
                  </Space>
                ),
              },
            ]}
            defaultActiveKey={['windows']}
          />
        )}

        {/* 策略详情 */}
        <Collapse
          size="small"
          ghost
          items={[
            // 预约策略
            ...(summary.policies.booking && summary.policies.booking.length > 0
              ? [
                  {
                    key: 'booking',
                    label: <Text strong>预约策略</Text>,
                    children: (
                      <Space size="small" style={{ width: '100%' }}>
                        {summary.policies.booking!.map((item, index) => (
                          <div key={index}>
                            <Text>{item}</Text>
                          </div>
                        ))}
                      </Space>
                    ),
                  },
                ]
              : []),
            // 签到策略
            ...(summary.policies.checkin && summary.policies.checkin.length > 0
              ? [
                  {
                    key: 'checkin',
                    label: <Text strong>签到策略</Text>,
                    children: (
                      <Space size="small" style={{ width: '100%' }}>
                        {summary.policies.checkin!.map((item, index) => (
                          <div key={index}>
                            <Text>{item}</Text>
                          </div>
                        ))}
                      </Space>
                    ),
                  },
                ]
              : []),
            // 容量策略
            ...(summary.policies.capacity && summary.policies.capacity.length > 0
              ? [
                  {
                    key: 'capacity',
                    label: <Text strong>容量策略</Text>,
                    children: (
                      <Space size="small" style={{ width: '100%' }}>
                        {summary.policies.capacity!.map((item, index) => (
                          <div key={index}>
                            <Text>{item}</Text>
                          </div>
                        ))}
                      </Space>
                    ),
                  },
                ]
              : []),
          ]}
        />
      </Space>
    </Card>
  );
};

export default React.memo(RuleSetSummaryCard);
