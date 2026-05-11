import { describe, it, expect, beforeEach } from 'vitest'
import { buildWeeklyReport } from './report'
import { cardKey, lastSundayMidnight } from './storage'
import type { HomeownerRecord, CardState } from './types'

function rec(owner: string, overrides: Partial<HomeownerRecord> = {}): HomeownerRecord {
  return {
    Owner1: owner,
    LocAddr: '123 Test St',
    Sale1D: '20240101',
    SalePrice: '500000',
    SOURCE: 'Bedford',
    LAT: '37.27',
    LON: '-79.81',
    ESTIMATED_ETHNICITY: 'Unknown',
    ETHNICITY_CONFIDENCE: '0',
    IS_CHINESE: '0',
    EST_HOUSEHOLD_SIZE: '4',
    HH_SIZE_BASIS: 'sqft',
    BR: '',
    MailCity: '',
    MailStat: '',
    DISTANCE_MILES: '5',
    VISITED: '',
    NOTES: '',
    ...overrides,
  }
}

function seed(r: HomeownerRecord, state: CardState) {
  localStorage.setItem(cardKey(r), JSON.stringify(state))
}

describe('buildWeeklyReport', () => {
  // Tuesday May 5 2026 — past Sunday is May 3
  const NOW = new Date('2026-05-05T22:00:00')

  beforeEach(() => {
    localStorage.clear()
  })

  it('reproduces the canonical example output', () => {
    const ts = lastSundayMidnight(NOW)
    const records = [
      rec('CHANG WAYNE & KIYANA P',          { Sale1D: '20240101', LAT: '37.27', LON: '-79.81' }),
      rec('VO NGUYEN AN',                    { Sale1D: '20240102', LAT: '37.28', LON: '-79.82' }),
      rec('PATEL NIRMIT',                    { Sale1D: '20240103', LAT: '37.29', LON: '-79.83' }),
      rec('SHI YONGYING',                    { Sale1D: '20240104', LAT: '37.30', LON: '-79.84' }),
      rec('HAMLETT EDWARD PHILLIP JR',       { Sale1D: '20240105', LAT: '37.31', LON: '-79.85' }),
      rec('BIRCH VICTOR A & BIRCH JEAN A',   { Sale1D: '20240106', LAT: '37.32', LON: '-79.86' }),
    ]
    const notes = [
      'Older, from Maryland; looks more Black than Asian',
      'Young, no kids, no religion; works at Framatome',
      'Hindu, no kids; near Leesville & Heritage School, across from Beula',
      'Rental property sign (no contact)',
      'No answer',
      'No answer',
    ]
    records.forEach((r, i) => seed(r, { visited: true, visitedAt: ts, note: notes[i] }))

    const expected = [
      'OIC Outreach Report — May 3 – 5 2026',
      '6 households attempted, 3 friendly conversations',
      '\t1.\tChang Wayne & Kiyana P — Older, from Maryland; looks more Black than Asian',
      '\t2.\tVo Nguyen An — Young, no kids, no religion; works at Framatome',
      '\t3.\tPatel Nirmit — Hindu, no kids; near Leesville & Heritage School, across from Beula',
      '\t4.\tShi Yongying — Rental property sign (no contact)',
      '\t5.\tHamlett Edward Phillip Jr — No answer',
      '\t6.\tBirch Victor A & Birch Jean A — No answer',
    ].join('\n')

    expect(buildWeeklyReport(records, NOW)).toBe(expected)
  })

  it('returns an empty-week message when no visits this week', () => {
    const records = [rec('SOMEONE')]
    const out = buildWeeklyReport(records, NOW)
    expect(out).toBe('OIC Outreach Report — May 3 – 5 2026\n(no visits logged this week)')
  })

  it('excludes visits from before this Sunday', () => {
    const records = [rec('OLD VISIT'), rec('NEW VISIT')]
    const oldTs = new Date('2026-04-25T12:00:00').getTime() // last week
    const newTs = new Date('2026-05-04T12:00:00').getTime() // Monday this week
    seed(records[0], { visited: true, visitedAt: oldTs, note: 'old' })
    seed(records[1], { visited: true, visitedAt: newTs, note: 'new' })

    const out = buildWeeklyReport(records, NOW)
    expect(out).toContain('1 household attempted')
    expect(out).toContain('New Visit')
    expect(out).not.toContain('Old Visit')
  })

  it('classifies notes as friendly only when substantive', () => {
    const records = [
      rec('FRIENDLY ALICE'),
      rec('NO ANSWER BOB'),
      rec('NOT HOME CAROL'),
      rec('RENTAL DAVE'),
      rec('NOBODY HOME EVE'),
      rec('DIDNT ANSWER FRANK'),
      rec('EMPTY NOTE GINA'),
    ]
    const ts = lastSundayMidnight(NOW)
    seed(records[0], { visited: true, visitedAt: ts, note: 'Had a great chat about kids' })
    seed(records[1], { visited: true, visitedAt: ts, note: 'No answer' })
    seed(records[2], { visited: true, visitedAt: ts, note: 'Not home' })
    seed(records[3], { visited: true, visitedAt: ts, note: 'Rental — landlord' })
    seed(records[4], { visited: true, visitedAt: ts, note: 'nobody home' })
    seed(records[5], { visited: true, visitedAt: ts, note: "didn't answer" })
    seed(records[6], { visited: true, visitedAt: ts, note: '' })

    const out = buildWeeklyReport(records, NOW)
    expect(out).toContain('7 households attempted, 1 friendly conversation')
  })

  it('places friendly conversations before no-answer entries', () => {
    const records = [rec('NO ANSWER FIRST'), rec('FRIENDLY SECOND')]
    const ts = lastSundayMidnight(NOW)
    seed(records[0], { visited: true, visitedAt: ts, note: 'No answer' })
    seed(records[1], { visited: true, visitedAt: ts, note: 'Lovely conversation' })

    const out = buildWeeklyReport(records, NOW)
    const friendlyIdx = out.indexOf('Friendly Second')
    const noAnswerIdx = out.indexOf('No Answer First')
    expect(friendlyIdx).toBeLessThan(noAnswerIdx)
    expect(out).toContain('\t1.\tFriendly Second')
    expect(out).toContain('\t2.\tNo Answer First')
  })

  it('formats single-day range without the dash', () => {
    const sunday = new Date('2026-05-03T18:00:00')
    const records = [rec('TODAY ONLY')]
    seed(records[0], { visited: true, visitedAt: lastSundayMidnight(sunday), note: 'visited' })

    const out = buildWeeklyReport(records, sunday)
    expect(out).toContain('OIC Outreach Report — May 3 2026')
  })

  it('formats cross-month range with both month names', () => {
    // Sunday April 26 → Saturday May 2 — but week resets each Sunday, so use a date late in this run
    // Today = Friday May 1 2026 → last Sunday = April 26
    const friday = new Date('2026-05-01T18:00:00')
    const records = [rec('CROSS MONTH')]
    seed(records[0], { visited: true, visitedAt: lastSundayMidnight(friday), note: 'visited' })

    const out = buildWeeklyReport(records, friday)
    expect(out).toContain('OIC Outreach Report — April 26 – May 1 2026')
  })

  it('omits the dash when only one household attempted', () => {
    const records = [rec('ONLY ONE')]
    seed(records[0], { visited: true, visitedAt: lastSundayMidnight(NOW), note: 'good chat' })

    const out = buildWeeklyReport(records, NOW)
    expect(out).toContain('1 household attempted, 1 friendly conversation')
  })
})
