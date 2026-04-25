import type { HomeownerRecord, ScoredRecord, DateRange } from './types'
import { inRange } from './periods'

const ENTITY_RE = /\b(LLC|INC|CORP|LTD|LP|LLP|TRUST|TRS|PROPERTIES|HOLDINGS|REALTY|GROUP|FUND|FOUNDATION|SERIES|CONSERVE|BUILDWELL|ENTERPRISES|PARTNERS)\b/i

export function isEntity(owner: string): boolean {
  return ENTITY_RE.test(owner)
}

export function distMiles(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 3958.8
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
}

function ethScore(r: HomeownerRecord): number {
  if (r.IS_CHINESE === 'True') return 3
  if (r.ESTIMATED_ETHNICITY === 'Asian/PI') return 2
  if (r.ESTIMATED_ETHNICITY === 'Hispanic' || r.ESTIMATED_ETHNICITY === 'Black') return 1
  return 0
}

function oriScore(r: HomeownerRecord): number {
  return r.MOVE_ORIGIN?.startsWith('Out-of-state') ? 2 : 1
}

// OIC-based scoring (index page) — distance from church
export const OIC_LAT = 37.3244
export const OIC_LON = -79.2885

export function scoreOIC(r: HomeownerRecord): { score: number; dist: number } | null {
  const lat = parseFloat(r.LAT), lon = parseFloat(r.LON)
  if (isNaN(lat) || isNaN(lon)) return null
  const dist = distMiles(OIC_LAT, OIC_LON, lat, lon)
  const disS = dist <= 5 ? 2 : dist <= 10 ? 1 : 0
  return { score: ethScore(r) + oriScore(r) + disS, dist }
}

// GPS-based scoring (near me page) — distance from user
export const NEARME_MAX_MILES = 3

export function scoreGPS(r: HomeownerRecord, uLat: number, uLon: number): { score: number; dist: number } | null {
  const lat = parseFloat(r.LAT), lon = parseFloat(r.LON)
  if (isNaN(lat) || isNaN(lon)) return null
  const dist = distMiles(uLat, uLon, lat, lon)
  if (dist > NEARME_MAX_MILES) return null
  const disS = dist <= 0.5 ? 3 : dist <= 1 ? 2 : dist <= 2 ? 1 : 0
  return { score: ethScore(r) + oriScore(r) + disS, dist }
}

export function top10(
  records: HomeownerRecord[],
  range: DateRange,
  scoreFn: (r: HomeownerRecord) => { score: number; dist: number } | null
): ScoredRecord[] {
  return records
    .filter(r => !isEntity(r.Owner1) && r.MOVE_ORIGIN !== 'Local' && inRange(r.Sale1D, range))
    .map(r => { const s = scoreFn(r); return s ? { r, ...s } : null })
    .filter((x): x is ScoredRecord => x !== null)
    .sort((a, b) => b.score - a.score || a.dist - b.dist)
    .slice(0, 10)
}
