import { Icon } from '../components/Icon'
import { Avatar, Dot, Meter, NavHead, PageBack, meterColor } from '../components/ui'
import { useStore } from '../state/store'

/**
 * Classement.
 *
 * « Les autres » est un classement PAR apprentissage : sélecteur à
 * gauche, liste à droite. La nouvelle planche remet un podium en tête
 * de cette liste — il avait été retiré de la précédente. Les trois
 * premiers ne se lisent pas comme les suivants : on les regarde, on ne
 * les parcourt pas, et une ligne de tableau ne dit pas ça.
 *
 * Les forces se lisent en colonne, bornées à 860px : au-delà, l'œil
 * ne relie plus le nom de l'apprentissage à sa jauge.
 */
export function Rank() {
  const { s, go, set, progression, rankRows, themes, t } = useStore()
  const forces = s.tab === 'forces'
  const mine = themes.filter((x) => x.subscribed)

  // Le premier de la liste est le point fort, le dernier celui qu'il
  // faut reprendre : l'API rend la progression du mieux réussi au moins
  // bon. Avec un seul apprentissage commencé, les deux sont le même —
  // on ne pose alors que la carte du haut.
  const [best, ...rest] = progression
  const weakest = progression.length > 1 ? progression[progression.length - 1] : undefined

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('exo', 'q')} title={t.ranking} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner is-full">
          <header className="page-head is-inline">
            <h1 className="page-title">{t.ranking}</h1>
            <p className="page-lead">{t.rankLead}</p>
          </header>

          <div className="segmented rank-tabs">
            <button
              className={forces ? 'segment is-on' : 'segment'}
              onClick={() => set({ tab: 'forces' })}
              aria-pressed={forces}
            >
              {t.myProgress}
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
            /* Deux colonnes égales : où j'en suis à gauche, où je me
               situe à droite. La planche les pose ensemble parce que
               l'une ne se lit pas sans l'autre — un pourcentage ne dit
               rien tant qu'on ne sait pas ce que font les autres. */
            <div className="rank-body">
              <section className="rank-col">
                <span className="mono">{t.byTheme}</span>

                {progression.length === 0 && (
                  <p className="body" style={{ fontSize: 16 }}>
                    {t.noStrengthsYet}
                  </p>
                )}

                {best && (
                  <div className="rank-best">
                    <div className="rank-line-head">
                      <span style={{ fontSize: 19, fontWeight: 700 }}>{best.name}</span>
                      <span className="rank-best-pct">{best.pct} %</span>
                    </div>
                    <Meter pct={best.pct} fill={meterColor(best.pct)} />
                    <span style={{ fontSize: 14, color: 'var(--sc-text3)' }}>
                      {t.yourStrength} · {t.exercisesCount(best.total)}
                    </span>
                  </div>
                )}

                {rest.map((f) => (
                  <div key={f.theme_id} className="rank-line">
                    <div className="rank-line-head">
                      <span style={{ fontSize: 16 }}>{f.name}</span>
                      <span className="rank-pct">{f.pct} %</span>
                    </div>
                    <Meter pct={f.pct} fill={meterColor(f.pct)} />
                    {f === weakest && (
                      <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                        {t.toResume} · {f.passed}/{f.total} {t.passed}
                      </span>
                    )}
                  </div>
                ))}
              </section>

              <section className="rank-col">
                <div className="rank-col-head">
                  <span className="mono">{t.rankOnLearning}</span>
                  {/* Un vrai `select` plutôt qu'un bouton dessiné : la
                      planche montre un menu déroulant, et celui du
                      navigateur se pilote au clavier sans rien écrire. */}
                  <span className="rank-select">
                    <select
                      value={s.rankTheme}
                      onChange={(e) => set({ rankTheme: Number(e.target.value) })}
                      aria-label={t.rankOnLearning}
                    >
                      <option value={0}>{t.allThemes}</option>
                      {mine.map((th) => (
                        <option key={th.id} value={th.id}>
                          {th.title}
                        </option>
                      ))}
                    </select>
                    <Icon name="chevronDown" size={16} stroke={2} />
                  </span>
                </div>

                {rankRows.length === 0 ? (
                  <p className="body" style={{ fontSize: 16 }}>
                    {t.nobodyYet}
                  </p>
                ) : (
                  <>
                    <div className="rank-rows">
                      {rankRows.slice(0, 8).map((o) => (
                        <div key={o.user_id} className={o.is_me ? 'rank-row is-me' : 'rank-row'}>
                          <span className="rank-place">{o.rank}</span>
                          <Avatar
                            name={o.is_me ? t.you : o.name}
                            color={o.is_me ? 'var(--sc-primary)' : 'var(--violet-500)'}
                          />
                          <span className="rank-name">{o.is_me ? t.you : o.name}</span>
                          <span className="rank-points">{o.points}</span>
                        </div>
                      ))}
                    </div>
                    <span style={{ fontSize: 14, color: 'var(--sc-text3)' }}>
                      {t.thisWeek} · {t.participants(rankRows.length)}
                    </span>
                  </>
                )}
              </section>
            </div>
          ) : (
            /* Sélecteur de thème à gauche, classement à droite : la
               maquette traite « les autres » comme un classement PAR
               thème, l'état existait déjà (s.rankTheme) sans écran
               pour le piloter. */
            <div className="rank-split">
              <aside className="rank-themes">
                <span className="eyebrow">{t.learnings}</span>
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
                  <>
                    <Podium rows={rankRows} />
                    {/* Le podium a déjà pris les trois premiers : appeler
                        la liste avec ce qui reste, et seulement s'il en
                        reste — sinon elle affiche son état vide sous un
                        podium qui, lui, est plein. */}
                    {rankRows.length > 3 && <LeaderList rows={rankRows.slice(3)} />}
                  </>
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
      <div className="desk-hide">
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
      </div>

      <div className="screen-scroll page">
        <div className="page-inner">
          {/* On arrive ici depuis la feuille du thème, par-dessus un
              exercice : c'est à l'exercice qu'on rend la main, comme la
              flèche du téléphone. */}
          <PageBack onClick={() => go('exo', 'q')} label={t.exercisesNav} />

          <header className="page-head">
            <h1 className="page-title">{exo?.theme ?? t.ranking}</h1>
            <p className="page-lead">{t.weeklyReset}</p>
          </header>

          {/* Ma place à gauche, le classement à droite : la maquette pose
              340px 1fr. On voit où l'on est en lisant qui est devant. */}
          <div className="split-340">
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

        <div className="stack" style={{ gap: 10 }}>
          <span className="eyebrow">{t.thisWeek}</span>
          <LeaderList rows={rankRows} />
        </div>
          </div>
        </div>
      </div>
    </div>
  )
}

type Row = { rank: number; user_id: number; name: string; points: number; is_me: boolean }

/**
 * Les trois premiers, en marches.
 *
 * L'ordre visuel est 2 · 1 · 3, pas 1 · 2 · 3 : c'est la disposition
 * d'un podium, et l'inverser ferait lire le premier comme le plus à
 * gauche plutôt que comme le plus haut. Avec moins de trois joueurs on
 * ne montre que les marches existantes.
 */
function Podium({ rows }: { rows: Row[] }) {
  const { t } = useStore()
  const [first, second, third] = rows
  const order = [
    { row: second, height: 74, size: 46 },
    { row: first, height: 104, size: 54 },
    { row: third, height: 58, size: 46 },
  ].filter((x) => x.row)

  return (
    <div className="podium">
      {order.map(({ row, height, size }) => {
        const o = row as Row
        const top = o.rank === 1
        return (
          <div key={o.user_id} className="podium-col">
            <Avatar
              name={o.is_me ? t.you : o.name}
              color={top ? 'var(--sc-primary)' : 'var(--violet-500)'}
              size={size}
            />
            <span
              className={top ? 'podium-block is-first' : 'podium-block'}
              style={{ height }}
            >
              <span className="podium-rank">{o.rank}</span>
              <span style={{ fontSize: 13, opacity: top ? 0.85 : 1 }}>{o.points}</span>
            </span>
          </div>
        )
      })}
    </div>
  )
}

function LeaderList({ rows }: { rows: Row[] }) {
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
