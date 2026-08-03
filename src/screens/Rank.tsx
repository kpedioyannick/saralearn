import { Avatar, Dot, Meter, NavHead, meterColor } from '../components/ui'
import { useStore } from '../state/store'

/**
 * Classement.
 *
 * Un classement se lit d'abord par le haut : qui mène, de combien.
 * L'ancienne liste traitait la première place comme la douzième, dans
 * une colonne de 520 px au milieu de l'écran. Le podium sort donc les
 * trois premiers, et le reste suit en rangées — plus denses, puisqu'on
 * les parcourt au lieu de les regarder.
 *
 * Les forces, elles, se comparent : deux colonnes de jauges se lisent
 * d'un coup d'œil, une pile verticale demande de faire défiler.
 */
export function Rank() {
  const { s, go, set, progression, rankRows, themes, t } = useStore()
  const forces = s.tab === 'forces'
  const mine = themes.filter((x) => x.subscribed)

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('exo', 'q')} title={t.ranking} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner">
          <header className="page-head">
            <h1 className="page-title">{t.ranking}</h1>
            <p className="page-lead">{t.weeklyReset}</p>
          </header>

          <div className="segmented rank-tabs">
            <button
              className={forces ? 'segment is-on' : 'segment'}
              onClick={() => set({ tab: 'forces' })}
              aria-pressed={forces}
            >
              {t.myStrengths}
            </button>
            <button
              className={!forces ? 'segment is-on' : 'segment'}
              onClick={() => set({ tab: 'others' })}
              aria-pressed={!forces}
            >
              {t.others}
            </button>
          </div>

          {forces ? (
            <div className="stack" style={{ gap: 16 }}>
              <p className="serif-italic prose" style={{ fontSize: 17 }}>
                {t.strengthsIntro}
              </p>
              {progression.length === 0 && (
                <p className="body" style={{ fontSize: 16 }}>
                  {t.noStrengthsYet}
                </p>
              )}
              <div className="forces-grid">
                {progression.map((f, i) => (
                  <div key={f.theme_id} className="card" style={{ padding: '14px 16px', gap: 9 }}>
                    <span
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: 12,
                      }}
                    >
                      <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span className="rank-badge">{i + 1}</span>
                        <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--sc-text)' }}>
                          {f.name}
                        </span>
                      </span>
                      <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--sc-text3)' }}>
                        {f.passed}/{f.total} · {f.pct} %
                      </span>
                    </span>
                    <Meter pct={f.pct} fill={meterColor(f.pct)} />
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Sélecteur de thème à gauche, classement à droite : la
               maquette traite « les autres » comme un classement PAR
               thème, l'état existait déjà (s.rankTheme) sans écran
               pour le piloter. */
            <div className="rank-split">
              <aside className="rank-themes">
                <span className="eyebrow">{t.themes}</span>
                <button
                  className={s.rankTheme === 0 ? 'rank-theme is-on' : 'rank-theme'}
                  onClick={() => set({ rankTheme: 0 })}
                  aria-pressed={s.rankTheme === 0}
                >
                  {t.allThemes}
                </button>
                {mine.map((th) => (
                  <button
                    key={th.id}
                    className={s.rankTheme === th.id ? 'rank-theme is-on' : 'rank-theme'}
                    onClick={() => set({ rankTheme: th.id })}
                    aria-pressed={s.rankTheme === th.id}
                  >
                    <Dot color={th.color ?? 'var(--sc-primary)'} size={9} />
                    <span className="rank-theme-name">{th.title}</span>
                  </button>
                ))}
              </aside>

              <div className="stack" style={{ gap: 12 }}>
                {rankRows.length === 0 ? (
                  <p className="body" style={{ fontSize: 16 }}>
                    {t.nobodyYet}
                  </p>
                ) : (
                  <LeaderList rows={rankRows} />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export function RankOne() {
  const { exo, go, rankRows, progression, t } = useStore()
  const me = rankRows.find((r) => r.is_me)
  const progress = exo ? progression.find((p) => p.theme_id === exo.themeId) : undefined

  return (
    <div className="screen">
      <NavHead onBack={() => go('exo', 'q')}>
        {exo && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
            <Dot color={exo.color} size={10} />
            <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--sc-text)' }}>
              {exo.theme}
            </span>
          </span>
        )}
      </NavHead>

      <div className="screen-scroll stack" style={{ padding: '6px 22px 30px', gap: 16 }}>
        {me && (
          <div
            style={{
              padding: 18,
              borderRadius: 14,
              background: 'var(--sc-primary-soft)',
              border: '1px solid var(--sc-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: 16,
            }}
          >
            <span
              className="display"
              style={{ fontSize: 44, lineHeight: 1, color: 'var(--sc-primary)' }}
            >
              {me.rank}
              <span style={{ fontSize: 20 }}>{me.rank === 1 ? 'er' : 'e'}</span>
            </span>
            <span className="stack" style={{ gap: 3 }}>
              <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--sc-text)' }}>
                {t.yourPlace}
              </span>
              <span style={{ fontSize: 14, color: 'var(--sc-text2)' }}>
                {me.points} {t.points}
                {progress ? ` · ${progress.passed}/${progress.total} ${t.passed} · ${progress.pct} %` : ''}
              </span>
            </span>
          </div>
        )}

        <span className="eyebrow">{t.thisWeek}</span>
        <LeaderList rows={rankRows} />

        <p className="serif-italic" style={{ fontSize: 16 }}>
          {t.weeklyReset}
        </p>
      </div>
    </div>
  )
}

function LeaderList({ rows }: { rows: { rank: number; user_id: number; name: string; points: number; is_me: boolean }[] }) {
  const { t } = useStore()
  if (rows.length === 0) {
    return (
      <p className="body" style={{ fontSize: 16 }}>
        {t.nobodyYet}
      </p>
    )
  }
  return (
    <>
      {rows.map((o) => (
        <div
          key={o.user_id}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '12px 16px',
            borderRadius: 14,
            border: `1px solid ${o.is_me ? 'var(--sc-primary)' : 'var(--sc-line)'}`,
            background: o.is_me ? 'var(--sc-primary-soft)' : 'var(--sc-surface)',
          }}
        >
          <span
            style={{
              width: 28,
              fontSize: 15,
              fontWeight: 700,
              color: o.is_me ? 'var(--sc-primary)' : 'var(--sc-text3)',
            }}
          >
            {o.rank}
          </span>
          <Avatar name={o.name} color={o.is_me ? 'var(--sc-primary)' : 'var(--violet-500)'} />
          <span style={{ flex: 1, fontSize: 16, fontWeight: 600, color: 'var(--sc-text)' }}>
            {o.is_me ? t.you : o.name}
          </span>
          <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--sc-text2)' }}>
            {o.points}
          </span>
        </div>
      ))}
    </>
  )
}
