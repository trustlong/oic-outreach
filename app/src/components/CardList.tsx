import type { ScoredRecord } from '../lib/types'
import Card from './Card'

interface Props {
  items: ScoredRecord[]
  onFollowUpChange: () => void
}

export default function CardList({ items, onFollowUpChange }: Props) {
  if (!items.length) {
    return <div style={{ textAlign: 'center', color: '#bbb', padding: '40px 16px', fontSize: '.9em' }}>No records for this period.</div>
  }
  return (
    <div style={{ padding: '0 12px 80px' }}>
      {items.map((item, i) => (
        <Card key={`${item.r.Owner1}-${item.r.Sale1D}-${item.r.LAT}`} item={item} rank={i + 1} onFollowUpChange={onFollowUpChange} />
      ))}
    </div>
  )
}
