import { useState, useEffect, useRef } from 'react'
import { ChevronDown, ChevronUp, Play, Trash2 } from 'lucide-react'
import { apiClient } from '../lib/api'
import { useQueryClient } from 'react-query'
import ConfirmDialog from './ConfirmDialog'

interface ExecutionPanelProps {
  selectedNode: any
  planId: string | null
  deployment: any
  onDeploymentDeleted?: () => void
}

interface AgentLog {
  timestamp: string
  agent: string
  message: string
  status: string
}

export default function ExecutionPanel({
  selectedNode,
  planId,
  deployment,
  onDeploymentDeleted,
}: ExecutionPanelProps) {
  const queryClient = useQueryClient()
  const [logsExpanded, setLogsExpanded] = useState(true)
  const [queueExpanded, setQueueExpanded] = useState(true)
  const [confidenceExpanded, setConfidenceExpanded] = useState(true)
  const [retryExpanded, setRetryExpanded] = useState(true)
  const [logs, setLogs] = useState<AgentLog[]>([])
  const [confidenceLevel, setConfidenceLevel] = useState(75)
  const [retryThreshold, setRetryThreshold] = useState(30)
  const [selectedRetryStep, setSelectedRetryStep] = useState<string>('')
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showHardDeleteOption, setShowHardDeleteOption] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)

  // Generate agent logs from deployment data with fallback
  useEffect(() => {
    if (!planId || !deployment) {
      setLogs([])
      return
    }

    const reasoningSteps = (deployment as any).reasoning_steps || []
    const newLogs: AgentLog[] = []

    // Process reasoning steps if available
    if (reasoningSteps.length > 0) {
      reasoningSteps.forEach((step: any) => {
        const agentName = step.agent_type || 'unknown'
        const status = step.status || 'pending'
        const stepTime = step.timestamp ? new Date(step.timestamp) : new Date()
        
        if (step.reasoning_chain?.steps) {
          step.reasoning_chain.steps.forEach((reasoningStep: any) => {
            newLogs.push({
              timestamp: stepTime.toLocaleTimeString(),
              agent: agentName,
              message: reasoningStep.thought || step.action,
              status: status,
            })
          })
        } else {
          newLogs.push({
            timestamp: stepTime.toLocaleTimeString(),
            agent: agentName,
            message: step.action || 'Processing...',
            status: status,
          })
        }

        if (step.output?.message) {
          newLogs.push({
            timestamp: stepTime.toLocaleTimeString(),
            agent: agentName,
            message: step.output.message,
            status: status,
          })
        }

        if (step.error) {
          newLogs.push({
            timestamp: stepTime.toLocaleTimeString(),
            agent: agentName,
            message: `Error: ${step.error}`,
            status: 'failed',
          })
        }
      })
    } else {
      // Fallback: Generate logs from deployment metadata
      const createdTime = deployment.created_at ? new Date(deployment.created_at) : new Date()
      const updatedTime = deployment.updated_at ? new Date(deployment.updated_at) : createdTime
      const status = (deployment as any).status || 'unknown'
      const intent = deployment.intent || 'Unknown command'
      const env = deployment.env || 'staging'
      
      // Deployment creation log
      newLogs.push({
        timestamp: createdTime.toLocaleTimeString(),
        agent: 'system',
        message: `Deployment created: ${intent}`,
        status: 'completed',
      })

      // Status log
      if (status !== 'unknown') {
        newLogs.push({
          timestamp: updatedTime.toLocaleTimeString(),
          agent: 'system',
          message: `Status: ${status}`,
          status: status === 'failed' ? 'failed' : status === 'deployed' ? 'completed' : 'pending',
        })
      }

      // Artifact information
      if ((deployment as any).artifact) {
        const artifact = (deployment as any).artifact
        if (artifact.endpoint_name) {
          newLogs.push({
            timestamp: updatedTime.toLocaleTimeString(),
            agent: 'executor',
            message: `Endpoint: ${artifact.endpoint_name} configured`,
            status: 'completed',
          })
        }
        if (artifact.model_name) {
          newLogs.push({
            timestamp: updatedTime.toLocaleTimeString(),
            agent: 'executor',
            message: `Model: ${artifact.model_name}`,
            status: 'completed',
          })
        }
        if (artifact.instance_type) {
          newLogs.push({
            timestamp: updatedTime.toLocaleTimeString(),
            agent: 'executor',
            message: `Instance: ${artifact.instance_type}`,
            status: 'completed',
          })
        }
      }

      // Validation errors if any
      if ((deployment as any).validation_errors && (deployment as any).validation_errors.length > 0) {
        (deployment as any).validation_errors.forEach((error: string) => {
          newLogs.push({
            timestamp: updatedTime.toLocaleTimeString(),
            agent: 'executor',
            message: `Validation error: ${error}`,
            status: 'failed',
          })
        })
      }

      // Environment info
      newLogs.push({
        timestamp: createdTime.toLocaleTimeString(),
        agent: 'system',
        message: `Environment: ${env.toUpperCase()}`,
        status: 'completed',
      })
    }

    setLogs(newLogs)
  }, [planId, deployment])

  // Auto-scroll logs to bottom
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  // Filter logs by selected node
  const filteredLogs = selectedNode
    ? logs.filter((log) => log.agent === selectedNode.data?.agentType)
    : logs

  // Get pending steps for queue
  const pendingSteps =
    deployment && (deployment as any).reasoning_steps
      ? (deployment as any).reasoning_steps.filter(
          (s: any) => !['completed', 'failed'].includes(s.status)
        )
      : []

  // Get failed steps for retry
  const failedSteps =
    deployment && (deployment as any).reasoning_steps
      ? (deployment as any).reasoning_steps.filter((s: any) => s.status === 'failed')
      : []

  const handleRetryStep = async () => {
    if (!planId || !selectedRetryStep) return
    try {
      await apiClient.retryWorkflowStep(planId, selectedRetryStep)
      // Refresh will happen via polling
      setSelectedRetryStep('') // Reset selection
    } catch (error) {
      console.error('Failed to retry step:', error)
    }
  }

  const handleDeleteClick = () => {
    if (!planId) return
    setShowDeleteDialog(true)
  }

  const handleDeleteConfirm = async () => {
    if (!planId) return

    setIsDeleting(true)
    try {
      const response = await apiClient.deleteDeployment(planId, showHardDeleteOption)
      
      if (response.success) {
        setShowDeleteDialog(false)
        setShowHardDeleteOption(false)
        // Invalidate all queries to refresh data
        queryClient.invalidateQueries()
        // Notify parent component
        if (onDeploymentDeleted) {
          onDeploymentDeleted()
        }
        // Show success message
        alert(response.message || 'Deployment deleted successfully')
      } else {
        throw new Error(response.message || 'Failed to delete deployment')
      }
    } catch (error: any) {
      console.error('Failed to delete deployment:', error)
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to delete deployment. Please try again.'
      alert(errorMessage)
    } finally {
      setIsDeleting(false)
    }
  }

  const getDeploymentName = () => {
    if (!deployment) return planId || 'deployment'
    return (deployment as any).artifact?.endpoint_name || deployment.intent || planId || 'deployment'
  }


  return (
    <div className="p-4 space-y-4">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Execution Panel
      </h2>

      {/* Agent Logs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <button
          onClick={() => setLogsExpanded(!logsExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <span className="font-medium text-gray-900 dark:text-white">Agent Logs</span>
          {logsExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </button>
        {logsExpanded && (
          <div className="px-4 pb-4">
            <div className="bg-gray-900 dark:bg-black rounded-lg p-3 h-64 overflow-y-auto font-mono text-xs">
              {filteredLogs.length === 0 ? (
                <div className="text-gray-500 dark:text-gray-400 text-center py-8 space-y-2">
                  <p className="text-sm font-medium">No logs available</p>
                  {planId && !deployment ? (
                    <p className="text-xs">Loading deployment details...</p>
                  ) : planId && deployment && (!(deployment as any).reasoning_steps || (deployment as any).reasoning_steps.length === 0) ? (
                    <p className="text-xs">Logs will appear as agents execute steps</p>
                  ) : (
                    <p className="text-xs">Select a deployment to view logs</p>
                  )}
                </div>
              ) : (
                filteredLogs.map((log, idx) => (
                  <div key={idx} className="mb-2 text-green-400 dark:text-green-300">
                    <span className="text-gray-500 dark:text-gray-400">[{log.timestamp}]</span>
                    <span className="text-blue-400 dark:text-blue-300 ml-1">
                      [{log.agent}]
                    </span>
                    <span className="ml-1">"{log.message}"</span>
                    <span className="text-yellow-400 dark:text-yellow-300 ml-1">
                      -&gt; {log.status.toUpperCase()}
                    </span>
                  </div>
                ))
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        )}
      </div>

      {/* Actions Queue */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <button
          onClick={() => setQueueExpanded(!queueExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <span className="font-medium text-gray-900 dark:text-white">Actions Queue</span>
          {queueExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </button>
        {queueExpanded && (
          <div className="px-4 pb-4">
            {pendingSteps.length === 0 ? (
              <div className="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
                No pending actions
              </div>
            ) : (
              <div className="space-y-2">
                {pendingSteps.map((step: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg border border-gray-200 dark:border-gray-600"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-gray-900 dark:text-white truncate">
                          {step.action || step.step_id}
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {step.agent_type} • {step.status}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Confidence Levels */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <button
          onClick={() => setConfidenceExpanded(!confidenceExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <span className="font-medium text-gray-900 dark:text-white">Confidence Levels</span>
          {confidenceExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </button>
        {confidenceExpanded && (
          <div className="px-4 pb-4 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Decision Threshold: {confidenceLevel}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={confidenceLevel}
                onChange={(e) => setConfidenceLevel(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Retry Threshold: {retryThreshold}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                value={retryThreshold}
                onChange={(e) => setRetryThreshold(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-orange-600"
              />
            </div>
          </div>
        )}
      </div>

      {/* Retry Step */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <button
          onClick={() => setRetryExpanded(!retryExpanded)}
          className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          <span className="font-medium text-gray-900 dark:text-white">Retry Step</span>
          {retryExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          )}
        </button>
        {retryExpanded && (
          <div className="px-4 pb-4">
            {failedSteps.length === 0 ? (
              <div className="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
                No failed steps
              </div>
            ) : (
              <div className="space-y-3">
                <select
                  value={selectedRetryStep}
                  onChange={(e) => setSelectedRetryStep(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm"
                >
                  <option value="">Select a failed step...</option>
                  {failedSteps.map((step: any, idx: number) => (
                    <option key={idx} value={step.step_id}>
                      {step.action || step.step_id} - {step.error || 'Failed'}
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleRetryStep}
                  disabled={!selectedRetryStep}
                  className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center justify-center space-x-2"
                >
                  <Play className="w-4 h-4" />
                  <span>Retry Step</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Delete Deployment - Show for all real deployments */}
      {planId && planId !== 'demo' && planId !== null && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-red-300 dark:border-red-700 overflow-hidden shadow-lg mt-4">
          <div className="px-4 py-3 border-b border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30">
            <span className="font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
              <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
              <span>Deployment Actions</span>
            </span>
          </div>
          <div className="px-4 pb-4 pt-4 space-y-3">
            <button
              onClick={handleDeleteClick}
              disabled={isDeleting || (deployment as any)?.status === 'deleted' || (deployment as any)?.status === 'DELETED'}
              className="w-full px-4 py-2.5 bg-red-600 hover:bg-red-700 active:bg-red-800 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-all flex items-center justify-center space-x-2 shadow-md hover:shadow-lg transform hover:scale-[1.02]"
            >
              {isDeleting ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>Deleting...</span>
                </>
              ) : (
                <>
                  <Trash2 className="w-4 h-4" />
                  <span>Delete Deployment</span>
                </>
              )}
            </button>
            {deployment && (deployment as any).status && (
              <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
                Current Status: <span className="font-medium capitalize">{(deployment as any).status.replace(/_/g, ' ')}</span>
              </p>
            )}
          </div>
        </div>
      )}


      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteDialog}
        onClose={() => {
          setShowDeleteDialog(false)
          setShowHardDeleteOption(false)
        }}
        onConfirm={handleDeleteConfirm}
        title="Delete Deployment"
        message={
          <div className="space-y-3">
            <p>
              Are you sure you want to delete deployment <strong>'{getDeploymentName()}'</strong>?
            </p>
            <div className="space-y-2">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showHardDeleteOption}
                  onChange={(e) => setShowHardDeleteOption(e.target.checked)}
                  className="rounded border-gray-300 text-red-600 focus:ring-red-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  <strong>Hard Delete:</strong> Also delete SageMaker resources (endpoint, model) and agent memories.
                  This action cannot be undone.
                </span>
              </label>
              {!showHardDeleteOption && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Soft delete (default): Marks deployment as deleted but keeps data for audit purposes.
                </p>
              )}
            </div>
          </div>
        }
        confirmText={showHardDeleteOption ? "Delete Permanently" : "Delete"}
        cancelText="Cancel"
        variant="danger"
        isLoading={isDeleting}
      />
    </div>
  )
}

