import axios from 'axios'

// In development, use Vite proxy (relative URLs)
// In production, use full Lambda Function URL from environment variable
const isDevelopment = import.meta.env.DEV
const API_BASE_URL = isDevelopment
  ? '' // Use proxy - requests to /api/* will be proxied
  : (() => {
      const url = import.meta.env.VITE_API_URL
      if (!url) {
        throw new Error('VITE_API_URL environment variable is required in production. Please set it in your .env file or deployment configuration.')
      }
      return url.replace(/\/$/, '')
    })()

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
})

// Add request interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      console.error('Network error details:', {
        message: error.message,
        code: error.code,
        apiUrl: API_BASE_URL,
        requestUrl: error.config?.url,
        method: error.config?.method,
      })
      
      // Provide more helpful error message
      const helpfulMessage = error.response 
        ? `API Error: ${error.response.status} - ${error.response.statusText}`
        : 'Network Error: Unable to connect to API. This may be a CORS issue. Make sure you are running from http://localhost:5173 or the Lambda Function URL CORS allows your origin.'
      
      throw new Error(helpfulMessage)
    }
    throw error
  }
)

// Add request interceptor to log requests (for debugging)
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

export interface ActiveDeployments {
  count: number
  deployments: Array<{
    plan_id: string
    endpoint_name: string | null
    status: string
    environment: string | null
    instance_type: string | null
  }>
}

export interface PendingApprovals {
  count: number
  approvals: Array<{
    plan_id: string
    plan: any
    created_at: string
  }>
}

export interface MonthlyCosts {
  amount: number
  currency: string
  trend: 'up' | 'down' | 'stable'
  percent_change: number
  period?: {
    start: string
    end: string
  }
  error?: string
}

export interface Deployment {
  plan_id: string
  status: string
  user_id: string
  intent: string
  env: string
  artifact: {
    model_name: string
    endpoint_name: string
    instance_type: string
    instance_count: number
    budget_usd_per_hour: number
  }
  created_at: string
  updated_at?: string
  approval?: {
    decision: string | null
    approver?: string
    timestamp?: string
  }
}

export interface DeploymentsResponse {
  deployments: Deployment[]
  count: number
}

export interface AgentCommandRequest {
  command: string
  user_id?: string
  env?: string
  constraints?: Record<string, any>
}

export interface AgentCommandResponse {
  command_id: string
  status: string
  result?: {
    plan_id: string
    status: string
    artifact?: any
    requires_approval?: boolean
    errors?: string[] | string
  }
  error?: string
}

export const apiClient = {
  getActiveDeployments: async (): Promise<ActiveDeployments> => {
    const response = await api.get<ActiveDeployments>('/api/metrics/deployments/active')
    return response.data
  },

  getPendingApprovals: async (): Promise<PendingApprovals> => {
    const response = await api.get<PendingApprovals>('/api/metrics/approvals/pending')
    return response.data
  },

  getMonthlyCosts: async (): Promise<MonthlyCosts> => {
    const response = await api.get<MonthlyCosts>('/api/metrics/costs/monthly')
    return response.data
  },

  getDeployments: async (): Promise<DeploymentsResponse> => {
    const response = await api.get<DeploymentsResponse>('/api/deployments')
    return response.data
  },

  sendCommand: async (command: AgentCommandRequest): Promise<AgentCommandResponse> => {
    const response = await api.post<AgentCommandResponse>('/api/agent/command', command)
    return response.data
  },

  pauseDeployment: async (plan_id: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post<{ success: boolean; message: string }>(`/api/deployments/${plan_id}/pause`)
    return response.data
  },

  restartDeployment: async (plan_id: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post<{ success: boolean; message: string }>(`/api/deployments/${plan_id}/restart`)
    return response.data
  },

  deleteDeployment: async (plan_id: string, hardDelete: boolean = false): Promise<{ 
    success: boolean
    message: string
    details?: {
      plan_deleted: boolean
      sagemaker_resources_deleted: boolean
      agent_memory_deleted: boolean
      memory_count: number
      errors: string[]
    }
    warnings?: string[]
  }> => {
    const response = await api.delete<{ 
      success: boolean
      message: string
      details?: any
      warnings?: string[]
    }>(`/api/deployments/${plan_id}`, {
      params: { hard_delete: hardDelete }
    })
    return response.data
  },

  getDeploymentDetails: async (plan_id: string): Promise<Deployment> => {
    // Try to get from /plan/{plan_id} endpoint, or use deployment from list
    try {
      const response = await api.get<{ plan: Deployment; approval?: any }>(`/plan/${plan_id}`)
      return response.data.plan
    } catch (error) {
      // Fallback: get from deployments list
      const deploymentsResponse = await api.get<DeploymentsResponse>('/api/deployments')
      const deployment = deploymentsResponse.data.deployments.find(d => d.plan_id === plan_id)
      if (!deployment) {
        throw new Error(`Deployment ${plan_id} not found`)
      }
      return deployment
    }
  },

  getDeploymentStatus: async (plan_id: string): Promise<{
    plan_id: string
    status: string
    current_step?: string
    progress?: number
    steps?: Array<{
      step_id: string
      agent_type: string
      action: string
      status: string
      message?: string
    }>
  }> => {
    // Get deployment plan to extract reasoning steps
    try {
      const deployment = await apiClient.getDeploymentDetails(plan_id)
      const reasoningSteps = (deployment as any).reasoning_steps || []
      
      // Calculate progress based on completed steps
      const completedSteps = reasoningSteps.filter((s: any) => s.status === 'completed').length
      const totalSteps = reasoningSteps.length
      const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0
      
      // Find current active step
      const activeStep = reasoningSteps.find((s: any) => 
        ['thinking', 'executing', 'retrying'].includes(s.status)
      )
      
      return {
        plan_id,
        status: deployment.status,
        current_step: activeStep?.action,
        progress,
        steps: reasoningSteps.map((s: any) => ({
          step_id: s.step_id,
          agent_type: s.agent_type,
          action: s.action,
          status: s.status,
          message: s.output?.message || s.error,
        })),
      }
    } catch (error) {
      throw new Error(`Failed to get deployment status: ${error}`)
    }
  },

  getWorkflowExecutionPlan: async (plan_id: string): Promise<any> => {
    // Get deployment details which includes reasoning_steps (ExecutionPlan)
    const deployment = await apiClient.getDeploymentDetails(plan_id)
    return {
      plan_id: deployment.plan_id,
      steps: (deployment as any).reasoning_steps || [],
      reasoning_chain: undefined,
      created_at: deployment.created_at,
      updated_at: deployment.updated_at,
    }
  },

  retryWorkflowStep: async (plan_id: string, _step_id: string): Promise<{ success: boolean; message: string }> => {
    // For now, restart the entire deployment (can be enhanced to retry specific step)
    return apiClient.restartDeployment(plan_id)
  },
}

export default api

