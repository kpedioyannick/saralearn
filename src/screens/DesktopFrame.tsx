import { useCallback } from 'react'
import { AudioBar } from '../components/AudioBar'
import { ClozePicks } from '../components/Cloze'
import { Icon, type IconName } from '../components/Icon'
import { LangSwitch } from '../components/LangSwitch'
import { OptionButton } from '../components/OptionButton'
import { ShortAnswer } from '../components/ShortAnswer'
import { PhaseBody } from '../components/PhaseBlocks'
import { Rail } from '../components/Rail'
import { Dot, Loader, Meter, PreparingText, useAttente } from '../components/ui'
import type { Dict } from '../i18n'
import { useDeckGestures } from '../lib/useDeckGestures'
import { type Screen, routeOf, useStore } from '../state/store'

/**
 * Le cadre desktop.
 *
 * La barre horizontale a laissé place à un rail vertical à gauche —
 * c'est le geste de la planche, et il libère toute la hauteur pour le
 * contenu. Replié, il tient en 84 px d'icônes ; déployé, il montre le
 * logo complet, les libellés et les apprentissages à reprendre.
 */

/** Les écrans qui méritent toute la largeur de l'écran. */
const WIDE = new Set<Screen>([
  'settings',
  'about',
  'rank',
  'themes',
  'picker',
  'picker2',
  'auth',
  'onb1',
  'onb2',
  'onb3',
  'publish',
  'rankOne',
  'create',
  'home',
  'shared',
  'sharedOne',
  'contact',
  'pseudo',
])

/** Les écrans qui se présentent seuls : ni rail, ni cadre d'app. */
const BARE = new Set<Screen>(['home'])

const NAV: { screen: Screen; icon: IconName; label: (t: Dict) => string }[] = [
  // Un point d'interrogation, pas une maison : la maison désigne
  // l'accueil public, et elle le désignait déjà dans les réglages. Le
  // même dessin pour deux destinations, c'est celui qu'on suit qui
  // devient un pari.
  { screen: 'exo', icon: 'question', label: (t) => t.exercisesNav },
  // La grille mène au CATALOGUE (`#add-themes`), pas à la liste de ce
  // qu'on suit (`#themes`). Les deux écrans montrent la même chose quand
  // on ne suit rien — sauf que celui-ci ne propose rien à faire. Le rail
  // envoie donc là où il y a quelque chose à choisir ; « mes
  // apprentissages » reste joignable par la flèche de retour du
  // catalogue, qui pointe déjà dessus.
  { screen: 'picker', icon: 'grid', label: (t) => t.myLearnings },
  { screen: 'rank', icon: 'trophy', label: (t) => t.ranking },
  { screen: 'settings', icon: 'sliders', label: (t) => t.settings },
]

/**
 * Le second groupe : deux pages qui ne sont pas le travail quotidien
 * mais qu'on doit pouvoir joindre d'un clic — l'accueil public, qu'on
 * envoie à quelqu'un pour expliquer l'app, et nous écrire, qu'on ouvre
 * quand quelque chose ne va pas. Elles vivaient au fond des réglages.
 */
const NAV_MORE: { screen: Screen; icon: IconName; label: (t: Dict) => string }[] = [
  { screen: 'home', icon: 'bulb', label: (t) => t.homeHow },
  { screen: 'contact', icon: 'mail', label: (t) => t.writeToUs },
]

function SideRail() {
  const { s, set, go, goCreate, user, progression, subscribedIds, t } = useStore()
  const open = s.railOpen

  const link = (screen: Screen, icon: IconName, label: string, badge?: string) => (
    <a
      key={screen}
      // La grille reste allumée sur les DEUX écrans du catalogue :
      // elle mène à « ajouter », mais « mes apprentissages » est la même
      // destination vue autrement, et l'éteindre en y arrivant donnerait
      // un rail où rien n'est sélectionné.
      className={
        s.screen === screen || (screen === 'picker' && s.screen === 'themes')
          ? 'side-link is-on'
          : 'side-link'
      }
      href={routeOf(screen)}
      title={open ? undefined : label}
      aria-label={label}
      aria-current={s.screen === screen ? 'page' : undefined}
      onClick={(e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey) return
        e.preventDefault()
        go(screen, screen === 'exo' ? 'q' : undefined)
      }}
    >
      <Icon name={icon} size={20} />
      {open && <span className="side-label">{label}</span>}
      {open && badge && <span className="side-badge">{badge}</span>}
    </a>
  )

  return (
    <nav className={open ? 'side-rail is-open' : 'side-rail'}>
      {open ? (
        <div className="side-head">
          <span className="side-mark" style={{ width: 34, height: 34, borderRadius: 10, fontSize: 17 }}>
            S
          </span>
          <span
            className="side-label"
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 25,
              fontWeight: 700,
              letterSpacing: '-0.02em',
            }}
          >
            <span style={{ color: 'var(--sc-brand)' }}>Sara</span>Learn
          </span>
          <button
            className="side-toggle"
            onClick={() => set({ railOpen: false })}
            aria-label={t.close}
          >
            <Icon name="chevronLeft" size={15} stroke={2} />
          </button>
        </div>
      ) : (
        <button className="side-mark" onClick={() => go('exo', 'q')} aria-label="SaraLearn">
          S
        </button>
      )}

      {NAV.map(({ screen, icon, label }) =>
        link(
          screen,
          icon,
          label(t),
          // Le compte suit la grille, qui a changé de destination : sans
          // ça la pastille disparaissait avec l'ancien écran.
          screen === 'picker' && subscribedIds.size > 0 ? String(subscribedIds.size) : undefined,
        ),
      )}

      {/* « Reprendre » n'a de sens que déployé : replié, trois icônes de
          plus deviendraient indistinctes des quatre destinations. */}
      {open && progression.length > 0 && (
        <>
          <hr className="side-rule" />
          <span className="mono" style={{ padding: '0 14px 8px' }}>
            {t.progression}
          </span>
          {progression.slice(0, 3).map((p) => (
            <a
              key={p.theme_id}
              className="side-link"
              href={routeOf('themes')}
              onClick={(e) => {
                e.preventDefault()
                go('themes')
              }}
            >
              <Dot color="var(--sc-primary)" size={10} />
              <span className="side-label">{p.name}</span>
              <span className="side-badge">{p.pct} %</span>
            </a>
          ))}
        </>
      )}

      <div style={{ flex: 1 }} />

      <hr className="side-rule" />
      {NAV_MORE.map(({ screen, icon, label }) => link(screen, icon, label(t)))}

      <button className="side-cta" onClick={() => goCreate(1)} aria-label={t.shareKnowledge}>
        <Icon name="plus" size={open ? 18 : 24} stroke={2.2} />
        {open && t.shareKnowledge}
      </button>

      {/* Repliée en « FR · EN », dépliée en toutes lettres : à 84 px de
          rail, deux mots entiers ne tiennent pas. */}
      <LangSwitch compact={!open} />

      {open ? (
        <button className="side-account" onClick={() => go('settings')}>
          <span
            style={{
              width: 38,
              height: 38,
              borderRadius: 999,
              background: 'var(--sc-veil)',
              display: 'grid',
              placeItems: 'center',
              fontSize: 15,
              fontWeight: 700,
            }}
          >
            {(user?.display_name || user?.email || 'S').charAt(0).toUpperCase()}
          </span>
          <span className="stack" style={{ flex: 1, gap: 0, textAlign: 'left' }}>
            <span style={{ fontSize: 15, fontWeight: 500 }}>
              {user?.display_name || user?.email || t.signIn}
            </span>
            <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
              {user && !user.is_anonymous ? t.myAccount : t.localAccount}
            </span>
          </span>
          <Icon name="chevronRight" size={16} color="var(--sc-text3)" />
        </button>
      ) : (
        <button
          className="side-toggle"
          onClick={() => set({ railOpen: true })}
          aria-label={t.menu}
        >
          <Icon name="chevronRight" size={15} stroke={2} />
        </button>
      )}
    </nav>
  )
}

export function DesktopFrame({ children }: { children?: React.ReactNode }) {
  const { s, exo, set, next, prev, advance, goCreate, /* themes, */ progression, subscribedIds, toggleSubscribe, ready, offline, t } =
    useStore()
  const onExercise = s.screen === 'exo'
  // La carte n'a pas d'exercice : elle en attend un, et souvent le
  // serveur est en train de l'écrire. La barre du haut de la carte, qui
  // donne le rythme d'un exercice, donne alors celui de l'attente.
  const attente = useAttente(onExercise && !exo && !(offline && ready))
  // Pendant l'inscription et sur l'accueil public, le rail ne propose
  // rien : on ne navigue pas dans une app où l'on n'est pas entré.
  const onboarding =
    s.screen === 'onb1' || s.screen === 'onb2' || s.screen === 'onb3' || s.screen === 'pseudo'
  const bare = BARE.has(s.screen) || onboarding

  const onDrag = useCallback((dragY: number) => set({ dragY }), [set])
  const gestures = useDeckGestures({
    active: onExercise && !s.sheet && exo !== null,
    onNext: next,
    onPrev: prev,
    onDrag,
  })

  if (bare) return <div className="screen">{children}</div>

  // Quatre suggestions à côté de l'exercice : celles auxquelles on
  // n'est pas encore abonné, l'abonnement se prenant d'un clic.
  // ENDORMI avec le bloc « À suivre aussi » — voir plus bas. Le calcul
  // reste écrit parce qu'il repartira avec lui ; `noUnusedLocals` est
  // actif, donc il ne peut pas rester vivant à côté d'un bloc muet.
  // const suggested = themes.filter((x) => !x.subscribed).slice(0, 3)
  const current = progression.find((p) => p.theme_id === exo?.themeId)

  return (
    <div className="screen">
      <div className="shell">
        <SideRail />

        {onExercise ? (
          <div className="desk-stage">
            <div className={s.phase === 'ok' ? 'desk-card is-ok' : 'desk-card'} {...gestures}>
              {/* Même bandeau qu'en téléphone, en haut de la carte — et
                  comme lui, il PARTAGE SA LIGNE avec la pastille
                  d'apprentissage et le « + ». Ils formaient une bande de
                  plus sous le loader, à côté d'un orbe qui laissait la
                  sienne presque vide. La carte fait 720 px de haut : ce
                  qui est repris là revient au texte, qui est ce qui
                  débordait. */}
              <div className="desk-card-bar">
                <AudioBar desktop />
                {exo && s.phase !== 'ok' && (
                  <>
                    <button className="chip" onClick={() => set({ sheet: 'theme' })}>
                      <Dot color={exo.color} size={7} />
                      <span style={{ fontSize: 15 }}>{exo.theme}</span>
                      <span
                        className="chip-sub"
                        onClick={(e) => {
                          e.stopPropagation()
                          toggleSubscribe(exo.themeId)
                        }}
                      >
                        {subscribedIds.has(exo.themeId) ? t.followed : t.follow}
                      </span>
                    </button>
                    <button
                      className="round-add"
                      onClick={() => goCreate(1)}
                      aria-label={t.shareKnowledge}
                    >
                      <Icon name="plus" size={22} stroke={2.2} />
                    </button>
                  </>
                )}
              </div>

              <Loader progress={exo ? s.prog : attente.progress} />

              {exo ? (
                <>
                  {/* Voir `Exercise` : `data-scroll` marque la zone de
                      lecture, à qui le geste revient tant qu'il reste du
                      texte sous le pointeur. */}
                  <div
                    className="desk-card-body"
                    data-scroll
                    style={{ transform: `translateY(${s.dragY}px)` }}
                  >
                    <PhaseBody desktop />
                  </div>

                  <div className="desk-card-foot">
                    {/* Même partage qu'en téléphone : produire ou choisir. */}
                    {s.phase === 'q' ? (
                      exo.typeQuestion === 'short_answer' ? (
                        <ShortAnswer key={exo.id} />
                      ) : exo.typeQuestion === 'cloze' ? (
                        <ClozePicks />
                      ) : (
                        <div className="options">
                          {exo.options.map((label, i) => (
                            <OptionButton key={`${exo.id}-${i}`} label={label} index={i} />
                          ))}
                        </div>
                      )
                    ) : s.phase === 'exp' ? (
                      <button className="btn-primary" onClick={advance}>
                        {t.nextExercise}
                      </button>
                    ) : (
                      <button className="btn-primary" onClick={advance}>
                        {t.seeExplanation}
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <div
                  className="stack"
                  style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: 14 }}
                >
                  {/* La branche « le serveur ne répond pas » manquait
                      ici : le téléphone l'avait, le desktop laissait
                      scintiller ses barres indéfiniment, et une panne
                      d'API se lisait comme une préparation sans fin. */}
                  {offline && ready ? (
                    <>
                      <Icon name="alert" size={32} color="var(--sc-text3)" />
                      <p className="display" style={{ fontSize: 24, textAlign: 'center' }}>
                        {t.serverDown}
                      </p>
                      <p className="body" style={{ textAlign: 'center', fontSize: 15 }}>
                        {t.serverDownHint}
                      </p>
                      <button
                        className="btn-primary"
                        style={{ width: 220 }}
                        onClick={() => window.location.reload()}
                      >
                        {t.retry}
                      </button>
                    </>
                  ) : (
                    <PreparingText
                      label={t.preparing}
                      longLabel={t.preparingLong}
                      long={attente.long}
                    />
                  )}
                </div>
              )}
            </div>

            {/* Les flèches entrent dans le rail — voir `Rail`. */}
            <Rail size="desktop" onPrev={prev} onNext={next} />

            {/* La colonne de droite reprend la planche : ce qu'on pourrait
                suivre, et où l'on en est sur l'apprentissage en cours.

                « À SUIVRE AUSSI » EST ENDORMI (20/08/2026). Le bloc est
                commenté et non supprimé : il tient debout tel quel, et
                le rallumer ne demande que d'ôter les deux marqueurs —
                ici et sur `suggested`, plus haut. La colonne ne montre
                donc plus que la progression de l'apprentissage en
                cours. */}
            <div className="desk-side">
              {/*
              <span className="mono">{t.followAlso}</span>
              {suggested.map((th) => (
                <div
                  key={th.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: 14,
                    borderRadius: 16,
                    background: 'var(--sc-veil)',
                  }}
                >
                  <span className="stack" style={{ flex: 1, gap: 2 }}>
                    <span style={{ fontSize: 16, fontWeight: 500 }}>{th.title}</span>
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                      {t.exercisesCount(th.exercise_count)}
                    </span>
                  </span>
                  <button
                    className="round-add"
                    style={{ borderRadius: 12 }}
                    onClick={() => toggleSubscribe(th.id)}
                    aria-label={`${t.follow} ${th.title}`}
                  >
                    <Icon name="plus" size={20} stroke={2.2} />
                  </button>
                </div>
              ))}
              */}
              {current && (
                <div
                  className="stack"
                  style={{
                    gap: 8,
                    padding: 16,
                    borderRadius: 16,
                    background: 'var(--sc-primary-soft)',
                    border: '1px solid var(--sc-primary-line)',
                  }}
                >
                  <span style={{ fontSize: 15, fontWeight: 700 }}>
                    {current.name} · {current.pct} %
                  </span>
                  <Meter pct={current.pct} />
                  <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>{t.progression}</span>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
            <div className={WIDE.has(s.screen) ? 'desk-column is-wide' : 'desk-column'}>
              {children}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
