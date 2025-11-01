import { useState, useRef, useEffect } from 'react'
import { useSendCommand } from '../lib/hooks'
import { useQuery } from 'react-query'
import { apiClient } from '../lib/api'
import { Send, Loader2, CheckCircle2, XCircle } from 'lucide-react'
import AgentActivityPanel from './AgentActivityPanel'
import ProgressIndicator from './ProgressIndicator'

const COMMAND_SUGGESTIONS = [
  // Basic deployments
  'deploy llama-3.1 8B for chatbot-x',
  'deploy llama-3.1 8B for customer support bot',
  'deploy llama-3.1 8B for production chatbot',
  'deploy llama-3.1 8B for staging environment',
  'deploy llama-3.1 8B for testing',
  'deploy llama-3.1 8B for development',
  
  // Nemotron deployments
  'deploy nemotron nano 8B for chatbot-x',
  'deploy nemotron nano 8B for customer support',
  'deploy nemotron nano 8B for testing',
  'deploy nemotron nano 8B for production',
  
  // With budget constraints
  'deploy llama-3.1 8B with budget $20 per hour',
  'deploy llama-3.1 8B with budget $15 per hour',
  'deploy llama model with budget constraint $25/hour',
  'deploy nemotron nano with budget $18 per hour',
  
  // Different use cases
  'deploy llama model for recommendation engine',
  'deploy llama-3.1 8B for document Q&A system',
  'deploy llama model for content generation',
  'deploy llama-3.1 8B for code assistant',
  'deploy llama model for email summarization',
  'deploy nemotron nano for sentiment analysis',
  
  // Environment specific
  'deploy llama-3.1 8B for chatbot-x production',
  'deploy llama model for chatbot-x staging',
  'deploy llama-3.1 8B for prod chatbot application',
  'deploy llama model for dev environment',
  
  // Instance count variations
  'deploy llama-3.1 8B with 2 instances',
  'deploy llama model with 3 instances for production',
  'deploy llama-3.1 8B with single instance',
  
  // Alternative phrasings
  'set up llama-3.1 8B for chatbot-x',
  'create deployment for llama model chatbot',
  'launch llama-3.1 8B endpoint for chatbot',
  'provision llama model for chatbot-x',
]

export default function CommandBar() {
  const [command, setCommand] = useState('')
  const [env, setEnv] = useState('staging')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>([])
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [recentCommands, setRecentCommands] = useState<string[]>([])
  const [currentPlanId, setCurrentPlanId] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const sendCommand = useSendCommand()

  // Poll deployment status if we have an active plan
  const { data: deploymentStatus } = useQuery(
    ['deploymentStatus', currentPlanId],
    () => apiClient.getDeploymentStatus(currentPlanId!),
    {
      enabled: !!currentPlanId,
      refetchInterval: (data) => {
        // Stop polling if completed or failed
        if (data?.status === 'deployed' || data?.status === 'failed' || data?.status === 'deleted') {
          return false
        }
        // Poll every 2 seconds while in progress
        return 2000
      },
    }
  )
  
  // Load recent commands from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('recentCommands')
    if (saved) {
      try {
        setRecentCommands(JSON.parse(saved))
      } catch (e) {
        // Ignore parse errors
      }
    }
  }, [])
  
  // Filter suggestions based on input
  useEffect(() => {
    if (!command.trim()) {
      setFilteredSuggestions([...COMMAND_SUGGESTIONS, ...recentCommands].slice(0, 8))
    } else {
      const filtered = [...COMMAND_SUGGESTIONS, ...recentCommands].filter(
        (suggestion) => suggestion.toLowerCase().includes(command.toLowerCase())
      )
      setFilteredSuggestions(filtered.slice(0, 8))
    }
    setSelectedIndex(-1)
  }, [command, recentCommands])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!command.trim() || sendCommand.isLoading) return
    
    const commandToSubmit = command.trim()

    try {
      const result = await sendCommand.mutateAsync({
        command: commandToSubmit,
        env: env,
        user_id: 'dashboard-user@agentops.ai',
      })
      
      // Save to recent commands
      const updated = [commandToSubmit, ...recentCommands.filter(c => c !== commandToSubmit)].slice(0, 5)
      setRecentCommands(updated)
      localStorage.setItem('recentCommands', JSON.stringify(updated))
      
      // Track plan ID for status polling
      if (result?.result?.plan_id) {
        setCurrentPlanId(result.result.plan_id)
      }
      
      setCommand('')
      setShowSuggestions(false)
    } catch (error) {
      console.error('Failed to send command:', error)
      setCurrentPlanId(null)
    }
  }
  
  const handleSuggestionSelect = (suggestion: string) => {
    setCommand(suggestion)
    setShowSuggestions(false)
    inputRef.current?.focus()
  }
  
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!showSuggestions || filteredSuggestions.length === 0) return
    
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(prev => (prev < filteredSuggestions.length - 1 ? prev + 1 : prev))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : -1))
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault()
      handleSuggestionSelect(filteredSuggestions[selectedIndex])
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
      setSelectedIndex(-1)
    }
  }

  return (
    <footer className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 shadow-lg transition-colors">
      <div className="container mx-auto px-4 py-4 max-w-7xl">
        <form onSubmit={handleSubmit} className="flex items-center space-x-4">
          <div className="flex-1 relative">
            {/* Command Suggestions Dropdown - Floating Above */}
            {showSuggestions && filteredSuggestions.length > 0 && (
              <div
                ref={suggestionsRef}
                className="absolute z-50 w-full bottom-full mb-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-xl max-h-80 overflow-y-auto"
              >
                {/* Show recent commands section if available */}
                {command.trim() === '' && recentCommands.length > 0 && (
                  <>
                    <div className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                      Recent Commands
                    </div>
                    {recentCommands.slice(0, 5).map((suggestion, index) => {
                      const isSelected = index === selectedIndex
                      return (
                        <button
                          key={`recent-${index}`}
                          type="button"
                          onClick={() => handleSuggestionSelect(suggestion)}
                          onMouseEnter={() => setSelectedIndex(index)}
                          className={`w-full text-left px-4 py-2 text-sm hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors ${
                            isSelected ? 'bg-blue-50 dark:bg-gray-700' : ''
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-gray-900 dark:text-gray-100">{suggestion}</span>
                            <span className="text-xs text-gray-500 dark:text-gray-400">Recent</span>
                          </div>
                        </button>
                      )
                    })}
                    <div className="px-4 py-2 text-xs font-semibold text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 border-t">
                      Suggestions
                    </div>
                  </>
                )}
                
                {/* Show filtered suggestions */}
                {filteredSuggestions
                  .filter(s => !recentCommands.includes(s) || command.trim() !== '')
                  .slice(0, command.trim() === '' ? 10 : 12)
                  .map((suggestion, index) => {
                    const isRecent = recentCommands.includes(suggestion)
                    const displayIndex = command.trim() === '' && recentCommands.length > 0 
                      ? index + recentCommands.length 
                      : index
                    const isSelected = displayIndex === selectedIndex
                    
                    return (
                      <button
                        key={index}
                        type="button"
                        onClick={() => handleSuggestionSelect(suggestion)}
                        onMouseEnter={() => setSelectedIndex(displayIndex)}
                        className={`w-full text-left px-4 py-2 text-sm hover:bg-blue-50 dark:hover:bg-gray-700 transition-colors ${
                          isSelected ? 'bg-blue-50 dark:bg-gray-700' : ''
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-gray-900 dark:text-gray-100">{suggestion}</span>
                          {isRecent && command.trim() !== '' && (
                            <span className="text-xs text-gray-500 dark:text-gray-400">Recent</span>
                          )}
                        </div>
                      </button>
                    )
                  })}
              </div>
            )}
            
            <div className="flex items-center space-x-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 px-4 py-2 focus-within:border-blue-500 dark:focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-200 dark:focus-within:ring-blue-800">
              <label htmlFor="env" className="text-sm font-medium text-gray-600 dark:text-gray-400 whitespace-nowrap">
                Env:
              </label>
              <select
                id="env"
                value={env}
                onChange={(e) => setEnv(e.target.value)}
                className="bg-transparent border-none text-sm font-medium text-gray-700 dark:text-gray-300 focus:outline-none cursor-pointer"
              >
                <option value="staging">STAGING</option>
                <option value="prod">PROD</option>
              </select>
              <div className="w-px h-6 bg-gray-300 dark:bg-gray-600"></div>
              <input
                ref={inputRef}
                type="text"
                value={command}
                onChange={(e) => {
                  setCommand(e.target.value)
                  setShowSuggestions(true)
                }}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => {
                  // Delay to allow suggestion click
                  setTimeout(() => setShowSuggestions(false), 200)
                }}
                onKeyDown={handleKeyDown}
                placeholder="Type a command... (e.g., deploy llama-3.1 8B for chatbot-x)"
                className="flex-1 bg-transparent border-none outline-none text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500"
                disabled={sendCommand.isLoading}
              />
              {command && (
                <button
                  type="button"
                  onClick={() => {
                    setCommand('')
                    setShowSuggestions(true)
                    inputRef.current?.focus()
                  }}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  aria-label="Clear command"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              )}
              {sendCommand.isSuccess && (
                <CheckCircle2 className="w-5 h-5 text-green-500" />
              )}
              {sendCommand.isError && (
                <XCircle className="w-5 h-5 text-red-500" />
              )}
            </div>
            
            {/* Show suggestions hint - below input */}
            {!command && !showSuggestions && (
              <div className="absolute top-full mt-2 text-xs text-gray-500 dark:text-gray-400 px-2">
                💡 Start typing to see suggestions above
              </div>
            )}
          </div>
          <button
            type="submit"
            disabled={!command.trim() || sendCommand.isLoading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
          >
            {sendCommand.isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Send</span>
              </>
            )}
          </button>
        </form>

        {sendCommand.isSuccess && sendCommand.data && !deploymentStatus && (
          <div className="mt-3 p-3 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-green-800 dark:text-green-400">
                  ✓ Command processed successfully!
                </p>
                {sendCommand.data.result?.artifact?.endpoint_name && (
                  <p className="text-xs text-green-700 dark:text-green-500 mt-1">
                    Endpoint: <span className="font-mono">{sendCommand.data.result.artifact.endpoint_name}</span>
                  </p>
                )}
                <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                  Status: <span className="font-medium">{sendCommand.data.result?.status?.toUpperCase() || 'PROCESSING'}</span>
                  {sendCommand.data.result?.requires_approval && (
                    <span className="ml-2">• Requires approval</span>
                  )}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Show real-time status when polling is active */}
        {sendCommand.isSuccess && sendCommand.data && deploymentStatus && (
          <div className={`mt-3 p-3 border rounded-lg ${
            deploymentStatus.status === 'deployed' 
              ? 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800'
              : deploymentStatus.status === 'failed'
              ? 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800'
              : 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800'
          }`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <p className={`text-sm font-medium ${
                  deploymentStatus.status === 'deployed'
                    ? 'text-green-800 dark:text-green-400'
                    : deploymentStatus.status === 'failed'
                    ? 'text-red-800 dark:text-red-400'
                    : 'text-blue-800 dark:text-blue-400'
                }`}>
                  {deploymentStatus.status === 'deployed' && '✓ Deployment completed!'}
                  {deploymentStatus.status === 'failed' && '✗ Deployment failed'}
                  {deploymentStatus.status === 'deploying' && '⏳ Deployment in progress...'}
                  {!['deployed', 'failed', 'deploying'].includes(deploymentStatus.status) && `Status: ${deploymentStatus.status.toUpperCase()}`}
                </p>
                {sendCommand.data.result?.artifact?.endpoint_name && (
                  <p className="text-xs text-gray-700 dark:text-gray-300 mt-1">
                    Endpoint: <span className="font-mono">{sendCommand.data.result.artifact.endpoint_name}</span>
                  </p>
                )}
                {deploymentStatus.current_step && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    Current step: <span className="font-medium">{deploymentStatus.current_step}</span>
                  </p>
                )}
                {deploymentStatus.progress !== undefined && (
                  <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                    Progress: <span className="font-medium">{deploymentStatus.progress}%</span>
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {sendCommand.isError && (
          <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm font-medium text-red-800 dark:text-red-400 mb-2">
              ✗ Error: {(sendCommand.error as Error)?.message || 'Failed to process command'}
            </p>
          </div>
        )}
        
        {sendCommand.isSuccess && sendCommand.data && sendCommand.data.status === 'validation_failed' && (
          <div className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-400 mb-2">
              ⚠️ Validation Failed
            </p>
            {sendCommand.data.result?.errors && (
              <ul className="text-xs text-yellow-700 dark:text-yellow-500 list-disc list-inside space-y-1">
                {Array.isArray(sendCommand.data.result.errors) ? (
                  sendCommand.data.result.errors.map((error: string, idx: number) => (
                    <li key={idx}>{error}</li>
                  ))
                ) : (
                  <li>{String(sendCommand.data.result.errors)}</li>
                )}
              </ul>
            )}
          </div>
        )}

        {/* Agent Activity Panel - Show during processing */}
        {sendCommand.isLoading && (
          <div className="mt-3">
            <AgentActivityPanel
              status="thinking"
              currentStep="Processing your command..."
              message="The agent is analyzing your request and planning the deployment."
            />
          </div>
        )}

        {/* Progress Indicator - Show when we have deployment status */}
        {currentPlanId && deploymentStatus && (
          <div className="mt-3">
            <ProgressIndicator
              steps={deploymentStatus.steps?.map((step: { step_id: string; action: string; status: string; message?: string }) => ({
                id: step.step_id,
                label: step.action,
                status: 
                  step.status === 'completed' ? 'completed' :
                  step.status === 'failed' || step.status === 'failed_permanently' ? 'failed' :
                  step.status === 'thinking' || step.status === 'executing' || step.status === 'retrying' ? 'active' :
                  'pending',
                message: step.message,
              })) || []}
              currentStepIndex={deploymentStatus.steps?.findIndex((s: { status: string }) => 
                ['thinking', 'executing', 'retrying'].includes(s.status)
              )}
            />
          </div>
        )}

        {/* Agent Activity Summary - Show after command succeeds but before status polling starts */}
        {sendCommand.isSuccess && sendCommand.data && !currentPlanId && (
          <div className="mt-3">
            <AgentActivityPanel
              status="completed"
              message="Command submitted successfully. Waiting for deployment plan..."
            />
          </div>
        )}
      </div>
    </footer>
  )
}

