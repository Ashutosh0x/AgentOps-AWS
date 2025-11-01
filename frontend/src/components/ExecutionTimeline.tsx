import { CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react'

interface TaskStep {
  step_id: string
  agent_type: string
  action: string
  status: string
  timestamp?: string
}

interface ExecutionTimelineProps {
  steps: TaskStep[]
  className?: string
}

const getStepIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-5 h-5 text-green-500" />
    case 'failed':
      return <XCircle className="w-5 h-5 text-red-500" />
    case 'thinking':
    case 'executing':
    case 'retrying':
      return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
    default:
      return <Clock className="w-5 h-5 text-gray-400" />
  }
}

const formatAction = (action: string) => {
  return action
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

const getAgentLabel = (agentType: string) => {
  const labels: Record<string, string> = {
    planner: 'Planner',
    executor: 'Executor',
    monitor: 'Monitor',
    retriever: 'Retriever',
  }
  return labels[agentType] || agentType
}

export default function ExecutionTimeline({ steps, className = '' }: ExecutionTimelineProps) {
  if (!steps || steps.length === 0) {
    return (
      <div className={`text-sm text-gray-500 dark:text-gray-400 p-4 ${className}`}>
        No execution timeline available
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Execution Timeline</h4>
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-300 dark:bg-gray-600" />

        {/* Steps */}
        <div className="relative space-y-6">
          {steps.map((step) => {
            const isActive = ['thinking', 'executing', 'retrying'].includes(step.status)
            const isCompleted = step.status === 'completed'
            const isFailed = step.status === 'failed'

            return (
              <div key={step.step_id} className="relative flex items-start space-x-4">
                {/* Icon */}
                <div className="relative z-10 flex items-center justify-center w-10 h-10 rounded-full bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700">
                  {getStepIcon(step.status)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 pt-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      {getAgentLabel(step.agent_type)}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded ${
                        isCompleted
                          ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                          : isFailed
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                          : isActive
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                          : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                      }`}
                    >
                      {step.status}
                    </span>
                  </div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {formatAction(step.action)}
                  </p>
                  {step.timestamp && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {new Date(step.timestamp).toLocaleTimeString()}
                    </p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

