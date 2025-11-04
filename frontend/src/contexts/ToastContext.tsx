import { createContext, useContext, useState, useCallback, ReactNode } from 'react'

type ToastVariant = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id: string
  title?: string
  message: string
  variant: ToastVariant
}

interface ToastContextValue {
  toasts: ToastItem[]
  showToast: (message: string, options?: { variant?: ToastVariant; title?: string; id?: string; durationMs?: number }) => void
  dismissToast: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback((message: string, options?: { variant?: ToastVariant; title?: string; id?: string; durationMs?: number }) => {
    const id = options?.id || Math.random().toString(36).slice(2)
    const item: ToastItem = {
      id,
      message,
      title: options?.title,
      variant: options?.variant || 'info',
    }
    setToasts((prev) => [item, ...prev].slice(0, 5))
    const duration = options?.durationMs ?? 5000
    if (duration > 0) {
      setTimeout(() => dismissToast(id), duration)
    }
  }, [dismissToast])

  return (
    <ToastContext.Provider value={{ toasts, showToast, dismissToast }}>
      {children}
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}


