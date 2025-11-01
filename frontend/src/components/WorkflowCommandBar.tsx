import { useState, useRef, useEffect } from 'react'
import { Send, ChevronDown } from 'lucide-react'
import { useMutation } from 'react-query'
import { apiClient, AgentCommandRequest } from '../lib/api'

interface WorkflowCommandBarProps {
  onCommandSubmit: (planId: string) => void
}

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

export default function WorkflowCommandBar({ onCommandSubmit }: WorkflowCommandBarProps) {
  const [command, setCommand] = useState('')
  const [env, setEnv] = useState('staging')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>([])
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [recentCommands, setRecentCommands] = useState<string[]>([])
  const inputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  const sendCommand = useMutation(
    (request: AgentCommandRequest) => apiClient.sendCommand(request),
    {
      onSuccess: (data) => {
        if (data.result?.plan_id) {
          // Save to recent commands
          const commandToSave = command.trim()
          if (commandToSave) {
            const updated = [commandToSave, ...recentCommands.filter(c => c !== commandToSave)].slice(0, 10)
            setRecentCommands(updated)
            localStorage.setItem('recentCommands', JSON.stringify(updated))
          }
          
          onCommandSubmit(data.result.plan_id)
          setCommand('')
          setShowSuggestions(false)
          setSelectedIndex(-1)
        }
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
    
    const commandToSubmit = selectedIndex >= 0 
      ? filteredSuggestions[selectedIndex] 
      : command.trim()

    sendCommand.mutate({
      command: commandToSubmit,
      env: env,
      user_id: 'workflow-user@agentops.ai',
    })
  }

  const handleSuggestionClick = (suggestion: string) => {
    setCommand(suggestion)
    setShowSuggestions(false)
    setSelectedIndex(-1)
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || filteredSuggestions.length === 0) return

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex((prev) => 
        prev < filteredSuggestions.length - 1 ? prev + 1 : prev
      )
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault()
      handleSuggestionClick(filteredSuggestions[selectedIndex])
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
      setSelectedIndex(-1)
    }
  }

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4">
      <form onSubmit={handleSubmit} className="flex items-center space-x-3">
        {/* Environment Selector */}
        <div className="relative">
          <select
            value={env}
            onChange={(e) => setEnv(e.target.value)}
            className="appearance-none bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2 pr-8 text-sm font-medium text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
          >
            <option value="staging">STAGING</option>
            <option value="dev">DEV</option>
            <option value="prod">PROD</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>

        {/* Command Input */}
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={command}
            onChange={(e) => {
              setCommand(e.target.value)
              setShowSuggestions(true)
            }}
            onFocus={() => setShowSuggestions(true)}
            onKeyDown={handleKeyDown}
            onBlur={() => {
              // Delay to allow suggestion click
              setTimeout(() => setShowSuggestions(false), 200)
            }}
            placeholder="type a command - (e.g., deploy llama-3.1-8B for chatbot-x)"
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />

          {/* Suggestions Dropdown */}
          {showSuggestions && filteredSuggestions.length > 0 && (
            <div
              ref={suggestionsRef}
              className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg max-h-48 overflow-y-auto"
            >
              {filteredSuggestions.map((suggestion, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSuggestionClick(suggestion)}
                  className={`w-full px-4 py-2 text-left text-sm transition-colors ${
                    idx === selectedIndex
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-900 dark:text-blue-100'
                      : 'text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Send Button */}
        <button
          type="submit"
          disabled={!command.trim() || sendCommand.isLoading}
          className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors flex items-center space-x-2"
        >
          {sendCommand.isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Sending...</span>
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              <span>Send</span>
            </>
          )}
        </button>
      </form>

      {/* Error Display */}
      {sendCommand.isError && (
        <div className="mt-2 px-4 py-2 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-800 dark:text-red-400">
            Error: {sendCommand.error instanceof Error ? sendCommand.error.message : 'Failed to send command'}
          </p>
        </div>
      )}
    </div>
  )
}

