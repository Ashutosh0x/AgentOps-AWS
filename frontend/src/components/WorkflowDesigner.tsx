import { useState, useEffect } from 'react'
import { useQuery } from 'react-query'
import WorkflowGraph from './WorkflowGraph'
import ExecutionPanel from './ExecutionPanel'
import WorkflowCommandBar from './WorkflowCommandBar'
import { apiClient } from '../lib/api'
import { executionPlanToGraph, ExecutionPlan } from '../lib/workflowTransform'

// Realistic workflow based on actual codebase flow
const REALISTIC_DEMO_WORKFLOW: ExecutionPlan = {
  plan_id: 'demo',
  steps: [
    {
      step_id: 'demo-retriever-1',
      agent_type: 'retriever',
      action: 'retrieve_policies',
      status: 'completed',
    },
    {
      step_id: 'demo-planner-1',
      agent_type: 'planner',
      action: 'generate_config',
      status: 'completed',
    },
    {
      step_id: 'demo-executor-1',
      agent_type: 'executor',
      action: 'validate_plan',
      status: 'completed',
    },
    {
      step_id: 'demo-executor-2',
      agent_type: 'executor',
      action: 'create_model',
      status: 'executing',
    },
    {
      step_id: 'demo-executor-3',
      agent_type: 'executor',
      action: 'create_endpoint_config',
      status: 'pending',
    },
    {
      step_id: 'demo-executor-4',
      agent_type: 'executor',
      action: 'create_endpoint',
      status: 'pending',
    },
    {
      step_id: 'demo-monitor-1',
      agent_type: 'monitor',
      action: 'configure_monitoring',
      status: 'pending',
    },
    {
      step_id: 'demo-monitor-2',
      agent_type: 'monitor',
      action: 'verify_deployment',
      status: 'pending',
    },
  ],
}

export default function WorkflowDesigner() {
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [nodes, setNodes] = useState<any[]>([])
  const [edges, setEdges] = useState<any[]>([])

  // Fetch all deployments to show list
  const { data: deploymentsResponse } = useQuery(
    'deployments-list',
    () => apiClient.getDeployments(),
    {
      refetchInterval: 5000, // Refresh every 5 seconds to get latest
    }
  )

  // Fetch deployment details and transform to graph
  const { data: deployment, isLoading } = useQuery(
    ['workflow-deployment', selectedPlanId],
    () => apiClient.getDeploymentDetails(selectedPlanId!),
    {
      enabled: !!selectedPlanId,
      refetchInterval: (data) => {
        // Poll every 2 seconds if deployment is in progress
        if (data?.status && !['deployed', 'failed', 'deleted'].includes(data.status)) {
          return 2000
        }
        return false
      },
    }
  )

  // Auto-select most recent deployment if none selected
  useEffect(() => {
    if (!selectedPlanId && deploymentsResponse && deploymentsResponse.deployments && deploymentsResponse.deployments.length > 0) {
      const mostRecent = [...deploymentsResponse.deployments]
        .sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
      setSelectedPlanId(mostRecent.plan_id)
    }
  }, [deploymentsResponse, selectedPlanId])

  // Transform deployment to graph when data changes
  useEffect(() => {
    if (deployment) {
      const executionPlan: ExecutionPlan = {
        plan_id: deployment.plan_id,
        steps: (deployment as any).reasoning_steps || [],
        reasoning_chain: undefined,
        created_at: deployment.created_at,
        updated_at: deployment.updated_at,
      }

      const evidence = (deployment as any).evidence || []
      const graph = executionPlanToGraph(executionPlan, evidence)
      setNodes(graph.nodes)
      setEdges(graph.edges)
    } else if (!selectedPlanId && (!deploymentsResponse || !deploymentsResponse.deployments || deploymentsResponse.deployments.length === 0)) {
      // Show realistic demo workflow only if no deployments exist
      const demoGraph = executionPlanToGraph(REALISTIC_DEMO_WORKFLOW, [])
      setNodes(demoGraph.nodes)
      setEdges(demoGraph.edges)
    }
  }, [deployment, selectedPlanId, deploymentsResponse])

  // Handle command submission - set the new plan ID
  const handleCommandSubmit = (planId: string) => {
    setSelectedPlanId(planId)
  }

  // Handle deployment deletion - clear selection and reload
  const handleDeploymentDeleted = () => {
    setSelectedPlanId(null)
    setSelectedNodeId(null)
    // Query will auto-refresh and show demo or select next deployment
  }

  // Get selected node data
  const selectedNode = nodes.find((n) => n.id === selectedNodeId)

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 88px)' }}>
      {/* Main workflow area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Graph area */}
        <div className="flex-1 relative bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700">
          {isLoading && selectedPlanId ? (
            <div className="absolute inset-0 p-6">
              <div className="animate-pulse space-y-4">
                <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
                <div className="grid grid-cols-3 gap-4">
                  <div className="h-32 bg-gray-100 dark:bg-gray-800 rounded"></div>
                  <div className="h-32 bg-gray-100 dark:bg-gray-800 rounded"></div>
                  <div className="h-32 bg-gray-100 dark:bg-gray-800 rounded"></div>
                </div>
              </div>
            </div>
          ) : (
            <WorkflowGraph
              nodes={nodes}
              edges={edges}
              selectedNodeId={selectedNodeId}
              onNodeSelect={setSelectedNodeId}
              planId={selectedPlanId}
            />
          )}
        </div>

        {/* Execution panel */}
        <div className="w-96 bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 overflow-y-auto">
          <ExecutionPanel
            selectedNode={selectedNode}
            planId={selectedPlanId}
            deployment={deployment}
            onDeploymentDeleted={handleDeploymentDeleted}
          />
        </div>
      </div>

      {/* Command console */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <WorkflowCommandBar onCommandSubmit={handleCommandSubmit} />
      </div>
    </div>
  )
}

