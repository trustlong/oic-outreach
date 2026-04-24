import type { HomeownerRecord } from './types'

export async function loadCSV(url: string): Promise<HomeownerRecord[]> {
  const res = await fetch(url)
  return parseCSV(await res.text()) as unknown as HomeownerRecord[]
}

function parseCSV(text: string): Record<string, string>[] {
  const lines = text.trim().split('\n')
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  return lines.slice(1).map(line => {
    const vals: string[] = []
    let cur = '', inQuote = false
    for (const ch of line) {
      if (ch === '"') { inQuote = !inQuote }
      else if (ch === ',' && !inQuote) { vals.push(cur.trim()); cur = '' }
      else { cur += ch }
    }
    vals.push(cur.trim())
    const obj: Record<string, string> = {}
    headers.forEach((h, i) => { obj[h] = vals[i] ?? '' })
    return obj
  })
}
