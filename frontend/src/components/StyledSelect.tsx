import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Check } from 'lucide-react'

interface Option {
  value: string
  label: string
}

interface StyledSelectProps {
  value: string
  onChange: (value: string) => void
  options: Option[]
  placeholder: string
}

export default function StyledSelect({ value, onChange, options, placeholder }: StyledSelectProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const selected = options.find(o => o.value === value)

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`
          flex items-center justify-between gap-2 px-3 py-1.5 text-sm rounded-lg
          border transition-all duration-150 min-w-[160px]
          ${value
            ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 dark:border-cyan-400/30 dark:bg-cyan-400/10'
            : 'border-gray-200 dark:border-gray-600 bg-white/80 dark:bg-gray-800/80 text-gray-700 dark:text-gray-300'
          }
          hover:border-cyan-500/60 dark:hover:border-cyan-400/50
          backdrop-blur-sm
        `}
      >
        <span className="truncate">{selected ? selected.label : placeholder}</span>
        <ChevronDown className={`w-3.5 h-3.5 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute z-[9999] mt-1 w-full min-w-[200px] py-1 rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-xl backdrop-blur-sm overflow-hidden">
          <div className="max-h-60 overflow-y-auto">
            {options.map((option) => (
              <button
                key={option.value}
                onClick={() => { onChange(option.value); setOpen(false) }}
                className={`
                  w-full flex items-center justify-between px-3 py-2 text-sm transition-colors
                  ${option.value === value
                    ? 'bg-cyan-50 dark:bg-cyan-900/20 text-cyan-700 dark:text-cyan-300'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }
                `}
              >
                <span className="truncate">{option.label}</span>
                {option.value === value && <Check className="w-3.5 h-3.5 flex-shrink-0 text-cyan-500" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
