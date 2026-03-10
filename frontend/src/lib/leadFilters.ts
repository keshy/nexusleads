export type FilterMode = 'include' | 'exclude'

export interface SelectFilterState {
  value: string
  mode: FilterMode
}

export function createEmptyFilter(): SelectFilterState {
  return { value: '', mode: 'include' }
}

export function isFilterActive(filter: SelectFilterState): boolean {
  return filter.value.length > 0
}

export function matchesFilter(candidate: string | null | undefined, filter: SelectFilterState): boolean {
  if (!filter.value) return true

  const matches = candidate === filter.value
  return filter.mode === 'exclude' ? !matches : matches
}

export function getFilterTone(filter: SelectFilterState): 'neutral' | FilterMode {
  return isFilterActive(filter) ? filter.mode : 'neutral'
}
