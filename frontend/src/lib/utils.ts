import { type ClassValue, clsx } from "clsx"

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

export function getStatusBadgeColor(status: string): string {
  const statusLower = status.toLowerCase()
  
  if (statusLower.includes('deployed')) {
    return 'bg-green-100 text-green-800 border-green-200'
  } else if (statusLower.includes('deploying')) {
    return 'bg-blue-100 text-blue-800 border-blue-200'
  } else if (statusLower.includes('pending') || statusLower.includes('approval')) {
    return 'bg-yellow-100 text-yellow-800 border-yellow-200'
  } else if (statusLower.includes('failed') || statusLower.includes('rejected')) {
    return 'bg-red-100 text-red-800 border-red-200'
  } else {
    return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

