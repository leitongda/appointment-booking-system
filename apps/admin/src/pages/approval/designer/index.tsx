import { useCallback, useRef, useState, useEffect } from 'react';
import {
  ReactFlow,
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  type Node,
  type Edge,
  type Connection,
  type NodeTypes,
  ReactFlowProvider,
  useReactFlow,
  type OnConnect,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Button, Space, message, Tag, Typography, Spin, Dropdown } from 'antd';
import {
  SaveOutlined, CheckCircleOutlined, ArrowLeftOutlined,
  LayoutOutlined, ExclamationCircleOutlined,
  UndoOutlined, RedoOutlined, AppstoreOutlined,
} from '@ant-design/icons';
import { history, useParams } from '@umijs/max';
import { approvalFlowApi } from '@hospital/api';
import { StartNode, ApprovalNode, ConditionNode, CcNode, EndNode } from './nodes';
import { ConditionEdge } from './edges';
import NodePanel from './NodePanel';
import PropertyPanel from './PropertyPanel';
import { fromFlowSchema, toFlowSchema } from './utils/transform';
import { validateFlow } from './utils/validate';
import { autoLayout } from './utils/layout';

const { Text } = Typography;

const nodeTypes: NodeTypes = {
  startNode: StartNode,
  approvalNode: ApprovalNode,
  conditionNode: ConditionNode,
  ccNode: CcNode,
  endNode: EndNode,
};

const edgeTypes = {
  conditionEdge: ConditionEdge,
};

const NODE_TYPE_MAP: Record<string, string> = {
  startNode: 'start',
  approvalNode: 'approval',
  conditionNode: 'condition',
  ccNode: 'cc',
  endNode: 'end',
};

const LABEL_MAP: Record<string, string> = {
  startNode: '开始',
  approvalNode: '审批节点',
  conditionNode: '条件判断',
  ccNode: '抄送',
  endNode: '结束',
};


const DesignerPageInner: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const isNew = id === 'new';
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();
  const nodeIdCounterRef = useRef(0);
  const getNodeId = useCallback((type: string) => `${type}_${++nodeIdCounterRef.current}`, []);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(!isNew);
  const [readonly, setReadonly] = useState(false);
  const [flowName, setFlowName] = useState('新流程');
  const [flowDefId, setFlowDefId] = useState<string | null>(isNew ? null : id!);
  const [templates, setTemplates] = useState<any[]>([]);

  // Undo/Redo 历史
  const [undoHistory, setUndoHistory] = useState<{ nodes: Node[]; edges: Edge[] }[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const isUndoRedoRef = useRef(false);

  // 保存历史
  const saveToHistory = useCallback((newNodes: Node[], newEdges: Edge[]) => {
    if (isUndoRedoRef.current) {
      isUndoRedoRef.current = false;
      return;
    }
    setUndoHistory(prev => {
      const truncated = prev.slice(0, historyIndex + 1);
      return [...truncated, { nodes: newNodes, edges: newEdges }];
    });
    setHistoryIndex(prev => prev + 1);
  }, [historyIndex]);

  // Undo/Redo 函数
  const undo = useCallback(() => {
    if (historyIndex <= 0) return;
    isUndoRedoRef.current = true;
    const prev = undoHistory[historyIndex - 1];
    setNodes(prev.nodes);
    setEdges(prev.edges);
    setHistoryIndex(historyIndex - 1);
  }, [undoHistory, historyIndex, setNodes, setEdges]);

  const redo = useCallback(() => {
    if (historyIndex >= undoHistory.length - 1) return;
    isUndoRedoRef.current = true;
    const next = undoHistory[historyIndex + 1];
    setNodes(next.nodes);
    setEdges(next.edges);
    setHistoryIndex(historyIndex + 1);
  }, [undoHistory, historyIndex, setNodes, setEdges]);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          redo();
        } else {
          undo();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo]);

  // 加载模板列表（仅新建时）
  useEffect(() => {
    if (isNew) {
      approvalFlowApi.getTemplates().then(res => setTemplates(res.items || [])).catch(() => {});
    }
  }, [isNew]);

  // 从模板加载到画布
  const handleLoadTemplate = useCallback((tpl: any) => {
    const { nodes: fn, edges: fe } = fromFlowSchema(tpl);
    setNodes(fn);
    setEdges(fe);
    setFlowName(tpl.name);
    const maxId = fn.reduce((max: number, n: Node) => {
      const match = n.id.match(/\d+$/);
      return match ? Math.max(max, parseInt(match[0])) : max;
    }, 0);
    nodeIdCounterRef.current = maxId;
    setUndoHistory([]);
    setHistoryIndex(-1);
    message.success(`已加载模板: ${tpl.name}`);
  }, [setNodes, setEdges]);

  // 加载已有流程
  useEffect(() => {
    if (!isNew && id) {
      setLoading(true);
      approvalFlowApi.getDetail(id).then((data: any) => {
        setFlowName(data.name);
        setFlowDefId(data.id);
        const { nodes: fn, edges: fe } = fromFlowSchema(data);
        setNodes(fn);
        setEdges(fe);
        // 更新 nodeIdCounter 避免冲突
        const maxId = fn.reduce((max: number, n: Node) => {
          const match = n.id.match(/\d+$/);
          return match ? Math.max(max, parseInt(match[0])) : max;
        }, 0);
        nodeIdCounterRef.current = maxId;
      }).catch(() => {
        message.error('加载流程失败');
      }).finally(() => setLoading(false));
    }
  }, [id, isNew, setNodes, setEdges]);

  // 选中节点
  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  // 点击空白取消选中
  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // 连接
  const onConnect: OnConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => {
        const newEdges = addEdge({ ...params, type: 'smoothstep' }, eds);
        setTimeout(() => saveToHistory(nodes, newEdges), 0);
        return newEdges;
      });
    },
    [setEdges, nodes, saveToHistory],
  );

  // 拖拽放置
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      const type = event.dataTransfer.getData('application/reactflow');
      const label = event.dataTransfer.getData('application/label');
      if (!type) return;

      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      const nodeType = NODE_TYPE_MAP[type] || type;
      const newNode: Node = {
        id: getNodeId(nodeType),
        type,
        position,
        data: { label: label || LABEL_MAP[type] || nodeType, nodeType },
      };

      setNodes((nds) => {
        const newNodes = nds.concat(newNode);
        setTimeout(() => saveToHistory(newNodes, edges), 0);
        return newNodes;
      });
    },
    [screenToFlowPosition, setNodes, edges, saveToHistory],
  );

  // 更新节点属性
  const handleUpdateNode = useCallback(
    (nodeId: string, data: Record<string, any>) => {
      setNodes((nds) => {
        const newNodes = nds.map((n) => (n.id === nodeId ? { ...n, data: { ...data } } : n));
        setTimeout(() => saveToHistory(newNodes, edges), 0);
        return newNodes;
      });
      setSelectedNode((prev) => (prev && prev.id === nodeId ? { ...prev, data: { ...data } } : prev));
    },
    [setNodes, edges, saveToHistory],
  );

  // 删除节点
  const handleDeleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => {
        const newNodes = nds.filter((n) => n.id !== nodeId);
        return newNodes;
      });
      setEdges((eds) => {
        const newEdges = eds.filter((e) => e.source !== nodeId && e.target !== nodeId);
        setTimeout(() => {
          setNodes((nds) => {
            saveToHistory(nds, newEdges);
            return nds;
          });
        }, 0);
        return newEdges;
      });
      setSelectedNode(null);
    },
    [setNodes, setEdges, saveToHistory],
  );

  // 自动布局
  const handleAutoLayout = useCallback(() => {
    const laid = autoLayout(nodes, edges);
    setNodes(laid);
    setTimeout(() => saveToHistory(laid, edges), 0);
  }, [nodes, edges, setNodes, saveToHistory]);

  // 包装 onNodesChange 以捕获拖拽结束和删除
  const handleNodesChange: typeof onNodesChange = useCallback((changes) => {
    onNodesChange(changes);
    const hasDragEnd = changes.some((c) => c.type === 'position' && !c.dragging);
    const hasRemove = changes.some((c) => c.type === 'remove');
    if (hasDragEnd || hasRemove) {
      setTimeout(() => saveToHistory(nodes, edges), 0);
    }
  }, [onNodesChange, nodes, edges, saveToHistory]);

  // 包装 onEdgesChange 以捕获删除
  const handleEdgesChange: typeof onEdgesChange = useCallback((changes) => {
    onEdgesChange(changes);
    const hasRemove = changes.some((c) => c.type === 'remove');
    if (hasRemove) {
      setTimeout(() => saveToHistory(nodes, edges), 0);
    }
  }, [onEdgesChange, nodes, edges, saveToHistory]);

  // 校验
  const handleValidate = useCallback(() => {
    const errors = validateFlow(nodes, edges);
    setValidationErrors(errors);
    if (errors.length === 0) {
      message.success('流程校验通过');
    }
    return errors;
  }, [nodes, edges]);

  // 保存
  const handleSave = useCallback(async () => {
    const errors = handleValidate();
    if (errors.length > 0) {
      message.warning('请先修复校验错误');
      return;
    }

    setSaving(true);
    try {
      const { nodes: apiNodes, edges: apiEdges } = toFlowSchema(nodes, edges);

      if (flowDefId) {
        await approvalFlowApi.update(flowDefId, {
          nodes: apiNodes,
          edges: apiEdges,
        });
        message.success('保存成功');
      } else {
        const res = await approvalFlowApi.create({
          name: flowName,
          businessType: 'custom',
          nodes: apiNodes,
          edges: apiEdges,
        });
        setFlowDefId(res.id);
        message.success('创建成功');
      }
    } catch (e: any) {
      message.error(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  }, [nodes, edges, flowDefId, flowName, handleValidate]);

  // 激活
  const handleActivate = useCallback(async () => {
    if (!flowDefId) {
      message.warning('请先保存');
      return;
    }
    try {
      await approvalFlowApi.activate(flowDefId);
      message.success('激活成功');
    } catch (e: any) {
      message.error(e.message || '激活失败');
    }
  }, [flowDefId]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f5f5f5' }}>
      {/* 顶部工具栏 */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '8px 16px', background: '#fff', borderBottom: '1px solid #e8e8e8',
      }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => history.push('/approval/definitions')}>返回</Button>
          <Text strong style={{ fontSize: 16 }}>{flowName}</Text>
          {flowDefId && <Tag color="blue">已保存</Tag>}
        </Space>
        <Space>
          <Button onClick={() => setReadonly(!readonly)}>{readonly ? '编辑模式' : '预览模式'}</Button>
          <Button icon={<UndoOutlined />} onClick={undo} disabled={historyIndex <= 0}>撤销</Button>
          <Button icon={<RedoOutlined />} onClick={redo} disabled={historyIndex >= undoHistory.length - 1}>重做</Button>
          <Button icon={<LayoutOutlined />} onClick={handleAutoLayout}>自动布局</Button>
          <Button icon={<ExclamationCircleOutlined />} onClick={handleValidate}>校验</Button>
          {isNew && templates.length > 0 && (
            <Dropdown
              menu={{
                items: templates.map(tpl => ({
                  key: tpl.id,
                  label: (
                    <div>
                      <div style={{ fontWeight: 500 }}>{tpl.name}</div>
                      <div style={{ fontSize: 12, color: '#999' }}>{tpl.description}</div>
                    </div>
                  ),
                })),
                onClick: ({ key }) => {
                  const tpl = templates.find(t => t.id === key);
                  if (tpl) handleLoadTemplate(tpl);
                },
              }}
            >
              <Button icon={<AppstoreOutlined />}>从模板创建</Button>
            </Dropdown>
          )}
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>保存</Button>
          <Button icon={<CheckCircleOutlined />} style={{ color: '#52c41a', borderColor: '#52c41a' }} onClick={handleActivate}>激活</Button>
        </Space>
      </div>

      {/* 主体区域 */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* 左侧节点面板 */}
        {!readonly && (
          <div style={{ padding: 8, background: '#fff', borderRight: '1px solid #e8e8e8', overflowY: 'auto' }}>
            <NodePanel />
          </div>
        )}

        {/* 中间画布 */}
        <div ref={reactFlowWrapper} style={{ flex: 1 }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={handleNodesChange}
            onEdgesChange={handleEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            nodesDraggable={!readonly}
            nodesConnectable={!readonly}
            elementsSelectable={!readonly}
            fitView
            snapToGrid
            snapGrid={[16, 16]}
            deleteKeyCode={readonly ? null : ['Backspace', 'Delete']}
            multiSelectionKeyCode="Meta"
            defaultEdgeOptions={{ type: 'smoothstep' }}
          >
            <Controls />
            <MiniMap />
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          </ReactFlow>
        </div>

        {/* 右侧属性面板 */}
        {!readonly && (
          <div style={{ padding: 8, background: '#fff', borderLeft: '1px solid #e8e8e8', overflowY: 'auto' }}>
            <PropertyPanel
              selectedNode={selectedNode}
              onUpdate={handleUpdateNode}
              onDelete={handleDeleteNode}
            />
          </div>
        )}
      </div>

      {/* 底部校验错误 */}
      {validationErrors.length > 0 && (
        <div style={{
          padding: '8px 16px', background: '#fff2f0', borderTop: '1px solid #ffccc7',
          maxHeight: 100, overflowY: 'auto',
        }}>
          {validationErrors.map((err, i) => (
            <div key={i} style={{ color: '#ff4d4f', fontSize: 12 }}>
              <ExclamationCircleOutlined style={{ marginRight: 4 }} />{err}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const DesignerPage: React.FC = () => (
  <ReactFlowProvider>
    <DesignerPageInner />
  </ReactFlowProvider>
);

export default DesignerPage;
