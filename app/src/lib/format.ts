export function fmtName(n: string): string {
  return n.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ')
}

import type { EthnicityFilter } from './scoring'

export function ethLabel(e: EthnicityFilter): string {
  switch (e) {
    case 'all':      return ''
    case 'chinese':  return 'Chinese '
    case 'asian':    return 'Asian '
    case 'white':    return 'White '
    case 'hispanic': return 'Hispanic '
    case 'black':    return 'Black '
  }
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
