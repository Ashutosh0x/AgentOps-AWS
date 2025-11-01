import { Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'

interface ProgressStep {
  id: string
  label: string
  status: 'pending' | 'active' | 'completed' | 'failed'
  message?: string
  error?: string
}

interface ProgressIndicatorProps {
  steps: ProgressStep[]
  currentStepIndex?: number
  className?: string
}

export default function ProgressIndicator({ steps, currentStepIndex: _currentStepIndex, className = '' }: ProgressIndicatorProps) {
  if (!steps || steps.length === 0) {
    return null
  }

  const getStepIcon = (step: ProgressStep, index: number) => {
    switch (step.status) {
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'active':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
      default:
        return (
          <div className="w-5 h-5 rounded-full border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 flex items-center justify-center">
            <span className="text-xs text-gray-400">{index + 1}</span>
          </div>
        )
    }
  }

  const getStepColor = (step: ProgressStep, _index: number) => {
    switch (step.status) {
      case 'completed':
        return 'text-green-600 dark:text-green-400'
      case 'failed':
        return 'text-red-600 dark:text-red-400'
      case 'active':
        return 'text-blue-600 dark:text-blue-400 font-medium'
      default:
        return 'text-gray-500 dark:text-gray-400'
    }
  }

  const getConnectorColor = (step: ProgressStep, _index: number) => {
    if (step.status === 'completed') {
      return 'bg-green-500'
    }
    if (step.status === 'failed') {
      return 'bg-red-500'
    }
    if (step.status === 'active') {
      return 'bg-blue-500'
    }
    return 'bg-gray-300 dark:bg-gray-600'
  }

  const completedCount = steps.filter(s => s.status === 'completed').length
  const totalSteps = steps.length
  const progressPercentage = totalSteps > 0 ? (completedCount / totalSteps) * 100 : 0

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Progress Summary */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Deployment Progress</h4>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {completedCount}/{totalSteps} steps completed
        </span>
      </div>

      {/* Progress Bar */}
      <div className="relative">
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((step, index) => {
          const isLast = index === steps.length - 1
          const stepColor = getStepColor(step, index)

          return (
            <div key={step.id} className="relative">
              <div className="flex items-start space-x-3">
                {/* Icon */}
                <div className="flex-shrink-0">{getStepIcon(step, index)}</div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center space-x-2">
                    <p className={`text-sm ${stepColor}`}>{step.label}</p>
                    {step.status === 'active' && (
                      <span className="text-xs text-blue-500 dark:text-blue-400 animate-pulse">Processing...</span>
                    )}
                  </div>
                  {step.message && (
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 ml-7">{step.message}</p>
                  )}
                  {step.error && (
                    <div className="mt-1 ml-7 flex items-start space-x-1">
                      <AlertCircle className="w-3 h-3 text-red-500 flex-shrink-0 mt-0.5" />
                      <p className="text-xs text-red-600 dark:text-red-400">{step.error}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Connector Line */}
              {!isLast && (
                <div className="absolute left-[10px] top-[28px] w-0.5 h-6">
                  <div className={`w-full h-full ${getConnectorColor(step, index)} transition-colors`} />
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

