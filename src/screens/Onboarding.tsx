import { useMemo, useState } from 'react'
import { Shelf, useShelves } from '../components/Catalogue'
import { Icon } from '../components/Icon'
import { LangSwitch } from '../components/LangSwitch'
import { Wordmark } from '../components/Wordmark'
import { Checkbox } from '../components/ui'
import type { ApiTheme } from '../lib/api'
import { useStore } from '../state/store'

/**
 * L'inscription, en deux étapes — planche 1e.
 *
 * Elle en comptait trois : une promesse, une grille de catégories, puis
 * les apprentissages de ces catégories. La grille du milieu ne faisait
 * que filtrer l'écran suivant ; elle demandait un choix qui n'était pas
 * un abonnement, et qu'il fallait ensuite refaire.
 *
 * La planche 2c la remplace par le même écran que « Ajouter » : une
 * recherche, des rayons, on prend ce qu'on veut. Reste une relecture —
 * « on affine » — où l'on retire ce qui ne parle pas.
 */

/**
 * Écran 1 — l'app ouvre sur un exercice ; ceci n'est qu'une porte.
 *
 * La marque et la bascule de langue sont DANS l'écran : c'est la
 * première page qu'un visiteur anglophone voit, et le feed n'a plus de
 * barre du haut où poser FR / EN.
 */
export function Welcome() {
  const { go, set, t } = useStore()
  return (
    <div className="screen onb-screen">
      <div className="onb-top">
        <Wordmark size={24} />
        <LangSwitch compact />
      </div>

      <div className="onb-promise">
        <p className="display onb-tagline">{t.tagline}</p>
        <p className="onb-line">{t.welcomeLine}</p>
      </div>

      <div className="onb-actions">
        <button className="btn-primary" onClick={() => go('onb2')}>
          {t.start}
        </button>
        {/* « Pas d'email, pas de mot de passe » était une mention inerte.
            La planche y met la sortie de ceux qui ont déjà un compte —
            eux n'ont rien à choisir. */}
        <button
          className="onb-have-account"
          onClick={() => set({ screen: 'auth', authMode: 'login', sheet: null, authError: null })}
        >
          {t.haveAccount}
        </button>
      </div>
    </div>
  )
}

/**
 * Étape 1 / 2 — le catalogue en rayons, exactement celui de « Ajouter ».
 *
 * L'abonnement part dès le tap : il n'y a rien à valider, le pied ne
 * fait qu'annoncer ce qu'on emporte.
 */
export function PickCatalogue() {
  const { themes, go, enterFeed, t } = useStore()
  const [query, setQuery] = useState('')
  const { byCategory } = useShelves()

  const needle = query.trim().toLowerCase()
  const results = useMemo(() => {
    if (!needle) return []
    return themes.filter(
      (th) =>
        th.title.toLowerCase().includes(needle) ||
        (th.category_label ?? '').toLowerCase().includes(needle) ||
        th.tags.some((tag) => tag.toLowerCase().includes(needle)),
    )
  }, [themes, needle])

  const chosen = themes.filter((th) => th.subscribed)
  const questionTotal = chosen.reduce((sum, th) => sum + th.exercise_count, 0)

  return (
    <div className="screen">
      <div className="learn-head is-onb">
        <div className="onb-step">
          <span className="mono">{t.stepOf(1, 2)}</span>
          <button className="onb-step-act" onClick={enterFeed}>
            {t.skip}
          </button>
        </div>

        <div className="stack" style={{ gap: 8 }}>
          <p className="display onb-step-title">{t.whatInterestsYou}</p>
          <p className="onb-step-lead">{t.searchOrPick}</p>
        </div>

        <label className="learn-field">
          <Icon name="search" size={18} color="var(--sc-text3)" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.whatToLearn}
            aria-label={t.whatToLearn}
          />
        </label>
      </div>

      <div className="learn-scroll">
        {needle ? (
          <Shelf spec={{ key: 'search', title: t.searchResults, items: results }} />
        ) : (
          <>
            {/* L'inscription montre le MÊME catalogue que « Ajouter » :
                les trois rayons éditoriaux y sont partis aussi, et pour
                la même raison — voir `useShelves`. À l'inscription, ils
                étaient même les plus faux des trois : on ne suit encore
                rien, donc « parce que vous suivez » n'existait pas et
                « les plus suivis » ne comptait que des zéros. */}
            {byCategory.length > 0 && (
              <div className="learn-rule">
                <span className="mono">
                  {t.byCategory} · {byCategory.length}
                </span>
                <span className="learn-rule-line" />
              </div>
            )}

            {byCategory.map((spec) => (
              <Shelf key={spec.key} spec={spec} showCategory={false} />
            ))}
          </>
        )}
      </div>

      <div className="learn-foot">
        <span className="stack" style={{ flex: 1, gap: 2, minWidth: 0 }}>
          <span className="learn-foot-count">{t.addedCount(chosen.length)}</span>
          <span className="learn-foot-meta">{t.approxQuestions(questionTotal)}</span>
        </span>
        <button className="learn-done" onClick={() => go('onb3')}>
          {t.continueLabel}
        </button>
      </div>
    </div>
  )
}

/**
 * Étape 2 / 2 — on affine.
 *
 * Ce qu'on a pris à l'étape d'avant, groupé par catégorie, tout coché.
 * On ne relit pas le catalogue entier : on relit sa propre sélection.
 */
export function Refine() {
  const { themes, enterFeed, toggleSubscribe, t } = useStore()

  // La liste est figée à l'arrivée sur l'écran : décocher ne doit pas
  // faire disparaître la ligne sous le doigt, sinon on n'a plus de
  // second avis à donner.
  const [shown] = useState<ApiTheme[]>(() => themes.filter((th) => th.subscribed))

  const groups = useMemo(() => {
    const map = new Map<string, ApiTheme[]>()
    for (const th of shown) {
      const key = th.category_label ?? ''
      const list = map.get(key) ?? []
      list.push(th)
      map.set(key, list)
    }
    return [...map.entries()]
  }, [shown])

  const live = new Set(themes.filter((th) => th.subscribed).map((th) => th.id))

  const uncheckAll = () => {
    for (const th of shown) if (live.has(th.id)) toggleSubscribe(th.id)
  }

  return (
    <div className="screen">
      <div className="learn-head is-onb">
        <div className="onb-step">
          <span className="mono">{t.stepOf(2, 2)}</span>
          <button className="onb-step-act" onClick={uncheckAll} disabled={live.size === 0}>
            {t.uncheckAll}
          </button>
        </div>

        <div className="stack" style={{ gap: 8 }}>
          <p className="display onb-step-title">{t.refine}</p>
          <p className="onb-step-lead">{shown.length > 0 ? t.refineLead : t.noThemeFollowed}</p>
        </div>
      </div>

      <div className="learn-scroll">
        {groups.map(([label, list]) => (
          <div key={label} className="learn-group">
            {label && <span className="mono learn-group-head">{label}</span>}
            {list.map((th) => (
              <button
                key={th.id}
                className={live.has(th.id) ? 'onb-pick is-on' : 'onb-pick'}
                aria-pressed={live.has(th.id)}
                onClick={() => toggleSubscribe(th.id)}
              >
                <Checkbox on={live.has(th.id)} />
                <span className="onb-pick-name">{th.title}</span>
              </button>
            ))}
          </div>
        ))}
      </div>

      <div className="learn-foot">
        <button
          className="btn-primary"
          style={{ flex: 1, minHeight: 58 }}
          onClick={enterFeed}
        >
          {t.letsGo}
        </button>
      </div>
    </div>
  )
}
