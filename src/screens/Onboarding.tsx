import { useState } from 'react'
import { Checkbox, Dot, TileCheck } from '../components/ui'
import { Wordmark } from '../components/Wordmark'
import { useStore } from '../state/store'

/** Écran 1 — l'app ouvre sur un exercice ; ceci n'est qu'une porte. */
export function Welcome() {
  const { go, t } = useStore()
  return (
    <div className="screen" style={{ justifyContent: 'center', gap: 28, padding: '0 30px' }}>
      <Wordmark size={42} />
      <p className="display" style={{ fontSize: 36 }}>
        {t.tagline}
      </p>
      <p className="body">
        {t.welcomeLine}
      </p>
      <div className="stack" style={{ gap: 14, marginTop: 8 }}>
        <button className="btn-primary" onClick={() => go('onb2')}>
          {t.start}
        </button>
        <span style={{ fontSize: 14, color: 'var(--sc-text3)', textAlign: 'center' }}>
          {t.noAccountNeeded}
        </span>
      </div>
    </div>
  )
}

/**
 * Écran 2 — catégories. Le choix ne filtre que l'écran suivant : c'est
 * l'abonnement au thème qui compte, pas la catégorie.
 */
export function PickCategories() {
  const { categories, go, set, t } = useStore()
  const [chosen, setChosen] = useState<Set<number>>(new Set())

  const toggle = (id: number) =>
    setChosen((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  return (
    <div className="screen">
      <div className="stack" style={{ padding: '60px 22px 14px', gap: 6, flex: 'none' }}>
        <span className="eyebrow">{t.step2}</span>
        <p className="display" style={{ fontSize: 32 }}>
          {t.pickInterests}
        </p>
      </div>

      <div className="screen-scroll grid-2" style={{ padding: '6px 22px 12px' }}>
        {categories.map((cat) => {
          const on = chosen.has(cat.id)
          return (
            <button
              key={cat.id}
              className="tile"
              aria-pressed={on}
              onClick={() => toggle(cat.id)}
              style={{
                background: on ? 'var(--sc-primary-soft)' : 'var(--sc-surface)',
                borderColor: on ? 'var(--sc-primary)' : 'var(--sc-line)',
              }}
            >
              <Dot color={cat.color} size={26} />
              <span className="stack" style={{ gap: 2 }}>
                <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--sc-text)' }}>
                  {cat.label}
                </span>
                <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                  {t.subThemes(cat.sub_categories.length)}
                </span>
              </span>
              {on && <TileCheck />}
            </button>
          )
        })}
      </div>

      <div className="footer-bar">
        <button
          className="btn-primary"
          onClick={() => {
            set({ onbCategories: [...chosen] })
            go('onb3')
          }}
        >
          {t.continueWith(chosen.size)}
        </button>
        <button className="btn-quiet" onClick={() => go('exo', 'q')}>
          {t.skip}
        </button>
      </div>
    </div>
  )
}

/** Écran 3 — les thèmes eux-mêmes. C'est ici que naît l'abonnement. */
export function PickSubcategories() {
  const { themes, s, go, toggleSubscribe, t } = useStore()
  const filter = s.onbCategories
  const visible =
    filter.length > 0 ? themes.filter((x) => filter.includes(x.category_id)) : themes
  const count = visible.filter((x) => x.subscribed).length

  return (
    <div className="screen">
      <div className="stack" style={{ padding: '60px 22px 14px', gap: 6, flex: 'none' }}>
        <span className="eyebrow">{t.step3}</span>
        <p className="display" style={{ fontSize: 32 }}>
          {t.uncheckWhatever}
        </p>
        <p style={{ margin: '4px 0 0', fontSize: 15, lineHeight: 1.6, color: 'var(--sc-text3)' }}>
          {t.defaultAll}
        </p>
      </div>

      <div className="screen-scroll stack" style={{ padding: '6px 22px 12px', gap: 8 }}>
        {visible.map((t) => (
          <button
            key={t.id}
            className="row-btn"
            aria-pressed={t.subscribed}
            onClick={() => toggleSubscribe(t.id)}
            style={{ background: t.subscribed ? 'var(--sc-surface)' : 'transparent' }}
          >
            <Checkbox on={t.subscribed} />
            <span className="stack">
              <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--sc-text)' }}>
                {t.title}
              </span>
              <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                {t.category_label}
              </span>
            </span>
          </button>
        ))}
      </div>

      <div className="footer-bar">
        <button className="btn-primary" onClick={() => go('exo', 'q')}>
          {t.letsGo}{count > 0 ? ` · ${t.themesCount(count)}` : ''}
        </button>
      </div>
    </div>
  )
}
