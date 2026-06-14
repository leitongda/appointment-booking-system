/** 低代码 Schema 运行时渲染器 */

import React, { useContext, createContext } from 'react';
import { View, Text, Image, Swiper, SwiperItem, Input, Textarea, Switch, Picker } from '@tarojs/components';
import Taro from '@tarojs/taro';
import type { LowCodeNode, PageDataSource, EventHandler, EventAction, LinkageRule } from '@hospital/shared';
import { DataProvider, useLowCodeData, type LowCodeDataContextValue } from './DataProvider';
import { executeLinkageRules } from './data-manager';

interface LowCodeRendererProps {
  schema: LowCodeNode;
}

// ---------------------------------------------------------------------------
// 节点级上下文: 为循环渲染提供 item/index 变量覆盖
// ---------------------------------------------------------------------------

interface NodeContextValue {
  /** 当前循环项 (仅在 loop 渲染内有效) */
  item?: any;
  /** 当前循环索引 (仅在 loop 渲染内有效) */
  index?: number;
  /** 循环变量名 (默认 "item") */
  itemName?: string;
  /** 循环索引变量名 (默认 "index") */
  indexName?: string;
}

const NodeContext = createContext<NodeContextValue>({});

/** 获取节点级上下文 (循环 item/index) */
function useNodeContext(): NodeContextValue {
  return useContext(NodeContext);
}

// ---------------------------------------------------------------------------
// 辅助: 注入循环变量到表达式
// ---------------------------------------------------------------------------

/**
 * 将表达式中的 {{item}} / {{item.xxx}} / {{index}} (或自定义变量名) 替换为实际值。
 * 返回替换后的表达式字符串。
 */
function injectLoopVariables(
  expr: string,
  nodeCtx: NodeContextValue,
): string {
  if (nodeCtx.item === undefined && nodeCtx.index === undefined) return expr;

  const itemName = nodeCtx.itemName || 'item';
  const indexName = nodeCtx.indexName || 'index';

  let result = expr;

  // 替换 {{item}} -> 实际值的 JSON
  if (nodeCtx.item !== undefined) {
    const itemPattern = new RegExp(`\\{\\{${itemName}\\}\\}`, 'g');
    const itemPathPattern = new RegExp(`\\{\\{${itemName}\\.([^}]+)\\}\\}`, 'g');
    result = result.replace(itemPattern, JSON.stringify(nodeCtx.item));
    result = result.replace(itemPathPattern, (_, path: string) => {
      const val = path.split('.').reduce((o: any, k: string) => o?.[k], nodeCtx.item);
      return val !== undefined ? JSON.stringify(val) : 'undefined';
    });
  }

  // 替换 {{index}} -> 实际索引值
  if (nodeCtx.index !== undefined) {
    const indexPattern = new RegExp(`\\{\\{${indexName}\\}\\}`, 'g');
    result = result.replace(indexPattern, String(nodeCtx.index));
  }

  return result;
}

// ---------------------------------------------------------------------------
// 辅助: 安全获取 DataProvider 上下文 (允许无 Provider 时返回 null)
// ---------------------------------------------------------------------------

/**
 * 尝试获取 LowCodeDataContext，如果不在 Provider 内则返回 null。
 * 这保证了无 dataSources 的旧页面仍能正常渲染。
 */
function useOptionalLowCodeData(): LowCodeDataContextValue | null {
  try {
    // useLowCodeData 在无 Provider 时会抛错，这里捕获并返回 null
    return useLowCodeData();
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// 辅助: 解析 props (应用 dataBinding)
// ---------------------------------------------------------------------------

/**
 * 将节点的静态 props 与 dataBinding 表达式合并。
 * 若节点无 dataBinding 或无 DataProvider 上下文，则原样返回静态 props。
 */
function resolveProps(
  node: LowCodeNode,
  dataCtx: LowCodeDataContextValue | null,
  nodeCtx: NodeContextValue,
): Record<string, any> {
  const { props, dataBinding } = node;

  if (!dataBinding?.bindings || !dataCtx) {
    return props;
  }

  // 构建求值上下文: 将 item/index 注入到表达式作用域
  const resolved: Record<string, any> = { ...props };
  for (const [key, expr] of Object.entries(dataBinding.bindings)) {
    if (typeof expr === 'string' && expr.includes('{{')) {
      try {
        // 注入循环变量 (item/index) 到表达式, 然后求值
        const resolvedExpr = injectLoopVariables(expr, nodeCtx);
        const innerExpr = resolvedExpr.replace(/^\{\{|\}\}$/g, '');
        resolved[key] = dataCtx.evaluate(innerExpr);
      } catch {
        // 求值失败时保留静态值
      }
    }
  }
  return resolved;
}

// ---------------------------------------------------------------------------
// 辅助: 绑定事件处理器
// ---------------------------------------------------------------------------

/**
 * 为节点创建事件处理函数映射。
 * 将 EventHandler[] 转换为 { onClick: () => ..., onLongPress: () => ... } 形式。
 * 事件处理完成后自动执行节点的联动规则。
 */
function bindEvents(
  events: EventHandler[] | undefined,
  dataCtx: LowCodeDataContextValue | null,
  linkageRules?: LinkageRule[],
): Record<string, () => void> {
  if (!events || events.length === 0) return {};

  const handlers: Record<string, () => void> = {};

  for (const handler of events) {
    const { event, actions } = handler;

    const executeActions = () => {
      for (const action of actions) {
        executeAction(action, dataCtx);
      }

      // 执行联动规则
      if (linkageRules && linkageRules.length > 0 && dataCtx) {
        executeLinkageRules(linkageRules, dataCtx.state, (updates) => {
          for (const [k, v] of Object.entries(updates)) {
            dataCtx.setData(k, v);
          }
        });
      }
    };

    // 映射事件名到 Taro 事件属性
    const eventKey = mapEventName(event);
    if (eventKey) {
      // 同一事件有多个 handler 时合并
      const prev = handlers[eventKey];
      handlers[eventKey] = prev
        ? () => { prev(); executeActions(); }
        : executeActions;
    }
  }

  return handlers;
}

/** 将低代码事件名映射为 Taro 组件事件属性名 */
function mapEventName(event: string): string | null {
  const map: Record<string, string> = {
    click: 'onClick',
    tap: 'onClick',
    longpress: 'onLongPress',
    change: 'onChange',
    submit: 'onSubmit',
    focus: 'onFocus',
    blur: 'onBlur',
  };
  return map[event.toLowerCase()] || null;
}

/** 执行单个事件动作 */
function executeAction(
  action: EventAction,
  dataCtx: LowCodeDataContextValue | null,
): void {
  const { type, payload } = action;

  switch (type) {
    case 'navigate': {
      const url = payload.url || payload.path;
      if (url) {
        Taro.navigateTo({ url }).catch(() => {
          // navigateTo 失败时尝试 redirectTo (可能是 tab 页)
          Taro.redirectTo({ url });
        });
      }
      break;
    }

    case 'showToast': {
      Taro.showToast({
        title: payload.title || payload.message || '',
        icon: payload.icon || 'none',
        duration: payload.duration || 2000,
      });
      break;
    }

    case 'updateVariable': {
      if (dataCtx && payload.key) {
        dataCtx.setData(payload.key, payload.value);
      }
      break;
    }

    case 'setData': {
      if (dataCtx && payload.key) {
        dataCtx.setData(payload.key, payload.value);
      }
      break;
    }

    case 'fetchApi': {
      if (dataCtx && payload.dataSourceId) {
        dataCtx.fetchDataSource(payload.dataSourceId);
      }
      break;
    }

    default:
      console.warn(`[LowCodeRenderer] 未知事件动作类型: ${type}`);
  }
}

// ---------------------------------------------------------------------------
// 节点渲染器
// ---------------------------------------------------------------------------

/** 单个节点渲染 */
function NodeRenderer({ node }: { node: LowCodeNode }) {
  const { componentName } = node;

  // 获取数据上下文 (可能为 null -- 向后兼容)
  const dataCtx = useOptionalLowCodeData();
  const nodeCtx = useNodeContext();

  // ---- 1. 条件渲染: visible ----
  if (node.visible && dataCtx) {
    try {
      const visExpr = injectLoopVariables(node.visible, nodeCtx);
      const innerExpr = visExpr.replace(/^\{\{|\}\}$/g, '');
      const visible = dataCtx.evaluate(innerExpr);
      if (!visible) return null;
    } catch {
      // 求值失败时默认可见
    }
  }

  // ---- 2. 解析 props (数据绑定) ----
  const resolvedProps = resolveProps(node, dataCtx, nodeCtx);

  // ---- 3. 绑定事件 ----
  const allEvents = [...(node.events || []), ...(node.dataBinding?.events || [])];
  const eventHandlers = bindEvents(allEvents, dataCtx, node.linkageRules);

  // ---- 4. 循环渲染 ----
  if (node.loop && dataCtx) {
    return <LoopRenderer node={node} resolvedProps={resolvedProps} eventHandlers={eventHandlers} />;
  }

  // ---- 5. 正常渲染 ----
  return (
    <ComponentRenderer
      componentName={componentName}
      resolvedProps={resolvedProps}
      eventHandlers={eventHandlers}
      node={node}
    />
  );
}

// ---------------------------------------------------------------------------
// 循环渲染器
// ---------------------------------------------------------------------------

interface LoopRendererProps {
  node: LowCodeNode;
  resolvedProps: Record<string, any>;
  eventHandlers: Record<string, () => void>;
}

function LoopRenderer({ node, resolvedProps, eventHandlers }: LoopRendererProps) {
  const dataCtx = useOptionalLowCodeData();
  if (!dataCtx || !node.loop) return null;

  const { dataSource, itemName = 'item', indexName = 'index' } = node.loop;

  // 求值获取数组数据
  let list: any[] = [];
  try {
    const innerExpr = dataSource.replace(/^\{\{|\}\}$/g, '');
    const result = dataCtx.evaluate(innerExpr);
    if (Array.isArray(result)) {
      list = result;
    } else if (result?.data && Array.isArray(result.data)) {
      // 兼容 apiData.xxx.data 格式
      list = result.data;
    }
  } catch {
    return null;
  }

  if (list.length === 0) return null;

  return (
    <>
      {list.map((item, index) => (
        <NodeContext.Provider key={`${node.id}-${index}`} value={{ item, index, itemName, indexName }}>
          <ComponentRenderer
            componentName={node.componentName}
            resolvedProps={resolvedProps}
            eventHandlers={eventHandlers}
            node={node}
            loopItem={item}
            loopIndex={index}
          />
        </NodeContext.Provider>
      ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// 组件渲染器 (实际的 Taro 组件映射)
// ---------------------------------------------------------------------------

interface ComponentRendererProps {
  componentName: string;
  resolvedProps: Record<string, any>;
  eventHandlers: Record<string, () => void>;
  node: LowCodeNode;
  loopItem?: any;
  loopIndex?: number;
}

function ComponentRenderer({
  componentName,
  resolvedProps,
  eventHandlers,
  node,
}: ComponentRendererProps) {
  const { children } = node;
  const props = resolvedProps;

  switch (componentName) {
    case 'Page':
      return (
        <View className="lowcode-page">
          {children?.map((child) => (
            <NodeRenderer key={child.id} node={child} />
          ))}
        </View>
      );

    case 'NutView':
    case 'View':
      return (
        <View
          style={{
            padding: props.padding,
            margin: props.margin,
            backgroundColor: props.backgroundColor,
            borderRadius: props.borderRadius,
          }}
          {...eventHandlers}
        >
          {children?.map((child) => (
            <NodeRenderer key={child.id} node={child} />
          ))}
        </View>
      );

    case 'NutText':
    case 'Text':
      return (
        <Text
          style={{
            fontSize: props.fontSize,
            color: props.color,
            fontWeight: props.fontWeight,
            textAlign: props.textAlign,
          }}
          {...eventHandlers}
        >
          {props.text || ''}
        </Text>
      );

    case 'NutImage':
    case 'Image':
      return (
        <Image
          src={props.src || ''}
          style={{
            width: props.width,
            height: props.height,
            objectFit: props.fit,
            borderRadius: props.borderRadius,
          }}
          mode={props.fit === 'cover' ? 'aspectFill' : 'widthFix'}
          {...eventHandlers}
        />
      );

    case 'NutButton':
      return (
        <View
          className={`nut-button nut-button--${props.type || 'primary'} ${props.block ? 'nut-button--block' : ''}`}
          {...eventHandlers}
        >
          <Text>{props.text || '按钮'}</Text>
        </View>
      );

    case 'NutDivider':
      return <View className="nut-divider" />;

    case 'NutSwiper':
      return (
        <Swiper
          className="nut-swiper"
          style={{ height: props.height || '200px' }}
          autoplay={props.autoPlay > 0}
          circular={props.loop}
          indicatorDots={props.pagination}
        >
          {children?.map((child) => (
            <SwiperItem key={child.id}>
              <NodeRenderer node={child} />
            </SwiperItem>
          ))}
        </Swiper>
      );

    case 'NutSwiperItem':
      return (
        <View>
          {children?.map((child) => (
            <NodeRenderer key={child.id} node={child} />
          ))}
        </View>
      );

    case 'NutCell':
      return (
        <View
          className="nut-cell"
          {...eventHandlers}
        >
          <View className="nut-cell__title">
            <Text>{props.title || ''}</Text>
          </View>
          {props.description && (
            <View className="nut-cell__description">
              <Text>{props.description}</Text>
            </View>
          )}
          {props.isLink && <View className="nut-cell__right" />}
        </View>
      );

    case 'NutCard':
      return (
        <View className="nut-card" {...eventHandlers}>
          <View className="nut-card__header">
            <Text className="nut-card__title">{props.title || ''}</Text>
            {props.subTitle && (
              <Text className="nut-card__sub-title">{props.subTitle}</Text>
            )}
          </View>
          {props.description && (
            <View className="nut-card__content">
              <Text>{props.description}</Text>
            </View>
          )}
          {children && children.length > 0 && (
            <View className="nut-card__body">
              {children.map((child) => (
                <NodeRenderer key={child.id} node={child} />
              ))}
            </View>
          )}
        </View>
      );

    case 'NutTabs':
      return (
        <View className="nut-tabs">
          {children?.map((child) => (
            <NodeRenderer key={child.id} node={child} />
          ))}
        </View>
      );

    case 'NutTabPane':
      return (
        <View className="nut-tab-pane">
          {children?.map((child) => (
            <NodeRenderer key={child.id} node={child} />
          ))}
        </View>
      );

    case 'NutEmpty':
      return (
        <View className="nut-empty" {...eventHandlers}>
          <Text>{props.description || '暂无数据'}</Text>
        </View>
      );

    case 'NutRow':
      return (
        <View
          className="nut-row"
          style={{
            display: 'flex',
            flexDirection: 'row',
            flexWrap: 'wrap',
          }}
          {...eventHandlers}
        >
          {children?.map((child) => (
            <NodeRenderer key={child.id} node={child} />
          ))}
        </View>
      );

    case 'NutCol':
      return (
        <View
          className="nut-col"
          style={{
            width: `${((props.span || 12) / 24) * 100}%`,
            flexShrink: 0,
          }}
          {...eventHandlers}
        >
          {children?.map((child) => (
            <NodeRenderer key={child.id} node={child} />
          ))}
        </View>
      );

    case 'NutInput':
      return (
        <View className="nut-input" style={{ padding: '8px 12px' }} {...eventHandlers}>
          <View style={{ display: 'flex', alignItems: 'center' }}>
            {props.label && (
              <Text style={{ fontSize: 14, color: '#333', minWidth: '60px' }}>
                {props.required && (
                  <Text style={{ color: '#ff4d4f', marginRight: '4px' }}>*</Text>
                )}
                {props.label}
              </Text>
            )}
            <Input
              type="text"
              placeholder={props.placeholder || '请输入'}
              disabled={props.disabled}
              maxlength={props.maxLength > 0 ? props.maxLength : -1}
              style={{
                flex: 1,
                fontSize: '14px',
                textAlign: props.textAlign || 'left',
              }}
            />
          </View>
        </View>
      );

    case 'NutTextarea':
      return (
        <View className="nut-textarea" style={{ padding: '8px 12px' }} {...eventHandlers}>
          {props.label && (
            <View style={{ marginBottom: '4px' }}>
              <Text style={{ fontSize: 14, color: '#333' }}>
                {props.required && (
                  <Text style={{ color: '#ff4d4f', marginRight: '4px' }}>*</Text>
                )}
                {props.label}
              </Text>
            </View>
          )}
          <Textarea
            placeholder={props.placeholder || '请输入'}
            disabled={props.disabled}
            maxlength={props.maxLength > 0 ? props.maxLength : -1}
            autoHeight={props.autosize}
            style={{
              width: '100%',
              fontSize: '14px',
              minHeight: `${(props.rows || 3) * 24}px`,
            }}
          />
        </View>
      );

    case 'NutSwitch':
      return (
        <View className="nut-switch" style={{ padding: '8px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }} {...eventHandlers}>
          {props.label && (
            <Text style={{ fontSize: 14, color: '#333' }}>{props.label}</Text>
          )}
          <View style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {props.activeText && (
              <Text style={{ fontSize: 12, color: '#333' }}>{props.activeText}</Text>
            )}
            <Switch
              checked={props.checked}
              disabled={props.disabled}
              color="#1677ff"
            />
            {props.inactiveText && (
              <Text style={{ fontSize: 12, color: '#999' }}>{props.inactiveText}</Text>
            )}
          </View>
        </View>
      );

    case 'NutPicker':
      return (
        <View className="nut-picker" style={{ padding: '8px 12px' }} {...eventHandlers}>
          <View style={{ display: 'flex', alignItems: 'center' }}>
            {props.label && (
              <Text style={{ fontSize: 14, color: '#333', minWidth: '60px' }}>
                {props.required && (
                  <Text style={{ color: '#ff4d4f', marginRight: '4px' }}>*</Text>
                )}
                {props.label}
              </Text>
            )}
            <Picker
              mode="selector"
              range={props.columns || []}
              disabled={props.disabled}
            >
              <View
                style={{
                  flex: 1,
                  height: '32px',
                  border: '1px solid #e5e5e5',
                  borderRadius: '4px',
                  padding: '0 8px',
                  fontSize: 14,
                  color: '#999',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <Text>{props.placeholder || '请选择'}</Text>
                <Text style={{ fontSize: 12, color: '#ccc' }}>▼</Text>
              </View>
            </Picker>
          </View>
        </View>
      );

    case 'NutForm':
      return (
        <View
          className="nut-form"
          style={{
            padding: props.border ? '12px' : '8px 0',
            border: props.border ? '1px solid #e5e5e5' : 'none',
            borderRadius: props.border ? '4px' : 0,
          }}
          {...eventHandlers}
        >
          {children?.map((child) => (
            <NodeRenderer key={child.id} node={child} />
          ))}
        </View>
      );

    default:
      return (
        <View className={`lowcode-${componentName.toLowerCase()}`} {...eventHandlers}>
          {children?.map((child) => (
            <NodeRenderer key={child.id} node={child} />
          ))}
        </View>
      );
  }
}

// ---------------------------------------------------------------------------
// 低代码渲染器入口
// ---------------------------------------------------------------------------

/**
 * 低代码 Schema 运行时渲染器。
 *
 * 支持:
 * - 数据绑定 (node.dataBinding) -- 属性表达式自动求值
 * - 条件渲染 (node.visible) -- 表达式为 falsy 时隐藏节点
 * - 列表渲染 (node.loop) -- 按数据源数组重复渲染
 * - 事件处理 (node.events) -- navigate / showToast / updateVariable / fetchApi
 * - 向后兼容: 无 dataSources / dataBinding 的旧页面渲染行为不变
 */
export const LowCodeRenderer: React.FC<LowCodeRendererProps> = ({ schema }) => {
  if (!schema) return null;

  // 页面级: 如果 schema 包含 dataSources / state 则用 DataProvider 包裹
  const pageProps = schema.props || {};
  const pageDataSources: PageDataSource[] =
    (schema as any).dataSources || pageProps.dataSources || [];
  const pageStateSchema: Record<string, any> | undefined =
    (schema as any).state || pageProps.state || undefined;

  // 有数据源定义时包裹 DataProvider, 否则直接渲染 (向后兼容)
  if (pageDataSources.length > 0 || pageStateSchema) {
    const pageParams = Taro.getCurrentInstance()?.router?.params || {};
    return (
      <DataProvider
        dataSources={pageDataSources}
        stateSchema={pageStateSchema}
        pageParams={pageParams}
      >
        <NodeRenderer node={schema} />
      </DataProvider>
    );
  }

  return <NodeRenderer node={schema} />;
};

export default LowCodeRenderer;
