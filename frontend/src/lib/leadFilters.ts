export type FilterMode = 'include' | 'exclude'

export interface SelectFilterState {
  values: string[]
  mode: FilterMode
}

export function createEmptyFilter(): SelectFilterState {
  return { values: [], mode: 'include' }
}

export function isFilterActive(filter: SelectFilterState): boolean {
  return filter.values.length > 0
}

export function getFilterTone(filter: SelectFilterState): 'neutral' | FilterMode {
  return isFilterActive(filter) ? filter.mode : 'neutral'
}

export function serializeFilter(filter: SelectFilterState): string {
  return `${filter.mode}:${filter.values.slice().sort().join('|')}`
}
