import type { EthnicityFilter } from '../lib/scoring'
import type { Period } from '../lib/periods'

export type { Period }
export type Ethnicity = EthnicityFilter

interface Props {
  period: Period
  onPeriodChange: (p: Period) => void
  ethnicity: Ethnicity
  onEthnicityChange: (e: Ethnicity) => void
}

const SELECT_STYLE: React.CSSProperties = {
  flex: '1 1 0',
  minWidth: 140,
  padding: '10px 32px 10px 12px',
  fontSize: '.85em',
  fontWeight: 600,
  border: '2px solid #1a73e8',
  borderRadius: 8,
  background: 'white',
  color: '#1a73e8',
  cursor: 'pointer',
  appearance: 'none',
  WebkitAppearance: 'none',
  backgroundImage:
    'url("data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'12\' height=\'12\' viewBox=\'0 0 12 12\'><path fill=\'%231a73e8\' d=\'M6 8.5L2 4.5h8z\'/></svg>")',
  backgroundRepeat: 'no-repeat',
  backgroundPosition: 'right 10px center',
}

export default function Filters({ period, onPeriodChange, ethnicity, onEthnicityChange }: Props) {
  return (
    <div style={{ display: 'flex', gap: 10, padding: '14px 16px' }}>
      <select
        value={period}
        onChange={e => onPeriodChange(e.target.value as Period)}
        style={SELECT_STYLE}
      >
        <option value="month">Last Month</option>
        <option value="3months">Last 3 Months</option>
        <option value="6months">Last 6 Months</option>
        <option value="year">Past 12 Months</option>
      </select>

      <select
        value={ethnicity}
        onChange={e => onEthnicityChange(e.target.value as Ethnicity)}
        style={SELECT_STYLE}
      >
        <option value="all">All ethnicities</option>
        <option value="chinese">Chinese</option>
        <option value="asian">Asian (incl. Chinese)</option>
        <option value="white">White</option>
        <option value="hispanic">Hispanic</option>
        <option value="black">Black</option>
      </select>
    </div>
  )
}
