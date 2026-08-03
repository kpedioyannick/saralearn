import { Icon } from '../components/Icon'
import { Meter, NavHead, meterColor } from '../components/ui'
import { useStore } from '../state/store'

/**
 * Mes thèmes — sorti des réglages.
 *
 * Choisir ce qu'on apprend n'est pas un réglage : c'est l'acte
 * principal de l'app, à côté de faire les exercices. Le mélanger au
 * son, au thème sombre et à la langue le rendait secondaire et
 * obligeait à traverser une page d'options pour y arriver.
 *
 * La progression suit les thèmes plutôt que les réglages : elle parle
 * des mêmes objets, et c'est là qu'on décide d'en ajouter ou d'en
 * retirer un.
 */
export function Themes() {
  const { go, themes, progression, toggleSubscribe, t } = useStore()

  const mine = themes.filter((x) => x.subscribed)

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('exo', 'q')} title={t.myThemes} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner">
          <header className="page-head">
            <h1 className="page-title">{t.myThemes}</h1>
            <p className="page-lead">{t.themesLead}</p>
          </header>

        <section className="stack" style={{ gap: 10 }}>
          <span className="eyebrow">{t.themes}</span>
          <div className="wrap">
            {mine.map((th) => (
              <span key={th.id} className="chip" style={{ cursor: 'default', paddingRight: 8 }}>
                <span
                  className="dot"
                  style={{ width: 8, height: 8, background: th.color ?? 'var(--sc-primary)' }}
                />
                {th.title}
                <button
                  className="hit-44"
                  onClick={() => toggleSubscribe(th.id)}
                  aria-label={`${t.discard} ${th.title}`}
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: 999,
                    border: 0,
                    background: 'var(--sc-sunk)',
                    display: 'grid',
                    placeItems: 'center',
                    cursor: 'pointer',
                    color: 'var(--sc-text3)',
                  }}
                >
                  <Icon name="minus" size={12} stroke={2.4} />
                </button>
              </span>
            ))}
            {mine.length === 0 && (
              <span style={{ fontSize: 14, color: 'var(--sc-text3)' }}>{t.noThemeFollowed}</span>
            )}
            <button
              className="chip"
              onClick={() => go('picker')}
              style={{
                border: '1px solid var(--sc-primary)',
                background: 'transparent',
                color: 'var(--sc-primary)',
                fontWeight: 700,
                gap: 6,
              }}
            >
              <Icon name="plus" size={15} stroke={2.2} />
              {t.add}
            </button>
          </div>
        </section>

        {/* Les pourcentages n'apparaissent qu'ici. */}
        <section className="stack" style={{ gap: 14 }}>
          <span className="eyebrow">{t.progression}</span>
          {progression.length === 0 && (
            <p className="serif-italic" style={{ fontSize: 16 }}>
              {t.nothingStarted}
            </p>
          )}
          {/* Des jauges se comparent : côte à côte elles se lisent d'un
              coup d'œil, empilées il faut faire défiler pour situer. */}
          <div className="forces-grid">
            {progression.map((p) => (
              <div key={p.theme_id} className="stack" style={{ gap: 7 }}>
                <span
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'baseline',
                    gap: 12,
                  }}
                >
                  <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--sc-text)' }}>
                    {p.name}
                  </span>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--sc-text3)' }}>
                    {p.pct} %
                  </span>
                </span>
                <Meter pct={p.pct} fill={meterColor(p.pct)} />
              </div>
            ))}
          </div>
        </section>
        </div>
      </div>
    </div>
  )
}
