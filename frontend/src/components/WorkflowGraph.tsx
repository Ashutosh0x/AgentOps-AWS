import { useCallback, useEffect } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  NodeTypes,
  ConnectionMode,
  Panel,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from 'reactflow'
import 'reactflow/dist/style.css'
import {
  Play,
  Brain,
  Settings,
  Activity,
  Database,
  FileText,
  Code,
  Bookmark,
  Check,
  X,
  Sun,
  RefreshCw,
  Clock,
} from 'lucide-react'
import { getStatusColor, getStatusIcon } from '../lib/workflowTransform'

interface WorkflowGraphProps {
  nodes: Node[]
  edges: Edge[]
  selectedNodeId: string | null
  onNodeSelect: (nodeId: string | null) => void
  planId: string | null
}

// Custom Start Node
function StartNode({ data }: { data: any }) {
  const isCompleted = data.status === 'completed'
  return (
    <div
      className={`px-6 py-4 rounded-lg shadow-lg border-2 ${
        isCompleted
          ? 'bg-green-500 border-green-600'
          : 'bg-green-400 border-green-500'
      } text-white`}
    >
      <Handle type="source" position={Position.Right} id="source-right" />
      <div className="flex items-center space-x-2">
        <Play className="w-5 h-5" />
        <span className="font-semibold text-lg">{data.label}</span>
        {isCompleted && (
          <div className="ml-auto">
            <Check className="w-5 h-5" />
          </div>
        )}
      </div>
    </div>
  )
}

// Custom Agent Node
function AgentNode({ data, selected }: { data: any; selected: boolean }) {
  const status = data.status || 'pending'
  const statusColor = getStatusColor(status)
  const statusIcon = getStatusIcon(status)
  
  const iconMap: Record<string, any> = {
    brain: Brain,
    settings: Settings,
    activity: Activity,
    database: Database,
  }
  
  const IconComponent = iconMap[data.icon] || Brain
  
  const statusIconMap: Record<string, any> = {
    check: Check,
    sun: Sun,
    x: X,
    refresh: RefreshCw,
    clock: Clock,
  }
  
  const StatusIcon = statusIconMap[statusIcon] || Clock
  
  return (
    <div
      className={`px-6 py-4 rounded-lg shadow-lg border-2 min-w-[200px] ${
        selected ? 'ring-2 ring-blue-500 ring-offset-2' : ''
      } ${
        status === 'completed'
          ? 'bg-green-50 dark:bg-green-900/20 border-green-500'
          : status === 'failed'
          ? 'bg-red-50 dark:bg-red-900/20 border-red-500'
          : status === 'executing'
          ? 'bg-orange-50 dark:bg-orange-900/20 border-orange-500'
          : 'bg-gray-50 dark:bg-gray-800 border-gray-300 dark:border-gray-600'
      }`}
      style={{ borderColor: status !== 'pending' ? statusColor : undefined }}
    >
      <Handle type="target" position={Position.Left} id="target-left" />
      <Handle type="target" position={Position.Bottom} id="target-bottom" />
      <Handle type="source" position={Position.Right} id="source-right" />
      <div className="flex items-start space-x-3">
        <div
          className="p-2 rounded-lg"
          style={{
            backgroundColor: data.bgColor || '#f3f4f6',
            color: data.color || '#6b7280',
          }}
        >
          <IconComponent className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm text-gray-900 dark:text-white truncate">
            {data.label}
          </div>
          {data.action && (
            <div className="text-xs text-gray-600 dark:text-gray-400 mt-1 truncate">
              {data.action}
            </div>
          )}
          <div className="flex items-center space-x-2 mt-2">
            <StatusIcon
              className={`w-4 h-4 ${
                status === 'completed'
                  ? 'text-green-600 dark:text-green-400'
                  : status === 'failed'
                  ? 'text-red-600 dark:text-red-400'
                  : status === 'executing'
                  ? 'text-orange-600 dark:text-orange-400 animate-pulse'
                  : 'text-gray-400'
              }`}
            />
            <span
              className="text-xs font-medium capitalize"
              style={{ color: statusColor }}
            >
              {status}
            </span>
            {data.confidence !== undefined && (
              <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
                {(data.confidence * 100).toFixed(0)}% confidence
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Custom Data Source Node
function DataSourceNode({ data }: { data: any }) {
  const iconMap: Record<string, any> = {
    'file-text': FileText,
    bookmark: Bookmark,
    code: Code,
    book: Bookmark,
  }
  
  const IconComponent = iconMap[data.icon] || Database
  
  return (
    <div className="px-4 py-3 rounded-lg shadow-md border-2 border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20 min-w-[150px]">
      <Handle type="source" position={Position.Top} id="source-top" />
      <div className="flex items-center space-x-2">
        <IconComponent className="w-4 h-4 text-blue-600 dark:text-blue-400" />
        <span className="font-medium text-sm text-gray-900 dark:text-white">
          {data.label}
        </span>
      </div>
    </div>
  )
}

// Memoize nodeTypes to avoid recreation warnings
const nodeTypes: NodeTypes = {
  start: StartNode,
  agent: AgentNode,
  dataSource: DataSourceNode,
}

export default function WorkflowGraph({
  nodes: initialNodes,
  edges: initialEdges,
  selectedNodeId,
  onNodeSelect,
  planId,
}: WorkflowGraphProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // Update nodes and edges when props change
  useEffect(() => {
    const nodesWithSelection = initialNodes.map((node) => ({
      ...node,
      selected: node.id === selectedNodeId,
    }))
    setNodes(nodesWithSelection)
    setEdges(initialEdges)
  }, [initialNodes, initialEdges, selectedNodeId, setNodes, setEdges])

  const onNodeClick = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      onNodeSelect(node.id === selectedNodeId ? null : node.id)
    },
    [selectedNodeId, onNodeSelect]
  )

  const onPaneClick = useCallback(() => {
    onNodeSelect(null)
  }, [onNodeSelect])

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        attributionPosition="bottom-left"
      >
        <Background color="#e5e7eb" gap={16} size={1} />
        <Controls />
        <MiniMap
          nodeColor={(node: Node) => {
            const status = node.data?.status || 'pending'
            return getStatusColor(status)
          }}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
        {!planId && (
          <Panel position="top-center" className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 max-w-md">
            <p className="text-sm text-gray-600 dark:text-gray-400 text-center">
              <span className="font-medium">Demo Workflow</span>
              <br />
              Enter a command in the console below to start a real deployment workflow
            </p>
          </Panel>
        )}
      </ReactFlow>
    </div>
  )
}

