import { AlertCircle } from 'lucide-react'

interface ConfirmDialogProps {
  title: string
  message: string
  onConfirm: () => void
  onCancel: () => void
  confirmText?: string
  cancelText?: string
}

export default function ConfirmDialog({
  title,
  message,
  onConfirm,
  onCancel,
  confirmText = 'Confirm',
  cancelText = 'Cancel'
}: ConfirmDialogProps) {
  return (
    <div className="mb-4 p-4 bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-lg">
      <div className="flex items-start space-x-3 mb-4">
        <AlertCircle className="w-6 h-6 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <p className="text-sm font-medium text-red-800 dark:text-red-200 mb-1">{title}</p>
          <p className="text-sm text-red-700 dark:text-red-300">{message}</p>
        </div>
      </div>
      <div className="flex items-center space-x-3">
        <button
          onClick={onConfirm}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium"
        >
          {confirmText}
        </button>
        <button
          onClick={onCancel}
          className="px-4 py-2 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-800 dark:text-gray-200 rounded-lg text-sm font-medium"
        >
          {cancelText}
        </button>
      </div>
    </div>
  )
}
