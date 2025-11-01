import { X, Download, CheckCircle2, XCircle, FileText } from 'lucide-react'
import ReasoningChain from './ReasoningChain'
import ExecutionTimeline from './ExecutionTimeline'

interface RAGEvidence {
  title: string
  snippet: string
  url?: string
  score?: number
}

interface SageMakerConfig {
  model_name: string
  endpoint_name: string
  instance_type: string
  instance_count: number
  budget_usd_per_hour: number
  max_payload_mb?: number
  autoscaling_min?: number
  autoscaling_max?: number
  rollback_alarms?: string[]
}

interface DeploymentPlan {
  plan_id: string
  status: string
  user_id: string
  intent: string
  env: string
  artifact: SageMakerConfig
  evidence?: RAGEvidence[]
  reasoning_steps?: any[]
  validation_errors?: string[]
  created_at: string
  updated_at?: string
}

interface DeploymentDetailsModalProps {
  isOpen: boolean
  onClose: () => void
  deployment: DeploymentPlan | null
}

export default function DeploymentDetailsModal({
  isOpen,
  onClose,
  deployment,
}: DeploymentDetailsModalProps) {
  if (!isOpen || !deployment) return null

  const handleExport = () => {
    const dataStr = JSON.stringify(deployment, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `deployment-plan-${deployment.plan_id}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const hasValidationErrors = deployment.validation_errors && deployment.validation_errors.length > 0
  const validationPassed = !hasValidationErrors && deployment.status !== 'validation_failed'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Deployment Details</h2>
            {validationPassed ? (
              <div title="Validation Passed">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
              </div>
            ) : hasValidationErrors ? (
              <div title="Validation Failed">
                <XCircle className="w-5 h-5 text-red-500" />
              </div>
            ) : null}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={handleExport}
              className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              title="Export as JSON"
            >
              <Download className="w-5 h-5" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content - Scrollable */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {/* Basic Info */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Basic Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Plan ID</p>
                <p className="text-sm text-gray-900 dark:text-white font-mono">{deployment.plan_id}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Status</p>
                <p className="text-sm text-gray-900 dark:text-white capitalize">{deployment.status}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Environment</p>
                <p className="text-sm text-gray-900 dark:text-white uppercase">{deployment.env}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">User</p>
                <p className="text-sm text-gray-900 dark:text-white">{deployment.user_id}</p>
              </div>
              <div className="col-span-2">
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Intent</p>
                <p className="text-sm text-gray-900 dark:text-white">{deployment.intent}</p>
              </div>
            </div>
          </div>

          {/* Reasoning Chain */}
          {deployment.reasoning_steps && deployment.reasoning_steps.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Agent Reasoning Chain</h3>
              <ReasoningChain steps={deployment.reasoning_steps} isExpanded={true} />
            </div>
          )}

          {/* Execution Timeline */}
          {deployment.reasoning_steps && deployment.reasoning_steps.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Execution Timeline</h3>
              <ExecutionTimeline steps={deployment.reasoning_steps} />
            </div>
          )}

          {/* Deployment Configuration */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Deployment Configuration</h3>
            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Model Name</p>
                  <p className="text-sm text-gray-900 dark:text-white font-mono">{deployment.artifact.model_name}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Endpoint Name</p>
                  <p className="text-sm text-gray-900 dark:text-white font-mono">{deployment.artifact.endpoint_name}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Instance Type</p>
                  <p className="text-sm text-gray-900 dark:text-white">{deployment.artifact.instance_type}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Instance Count</p>
                  <p className="text-sm text-gray-900 dark:text-white">{deployment.artifact.instance_count}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Budget (USD/hour)</p>
                  <p className="text-sm text-gray-900 dark:text-white">${deployment.artifact.budget_usd_per_hour}</p>
                </div>
                {deployment.artifact.autoscaling_min && deployment.artifact.autoscaling_max && (
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Auto-scaling</p>
                    <p className="text-sm text-gray-900 dark:text-white">
                      {deployment.artifact.autoscaling_min} - {deployment.artifact.autoscaling_max} instances
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* RAG Evidence */}
          {deployment.evidence && deployment.evidence.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">RAG Evidence</h3>
              <div className="space-y-3">
                {deployment.evidence.map((ev, idx) => (
                  <div
                    key={idx}
                    className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-900"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-white">{ev.title}</h4>
                      {ev.score && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          Score: {ev.score.toFixed(3)}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">{ev.snippet}</p>
                    {ev.url && (
                      <a
                        href={ev.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-600 dark:text-blue-400 hover:underline flex items-center space-x-1"
                      >
                        <FileText className="w-3 h-3" />
                        <span>View source</span>
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Validation Results */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Validation Results</h3>
            {validationPassed ? (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
                  <p className="text-sm text-green-800 dark:text-green-300">All validation checks passed</p>
                </div>
              </div>
            ) : hasValidationErrors ? (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <div className="flex items-start space-x-2">
                  <XCircle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-red-800 dark:text-red-300 mb-2">Validation Errors:</p>
                    <ul className="list-disc list-inside space-y-1">
                      {deployment.validation_errors?.map((error, idx) => (
                        <li key={idx} className="text-sm text-red-700 dark:text-red-400">
                          {error}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">No validation information available</p>
              </div>
            )}
          </div>

          {/* Cost Breakdown (if available) */}
          {deployment.artifact.budget_usd_per_hour && (
            <div>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Cost Estimate</h3>
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Estimated hourly cost: <span className="font-semibold text-gray-900 dark:text-white">${deployment.artifact.budget_usd_per_hour}/hour</span>
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  Based on {deployment.artifact.instance_count} × {deployment.artifact.instance_type} instance(s)
                </p>
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div>
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Timestamps</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Created</p>
                <p className="text-sm text-gray-900 dark:text-white">
                  {new Date(deployment.created_at).toLocaleString()}
                </p>
              </div>
              {deployment.updated_at && (
                <div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Last Updated</p>
                  <p className="text-sm text-gray-900 dark:text-white">
                    {new Date(deployment.updated_at).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-md transition-colors text-sm font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

