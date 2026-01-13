/**
 * 规则组侧边抽屉预览组件
 * 用于列表页查看规则组详情
 */

import React from 'react';
import { Drawer, Space, Typography, Tag, Divider, Collapse } from 'antd';
import type { RuleSet } from '@hospital/shared';
import RuleSetSummaryCard from './RuleSetSummaryCard';
import RuleSetTimeline from './RuleSetTimeline';

const { Title, Text } = Typography;

// ==================== 类型定义 ====================

export interface RuleSetPreviewDrawerProps {
  open: boolean;
  onClose: () => void;
  ruleSet: Partial<RuleSet> | null;
  width?: number;
}

// ==================== 子组件 ====================

/**
 * 策略详情展示组件
 */
interface PolicyDetailsProps {
  ruleSet: Partial<RuleSet>;
}

const PolicyDetails: React.FC<PolicyDetailsProps> = ({ ruleSet }) => {
  const { bookingPolicy, checkinPolicy, capacityPolicy } = ruleSet;

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {/* 预约策略 */}
      {bookingPolicy && (
        <div>
          <Text strong>预约策略</Text>
          <div style={{ marginTop: 8, padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '6px' }}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <div>
                <Text type="secondary">前置条件：</Text>
                <div style={{ marginLeft: 12 }}>
                  {bookingPolicy.requireAuth && <Tag color="blue">需要登录</Tag>}
                  {bookingPolicy.requirePatientProfileComplete && <Tag color="blue">需要完整档案</Tag>}
                </div>
              </div>
              <div>
                <Text type="secondary">限约配置：</Text>
                <div style={{ marginLeft: 12 }}>
                  <Text>每班次限约 {bookingPolicy.perUserPerShift} 次</Text>
                  {bookingPolicy.perUserPerDay && <Text>，每天限约 {bookingPolicy.perUserPerDay} 次</Text>}
                  {bookingPolicy.perUserPerWeek && <Text>，每周限约 {bookingPolicy.perUserPerWeek} 次</Text>}
                </div>
              </div>
              <div>
                <Text type="secondary">冲突处理：</Text>
                <div style={{ marginLeft: 12 }}>
                  <div>
                    同班次冲突：
                    <Tag color={bookingPolicy.conflictSameShift === 'REJECT' ? 'red' : 'green'}>
                      {bookingPolicy.conflictSameShift === 'REJECT' ? '拒绝' : '替换'}
                    </Tag>
                  </div>
                  <div>
                    时间重叠：
                    <Tag color={bookingPolicy.conflictOverlapTime === 'REJECT' ? 'red' : 'green'}>
                      {bookingPolicy.conflictOverlapTime === 'REJECT' ? '拒绝' : '允许'}
                    </Tag>
                  </div>
                  <div>
                    同类型同日：
                    <Tag color={bookingPolicy.conflictSameTypeSameDay === 'REJECT' ? 'red' : 'green'}>
                      {bookingPolicy.conflictSameTypeSameDay === 'REJECT' ? '拒绝' : '允许'}
                    </Tag>
                  </div>
                </div>
              </div>
            </Space>
          </div>
        </div>
      )}

      {/* 签到策略 */}
      {checkinPolicy && (
        <div>
          <Text strong>签到策略</Text>
          <div style={{ marginTop: 8, padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '6px' }}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <div>
                <Text type="secondary">前置条件：</Text>
                <div style={{ marginLeft: 12 }}>
                  {checkinPolicy.requireBooking && <Tag color="green">必须预约</Tag>}
                  {checkinPolicy.allowOnsiteBooking && <Tag color="orange">允许现场预约</Tag>}
                  {checkinPolicy.auditLog && <Tag color="blue">记录日志</Tag>}
                </div>
              </div>
              <div>
                <Text type="secondary">签到限制：</Text>
                <div style={{ marginLeft: 12 }}>
                  <Text>最多签到 {checkinPolicy.maxTimes} 次</Text>
                  {checkinPolicy.gracePeriodSec > 0 && (
                    <Text>，宽限期 {Math.floor(checkinPolicy.gracePeriodSec / 60)} 分钟</Text>
                  )}
                </div>
              </div>
              <div>
                <Text type="secondary">超时处理：</Text>
                <div style={{ marginLeft: 12 }}>
                  <Tag color="volcano">
                    {checkinPolicy.noCheckinAfterClose === 'KEEP_BOOKED' && '保持预约'}
                    {checkinPolicy.noCheckinAfterClose === 'AUTO_CANCEL' && '自动取消'}
                    {checkinPolicy.noCheckinAfterClose === 'ABSENT' && '标记为爽约'}
                  </Tag>
                </div>
              </div>
            </Space>
          </div>
        </div>
      )}

      {/* 容量策略 */}
      {capacityPolicy && (
        <div>
          <Text strong>容量策略</Text>
          <div style={{ marginTop: 8, padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '6px' }}>
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <div>
                <Text type="secondary">基础容量：</Text>
                <div style={{ marginLeft: 12 }}>
                  <Text>总容量 {capacityPolicy.totalCapacity} 人，每人限约 {capacityPolicy.perUserCapacity} 个</Text>
                </div>
              </div>
              <div>
                <Text type="secondary">候补配置：</Text>
                <div style={{ marginLeft: 12 }}>
                  {capacityPolicy.waitlistEnabled ? (
                    <>
                      <Tag color="cyan">启用候补</Tag>
                      <Text>队列大小 {capacityPolicy.waitlistMaxSize}</Text>
                    </>
                  ) : (
                    <Tag>未启用候补</Tag>
                  )}
                </div>
              </div>
              <div>
                <Text type="secondary">超额预约：</Text>
                <div style={{ marginLeft: 12 }}>
                  {capacityPolicy.overbookingEnabled ? (
                    <>
                      <Tag color="orange">允许超额</Tag>
                      <Text>最多 {capacityPolicy.overbookingMax} 人</Text>
                    </>
                  ) : (
                    <Tag>不允许超额</Tag>
                  )}
                </div>
              </div>
            </Space>
          </div>
        </div>
      )}
    </Space>
  );
};

// ==================== 主组件 ====================

/**
 * 规则组预览抽屉组件
 */
const RuleSetPreviewDrawer: React.FC<RuleSetPreviewDrawerProps> = ({
  open,
  onClose,
  ruleSet,
  width = 600,
}) => {
  if (!ruleSet) return null;

  return (
    <Drawer
      title={
        <Space>
          <span>{ruleSet.name}</span>
          {ruleSet.priority && <Tag color="blue">优先级 {ruleSet.priority}</Tag>}
          {ruleSet.enabled !== undefined && (
            <Tag color={ruleSet.enabled ? 'success' : 'default'}>
              {ruleSet.enabled ? '启用' : '禁用'}
            </Tag>
          )}
        </Space>
      }
      placement="right"
      open={open}
      onClose={onClose}
      width={width}
      styles={{ body: { padding: '16px 24px' } }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 规则摘要 */}
        <RuleSetSummaryCard ruleSet={ruleSet} variant="default" />

        <Divider />

        {/* 时间窗可视化 */}
        <div>
          <Title level={5}>时间窗配置</Title>
          {ruleSet.windows && ruleSet.windows.length > 0 ? (
            <RuleSetTimeline windows={ruleSet.windows} direction="vertical" />
          ) : (
            <Text type="secondary">暂无时间窗配置</Text>
          )}
        </div>

        <Divider />

        {/* 策略详情 */}
        <div>
          <Title level={5}>策略详情</Title>
          <PolicyDetails ruleSet={ruleSet} />
        </div>

        {/* 其他信息 */}
        {ruleSet.description && (
          <>
            <Divider />
            <div>
              <Title level={5}>描述</Title>
              <Text type="secondary">{ruleSet.description}</Text>
            </div>
          </>
        )}

        {/* 适用班次类型 */}
        {ruleSet.shiftTypes && ruleSet.shiftTypes.length > 0 && (
          <>
            <Divider />
            <div>
              <Title level={5}>适用班次类型</Title>
              <Space wrap>
                {ruleSet.shiftTypes.map((shiftType) => (
                  <Tag key={shiftType.id} color="geekblue">
                    {shiftType.name}
                  </Tag>
                ))}
              </Space>
            </div>
          </>
        )}
      </Space>
    </Drawer>
  );
};

export default RuleSetPreviewDrawer;
