import { useState } from 'react'
import { ChevronDown, ChevronRight, Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react'

interface TaskStep {
  step_id: string
  agent_type: string
  action: string
  status: string
  input?: Record<string, any>
  output?: Record<string, any>
  timestamp?: string
  error?: string
  retry_count?: number
}

interface ReasoningChainProps {
  steps: TaskStep[]
  isExpanded?: boolean
  onToggle?: () => void
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'thinking':
    case 'executing':
    case 'retrying':
      return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-green-500" />
    case 'failed':
      return <XCircle className="w-4 h-4 text-red-500" />
    default:
      return <Clock className="w-4 h-4 text-gray-400" />
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'thinking':
    case 'executing':
    case 'retrying':
      return 'border-blue-300 bg-blue-50 dark:bg-blue-900/20'
    case 'completed':
      return 'border-green-300 bg-green-50 dark:bg-green-900/20'
    case 'failed':
      return 'border-red-300 bg-red-50 dark:bg-red-900/20'
    default:
      return 'border-gray-300 bg-gray-50 dark:bg-gray-800'
  }
}

const getAgentLabel = (agentType: string) => {
  const labels: Record<string, string> = {
    planner: 'Planner Agent',
    executor: 'Executor Agent',
    monitor: 'Monitoring Agent',
    retriever: 'Retriever Agent',
  }
  return labels[agentType] || agentType
}

const formatAction = (action: string) => {
  return action
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

export default function ReasoningChain({ steps, isExpanded: defaultExpanded = false, onToggle }: ReasoningChainProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())

  if (!steps || steps.length === 0) {
    return (
      <div className="text-sm text-gray-500 dark:text-gray-400 p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
        No reasoning steps available
      </div>
    )
  }

  const toggleExpanded = () => {
    setExpanded(!expanded)
    onToggle?.()
  }

  const toggleStep = (stepId: string) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(stepId)) {
      newExpanded.delete(stepId)
    } else {
      newExpanded.add(stepId)
    }
    setExpandedSteps(newExpanded)
  }

  const completedCount = steps.filter(s => s.status === 'completed').length
  const failedCount = steps.filter(s => s.status === 'failed').length
  const inProgressCount = steps.filter(s => ['thinking', 'executing', 'retrying'].includes(s.status)).length

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={toggleExpanded}
        className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        <div className="flex items-center space-x-3">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Agent Reasoning Chain</h3>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {completedCount}/{steps.length} completed
          </span>
          {failedCount > 0 && (
            <span className="text-xs text-red-600 dark:text-red-400">{failedCount} failed</span>
          )}
          {inProgressCount > 0 && (
            <span className="text-xs text-blue-600 dark:text-blue-400">{inProgressCount} in progress</span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            {steps.map((step, _idx) => (
              <div
                key={step.step_id}
                className={`w-2 h-2 rounded-full ${
                  step.status === 'completed'
                    ? 'bg-green-500'
                    : step.status === 'failed'
                    ? 'bg-red-500'
                    : ['thinking', 'executing', 'retrying'].includes(step.status)
                    ? 'bg-blue-500 animate-pulse'
                    : 'bg-gray-300'
                }`}
                title={`${formatAction(step.action)}: ${step.status}`}
              />
            ))}
          </div>
        </div>
      </button>

      {/* Steps List */}
      {expanded && (
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {steps.map((step, index) => {
            const isStepExpanded = expandedSteps.has(step.step_id)
            const stepStatusColor = getStatusColor(step.status)

            return (
              <div
                key={step.step_id}
                className={`${stepStatusColor} border-l-4 transition-colors`}
              >
                <button
                  onClick={() => toggleStep(step.step_id)}
                  className="w-full px-4 py-3 flex items-start justify-between hover:bg-opacity-80 transition-colors"
                >
                  <div className="flex items-start space-x-3 flex-1">
                    <div className="mt-0.5">{getStatusIcon(step.status)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                          Step {index + 1}
                        </span>
                        <span className="text-xs px-2 py-0.5 rounded bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
                          {getAgentLabel(step.agent_type)}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white mt-1">
                        {formatAction(step.action)}
                      </p>
                      {step.error && (
                        <p className="text-xs text-red-600 dark:text-red-400 mt-1">{step.error}</p>
                      )}
                      {step.retry_count && step.retry_count > 0 && (
                        <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                          Retry attempt {step.retry_count}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="ml-4">
                    {isStepExpanded ? (
                      <ChevronDown className="w-4 h-4 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-400" />
                    )}
                  </div>
                </button>

                {/* Step Details */}
                {isStepExpanded && (
                  <div className="px-4 pb-3 pt-0 space-y-3">
                    {step.input && Object.keys(step.input).length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Input:</p>
                        <pre className="text-xs bg-white dark:bg-gray-900 p-2 rounded border border-gray-200 dark:border-gray-700 overflow-x-auto">
                          {JSON.stringify(step.input, null, 2)}
                        </pre>
                      </div>
                    )}
                    {step.output && Object.keys(step.output).length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Output:</p>
                        <pre className="text-xs bg-white dark:bg-gray-900 p-2 rounded border border-gray-200 dark:border-gray-700 overflow-x-auto">
                          {JSON.stringify(step.output, null, 2)}
                        </pre>
                      </div>
                    )}
                    {step.timestamp && (
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Timestamp: {new Date(step.timestamp).toLocaleString()}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

