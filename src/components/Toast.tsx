import { useStore } from '../state/store'
import { Icon } from './Icon'

export function Toast() {
  const { s, t } = useStore()
  if (!s.toast) return null

  return (
    <div className="toast" role="status">
      <span
        style={{
          width: 30,
          height: 30,
          borderRadius: 999,
          background: 'var(--gold-500)',
          display: 'grid',
          placeItems: 'center',
          flex: 'none',
        }}
      >
        <Icon name="check" size={17} stroke={2.6} color="#FFFFFF" />
      </span>
      <span className="stack">
        <span style={{ fontSize: 15, fontWeight: 700 }}>{t.ready}</span>
        <span style={{ fontSize: 13, opacity: 0.75 }}>{t.toReviewCount(s.genCount)}</span>
      </span>
    </div>
  )
}
