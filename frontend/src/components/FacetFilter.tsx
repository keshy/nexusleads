import StyledSelect from './StyledSelect'
import { getFilterTone, isFilterActive, type SelectFilterState } from '../lib/leadFilters'

interface Option {
  value: string
  label: string
}

interface FacetFilterProps {
  label: string
  filter: SelectFilterState
  onChange: (filter: SelectFilterState) => void
  options: Option[]
  placeholder: string
  className?: string
}

export default function FacetFilter({
  label,
  filter,
  onChange,
  options,
  placeholder,
  className,
}: FacetFilterProps) {
  const active = isFilterActive(filter)
  const exclude = filter.mode === 'exclude'

  return (
    <div className={className}>
      <div className="mb-1.5 text-xs font-medium text-gray-500 dark:text-gray-400">{label}</div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => onChange({ ...filter, mode: exclude ? 'include' : 'exclude' })}
          className={`
            shrink-0 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors
            ${active
              ? exclude
                ? 'border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-500/40 dark:bg-rose-500/10 dark:text-rose-300'
                : 'border-cyan-300 bg-cyan-50 text-cyan-700 dark:border-cyan-500/40 dark:bg-cyan-500/10 dark:text-cyan-300'
              : 'border-gray-200 bg-white text-gray-600 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300'
            }
          `}
          aria-label={`${label} filter mode: ${exclude ? 'exclude' : 'include'}`}
          title={exclude ? `Exclude matching ${label.toLowerCase()}` : `Include matching ${label.toLowerCase()}`}
        >
          {exclude ? 'is not' : 'is'}
        </button>
        <StyledSelect
          value={filter.value}
          onChange={(value) => onChange({ ...filter, value })}
          options={options}
          placeholder={placeholder}
          tone={getFilterTone(filter)}
          className="min-w-[180px] w-full"
        />
      </div>
    </div>
  )
}
