import { Loader2, CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react'

interface AgentActivityProps {
  status: 'idle' | 'thinking' | 'planning' | 'retrieving' | 'validating' | 'executing' | 'completed' | 'failed'
  currentStep?: string
  progress?: number
  message?: string
  error?: string
}

export default function AgentActivityPanel({
  status,
  currentStep,
  progress,
  message,
  error,
}: AgentActivityProps) {
  if (status === 'idle') {
    return null
  }

  const getStatusIcon = () => {
    switch (status) {
      case 'thinking':
      case 'planning':
      case 'retrieving':
      case 'validating':
      case 'executing':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
      case 'completed':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  const getStatusColor = () => {
    switch (status) {
      case 'thinking':
      case 'planning':
      case 'retrieving':
      case 'validating':
      case 'executing':
        return 'border-blue-300 bg-blue-50 dark:bg-blue-900/20'
      case 'completed':
        return 'border-green-300 bg-green-50 dark:bg-green-900/20'
      case 'failed':
        return 'border-red-300 bg-red-50 dark:bg-red-900/20'
      default:
        return 'border-gray-300 bg-gray-50 dark:bg-gray-800'
    }
  }

  const getStatusText = () => {
    switch (status) {
      case 'thinking':
        return 'Thinking...'
      case 'planning':
        return 'Planning deployment steps...'
      case 'retrieving':
        return 'Retrieving relevant policies...'
      case 'validating':
        return 'Validating deployment plan...'
      case 'executing':
        return currentStep || 'Executing deployment...'
      case 'completed':
        return 'Deployment completed successfully'
      case 'failed':
        return 'Deployment failed'
      default:
        return 'Processing...'
    }
  }

  const statusColor = getStatusColor()

  return (
    <div className={`border-l-4 rounded-r-lg p-4 ${statusColor} transition-colors duration-300`}>
      <div className="flex items-start space-x-3">
        <div className="flex-shrink-0 mt-0.5">{getStatusIcon()}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {getStatusText()}
            </p>
            {progress !== undefined && status !== 'completed' && status !== 'failed' && (
              <span className="text-xs text-gray-500 dark:text-gray-400">{progress}%</span>
            )}
          </div>

          {/* Progress Bar */}
          {progress !== undefined && status !== 'completed' && status !== 'failed' && (
            <div className="mb-2">
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all duration-300 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Message */}
          {message && (
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{message}</p>
          )}

          {/* Error */}
          {error && (
            <div className="mt-2 flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-red-600 dark:text-red-400">{error}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

