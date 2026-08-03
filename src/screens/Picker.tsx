import { useState } from 'react'
import { Icon } from '../components/Icon'
import { Dot, NavHead, TileCheck } from '../components/ui'
import { useStore } from '../state/store'

/** Niveau 1 — catégories (filtre local), puis les thèmes eux-mêmes. */
export function Picker() {
  const { categories, themes, go, goCreate, toggleSubscribe, set, t } = useStore()
  const [filter, setFilter] = useState<Set<number>>(new Set())

  const toggle = (id: number) =>
    setFilter((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const visible =
    filter.size > 0 ? themes.filter((x) => filter.has(x.category_id)) : themes

  const count = (categoryId: number) =>
    themes.filter((x) => x.category_id === categoryId).length

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('themes')} title={t.addThemes} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner">
          <header className="page-head">
            <h1 className="page-title">{t.addThemes}</h1>
            <p className="page-lead">{t.addThemesLead}</p>
          </header>

        {/* Trois colonnes, tuiles de 160 px : mesures de la planche
            validée. En dessous de 1024 px, deux colonnes comme avant. */}
        <div className="grid-2 cat-grid">
          {categories.map((cat) => {
            const on = filter.has(cat.id)
            return (
              <button
                key={cat.id}
                className="tile cat-tile"
                aria-pressed={on}
                onClick={() => toggle(cat.id)}
                style={{
                  background: on ? 'var(--sc-primary-soft)' : 'var(--sc-surface)',
                  borderColor: on ? 'var(--sc-primary)' : 'var(--sc-line)',
                }}
              >
                <Dot color={cat.color} size={24} />
                <span className="stack" style={{ gap: 4 }}>
                  <span className="cat-label">{cat.label}</span>
                  {/* La maquette met un compte sous le nom. On compte les
                      thèmes, pas les sous-catégories : c'est ce qu'on vient
                      choisir ici, et plusieurs catégories n'ont aucune
                      sous-catégorie — le compte y aurait affiché zéro. */}
                  {count(cat.id) > 0 && (
                    <span className="cat-sub">{t.themesCount(count(cat.id))}</span>
                  )}
                </span>
                {on && <TileCheck />}
              </button>
            )
          })}
        </div>

        <div className="stack" style={{ gap: 10 }}>
          <span className="eyebrow">
            {filter.size > 0 ? t.themesOfChosen : t.allThemes}
          </span>
          <div className="wrap">
            {visible.map((t) => (
              <button
                key={t.id}
                className="chip"
                aria-pressed={t.subscribed}
                onClick={() => toggleSubscribe(t.id)}
                style={{
                  background: t.subscribed ? 'var(--sc-primary-soft)' : 'transparent',
                  borderColor: t.subscribed ? 'var(--sc-primary)' : 'var(--sc-line)',
                }}
              >
                {t.title}
              </button>
            ))}
          </div>
        </div>

        <button
          className="create-own"
          onClick={() => {
            set({ createStep: 1 })
            goCreate(1)
          }}
        >
          <Icon name="plus" size={20} stroke={1.9} />
          {t.createOwn}
        </button>
        </div>
      </div>

      <div className="footer-bar">
        <button className="btn-primary" onClick={() => go('picker2')}>
          {t.continue}
        </button>
      </div>
    </div>
  )
}

/** Niveau 2 — la grille des thèmes, avec l'abonnement en clair. */
export function Picker2() {
  const { themes, go, toggleSubscribe, t } = useStore()
  const count = themes.filter((x) => x.subscribed).length

  return (
    <div className="screen">
      <NavHead onBack={() => go('picker')} title={t.subCategories} subtitle={t.level2} />

      <div className="screen-scroll grid-2" style={{ padding: '6px 22px 12px' }}>
        {themes.map((t) => (
          <button
            key={t.id}
            className="tile"
            aria-pressed={t.subscribed}
            onClick={() => toggleSubscribe(t.id)}
            style={{
              minHeight: 110,
              background: t.subscribed ? 'var(--sc-primary-soft)' : 'var(--sc-surface)',
              borderColor: t.subscribed ? 'var(--sc-primary)' : 'var(--sc-line)',
            }}
          >
            <Dot color={t.color ?? 'var(--sc-primary)'} size={24} />
            <span className="stack" style={{ gap: 2 }}>
              <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--sc-text)' }}>
                {t.title}
              </span>
              <span style={{ fontSize: 12, color: 'var(--sc-text3)' }}>
                {t.category_label}
              </span>
            </span>
            {t.subscribed && <TileCheck />}
          </button>
        ))}
      </div>

      <div className="footer-bar">
        <button className="btn-primary" onClick={() => go('themes')}>
          {t.letsGo}{count > 0 ? ` · ${t.themesCount(count)}` : ''}
        </button>
      </div>
    </div>
  )
}
