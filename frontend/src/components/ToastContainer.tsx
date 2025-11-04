import { X } from 'lucide-react'
import { useToast } from '../contexts/ToastContext'

export default function ToastContainer() {
  const { toasts, dismissToast } = useToast()

  const color = (variant: string) => {
    switch (variant) {
      case 'success':
        return 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800 text-green-800 dark:text-green-300'
      case 'error':
        return 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300'
      case 'warning':
        return 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-300'
      default:
        return 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300'
    }
  }

  return (
    <div className="fixed bottom-20 right-4 z-[10000] space-y-2 w-96 max-w-[95vw]">
      {toasts.map((t) => (
        <div key={t.id} className={`border rounded-lg shadow-md px-4 py-3 ${color(t.variant)}`}>
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1">
              {t.title && (
                <div className="text-sm font-semibold mb-0.5">{t.title}</div>
              )}
              <div className="text-sm leading-snug">{t.message}</div>
            </div>
            <button
              onClick={() => dismissToast(t.id)}
              className="text-current/70 hover:text-current"
              aria-label="Dismiss notification"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}


