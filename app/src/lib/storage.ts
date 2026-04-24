import type { HomeownerRecord, CardState } from './types'

export function cardKey(r: HomeownerRecord): string {
  const name = r.Owner1.replace(/[^a-z0-9]/gi, '').toLowerCase().slice(0, 12)
  const date = r.Sale1D.replace(/[^0-9]/g, '')
  const lat  = parseFloat(r.LAT || '0').toFixed(3)
  const lon  = parseFloat(r.LON || '0').toFixed(3)
  return `oic-${name}-${date}-${lat}-${lon}`
}

export function getState(r: HomeownerRecord): CardState {
  return JSON.parse(localStorage.getItem(cardKey(r)) ?? '{}')
}

export function setState(r: HomeownerRecord, patch: Partial<CardState>): void {
  const s = getState(r)
  localStorage.setItem(cardKey(r), JSON.stringify({ ...s, ...patch }))
}
