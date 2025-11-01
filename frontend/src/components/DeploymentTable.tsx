import { useState, useRef, useEffect } from 'react'
import { useQueryClient } from 'react-query'
import { useDeployments } from '../lib/hooks'
import { formatDate, getStatusBadgeColor } from '../lib/utils'
import { ExternalLink, MoreVertical, FileText, Pause, RotateCw, X } from 'lucide-react'
import { apiClient } from '../lib/api'
import ConfirmDialog from './ConfirmDialog'
import DeploymentDetailsModal from './DeploymentDetailsModal'

export default function DeploymentTable() {
  const { data, isLoading, error } = useDeployments()
  const [selectedDeployment, setSelectedDeployment] = useState<any>(null)
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false)

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-red-200 dark:border-red-800 shadow-sm p-8">
        <p className="text-red-600 dark:text-red-400">Error loading deployments: {(error as Error).message}</p>
      </div>
    )
  }

  const deployments = data?.deployments || []

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-visible">
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Deployment Plans</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{deployments.length} total deployments</p>
      </div>

      <DeploymentDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={() => {
          setIsDetailsModalOpen(false)
          setSelectedDeployment(null)
        }}
        deployment={selectedDeployment}
      />

      {deployments.length === 0 ? (
        <div className="p-12 text-center">
          <p className="text-gray-500 dark:text-gray-400">No deployments yet. Use the command bar below to deploy a model.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full" style={{ tableLayout: 'auto' }}>
            <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Intent
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Endpoint
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Environment
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Instance
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider pr-6">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {deployments.map((deployment) => (
                <DeploymentTableRow 
                  key={deployment.plan_id} 
                  deployment={deployment}
                  onViewDetails={(deployment) => {
                    setSelectedDeployment(deployment)
                    setIsDetailsModalOpen(true)
                  }}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// Define DeploymentActionsMenu BEFORE DeploymentTableRow since it's used there
interface DeploymentActionsMenuProps {
  deployment: any
  onMenuToggle?: (isOpen: boolean) => void
  onViewDetails?: (deployment: any) => void
}

function DeploymentActionsMenu({ deployment, onMenuToggle, onViewDetails }: DeploymentActionsMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const queryClient = useQueryClient()

  // Notify parent when menu state changes
  useEffect(() => {
    if (onMenuToggle) {
      onMenuToggle(isOpen)
    }
  }, [isOpen, onMenuToggle])

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => {
        document.removeEventListener('mousedown', handleClickOutside)
      }
    }
  }, [isOpen])

  const handleViewDetails = () => {
    setIsOpen(false)
    if (onViewDetails) {
      onViewDetails(deployment)
    }
  }

  const handlePause = async () => {
    setIsOpen(false)
    setIsProcessing(true)
    try {
      await apiClient.pauseDeployment(deployment.plan_id)
      // Refresh deployments list
      queryClient.invalidateQueries('deployments')
    } catch (error) {
      console.error('Failed to pause deployment:', error)
      alert('Failed to pause deployment. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleRestart = async () => {
    setIsOpen(false)
    setIsProcessing(true)
    try {
      await apiClient.restartDeployment(deployment.plan_id)
      // Refresh deployments list
      queryClient.invalidateQueries('deployments')
    } catch (error) {
      console.error('Failed to restart deployment:', error)
      alert('Failed to restart deployment. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleDeleteClick = () => {
    setIsOpen(false)
    setShowDeleteDialog(true)
  }

  const handleDeleteConfirm = async () => {
    setIsProcessing(true)
    try {
      const response = await apiClient.deleteDeployment(deployment.plan_id)
      if (response.success) {
        setShowDeleteDialog(false)
        // Refresh deployments list
        queryClient.invalidateQueries('deployments')
      } else {
        throw new Error(response.message || 'Failed to delete deployment')
      }
    } catch (error: any) {
      console.error('Failed to delete deployment:', error)
      // Show error message but keep dialog open for retry
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to delete deployment. Please try again.'
      alert(errorMessage) // Could replace with a toast notification
      // Dialog will stay open on error so user can retry
    } finally {
      setIsProcessing(false)
    }
  }

  // Position menu using fixed positioning to prevent clipping
  useEffect(() => {
    if (isOpen && menuRef.current && buttonRef.current) {
      const buttonRect = buttonRef.current.getBoundingClientRect()
      const viewportHeight = window.innerHeight
      const viewportWidth = window.innerWidth
      const menuWidth = 224 // w-56 = 14rem = 224px
      const menuHeight = 200 // Approximate height
      
      // Calculate position
      let top: number | string = buttonRect.bottom + 8 // 8px = 0.5rem margin
      let right = viewportWidth - buttonRect.right
      let bottom: number | string = 'auto'
      
      // If menu would go off bottom, show above button
      if (buttonRect.bottom + menuHeight > viewportHeight) {
        top = 'auto'
        bottom = viewportHeight - buttonRect.top + 8
      }
      
      // If menu would go off right, adjust
      if (buttonRect.right + menuWidth > viewportWidth) {
        right = viewportWidth - buttonRect.right
      }
      
      menuRef.current.style.position = 'fixed'
      menuRef.current.style.top = typeof top === 'number' ? `${top}px` : 'auto'
      menuRef.current.style.bottom = typeof bottom === 'number' ? `${bottom}px` : 'auto'
      menuRef.current.style.right = `${right}px`
      menuRef.current.style.left = 'auto'
      menuRef.current.style.zIndex = '9999'
    }
  }, [isOpen])

  return (
    <div className="relative inline-block text-left">
      <button
        ref={buttonRef}
        onClick={() => setIsOpen(!isOpen)}
        disabled={isProcessing}
        className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        aria-label="Actions menu"
        aria-expanded={isOpen}
      >
        <MoreVertical className="w-5 h-5" />
      </button>

      {isOpen && (
        <>
          {/* Backdrop to close menu on outside click */}
          <div 
            className="fixed inset-0 z-[9998]" 
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <div
            ref={menuRef}
            className="fixed z-[9999] w-56 origin-top-right rounded-md bg-white dark:bg-gray-800 shadow-xl ring-1 ring-black ring-opacity-5 focus:outline-none border border-gray-200 dark:border-gray-700"
          >
          <div className="py-1" role="menu" aria-orientation="vertical">
            <button
              onClick={handleViewDetails}
              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              role="menuitem"
            >
              <FileText className="w-4 h-4 mr-3 text-gray-400 dark:text-gray-500" />
              View Details
            </button>

            <button
              onClick={handlePause}
              disabled={deployment.status === 'paused' || deployment.status === 'failed'}
              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              role="menuitem"
            >
              <Pause className="w-4 h-4 mr-3 text-gray-400 dark:text-gray-500" />
              Pause
            </button>

            <button
              onClick={handleRestart}
              disabled={deployment.status === 'deploying'}
              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              role="menuitem"
            >
              <RotateCw className="w-4 h-4 mr-3 text-gray-400 dark:text-gray-500" />
              Restart
            </button>

            <div className="border-t border-gray-200 dark:border-gray-700 my-1"></div>

            <button
              onClick={handleDeleteClick}
              className="flex items-center w-full px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              role="menuitem"
            >
              <X className="w-4 h-4 mr-3" />
              Delete
            </button>
          </div>
        </div>
        </>
      )}

      <ConfirmDialog
        isOpen={showDeleteDialog}
        onClose={() => {
          setShowDeleteDialog(false)
          setIsProcessing(false)
        }}
        onConfirm={handleDeleteConfirm}
        title="Delete Deployment"
        message={`Are you sure you want to delete deployment "${deployment.artifact?.endpoint_name || deployment.plan_id}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
        isLoading={isProcessing}
      />
    </div>
  )
}

interface DeploymentTableRowProps {
  deployment: any
  onViewDetails?: (deployment: any) => void
}

function DeploymentTableRow({ deployment, onViewDetails }: DeploymentTableRowProps) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  return (
    <tr className={`hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
      isMenuOpen ? 'bg-gray-50 dark:bg-gray-700' : ''
    }`}>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900 dark:text-white">{deployment.intent}</div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">{deployment.user_id}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-900 dark:text-gray-100 font-mono">
                        {deployment.artifact?.endpoint_name || 'N/A'}
                      </span>
                      {deployment.artifact?.endpoint_name && (
                        <ExternalLink className="w-4 h-4 text-gray-400 dark:text-gray-500" />
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                      deployment.env === 'prod' 
                        ? 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-400' 
                        : 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-400'
                    }`}>
                      {deployment.env.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 dark:text-gray-100 font-mono">
                      {deployment.artifact?.instance_type || 'N/A'}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">
                      {deployment.artifact?.instance_count || 0} instance{deployment.artifact?.instance_count !== 1 ? 's' : ''}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-3 py-1 text-xs font-medium rounded-full border ${getStatusBadgeColor(deployment.status)} dark:border-opacity-50`}>
                      {deployment.status.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {formatDate(deployment.created_at)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium pr-6">
                    <DeploymentActionsMenu 
                      deployment={deployment} 
                      onMenuToggle={setIsMenuOpen}
                      onViewDetails={onViewDetails}
                    />
                  </td>
                </tr>
  )
}

