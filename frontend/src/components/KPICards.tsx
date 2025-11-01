import { useActiveDeployments, usePendingApprovals, useMonthlyCosts } from '../lib/hooks'
import { formatCurrency } from '../lib/utils'
import { TrendingUp, TrendingDown, Minus, Server, Clock, DollarSign } from 'lucide-react'

export default function KPICards() {
  const { data: deployments, isLoading: deploymentsLoading } = useActiveDeployments()
  const { data: approvals, isLoading: approvalsLoading } = usePendingApprovals()
  const { data: costs, isLoading: costsLoading } = useMonthlyCosts()

  const cards = [
    {
      title: 'Active Deployments',
      value: deployments?.count ?? 0,
      icon: Server,
      color: 'blue',
      loading: deploymentsLoading,
    },
    {
      title: 'Pending Approvals',
      value: approvals?.count ?? 0,
      icon: Clock,
      color: 'yellow',
      loading: approvalsLoading,
    },
    {
      title: 'Monthly GPU Spend',
      value: costs ? formatCurrency(costs.amount, costs.currency) : '$0.00',
      subtitle: costs 
        ? `${costs.trend === 'up' ? '+' : costs.trend === 'down' ? '-' : ''}${costs.percent_change}% from last month`
        : '',
      icon: DollarSign,
      color: 'green',
      trend: costs?.trend,
      loading: costsLoading,
    },
  ]

  const getColorClasses = (color: string) => {
    const colors = {
      blue: 'bg-blue-50 border-blue-200 text-blue-900',
      yellow: 'bg-yellow-50 border-yellow-200 text-yellow-900',
      green: 'bg-green-50 border-green-200 text-green-900',
    }
    return colors[color as keyof typeof colors] || colors.blue
  }

  const getIconColor = (color: string) => {
    const colors = {
      blue: 'text-blue-600',
      yellow: 'text-yellow-600',
      green: 'text-green-600',
    }
    return colors[color as keyof typeof colors] || colors.blue
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {cards.map((card) => {
        const Icon = card.icon
        return (
          <div
            key={card.title}
            className={`${getColorClasses(card.color)} dark:border-opacity-50 rounded-xl border-2 p-6 shadow-sm transition-all hover:shadow-md`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <Icon className={`w-5 h-5 ${getIconColor(card.color)}`} />
                  <p className="text-sm font-medium opacity-80">{card.title}</p>
                </div>
                {card.loading ? (
                  <div className="h-8 w-24 bg-current opacity-20 rounded animate-pulse"></div>
                ) : (
                  <>
                    <p className="text-3xl font-bold mt-2">{card.value}</p>
                    {card.subtitle && (
                      <div className="flex items-center space-x-1 mt-2">
                        {card.trend === 'up' && <TrendingUp className="w-4 h-4" />}
                        {card.trend === 'down' && <TrendingDown className="w-4 h-4" />}
                        {card.trend === 'stable' && <Minus className="w-4 h-4" />}
                        <p className="text-xs opacity-70">{card.subtitle}</p>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

