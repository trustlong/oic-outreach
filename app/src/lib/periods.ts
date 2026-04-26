import type { DateRange } from './types'

const MONTH_NAMES = ['January','February','March','April','May','June',
  'July','August','September','October','November','December']

export type Period = 'month' | '3months' | '6months' | 'year'

export function lastMonthRange(): DateRange {
  const now = new Date()
  const end   = new Date(now.getFullYear(), now.getMonth(), 1)
  const start = new Date(end.getFullYear(), end.getMonth() - 1, 1)
  return { start, end, label: `${MONTH_NAMES[start.getMonth()]} ${start.getFullYear()}` }
}

function lastNMonthsRange(n: number, label: string): DateRange {
  const start = new Date()
  start.setMonth(start.getMonth() - n)
  return { start, end: null, label }
}

export function lastYearRange(): DateRange {
  return lastNMonthsRange(12, 'Past 12 Months')
}

export function getRange(period: Period): DateRange {
  switch (period) {
    case 'month':   return lastMonthRange()
    case '3months': return lastNMonthsRange(3, 'Last 3 Months')
    case '6months': return lastNMonthsRange(6, 'Last 6 Months')
    case 'year':    return lastYearRange()
  }
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
