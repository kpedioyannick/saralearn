import { useEffect, useMemo, useState, type KeyboardEvent } from 'react'
import { Icon } from '../components/Icon'
import { Meter, NavHead } from '../components/ui'
import { api, type ApiTheme } from '../lib/api'
import { useIsDesktop } from '../lib/useIsDesktop'
import { useStore } from '../state/store'

/**
 * Mes apprentissages — sorti des réglages.
 *
 * Choisir ce qu'on apprend n'est pas un réglage : c'est l'acte
 * principal de l'app, à côté de faire les exercices.
 *
 * Deux planches gouvernent cet écran et ne disent pas la même chose.
 * En téléphone (1f), une liste dense en une colonne, deux onglets,
 * l'ajout en bas. En desktop (1m), la largeur sert à quelque chose :
 * l'ajout remonte à côté de la recherche, la liste devient une grille
 * de cartes blanches sur deux colonnes, et une colonne de 340 px porte
 * les suggestions puis l'invitation à partager. Le pied de page
 * disparaît alors : son action a trouvé sa place dans la colonne.
 */

type Tab = 'followed' | 'suggested' | 'popular' | 'started' | 'mine'

/** La planche 1f pose « Suivis · Suggérés · Populaires », la planche 1m
 *  « Suivis · Commencés · Créés par moi ». Le téléphone garde en plus
 *  « Créés par moi » : c'est de là que s'ouvre la fiche d'auteur, et une
 *  feuille du bas qu'on ne peut atteindre qu'en desktop n'est pas une
 *  feuille du bas. */
const MOBILE_TABS: Tab[] = ['followed', 'suggested', 'popular', 'mine']
const DESKTOP_TABS: Tab[] = ['followed', 'started', 'mine']

export function Themes() {
  const {
    go, goCreate, openMyTheme, themes, myThemes, progression, subscribedIds,
    toggleSubscribe, t,
  } = useStore()
  const isDesktop = useIsDesktop()
  const [query, setQuery] = useState('')

  /**
   * La recherche par code de partage.
   *
   * La barre filtre en local sur ce qui est déjà chargé — titre,
   * catégorie, tags. Un code n'y est pas : le quiz cherché peut être
   * privé, donc absent du catalogue servi. Quand la saisie a la forme
   * d'un code et que le filtre local ne rend rien, on demande au
   * serveur, et le résultat se pose dans les suggestions comme un
   * apprentissage ordinaire — avec son bouton d'ajout.
   */
  const [byCode, setByCode] = useState<ApiTheme | null>(null)
  const [codeMiss, setCodeMiss] = useState(false)
  const [wanted, setWanted] = useState<Tab>('followed')

  const pct = useMemo(
    () => new Map(progression.map((p) => [p.theme_id, p.pct])),
    [progression],
  )

  const needle = query.trim().toLowerCase()
  const hit = (x: (typeof themes)[number]) =>
    needle === '' ||
    x.title.toLowerCase().includes(needle) ||
    (x.category_label ?? '').toLowerCase().includes(needle) ||
    x.tags.some((tag) => tag.toLowerCase().includes(needle))

  const matches = themes.filter(hit)

  // Six caractères de l'alphabet des codes : on ne va au serveur que si
  // la saisie peut EN être un, sinon chaque lettre tapée partirait en
  // requête.
  const looksLikeCode = /^[ACDEFGHJKMNPQRTVWXY23479]{6}$/i.test(needle.replace(/[\s-]/g, ''))

  useEffect(() => {
    if (!looksLikeCode || matches.length > 0) {
      setByCode(null)
      setCodeMiss(false)
      return
    }
    let alive = true
    api
      .themeByCode(needle.replace(/[\s-]/g, ''))
      .then((th) => alive && (setByCode(th), setCodeMiss(false)))
      .catch(() => alive && (setByCode(null), setCodeMiss(true)))
    return () => {
      alive = false
    }
  }, [looksLikeCode, needle, matches.length])

  const followed = matches.filter((x) => x.subscribed)
  // Le quiz trouvé par code rejoint les suggestions : c'est là qu'on
  // ajoute, et il ne doit pas inventer une quatrième liste pour lui seul.
  const suggested = byCode
    ? [byCode, ...matches.filter((x) => !x.subscribed && x.id !== byCode.id)]
    : matches.filter((x) => !x.subscribed)
  const started = followed.filter((x) => (pct.get(x.id) ?? 0) > 0)
  // `myThemes` et pas `matches` : le catalogue public ne sert pas mes
  // brouillons privés, et un auteur doit voir ce qu'il n'a pas publié.
  const mine = myThemes.filter(hit)
  // « Populaires » se lit sur le nombre d'abonnés, la seule mesure
  // d'audience que l'API renvoie. `slice()` avant `sort()` : trier en
  // place réordonnerait le tableau que les autres onglets lisent.
  const popular = matches
    .slice()
    .sort((a, b) => b.subscriber_count - a.subscriber_count)

  // Les onglets dépendent de la largeur : en rétrécissant la fenêtre,
  // « Commencés » disparaît et l'écran retomberait sur une liste vide
  // s'il gardait un onglet qui n'existe plus.
  const tabs = isDesktop ? DESKTOP_TABS : MOBILE_TABS
  const tab = tabs.includes(wanted) ? wanted : 'followed'

  const lists: Record<Tab, typeof themes> = { followed, suggested, popular, started, mine }
  const labels: Record<Tab, string> = {
    followed: t.followedTab,
    suggested: t.suggestedTab,
    popular: t.popularTab,
    started: t.startedTab,
    mine: t.createdByMeTab,
  }
  const empty: Record<Tab, string> = {
    followed: t.noThemeFollowed,
    suggested: t.nothingToSuggest,
    popular: t.noPopular,
    started: t.noThemeStarted,
    mine: t.noThemeCreated,
  }
  const shown = lists[tab]

  // La planche 1f pose les suggestions sous la liste suivie, en
  // téléphone seulement — en desktop elles ont leur colonne, et les
  // écrire deux fois serait les dire deux fois. On ne les montre que
  // sous l'onglet « Suivis » : ailleurs, la liste EST déjà la
  // suggestion.
  const inlineSuggested =
    !isDesktop && tab === 'followed' ? suggested.slice(0, 2) : []
  const followedCategories = new Set(followed.map((x) => x.category_label ?? ''))

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('exo', 'q')} title={t.myLearnings} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner is-full">
          {/* La planche desktop pose le titre et le décompte sur une
              même ligne de base, sans filet : la page respire moins
              haut et la grille commence plus tôt. */}
          <header className="page-head is-inline">
            <h1 className="page-title">{t.myLearnings}</h1>
            <p className="page-lead">{t.themesMeta(followed.length, themes.length)}</p>
          </header>

          <div className="learn-body">
            <div className="learn-main">
              <div className="learn-search-row">
                <label className="learn-search">
                  <Icon name="search" size={17} color="var(--sc-text3)" />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={`${t.searchLearning} — ${t.codeSearchHint.toLowerCase()}`}
                    aria-label={t.searchLearning}
                  />
                </label>

                {/* L'ajout se tient à côté de la recherche : chercher et
                    ajouter sont le même geste, séparés par un clic. En
                    téléphone il reprend sa place en bas de liste. */}
                <button className="btn-primary learn-add desk-only" onClick={() => go('picker')}>
                  {t.addLearnings}
                </button>
              </div>

              {/* Le code cherché n'existe pas : on le dit, plutôt que de
                  laisser une liste vide qui ressemble à un catalogue
                  pauvre. Le placeholder, lui, annonce que la barre
                  accepte aussi un code. */}
              {codeMiss && <p className="learn-code-miss">{t.codeNotFound}</p>}

              <div className="wrap" style={{ gap: 8 }}>
                {tabs.map((key) => (
                  <button
                    key={key}
                    className="chip"
                    aria-pressed={tab === key}
                    onClick={() => setWanted(key)}
                    style={{
                      cursor: 'pointer',
                      background: tab === key ? 'var(--sc-primary)' : undefined,
                      borderColor: tab === key ? 'var(--sc-primary)' : undefined,
                      color: tab === key ? 'var(--sc-on-primary)' : undefined,
                      fontWeight: tab === key ? 700 : 500,
                    }}
                  >
                    {labels[key]} {lists[key].length}
                  </button>
                ))}
              </div>

              <div className="learn-list">
                {shown.length === 0 && <p className="serif-italic">{empty[tab]}</p>}

                {shown.map((th) => {
                  const on = subscribedIds.has(th.id)
                  // Les deux planches donnent une jauge à CHAQUE
                  // apprentissage suivi, y compris celui qu'on vient
                  // d'ajouter. Sans le « ?? 0 », la carte d'un
                  // apprentissage jamais commencé perdait sa barre et la
                  // grille prenait deux hauteurs. Un apprentissage non
                  // suivi n'a pas de jauge : il n'y a rien à mesurer.
                  const done = on ? (pct.get(th.id) ?? 0) : pct.get(th.id)
                  // Sous « Créés par moi », la ligne parle à l'auteur, pas
                  // à l'apprenant : ce qu'il veut savoir, c'est combien de
                  // consignes portent son apprentissage, ce qu'elles ont
                  // produit, et combien de gens s'y sont frottés.
                  const asOwner = tab === 'mine'
                  return (
                    <div
                      key={th.id}
                      className={asOwner ? 'learn-row is-mine' : 'learn-row'}
                      {...(asOwner
                        ? {
                            role: 'button',
                            tabIndex: 0,
                            'aria-label': `${t.themeDetail} — ${th.title}`,
                            onClick: () => openMyTheme(th.id),
                            onKeyDown: (e: KeyboardEvent<HTMLDivElement>) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault()
                                openMyTheme(th.id)
                              }
                            },
                          }
                        : {})}
                    >
                      <div className="learn-row-head">
                        <span className="stack" style={{ flex: 1, gap: 6, minWidth: 0 }}>
                          <span style={{ fontSize: 17, fontWeight: 500 }}>{th.title}</span>
                          <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                            {asOwner
                              ? `${t.promptsCount(th.prompt_count)} · ${t.exercisesCount(
                                  th.exercise_count,
                                )} · ${t.learnersCount(th.learner_count)}`
                              : `${th.category_label ?? ''} · ${t.exercisesCount(
                                  th.exercise_count,
                                )}`}
                          </span>
                        </span>
                        {/* Une croix, pas une coche. Le bouton ne dit pas
                            l'état de la ligne — il fait quelque chose, et
                            sur un apprentissage suivi ce quelque chose est
                            le retirer. La planche desktop écrit « Suivi ✓ »
                            au repos parce qu'elle a la place de nommer
                            l'état ; au survol, la pastille redevient le
                            geste et annonce « Retirer ». */}
                        <button
                          className={on ? 'learn-toggle is-on' : 'learn-toggle'}
                          aria-pressed={on}
                          aria-label={`${on ? t.unfollow : t.follow} — ${th.title}`}
                          title={on ? t.unfollow : t.follow}
                          onClick={(e) => {
                            // La ligne d'auteur est cliquable : sans ça,
                            // se désabonner ouvrirait la fiche au passage.
                            e.stopPropagation()
                            toggleSubscribe(th.id)
                          }}
                        >
                          {on && (
                            <span className="lt-face lt-rest">
                              {t.followedShort}
                              <Icon name="check" size={16} stroke={2.6} />
                            </span>
                          )}
                          <span className="lt-face lt-act">
                            <span className="lt-word">
                              {on ? t.unfollowShort : t.followShort}
                            </span>
                            <Icon
                              name={on ? 'close' : 'plus'}
                              size={on ? 18 : 20}
                              stroke={2.2}
                            />
                          </span>
                        </button>
                      </div>

                      {done !== undefined && (
                        <div className="learn-row-meter">
                          <Meter pct={done} />
                          <span className="learn-pct">{done} %</span>
                        </div>
                      )}
                    </div>
                  )
                })}

                {/* « Suggéré pour vous » — planche 1f. Le cadre est
                    pointillé, pas plein : ces lignes ne sont pas encore
                    à vous, et le bouton est un « + » vert, pas une
                    coche. */}
                {inlineSuggested.length > 0 && (
                  <>
                    <span className="mono learn-sugg-head">{t.suggestedForYou}</span>
                    {inlineSuggested.map((th) => (
                      <div key={th.id} className="learn-row is-sugg">
                        <span className="stack" style={{ flex: 1, gap: 4, minWidth: 0 }}>
                          <span style={{ fontSize: 17, fontWeight: 500 }}>{th.title}</span>
                          <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                            {/* La planche écrit « proche de vos
                                apprentissages » sur la suggestion qui
                                partage une catégorie avec un
                                apprentissage suivi, et le nombre
                                d'exercices sur les autres. Sans rien de
                                suivi, il n'y a rien dont être proche. */}
                            {th.category_label ?? ''} ·{' '}
                            {followedCategories.has(th.category_label ?? '')
                              ? t.nearYourLearnings
                              : t.exercisesCount(th.exercise_count)}
                          </span>
                        </span>
                        <button
                          className="learn-toggle"
                          aria-label={`${t.follow} — ${th.title}`}
                          title={t.follow}
                          onClick={() => toggleSubscribe(th.id)}
                        >
                          <span className="lt-face lt-act">
                            <span className="lt-word">{t.followShort}</span>
                            <Icon name="plus" size={20} stroke={2.2} />
                          </span>
                        </button>
                      </div>
                    ))}
                  </>
                )}
              </div>

              <button className="btn-primary themes-add desk-hide" onClick={() => go('picker')}>
                <Icon name="plus" size={18} stroke={2.2} />
                {t.addLearnings}
              </button>
            </div>

            {/* La colonne de droite : ce qu'on pourrait suivre, puis
                l'invitation à produire. Elle n'existe qu'en desktop —
                en téléphone ces deux blocs vivent dans l'onglet
                « Suggérés » et dans la barre du bas. */}
            <aside className="learn-side desk-only">
              <span className="mono">{t.suggestions}</span>

              {suggested.slice(0, 4).map((th) => (
                <div key={th.id} className="sugg-row">
                  <span className="stack" style={{ flex: 1, gap: 2, minWidth: 0 }}>
                    <span style={{ fontSize: 16, fontWeight: 500 }}>{th.title}</span>
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                      {th.category_label ?? ''} · {t.exercisesCount(th.exercise_count)}
                    </span>
                  </span>
                  <button
                    className="round-add"
                    style={{ borderRadius: 10, width: 44, height: 44 }}
                    onClick={() => toggleSubscribe(th.id)}
                    aria-label={`${t.follow} — ${th.title}`}
                  >
                    <Icon name="plus" size={20} stroke={2.2} />
                  </button>
                </div>
              ))}

              <div className="learn-promo">
                <span style={{ fontSize: 16, fontWeight: 700 }}>{t.shareKnowledge}</span>
                <span style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--sc-text2)' }}>
                  {t.shareKnowledgeLine}
                </span>
                <button className="btn-primary learn-promo-cta" onClick={() => goCreate(1)}>
                  {t.startSharing}
                </button>
              </div>
            </aside>
          </div>
        </div>
      </div>

      {/* En desktop, « partager une connaissance » est passée dans la
          colonne de droite : garder la barre du bas la dirait deux fois. */}
      <div className="footer-bar desk-hide">
        <button className="btn-outline" onClick={() => goCreate(1)}>
          <Icon name="plus" size={18} stroke={2.2} />
          {t.shareKnowledge}
        </button>
      </div>
    </div>
  )
}
