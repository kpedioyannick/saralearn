import { Icon } from '../components/Icon'
import { NavHead } from '../components/ui'
import { useStore } from '../state/store'

/** Privé par défaut. Le public passe par une relecture. */
export function Publish() {
  const { s, set, go, goCreate, publishDraft, t } = useStore()

  if (s.published) {
    return (
      <div className="screen">
        <NavHead onBack={() => goCreate(4)} title={t.publication} />
        <div
          className="stack"
          style={{ flex: 1, justifyContent: 'center', gap: 22, padding: '0 30px' }}
        >
          <span
            className="anim-pop"
            style={{
              width: 72,
              height: 72,
              borderRadius: 999,
              background: 'var(--gold-500)',
              display: 'grid',
              placeItems: 'center',
            }}
          >
            <Icon name="check" size={36} stroke={2.2} color="#FFFFFF" />
          </span>
          <p className="display" style={{ fontSize: 32 }}>
            {s.pubPublic ? t.sentForReview : t.savedPrivate}
          </p>
          <p className="body">
            {s.pubPublic
              ? t.sentForReviewLine
              : t.savedPrivateLine}
          </p>
          <button className="btn-primary" onClick={() => go('exo', 'q')}>
            {t.backToExercises}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="screen">
      <NavHead onBack={() => goCreate(4)} title={t.publication} />

      <div className="screen-scroll stack" style={{ padding: '10px 22px 22px', gap: 18 }}>
        <p className="display" style={{ fontSize: 30 }}>
          {s.draftTitle || 'Nouveau thème'}
        </p>
        <p className="body" style={{ fontSize: 16 }}>
          {s.validated} exercice{s.validated > 1 ? 's' : ''} validé{s.validated > 1 ? 's' : ''}
          {s.draftTags.length > 0 ? ` · ${s.draftTags.join(' · ')}` : ''}
        </p>

        <div className="stack" style={{ gap: 10 }}>
          <VisibilityCard
            on={!s.pubPublic}
            onClick={() => set({ pubPublic: false })}
            icon="lock"
            title={t.privateLabel}
            badge={t.byDefault}
            line={t.privateLine}
          />
          <VisibilityCard
            on={s.pubPublic}
            onClick={() => set({ pubPublic: true })}
            icon="globe"
            title={t.publicLabel}
            line={t.publicLine}
          />
        </div>

        <div className="card-sunk">
          <p className="serif-italic" style={{ fontSize: 16 }}>
            {t.canSwitchLater}
          </p>
        </div>
      </div>

      <div className="footer-bar">
        <button className="btn-primary" onClick={() => void publishDraft(s.pubPublic)}>
          {s.pubPublic ? t.askPublication : t.savePrivate}
        </button>
      </div>
    </div>
  )
}

function VisibilityCard({
  on,
  onClick,
  icon,
  title,
  badge,
  line,
}: {
  on: boolean
  onClick: () => void
  icon: 'lock' | 'globe'
  title: string
  badge?: string
  line: string
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={on}
      className="stack"
      style={{
        padding: 16,
        borderRadius: 14,
        textAlign: 'left',
        cursor: 'pointer',
        gap: 6,
        border: `1.5px solid ${on ? 'var(--sc-primary)' : 'var(--sc-line)'}`,
        background: on ? 'var(--sc-primary-soft)' : 'var(--sc-surface)',
      }}
    >
      <span style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
        <Icon name={icon} size={18} stroke={1.9} color="var(--sc-text)" />
        <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--sc-text)' }}>{title}</span>
        {badge && (
          <span
            style={{
              height: 22,
              padding: '0 9px',
              borderRadius: 999,
              background: 'var(--sc-sunk)',
              fontSize: 11,
              fontWeight: 700,
              color: 'var(--sc-text3)',
              display: 'grid',
              placeItems: 'center',
            }}
          >
            {badge}
          </span>
        )}
      </span>
      <span style={{ fontSize: 14, lineHeight: 1.6, color: 'var(--sc-text2)' }}>{line}</span>
    </button>
  )
}
