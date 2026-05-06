import type { HomeownerRecord, CardState } from './types'
import { getState, lastSundayMidnight } from './storage'
import { fmtName } from './format'

const NO_ANSWER_RE = /\b(no answer|no show|not home|no contact|nobody home|did ?n'?t answer|rental)\b/i

function fmtMonthDay(d: Date): string {
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric' })
}

function fmtRange(start: Date, end: Date): string {
  const yr = end.getFullYear()
  if (start.toDateString() === end.toDateString()) return `${fmtMonthDay(start)} ${yr}`
  if (start.getMonth() === end.getMonth()) return `${fmtMonthDay(start)} – ${end.getDate()} ${yr}`
  return `${fmtMonthDay(start)} – ${fmtMonthDay(end)} ${yr}`
}

export function buildWeeklyReport(records: HomeownerRecord[], now: Date = new Date()): string {
  const sunday = lastSundayMidnight(now)
  const visits = records
    .map(r => ({ r, s: getState(r) as CardState }))
    .filter(({ s }) => s.visited && (s.visitedAt ?? 0) >= sunday)

  const isFriendly = (s: CardState) => {
    const note = (s.note ?? '').trim()
    return note.length > 0 && !NO_ANSWER_RE.test(note)
  }

  const friendly = visits.filter(({ s }) => isFriendly(s))
  const others = visits.filter(({ s }) => !isFriendly(s))
  const sorted = [...friendly, ...others]

  const header = `OIC Outreach Report — ${fmtRange(new Date(sunday), now)}`
  const summary = `${visits.length} household${visits.length === 1 ? '' : 's'} attempted, ${friendly.length} friendly conversation${friendly.length === 1 ? '' : 's'}`

  if (!visits.length) return `${header}\n(no visits logged this week)`

  const lines = sorted.map(({ r, s }, i) => {
    const note = (s.note ?? '').trim()
    return `\t${i + 1}.\t${fmtName(r.Owner1)}${note ? ` — ${note}` : ''}`
  })

  return [header, summary, ...lines].join('\n')
}
