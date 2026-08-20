import { Icon } from '../components/Icon'
import { NavHead, PageBack } from '../components/ui'
import type { ApiTheme } from '../lib/api'
import { useStore } from '../state/store'

/**
 * Ce que je partage — mes connaissances publiées et leur écho.
 *
 * La planche montre quatre métriques par connaissance : utilisations,
 * j'aime, j'aime pas, commentaires. L'API n'en remonte aujourd'hui que
 * deux — le nombre d'abonnés et le nombre d'exercices. Les deux autres
 * sont affichées en tiret plutôt qu'estimées : un chiffre inventé sur
 * un tableau de bord d'auteur est pire que pas de chiffre du tout.
 */

function statusLabel(theme: ApiTheme, t: ReturnType<typeof useStore>['t']): string {
  if (theme.visibility === 'public') return t.publicLabel
  if (theme.visibility === 'pending') return t.pendingLabel
  return t.privateLabel
}

export function Shared() {
  const { myThemes, go, goCreate, set, t } = useStore()

  const published = myThemes.filter((x) => x.visibility !== 'private')
  const subscribers = myThemes.reduce((n, x) => n + x.subscriber_count, 0)
  const exercises = myThemes.reduce((n, x) => n + x.exercise_count, 0)

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('settings')} title={t.whatIShare} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner">
          <PageBack onClick={() => go('settings')} label={t.settings} />

          <header className="page-head">
            <h1 className="page-title">{t.whatIShare}</h1>
            <p className="page-lead">{t.whatIShareLead}</p>
          </header>

          <div className="share-hero">
            <span className="share-stat">
              <b>{myThemes.length}</b>
              <span>{t.learnings.toLowerCase()}</span>
            </span>
            <span className="share-stat">
              <b>{published.length}</b>
              <span>{t.publicLabel.toLowerCase()}</span>
            </span>
            <span className="share-stat">
              <b>{subscribers}</b>
              <span>{t.subscribers}</span>
            </span>
            <span className="share-stat">
              <b>{exercises}</b>
              <span>{t.exercises}</span>
            </span>
          </div>

          {myThemes.length === 0 && (
            <p className="serif-italic">{t.nothingShared}</p>
          )}

          <div className="stack" style={{ gap: 10 }}>
            {myThemes.map((th) => (
              <button
                key={th.id}
                className={th.visibility === 'private' ? 'share-card is-draft' : 'share-card'}
                onClick={() => set({ screen: 'sharedOne', sharedThemeId: th.id, sheet: null })}
              >
                <span style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                  <span className="stack" style={{ flex: 1, gap: 4, textAlign: 'left' }}>
                    <span style={{ fontSize: 17, fontWeight: 700 }}>{th.title}</span>
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                      {th.category_label ?? ''} · {t.exercisesCount(th.exercise_count)}
                    </span>
                  </span>
                  <span
                    className={
                      th.visibility === 'private' ? 'share-badge is-private' : 'share-badge'
                    }
                  >
                    {statusLabel(th, t)}
                  </span>
                </span>

                <span className="share-metrics">
                  <span className="share-metric">
                    <b>{th.subscriber_count}</b>
                    <span>{t.subscribers}</span>
                  </span>
                  <span className="share-metric">
                    <b>{th.exercise_count}</b>
                    <span>{t.exercises}</span>
                  </span>
                  <span className="share-metric">
                    <b>—</b>
                    <span>{t.usages}</span>
                  </span>
                  <span className="share-metric">
                    <b>—</b>
                    <span>{t.comments.toLowerCase()}</span>
                  </span>
                </span>
              </button>
            ))}
          </div>

          <p style={{ margin: 0, fontSize: 13, color: 'var(--sc-text3)' }}>
            {t.metricUnavailableLine}
          </p>
        </div>
      </div>

      <div className="footer-bar">
        <button className="btn-primary" onClick={() => goCreate(1)}>
          <Icon name="plus" size={18} stroke={2.2} />
          {t.shareKnowledge}
        </button>
      </div>
    </div>
  )
}

/** Le détail d'une connaissance : ses chiffres et ses exercices. */
export function SharedOne() {
  const { s, myThemes, sharedExercises, go, set, publishDraft, resumeDraft, t } = useStore()
  const theme = myThemes.find((x) => x.id === s.sharedThemeId) ?? null

  if (!theme) {
    // Deux absences que « Un instant… » confondait. Sans identifiant —
    // on est arrivé ici par l'URL — ou avec un identifiant qui ne
    // correspond à rien une fois la liste chargée, il n'y a rien à
    // attendre : le message tournait indéfiniment, et le retour est
    // masqué en desktop. C'était un cul-de-sac.
    const enAttente = s.sharedThemeId !== null && myThemes.length === 0

    return (
      <div className="screen">
        <div className="desk-hide">
          <NavHead onBack={() => go('shared')} title={t.whatIShare} />
        </div>
        <div className="screen-scroll page">
          <div className="page-inner">
            <PageBack onClick={() => go('shared')} label={t.whatIShare} />

            {enAttente ? (
              <p className="serif-italic">{t.oneMoment}</p>
            ) : (
              <div className="stack" style={{ gap: 16, alignItems: 'flex-start' }}>
                <p className="serif-italic">{t.sharedNotFound}</p>
                <button
                  className="btn-outline"
                  style={{ width: 'auto', padding: '0 22px' }}
                  onClick={() => go('shared')}
                >
                  {t.whatIShare}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('shared')} title={theme.title} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner">
          <PageBack onClick={() => go('shared')} label={t.whatIShare} />

          <header className="page-head">
            <h1 className="page-title">{theme.title}</h1>
            {theme.description && <p className="page-lead">{theme.description}</p>}
          </header>

          <div className="wrap" style={{ gap: 8 }}>
            <span
              className={theme.visibility === 'private' ? 'share-badge is-private' : 'share-badge'}
            >
              {statusLabel(theme, t)}
            </span>
            <span className="share-badge is-private">
              {theme.category_label ?? ''}
            </span>
            <span className="share-badge is-private">{t.exercisesCount(theme.exercise_count)}</span>
          </div>

          <div className="share-grid">
            <div className="stat-card">
              <b>{theme.subscriber_count}</b>
              <span>{t.subscribers}</span>
            </div>
            <div className="stat-card">
              <b>{theme.exercise_count}</b>
              <span>{t.exercises}</span>
            </div>
            <div className="stat-card">
              <b>—</b>
              <span>
                {t.usages} · {t.metricUnavailable}
              </span>
            </div>
            <div className="stat-card">
              <b>—</b>
              <span>
                {t.comments.toLowerCase()} · {t.metricUnavailable}
              </span>
            </div>
          </div>

          {theme.tags.length > 0 && (
            <div className="wrap" style={{ gap: 8 }}>
              {theme.tags.map((tag) => (
                <span key={tag} className="chip" style={{ cursor: 'default' }}>
                  {tag}
                </span>
              ))}
            </div>
          )}

          <section className="stack" style={{ gap: 10 }}>
            <span className="eyebrow">{t.exercisesOf}</span>
            {sharedExercises.length === 0 && (
              <p className="serif-italic">{t.noExerciseYet}</p>
            )}
            {sharedExercises.map((ex) => (
              <div key={ex.id} className="card" style={{ gap: 8 }}>
                <span className="eyebrow">{t[ex.type_question]}</span>
                <span style={{ fontSize: 17, fontWeight: 500, lineHeight: 1.3 }}>{ex.prompt}</span>
                <span style={{ fontSize: 14, color: 'var(--sc-text3)' }}>
                  {ex.options[ex.correct_index]?.label ?? ''}
                </span>
              </div>
            ))}
          </section>
        </div>
      </div>

      <div className="footer-bar" style={{ flexDirection: 'row', gap: 10 }}>
        {theme.visibility === 'private' && (
          <button
            className="btn-primary"
            onClick={() => {
              set({ draftThemeId: theme.id })
              void publishDraft(true)
            }}
          >
            {t.publishIt}
          </button>
        )}
        <button className="btn-outline" onClick={() => void resumeDraft(theme.id)}>
          {t.editExercises}
        </button>
      </div>
    </div>
  )
}
