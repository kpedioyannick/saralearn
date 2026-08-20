import { useMemo, useState } from 'react'
import {
  CodeChip,
  GroupedList,
  type ShelfSpec,
  Shelf,
  categoriesTouched,
  useShelves,
} from '../components/Catalogue'
import { Icon } from '../components/Icon'
import { Checkbox, Dot, NavHead, PageBack, TileCheck } from '../components/ui'
import type { ApiTheme } from '../lib/api'
import { useIsDesktop } from '../lib/useIsDesktop'
import { useStore } from '../state/store'

/**
 * Ajouter des apprentissages.
 *
 * Deux mises en scène, pas une seule étirée.
 *
 * En téléphone, la planche 2c : la recherche d'abord, les rayons
 * ensuite. Le deux-panneaux y tombait — 118 px pour les catégories,
 * 250 pour la liste — et l'arbre est abandonné.
 *
 * En desktop, la planche 1m tient toujours : trois colonnes, les
 * catégories à gauche, les apprentissages au milieu, la sélection à
 * droite. Le tour 2 ne parle que du téléphone, et 1440 px n'a jamais
 * eu le problème que 2c résout.
 */

export function Picker() {
  const isDesktop = useIsDesktop()
  return isDesktop ? <PickerDesktop /> : <PickerMobile />
}

/**
 * Le catalogue en rayons, sur téléphone.
 *
 * L'abonnement part dès le tap — il n'y a pas de panier à valider. Le
 * pied ne fait que dire ce qu'on a pris et rendre la sortie visible :
 * la planche le montre en recherche, on le garde partout dès qu'il y a
 * quelque chose à annoncer, sinon l'ajout depuis un rayon ne renvoie
 * aucun signe.
 */
function PickerMobile() {
  const { s, themes, categories, go, goCreate, t } = useStore()
  const [query, setQuery] = useState('')
  const [seeAll, setSeeAll] = useState<ShelfSpec | null>(null)
  const { byCategory } = useShelves()

  const needle = query.trim().toLowerCase()
  const searching = needle !== ''

  const results = useMemo(() => {
    if (!searching) return []
    return themes.filter(
      (th) =>
        th.title.toLowerCase().includes(needle) ||
        (th.category_label ?? '').toLowerCase().includes(needle) ||
        th.tags.some((tag) => tag.toLowerCase().includes(needle)),
    )
  }, [themes, needle, searching])

  // Les suggestions sont des noms de catégorie, pas des titres
  // d'apprentissage : la planche les montre courts — « fractions »,
  // « capitales » — et un titre réel comme « Accord du participe passé
  // (passé composé, plus-que-parfait) » remplit trois pastilles à lui
  // seul. La recherche traverse déjà les catégories : taper dessus
  // ramène tout le rayon.
  const hints = useMemo(() => categories.slice(0, 4).map((c) => c.label), [categories])

  const chosen = themes.filter((th) => th.subscribed)
  const questionTotal = chosen.reduce((sum, th) => sum + th.exercise_count, 0)

  const leave = () => {
    if (seeAll) setSeeAll(null)
    else if (searching) setQuery('')
    else go('themes')
  }

  // Le mot d'explication ne s'affiche que si on n'a rien demandé — donc
  // après un renvoi — et disparaît au premier apprentissage choisi : le
  // pied de page prend alors le relais et dit combien on en a pris.
  const explain = s.sentToPicker && chosen.length === 0 && !searching && !seeAll

  return (
    <div className="screen">
      {/* Le champ garde sa place dans la liste d'enfants, quel que soit
          l'état : sorti d'une branche et remis dans une autre, il se
          remonterait à la première lettre tapée — le clavier se ferme et
          le curseur saute. */}
      <div className="learn-head">
        {!searching && (
          <div className="learn-head-row">
            <button className="learn-back" onClick={leave} aria-label={t.back}>
              <Icon name="chevronLeft" size={20} stroke={2} />
            </button>
            <h1 className="learn-title">{seeAll ? seeAll.title : t.addShort}</h1>
          </div>
        )}

        {explain && (
          <div className="learn-why" role="status">
            <Icon name="bulb" size={18} stroke={1.9} color="var(--sc-text2)" />
            <span className="stack" style={{ gap: 4 }}>
              <span className="learn-why-title">{t.whyHereTitle}</span>
              <span className="learn-why-line">{t.whyHereLine}</span>
            </span>
          </div>
        )}

        {!seeAll && (
          <div className="learn-head-row">
            <SearchField value={query} onChange={setQuery} />
            {searching && (
              <button className="learn-cancel" onClick={() => setQuery('')}>
                {t.cancelSearch}
              </button>
            )}
          </div>
        )}

        {searching ? (
          <p className="learn-count">{t.resultsIn(results.length, categoriesTouched(results))}</p>
        ) : (
          !seeAll && (
            <div className="learn-hints">
              {hints.map((hint) => (
                <button key={hint} className="learn-hint" onClick={() => setQuery(hint)}>
                  {hint}
                </button>
              ))}
            </div>
          )
        )}
      </div>

      <div className="learn-scroll">
        {searching ? (
          <GroupedList items={results} />
        ) : seeAll ? (
          <GroupedList items={seeAll.items} />
        ) : (
          <>
            {/* La règle séparait les rayons éditoriaux des catégories.
                Les éditoriaux sont partis — voir `useShelves` — mais elle
                reste : c'est le seul repère qui dise ce que la liste est,
                et sans elle les onze rayons commencent sans titre. */}
            {byCategory.length > 0 && (
              <div className="learn-rule">
                <span className="mono">
                  {t.byCategory} · {byCategory.length}
                </span>
                <span className="learn-rule-line" />
              </div>
            )}

            {byCategory.map((spec) => (
              <Shelf
                key={spec.key}
                spec={spec}
                showCategory={false}
                onSeeAll={() => setSeeAll(spec)}
              />
            ))}

            {byCategory.length === 0 && (
              <p className="learn-empty">{t.emptyCatalogue}</p>
            )}

            {/* Créer n'est pas une entrée de liste : le bouton reste hors
                des rayons, en bas du défilement. */}
            <button className="create-own" onClick={() => goCreate(1)}>
              <Icon name="plus" size={20} stroke={1.9} />
              {t.shareKnowledge}
            </button>
          </>
        )}
      </div>

      {chosen.length > 0 && (
        <div className="learn-foot">
          <span className="stack" style={{ flex: 1, gap: 2, minWidth: 0 }}>
            <span className="learn-foot-count">{t.addedCount(chosen.length)}</span>
            <span className="learn-foot-meta">{t.approxQuestions(questionTotal)}</span>
          </span>
          <button className="learn-done" onClick={() => go('themes')}>
            {t.finish}
          </button>
        </div>
      )}
    </div>
  )
}

function SearchField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { t } = useStore()
  return (
    <label className="learn-field">
      <Icon name="search" size={18} color="var(--sc-text3)" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t.whatToLearn}
        aria-label={t.whatToLearn}
      />
    </label>
  )
}

/**
 * L'ordre d'affichage — le seul, et le même que celui de l'API.
 *
 * L'ÉTAGE D'ABORD. L'article racine du thème ouvre sa catégorie :
 * « Terre » avant « Océan », « Lumière » avant « Optique ». Il contient
 * tous les autres — 300 articles pour « Terre » — et rangé au poids il
 * tombait deuxième, derrière un pilier qui a le même nombre d'enfants
 * directs que lui. Un parent au milieu de ses propres enfants se lit
 * comme une ligne en double.
 *
 * LE POIDS ENSUITE : le nombre d'articles qui descendent du chapitre.
 * L'alphabet ne disait rien — il mettait « Théorie corpusculaire de la
 * lumière », cul-de-sac de l'arbre, devant « Optique », qui porte 76
 * articles. Le nombre d'enfants, lui, est un signal : Wikipédia relie un
 * article à d'autant plus d'articles qu'il couvre de sujet.
 *
 * Le titre départage les ex æquo, et c'est le titre AFFICHÉ — une liste
 * française rangée dans l'ordre alphabétique anglais se lit comme un
 * désordre.
 */
const byWeight = (a: ApiTheme, b: ApiTheme) =>
  a.depth - b.depth ||
  b.child_count - a.child_count ||
  a.title.localeCompare(b.title)

/**
 * Les trois colonnes de la planche 1m — desktop seulement.
 *
 * Au-dessus, une barre d'outils réduite à ce qu'elle sert : chercher
 * dans tout le catalogue. La recherche traverse les catégories —
 * chercher « fraction » sans savoir qu'il faut d'abord ouvrir « Maths »
 * est le cas normal.
 */
function PickerDesktop() {
  const { s, categories, themes, go, toggleSubscribe, subscribedIds, t } = useStore()
  const [open, setOpen] = useState<number | null>(null)
  const [query, setQuery] = useState('')

  // La première catégorie sert de point d'entrée : une colonne de
  // droite vide au chargement se lit comme un écran cassé.
  const active = open ?? categories[0]?.id ?? null

  const byCategory = useMemo(() => {
    const map = new Map<number, ApiTheme[]>()
    for (const th of themes) {
      const list = map.get(th.category_id) ?? []
      list.push(th)
      map.set(th.category_id, list)
    }
    for (const list of map.values()) list.sort(byWeight)
    return map
  }, [themes])

  const needle = query.trim().toLowerCase()
  const searching = needle !== ''

  const keep = (th: ApiTheme) =>
    !searching ||
    th.title.toLowerCase().includes(needle) ||
    (th.category_label ?? '').toLowerCase().includes(needle) ||
    th.tags.some((tag) => tag.toLowerCase().includes(needle))

  // En recherche, la colonne du milieu traverse les catégories : celle
  // qui est ouverte ne dit plus rien de ce qu'on cherche.
  const visible = searching
    ? [...themes].filter(keep).sort(byWeight)
    : (active === null ? [] : byCategory.get(active) ?? []).filter(keep)

  const activeLabel = searching
    ? t.searchResults
    : categories.find((c) => c.id === active)?.label ?? ''

  const chosen = themes.filter((th) => th.subscribed)
  const selected = subscribedIds.size
  const exerciseTotal = chosen.reduce((sum, th) => sum + th.exercise_count, 0)

  const followAll = () => {
    for (const th of visible) if (!th.subscribed) toggleSubscribe(th.id)
  }

  const clearSelection = () => {
    for (const th of chosen) toggleSubscribe(th.id)
  }

  return (
    <div className="screen">
      {/* La page ne défile pas : les deux colonnes tiennent la hauteur
          disponible et défilent chacune pour soi, comme sur la planche.
          Faire défiler la page entière emportait la colonne des
          catégories hors de l'écran — on ne pouvait plus en changer sans
          remonter. */}
      <div className="page pick-page">
        <div className="page-inner pick-inner is-full">
          {/* Le rail n'a pas d'entrée « ajouter » : on vient d'ici par
              « mes apprentissages », et c'est là qu'on retourne — comme
              le fait déjà la flèche du téléphone. */}
          <PageBack onClick={() => go('themes')} label={t.myLearnings} />

          <header className="page-head is-inline">
            <h1 className="page-title">{t.addLearnings}</h1>
            <p className="page-lead">{t.pickerMeta(themes.length, categories.length)}</p>
          </header>

          {/* Même mot qu'en téléphone, aux mêmes conditions : on n'a rien
              demandé, et rien n'est encore choisi. */}
          {s.sentToPicker && chosen.length === 0 && (
            <div className="learn-why" role="status">
              <Icon name="bulb" size={18} stroke={1.9} color="var(--sc-text2)" />
              <span className="stack" style={{ gap: 4 }}>
                <span className="learn-why-title">{t.whyHereTitle}</span>
                <span className="learn-why-line">{t.whyHereLine}</span>
              </span>
            </div>
          )}

          {/* La barre d'outils n'a plus qu'un outil : chercher.
              « Populaires », « Nouveaux » et « Filtres » sont partis.

              Les deux tris ne trient rien : « Populaires » lit
              `subscriber_count`, qui vaut zéro tant que personne n'a
              joué, et « Nouveaux » lit l'identifiant, c'est-à-dire
              l'ordre du semis — les feuilles les plus lointaines en
              tête. Les deux retombaient sur le même ordre que le repos.
              Trois boutons pour une seule liste, c'est trois façons de
              faire croire qu'on choisit.

              L'ordre unique est celui du poids : le nombre d'articles
              qui descendent du chapitre. */}
          <div className="pick-tools">
            <label className="learn-search">
              <Icon name="search" size={17} color="var(--sc-text3)" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t.searchCatalogue(themes.length)}
                aria-label={t.searchCatalogue(themes.length)}
              />
            </label>
          </div>

          <div className="pick-split">
            <aside className="pick-cats">
              <span className="mono" style={{ padding: '4px 10px 8px' }}>
                {t.categories}
              </span>
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  className={cat.id === active ? 'pick-cat is-on' : 'pick-cat'}
                  aria-pressed={cat.id === active}
                  onClick={() => setOpen(cat.id)}
                >
                  {/* Le compte passe SOUS le nom en téléphone : la
                      colonne y est étroite et un nom comme « Permis de
                      conduire » tient sur deux lignes — le compte posé à
                      côté venait se coller au dernier mot. Dès 1024 px
                      il repasse à droite, comme sur la planche.
                      Pas de pastille de couleur : ni la planche
                      téléphone ni la desktop n'en portent ici, et les
                      16 px qu'elle prenait manquaient à des noms comme
                      « Orthographe ». */}
                  <span className="pick-cat-body">
                    <span className="pick-cat-name">
                      <span className="side-label">{cat.label}</span>
                    </span>
                    <span className="side-badge">{byCategory.get(cat.id)?.length ?? 0}</span>
                  </span>
                </button>
              ))}
            </aside>

            <div className="pick-list">
              {/* Le titre de la catégorie et « tout suivre » restent en
                  place : ce sont les seuls repères quand la liste file. */}
              <div className="pick-list-head">
                <span className="pick-list-title">
                  <span style={{ fontWeight: 700 }}>{activeLabel}</span>{' '}
                  <span className="pick-list-count">
                    <span className="desk-only">· </span>
                    {t.learningsCount(visible.length)}
                  </span>
                </span>
                {visible.length > 0 && (
                  <button
                    className="btn-link"
                    style={{ padding: 0, flex: 'none', whiteSpace: 'nowrap' }}
                    onClick={followAll}
                  >
                    {t.followAll}
                  </button>
                )}
              </div>

              <div className="pick-rows">
                {visible.length === 0 && (
                  <p className="serif-italic" style={{ gridColumn: '1 / -1' }}>
                    {t.noMatch}
                  </p>
                )}
                {visible.map((th) => (
                  <button
                    key={th.id}
                    className={th.subscribed ? 'pick-row is-on' : 'pick-row'}
                    aria-pressed={th.subscribed}
                    onClick={() => toggleSubscribe(th.id)}
                  >
                    <Checkbox on={th.subscribed} />
                    <span className="pick-row-name">{th.title}</span>
                    <CodeChip code={th.code} />
                    <span
                      style={{
                        flex: 'none',
                        whiteSpace: 'nowrap',
                        fontSize: 13,
                        color: 'var(--sc-text3)',
                      }}
                    >
                      {t.exercisesShort(th.exercise_count)}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* La sélection en cours, en colonne : les noms retenus, ce
                que ça pèse en exercices, et les deux sorties. Elle
                remplace la barre du bas dès qu'il y a la place — la
                barre ne montrait qu'un compte, sans dire de quoi. */}
            <aside className="pick-cart">
              <span style={{ fontSize: 17, fontWeight: 700 }}>
                {t.selection} · {selected}
              </span>

              {selected === 0 ? (
                <span style={{ fontSize: 14, color: 'var(--sc-text3)' }}>
                  {t.emptySelection}
                </span>
              ) : (
                <div className="wrap" style={{ gap: 8 }}>
                  {chosen.slice(0, 6).map((th) => (
                    <button
                      key={th.id}
                      className="pick-tag"
                      onClick={() => toggleSubscribe(th.id)}
                      aria-label={`${t.unfollow} — ${th.title}`}
                      title={t.unfollow}
                    >
                      {th.title}
                      <Icon name="close" size={13} stroke={2.4} />
                    </button>
                  ))}
                  {chosen.length > 6 && (
                    <span className="pick-tag is-quiet">{t.moreOthers(chosen.length - 6)}</span>
                  )}
                </div>
              )}

              <div style={{ flex: 1 }} />

              {selected > 0 && (
                <span style={{ fontSize: 14, color: 'var(--sc-text3)' }}>
                  {t.feedEstimate(exerciseTotal)}
                </span>
              )}

              <button
                className="btn-primary"
                style={{ minHeight: 50, boxShadow: 'none' }}
                onClick={() => go('themes')}
              >
                {t.addToFeed}
              </button>

              <button
                className="btn-quiet"
                style={{ textDecoration: 'none' }}
                onClick={clearSelection}
                disabled={selected === 0}
              >
                {t.clearSelection}
              </button>
            </aside>
          </div>

          {/* Le rail desktop porte déjà « partager une connaissance » :
              l'entrée qui vivait ici doublait la sienne, et le téléphone
              a désormais la sienne au bas des rayons. */}
        </div>
      </div>
    </div>
  )
}

/** Niveau 2 — la grille complète, tous apprentissages confondus. */
export function Picker2() {
  const { themes, go, toggleSubscribe, t } = useStore()
  const count = themes.filter((x) => x.subscribed).length

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('picker')} title={t.subCategories} subtitle={t.level2} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner">
          <PageBack onClick={() => go('picker')} label={t.addShort} />

          <header className="page-head">
            <span className="eyebrow">{t.level2}</span>
            <h1 className="page-title">{t.subCategories}</h1>
          </header>

          <div className="grid-2 grid-4">
            {themes.map((th) => (
              <button
                key={th.id}
                className="tile"
                aria-pressed={th.subscribed}
                onClick={() => toggleSubscribe(th.id)}
                style={{
                  minHeight: 110,
                  background: th.subscribed ? 'var(--sc-primary-soft)' : 'var(--sc-surface)',
                  borderColor: th.subscribed ? 'var(--sc-primary)' : 'var(--sc-line)',
                }}
              >
                <Dot color={th.color ?? 'var(--sc-primary)'} size={24} />
                <span className="stack" style={{ gap: 2 }}>
                  <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--sc-text)' }}>
                    {th.title}
                  </span>
                  <span style={{ fontSize: 12, color: 'var(--sc-text3)' }}>
                    {th.category_label}
                  </span>
                </span>
                {th.subscribed && <TileCheck />}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="footer-bar">
        <button className="btn-primary" onClick={() => go('themes')}>
          {t.letsGo}
          {count > 0 ? ` · ${t.learningsCount(count)}` : ''}
        </button>
      </div>
    </div>
  )
}
