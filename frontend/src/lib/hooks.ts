import { useQuery, useMutation, useQueryClient } from 'react-query'
import { apiClient, AgentCommandRequest } from './api'

// Re-export useQueryClient for convenience
export { useQueryClient }

// Query hooks with automatic polling
export const useActiveDeployments = () => {
  return useQuery('activeDeployments', apiClient.getActiveDeployments, {
    refetchInterval: (data) => {
      // Poll every 5 seconds if there are active deployments, otherwise 60 seconds
      const hasActive = (data as any)?.count > 0
      return hasActive ? 5000 : 60000
    },
  })
}

export const usePendingApprovals = () => {
  return useQuery('pendingApprovals', apiClient.getPendingApprovals, {
    refetchInterval: (data) => {
      // Poll every 5 seconds if there are pending approvals, otherwise 60 seconds
      const hasPending = (data as any)?.count > 0
      return hasPending ? 5000 : 60000
    },
  })
}

export const useMonthlyCosts = () => {
  return useQuery('monthlyCosts', apiClient.getMonthlyCosts, {
    refetchInterval: 300000, // Poll every 5 minutes (costs change less frequently)
  })
}

export const useDeployments = () => {
  return useQuery('deployments', apiClient.getDeployments, {
    refetchInterval: (data) => {
      // Poll more frequently if any deployment is in progress
      const deployments = (data as any)?.deployments || []
      const hasInProgress = deployments.some((d: any) => 
        d.status === 'deploying' || d.status === 'pending_approval'
      )
      return hasInProgress ? 5000 : 60000 // 5 seconds if deploying, 60 seconds otherwise
    },
  })
}

export const useSendCommand = () => {
  const queryClient = useQueryClient()

  return useMutation(
    (command: AgentCommandRequest) => apiClient.sendCommand(command),
    {
      onSuccess: (data, variables) => {
        // Immediately refetch deployments to show new deployment
        queryClient.invalidateQueries()
        
        // Optimistically update deployments list
        if (data.status === 'success' && data.result) {
          queryClient.setQueryData('deployments', (old: any) => {
            const newDeployment = {
              plan_id: data.result?.plan_id || data.command_id,
              status: data.result?.status || 'deploying',
              intent: variables.command,
              user_id: variables.user_id || 'dashboard-user@agentops.ai',
              env: variables.env || 'staging',
              artifact: data.result?.artifact || {},
              created_at: new Date().toISOString(),
            }
            return {
              deployments: [newDeployment, ...(old?.deployments || [])],
              count: (old?.count || 0) + 1
            }
          })
          
          // Update active deployments if deploying/deployed
          if (data.result?.status === 'deploying' || data.result?.status === 'deployed') {
            queryClient.setQueryData('activeDeployments', (old: any) => ({
              count: (old?.count || 0) + 1,
              deployments: [
                ...(old?.deployments || []),
                {
                  plan_id: data.result?.plan_id || data.command_id,
                  endpoint_name: data.result?.artifact?.endpoint_name,
                  status: data.result?.status || 'deploying',
                  environment: variables.env || 'staging',
                  instance_type: data.result?.artifact?.instance_type
                }
              ]
            }))
          }
          
          // If requires approval, update pending approvals
          if (data.result?.requires_approval) {
            queryClient.setQueryData('pendingApprovals', (old: any) => ({
              count: (old?.count || 0) + 1,
              approvals: [
                ...(old?.approvals || []),
                {
                  plan_id: data.result?.plan_id || data.command_id,
                  created_at: new Date().toISOString()
                }
              ]
            }))
          }
        }
        
        // Refetch immediately to get accurate data
        queryClient.refetchQueries(['deployments', 'activeDeployments', 'pendingApprovals'], { exact: false })
      },
    }
  )
}

