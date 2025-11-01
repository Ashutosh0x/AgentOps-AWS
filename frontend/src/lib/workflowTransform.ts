import { Node, Edge, MarkerType } from 'reactflow'

export interface TaskStep {
  step_id: string
  agent_type: string
  action: string
  status: string
  input?: Record<string, any>
  output?: Record<string, any>
  timestamp?: string
  error?: string
  retry_count?: number
  reasoning_chain?: {
    agent_name: string
    context: string
    steps: Array<{
      thought: string
      reasoning: string
      confidence: number
    }>
    overall_confidence?: number
  }
}

export interface ExecutionPlan {
  plan_id: string
  steps: TaskStep[]
  reasoning_chain?: {
    agent_name: string
    context: string
    overall_confidence?: number
  }
  created_at?: string
  updated_at?: string
}

// Agent type colors and labels
const AGENT_CONFIG: Record<string, { label: string; color: string; icon: string; bgColor: string }> = {
  planner: {
    label: 'Command Parser Agent',
    color: '#ec4899',
    bgColor: '#fce7f3',
    icon: 'brain',
  },
  executor: {
    label: 'Technical Agent',
    color: '#14b8a6',
    bgColor: '#ccfbf1',
    icon: 'settings',
  },
  monitor: {
    label: 'Status Agent',
    color: '#f97316',
    bgColor: '#ffedd5',
    icon: 'activity',
  },
  retriever: {
    label: 'Retriever Agent',
    color: '#3b82f6',
    bgColor: '#dbeafe',
    icon: 'database',
  },
}

// Status colors
const STATUS_COLORS: Record<string, string> = {
  completed: '#10b981',
  executing: '#f97316',
  thinking: '#6b7280',
  failed: '#ef4444',
  retrying: '#eab308',
  pending: '#9ca3af',
}

const STATUS_ICONS: Record<string, string> = {
  completed: 'check',
  executing: 'sun',
  failed: 'x',
  retrying: 'refresh',
  thinking: 'brain',
  pending: 'clock',
}

// Data sources (from RAG evidence)
const DATA_SOURCES = [
  { id: 'internal-docs', label: 'Internal Docs', icon: 'file-text' },
  { id: 'intel-sources', label: 'Intel Sources', icon: 'bookmark' },
  { id: 'code-repo', label: 'Code Repository', icon: 'code' },
  { id: 'docs', label: 'Docs', icon: 'book' },
]

export function executionPlanToGraph(
  executionPlan: ExecutionPlan | null,
  _evidence?: Array<{ title?: string; source?: string }>
): { nodes: Node[]; edges: Edge[] } {
  if (!executionPlan || !executionPlan.steps || executionPlan.steps.length === 0) {
    // Return empty graph with just start node
    return {
      nodes: [
        {
          id: 'start',
          type: 'start',
          position: { x: 100, y: 250 },
          data: { label: 'Start' },
        },
      ],
      edges: [],
    }
  }

  const nodes: Node[] = []
  const edges: Edge[] = []
  const agentNodes: Map<string, Node> = new Map()
  const stepToNodeMap: Map<string, string> = new Map()

  // Start node
  nodes.push({
    id: 'start',
    type: 'start',
    position: { x: 100, y: 250 },
    data: { label: 'Start', status: 'completed' },
  })

  // Group steps by agent type
  const stepsByAgent: Record<string, TaskStep[]> = {}
  executionPlan.steps.forEach((step) => {
    if (!stepsByAgent[step.agent_type]) {
      stepsByAgent[step.agent_type] = []
    }
    stepsByAgent[step.agent_type].push(step)
  })

  // Create agent nodes
  let xPosition = 350
  const agentTypes = Object.keys(stepsByAgent)
  const agentYPositions: Record<string, number> = {}

  agentTypes.forEach((agentType, index) => {
    const config = AGENT_CONFIG[agentType] || AGENT_CONFIG.executor
    const steps = stepsByAgent[agentType]
    
    // Determine node status based on steps
    const hasActive = steps.some((s) => ['executing', 'thinking', 'retrying'].includes(s.status))
    const hasFailed = steps.some((s) => s.status === 'failed')
    const allCompleted = steps.every((s) => s.status === 'completed')
    
    let status = 'pending'
    if (hasFailed) status = 'failed'
    else if (hasActive) status = 'executing'
    else if (allCompleted) status = 'completed'

    // Get latest step for node info
    const latestStep = steps[steps.length - 1]
    const confidence = latestStep.reasoning_chain?.overall_confidence || 
                       executionPlan.reasoning_chain?.overall_confidence || 0.5

    const yPos = 150 + (index * 200)
    agentYPositions[agentType] = yPos

    const nodeId = `agent-${agentType}`
    const node: Node = {
      id: nodeId,
      type: 'agent',
      position: { x: xPosition, y: yPos },
      data: {
        label: config.label,
        agentType,
        steps,
        status,
        confidence,
        action: latestStep.action,
        icon: config.icon,
        color: config.color,
        bgColor: config.bgColor,
      },
    }

    nodes.push(node)
    agentNodes.set(agentType, node)
    steps.forEach((step) => {
      stepToNodeMap.set(step.step_id, nodeId)
    })

    xPosition += 400
  })

  // Create edges from start to first agent
  if (agentTypes.length > 0) {
    const firstAgentType = agentTypes[0]
      edges.push({
        id: 'start-to-planner',
        source: 'start',
        sourceHandle: 'source-right',
        target: `agent-${firstAgentType}`,
        targetHandle: 'target-left',
        type: 'smoothstep',
        markerEnd: { type: MarkerType.ArrowClosed },
        animated: agentNodes.get(firstAgentType)?.data.status === 'executing',
        style: {
          stroke: agentNodes.get(firstAgentType)?.data.status === 'executing' ? '#f97316' : 
                  agentNodes.get(firstAgentType)?.data.status === 'completed' ? '#10b981' : '#6b7280',
          strokeWidth: 2,
        },
      })
  }

  // Create edges between agents (execution flow)
  for (let i = 0; i < agentTypes.length - 1; i++) {
    const fromAgent = agentTypes[i]
    const toAgent = agentTypes[i + 1]
    const fromNode = agentNodes.get(fromAgent)
    const toNode = agentNodes.get(toAgent)

    if (fromNode && toNode) {
      const isActive = toNode.data.status === 'executing' || fromNode.data.status === 'executing'
      const isCompleted = fromNode.data.status === 'completed' && 
                         ['executing', 'completed'].includes(toNode.data.status)

      edges.push({
        id: `${fromAgent}-to-${toAgent}`,
        source: fromNode.id,
        sourceHandle: 'source-right',
        target: toNode.id,
        targetHandle: 'target-left',
        type: 'smoothstep',
        markerEnd: { type: MarkerType.ArrowClosed },
        animated: isActive,
        style: {
          stroke: isCompleted ? '#10b981' : isActive ? '#f97316' : '#6b7280',
          strokeWidth: 2,
        },
      })
    }
  }

  // Add data source nodes at bottom
  const dataSourceY = 700
  let dataSourceX = 100
  DATA_SOURCES.forEach((source) => {
    const sourceNode: Node = {
      id: `source-${source.id}`,
      type: 'dataSource',
      position: { x: dataSourceX, y: dataSourceY },
      data: {
        label: source.label,
        icon: source.icon,
      },
    }
    nodes.push(sourceNode)

    // Connect data sources to planner/retriever agents with dashed edges
    if (agentNodes.has('planner') || agentNodes.has('retriever')) {
      const targetAgent = agentNodes.get('planner') || agentNodes.get('retriever')
      if (targetAgent) {
        edges.push({
          id: `${source.id}-to-${targetAgent.id}`,
          source: sourceNode.id,
          target: targetAgent.id,
          type: 'smoothstep',
          markerEnd: { type: MarkerType.ArrowClosed },
          style: {
            stroke: '#6b7280',
            strokeWidth: 1.5,
            strokeDasharray: '5,5',
          },
        })
      }
    }

    dataSourceX += 300
  })

  return { nodes, edges }
}

export function getStatusColor(status: string): string {
  return STATUS_COLORS[status] || STATUS_COLORS.pending
}

export function getStatusIcon(status: string): string {
  return STATUS_ICONS[status] || STATUS_ICONS.pending
}

export { AGENT_CONFIG, STATUS_COLORS, STATUS_ICONS, DATA_SOURCES }

