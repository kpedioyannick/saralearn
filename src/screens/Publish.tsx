import { Icon } from '../components/Icon'
import { NavHead, PageBack } from '../components/ui'
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
      <div className="desk-hide">
        <NavHead onBack={() => goCreate(4)} title={t.publication} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner">
          {/* Retour à la relecture, pas au rail : on publie ce qu'on
              vient de relire, et sortir par le rail perdrait l'étape. */}
          <PageBack onClick={() => goCreate(4)} label={t.back} />

          <header className="page-head">
            <h1 className="page-title">{t.publication}</h1>
            <p className="page-lead">{s.draftTitle || t.newLearning}</p>
          </header>

          {/* Choix à gauche, récapitulatif à droite : la maquette pose
              1fr 380px, pour qu'on voie ce qu'on publie en décidant
              comment on le publie. */}
          <div className="split-380">
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
              <div className="card-sunk">
                <p className="serif-italic" style={{ fontSize: 16 }}>
                  {t.canSwitchLater}
                </p>
              </div>
            </div>

            <aside className="page-card">
              <span className="eyebrow">{t.summary}</span>
              <p className="display" style={{ fontSize: 22 }}>
                {s.draftTitle || t.newLearning}
              </p>
              <p className="body" style={{ fontSize: 15 }}>
                {t.validatedExercises(s.validated)}
              </p>
              {s.draftTags.length > 0 && (
                <div className="wrap">
                  {s.draftTags.map((tag) => (
                    <span key={tag} className="chip" style={{ cursor: 'default' }}>
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </aside>
          </div>
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
