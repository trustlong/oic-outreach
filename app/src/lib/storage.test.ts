import { describe, it, expect, beforeEach } from 'vitest'
import { lastSundayMidnight, migrateVisitedTimestamps, getState, cardKey } from './storage'
import type { HomeownerRecord } from './types'

function rec(overrides: Partial<HomeownerRecord> = {}): HomeownerRecord {
  return {
    Owner1: 'TEST OWNER',
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

describe('lastSundayMidnight', () => {
  it('returns same Sunday at midnight when called on Sunday', () => {
    const sunday = new Date('2026-05-03T15:30:00')
    const ts = lastSundayMidnight(sunday)
    const d = new Date(ts)
    expect(d.getDay()).toBe(0)
    expect(d.getHours()).toBe(0)
    expect(d.getDate()).toBe(3)
    expect(d.getMonth()).toBe(4) // May
  })

  it('returns previous Sunday when called mid-week', () => {
    const tuesday = new Date('2026-05-05T22:30:00')
    const ts = lastSundayMidnight(tuesday)
    const d = new Date(ts)
    expect(d.getDay()).toBe(0)
    expect(d.getDate()).toBe(3)
  })

  it('returns previous Sunday when called on Saturday', () => {
    const saturday = new Date('2026-05-09T23:59:00')
    const ts = lastSundayMidnight(saturday)
    const d = new Date(ts)
    expect(d.getDay()).toBe(0)
    expect(d.getDate()).toBe(3)
  })
})

describe('migrateVisitedTimestamps', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('stamps visitedAt on legacy visited entries and sets migration flag', () => {
    const r = rec({ Owner1: 'ALPHA' })
    localStorage.setItem(cardKey(r), JSON.stringify({ visited: true, note: 'hi' }))

    migrateVisitedTimestamps()

    const state = getState(r)
    expect(state.visitedAt).toBeDefined()
    expect(state.visitedAt).toBe(lastSundayMidnight())
    expect(localStorage.getItem('oic-migrated-visitedAt')).toBe('1')
  })

  it('does not overwrite an existing visitedAt', () => {
    const r = rec({ Owner1: 'BETA' })
    const original = 1700000000000
    localStorage.setItem(cardKey(r), JSON.stringify({ visited: true, visitedAt: original }))

    migrateVisitedTimestamps()

    expect(getState(r).visitedAt).toBe(original)
  })

  it('skips entries that are not visited', () => {
    const r = rec({ Owner1: 'GAMMA' })
    localStorage.setItem(cardKey(r), JSON.stringify({ interested: true, note: 'maybe' }))

    migrateVisitedTimestamps()

    expect(getState(r).visitedAt).toBeUndefined()
  })

  it('is idempotent: subsequent calls do not re-stamp', () => {
    migrateVisitedTimestamps()
    const r = rec({ Owner1: 'DELTA' })
    // Add legacy entry AFTER first migration
    localStorage.setItem(cardKey(r), JSON.stringify({ visited: true }))

    migrateVisitedTimestamps()

    expect(getState(r).visitedAt).toBeUndefined()
  })

  it('ignores non-oic keys', () => {
    localStorage.setItem('unrelated-key', 'not-json')
    expect(() => migrateVisitedTimestamps()).not.toThrow()
  })

  it('survives malformed JSON in oic-* keys', () => {
    localStorage.setItem('oic-bogus', '{not json')
    expect(() => migrateVisitedTimestamps()).not.toThrow()
    expect(localStorage.getItem('oic-migrated-visitedAt')).toBe('1')
  })
})
