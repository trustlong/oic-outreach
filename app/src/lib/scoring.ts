import type { HomeownerRecord, ScoredRecord, DateRange } from './types'
import { inRange } from './periods'

const ENTITY_RE = /\b(LLC|INC|CORP|LTD|LP|LLP|TRUST|TRUSTEE|TRS|PROPERTIES|PROPERTY|HOLDINGS|REALTY|GROUP|FUND|FOUNDATION|SERIES|CONSERVE|BUILDWELL|ENTERPRISES|PARTNERS|ASSOCIATION|ASSN|ASSOC|HOA|HOMEOWNERS|OWNERS|AUTHORITY|COMMISSION|DEPARTMENT|UTILITIES|UTILITY|CEMETERY|VFD|INTERNATIONAL|FELLOWSHIP|EXEC|EXECUTOR|EXECUTRIX|ADMINISTRATOR|ADMR|HEIRS?|ESTATE|ROAD|RD|STREET|AVENUE|AVE|DRIVE|DR|BOULEVARD|BLVD|HIGHWAY|HWY|PARKWAY|PKWY|TERRACE|WAY|CIRCLE|CIR|COUNTRY|VISTA|RIDGE|GROVE|MEADOW|VALLEY|ESTATES|VILLAGE|CROSSING|POINTE|COMMONS|RESERVE|HEIGHTS|LANDING)\b|\b(CITY|TOWN|COUNTY)\s+OF\b|\bFRIENDS\s+OF\b|\bET\s+AL\b/i

export function isEntity(owner: string): boolean {
  return ENTITY_RE.test(owner)
}

export type EthnicityFilter = 'all' | 'chinese' | 'asian' | 'white' | 'hispanic' | 'black'

export function matchesEthnicity(r: HomeownerRecord, f: EthnicityFilter): boolean {
  switch (f) {
    case 'all':      return true
    case 'chinese':  return r.IS_CHINESE === 'True'
    case 'asian':    return r.IS_CHINESE === 'True' || r.ESTIMATED_ETHNICITY === 'Asian/PI'
    case 'white':    return r.ESTIMATED_ETHNICITY === 'White'
    case 'hispanic': return r.ESTIMATED_ETHNICITY === 'Hispanic'
    case 'black':    return r.ESTIMATED_ETHNICITY === 'Black'
  }
}

export function distMiles(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 3958.8
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLon = (lon2 - lon1) * Math.PI / 180
  const a = Math.sin(dLat/2)**2 + Math.cos(lat1*Math.PI/180)*Math.cos(lat2*Math.PI/180)*Math.sin(dLon/2)**2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
}

// OIC serves both Chinese and English ministries — every newcomer is welcome,
// Chinese households still rank slightly higher to support the Chinese service.
function ethScore(r: HomeownerRecord): number {
  if (r.IS_CHINESE === 'True') return 2
  if (r.ESTIMATED_ETHNICITY === 'Asian/PI') return 1
  return 1
}

// OIC-based scoring (index page) — distance from church
export const OIC_LAT = 37.3244
export const OIC_LON = -79.2885

export function scoreOIC(r: HomeownerRecord): { score: number; dist: number } | null {
  const lat = parseFloat(r.LAT), lon = parseFloat(r.LON)
  if (isNaN(lat) || isNaN(lon)) return null
  const dist = distMiles(OIC_LAT, OIC_LON, lat, lon)
  const disS = dist <= 2 ? 3 : dist <= 5 ? 2 : dist <= 10 ? 1 : 0
  return { score: ethScore(r) + disS, dist }
}

// GPS-based scoring (near me page) — distance from user
export const NEARME_MAX_MILES = 3

export function scoreGPS(r: HomeownerRecord, uLat: number, uLon: number): { score: number; dist: number } | null {
  const lat = parseFloat(r.LAT), lon = parseFloat(r.LON)
  if (isNaN(lat) || isNaN(lon)) return null
  const dist = distMiles(uLat, uLon, lat, lon)
  if (dist > NEARME_MAX_MILES) return null
  const disS = dist <= 0.5 ? 3 : dist <= 1 ? 2 : dist <= 2 ? 1 : 0
  return { score: ethScore(r) + disS, dist }
}

export function top10(
  records: HomeownerRecord[],
  range: DateRange,
  scoreFn: (r: HomeownerRecord) => { score: number; dist: number } | null
): ScoredRecord[] {
  return records
    .filter(r => !isEntity(r.Owner1) && inRange(r.Sale1D, range))
    .map(r => { const s = scoreFn(r); return s ? { r, ...s } : null })
    .filter((x): x is ScoredRecord => x !== null)
    .sort((a, b) => b.score - a.score || a.dist - b.dist)
    .slice(0, 10)
}
