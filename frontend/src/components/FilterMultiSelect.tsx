import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, ChevronDown, Search } from 'lucide-react'

interface Option {
  value: string
  label: string
}

interface FilterMultiSelectProps {
  values: string[]
  onChange: (values: string[]) => void
  options: Option[]
  placeholder: string
  className?: string
  tone?: 'neutral' | 'include' | 'exclude'
}

export default function FilterMultiSelect({
  values,
  onChange,
  options,
  placeholder,
  className,
  tone = 'neutral',
}: FilterMultiSelectProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (!open) {
      setSearch('')
      return
    }
    setTimeout(() => searchRef.current?.focus(), 0)
  }, [open])

  const selectedLabels = useMemo(() => {
    const labels = new Map(options.map(option => [option.value, option.label]))
    return values.map(value => labels.get(value) || value)
  }, [options, values])

  const filteredOptions = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return options
    return options.filter(option => option.label.toLowerCase().includes(needle))
  }, [options, search])

  const activeTone = values.length ? tone : 'neutral'
  const activeButtonClasses = activeTone === 'exclude'
    ? 'border-rose-500/40 bg-rose-500/10 text-rose-700 dark:text-rose-300 dark:border-rose-400/30 dark:bg-rose-400/10 hover:border-rose-500/60 dark:hover:border-rose-400/50'
    : 'border-cyan-500/40 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 dark:border-cyan-400/30 dark:bg-cyan-400/10 hover:border-cyan-500/60 dark:hover:border-cyan-400/50'
  const activeOptionClasses = activeTone === 'exclude'
    ? 'bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300'
    : 'bg-cyan-50 dark:bg-cyan-900/20 text-cyan-700 dark:text-cyan-300'
  const activeCheckColor = activeTone === 'exclude' ? 'text-rose-500' : 'text-cyan-500'

  const summary = selectedLabels.length === 0
    ? placeholder
    : selectedLabels.length <= 2
      ? selectedLabels.join(', ')
      : `${selectedLabels.slice(0, 2).join(', ')} +${selectedLabels.length - 2}`

  const toggleValue = (value: string) => {
    if (values.includes(value)) {
      onChange(values.filter(existing => existing !== value))
      return
    }
    onChange([...values, value])
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`
          flex items-center justify-between gap-2 px-3 py-1.5 text-sm rounded-lg
          border transition-all duration-150 ${className || 'min-w-[180px]'}
          ${values.length
            ? activeButtonClasses
            : 'border-gray-200 dark:border-gray-600 bg-white/80 dark:bg-gray-800/80 text-gray-700 dark:text-gray-300 hover:border-cyan-500/60 dark:hover:border-cyan-400/50'
          }
          backdrop-blur-sm
        `}
      >
        <span className="truncate text-left">{summary}</span>
        <ChevronDown className={`w-3.5 h-3.5 flex-shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute z-[9999] mt-1 w-full min-w-[260px] rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 shadow-xl backdrop-blur-sm overflow-hidden">
          <div className="border-b border-gray-100 dark:border-gray-700 p-2">
            <div className="flex items-center gap-2 rounded-md border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-900/50 px-2">
              <Search className="h-3.5 w-3.5 text-gray-400" />
              <input
                ref={searchRef}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search options"
                className="w-full bg-transparent py-1.5 text-sm text-gray-700 dark:text-gray-200 outline-none placeholder:text-gray-400"
              />
              {values.length > 0 && (
                <button
                  type="button"
                  onClick={() => onChange([])}
                  className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
          <div className="max-h-72 overflow-y-auto py-1">
            {filteredOptions.length === 0 ? (
              <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">No matches found</div>
            ) : (
              filteredOptions.map((option) => {
                const selected = values.includes(option.value)
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => toggleValue(option.value)}
                    className={`
                      w-full flex items-center justify-between gap-3 px-3 py-2 text-sm transition-colors
                      ${selected
                        ? activeOptionClasses
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50'
                      }
                    `}
                  >
                    <span className="truncate text-left">{option.label}</span>
                    {selected && <Check className={`w-3.5 h-3.5 flex-shrink-0 ${activeCheckColor}`} />}
                  </button>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
