export interface HomeownerRecord {
  Owner1: string
  LocAddr: string
  Sale1D: string
  SalePrice: string
  SOURCE: string
  LAT: string
  LON: string
  ESTIMATED_ETHNICITY: string
  ETHNICITY_CONFIDENCE: string
  IS_CHINESE: string
  EST_HOUSEHOLD_SIZE: string
  HH_SIZE_BASIS: string
  MailCity: string
  MailStat: string
  DISTANCE_MILES: string
  VISITED: string
  NOTES: string
}

export interface ScoredRecord {
  r: HomeownerRecord
  score: number
  dist: number
}

export interface DateRange {
  start: Date
  end: Date | null
  label: string
}

export interface CardState {
  visited?: boolean
  interested?: boolean
  note?: string
}
