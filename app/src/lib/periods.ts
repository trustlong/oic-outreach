import type { DateRange } from './types'

const MONTH_NAMES = ['January','February','March','April','May','June',
  'July','August','September','October','November','December']

export function lastMonthRange(): DateRange {
  const now = new Date()
  const end   = new Date(now.getFullYear(), now.getMonth(), 1)
  const start = new Date(end.getFullYear(), end.getMonth() - 1, 1)
  return { start, end, label: `${MONTH_NAMES[start.getMonth()]} ${start.getFullYear()}` }
}

export function lastYearRange(): DateRange {
  const start = new Date()
  start.setFullYear(start.getFullYear() - 1)
  return { start, end: null, label: 'Past 12 Months' }
}

export function parseDate(s: string): Date | null {
  for (const re of [/(\d{2})\/(\d{2})\/(\d{4})/, /(\d{4})-(\d{2})-(\d{2})/]) {
    const m = s.match(re)
    if (m) return re.source.startsWith('(\\d{2})')
      ? new Date(+m[3], +m[1] - 1, +m[2])
      : new Date(+m[1], +m[2] - 1, +m[3])
  }
  return null
}

export function inRange(dateStr: string, range: DateRange): boolean {
  const d = parseDate(dateStr)
  return !!d && d >= range.start && (range.end === null || d < range.end)
}
