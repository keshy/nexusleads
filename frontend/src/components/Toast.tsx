import { X, CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react'
import { useEffect } from 'react'

interface ToastProps {
  message: string
  type: 'success' | 'error' | 'warning' | 'info'
  onClose: () => void
  duration?: number
}

export default function Toast({ message, type, onClose, duration = 5000 }: ToastProps) {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onClose, duration)
      return () => clearTimeout(timer)
    }
  }, [duration, onClose])

  const getIcon = () => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
      case 'error':
        return <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
      case 'warning':
        return <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
      case 'info':
        return <Info className="w-5 h-5 text-blue-600 dark:text-blue-400" />
    }
  }

  const getStyles = () => {
    switch (type) {
      case 'success':
        return 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800'
      case 'error':
        return 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800'
      case 'warning':
        return 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800'
      case 'info':
        return 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800'
    }
  }

  return (
    <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 animate-in slide-in-from-top-2 duration-300">
      <div className={`flex items-start space-x-3 p-4 rounded-lg border shadow-lg max-w-md ${getStyles()}`}>
        {getIcon()}
        <p className="flex-1 text-sm text-gray-900 dark:text-gray-100">{message}</p>
        <button
          onClick={onClose}
          className="flex-shrink-0 p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
        >
          <X className="w-4 h-4 text-gray-600 dark:text-gray-400" />
        </button>
      </div>
    </div>
  )
}
