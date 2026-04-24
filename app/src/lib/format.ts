export function fmtName(n: string): string {
  return n.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ')
}

export function fmtOrigin(o: string): string {
  if (o.startsWith('Out-of-state')) return '✈ Moved from ' + o.replace('Out-of-state (', '').replace(')', '')
  if (o.startsWith('In-state')) return '↔ Moved within VA'
  return '? Origin unknown'
}

export function fmtAddr(s: string): string {
  return s.replace(/^\d+\.0\s*/, '').trim() || 'Address on file'
}

export const ETH_COLOR: Record<string, string> = {
  'Asian/PI':    '#1a73e8',
  'Hispanic':    '#e67e22',
  'Black':       '#8e44ad',
  'White':       '#7f8c8d',
  'Unknown':     '#95a5a6',
  'Am.Indian':   '#27ae60',
  'Multiracial': '#c0392b',
}
