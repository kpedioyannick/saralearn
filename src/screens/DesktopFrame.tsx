import { useCallback } from 'react'
import { ClozePicks } from '../components/Cloze'
import { Icon } from '../components/Icon'
import { OptionButton } from '../components/OptionButton'
import { ShortAnswer } from '../components/ShortAnswer'
import { PhaseBody } from '../components/PhaseBlocks'
import { Rail } from '../components/Rail'
import { Wordmark } from '../components/Wordmark'
import { Dot, Loader } from '../components/ui'
import type { Dict } from '../i18n'
import { useDeckGestures } from '../lib/useDeckGestures'
import { type Screen, routeOf, useStore } from '../state/store'

/**
 * Le même flux, dans un cadre vertical centré. Les réponses sortent du
 * bloc question, le rail passe à gauche, les thèmes à suivre à droite,
 * et la navigation haut/bas double la molette et les flèches.
 */
/** Les écrans qui méritent toute la largeur de l'écran. */
const WIDE = new Set<Screen>(['settings', 'about', 'rank', 'themes', 'picker', 'auth'])

/** Les quatre destinations qu'on doit pouvoir atteindre d'un clic, partout. */
const NAV: { screen: Screen; label: (t: Dict) => string }[] = [
  { screen: 'themes', label: (t) => t.myThemes },
  { screen: 'rank', label: (t) => t.ranking },
  { screen: 'settings', label: (t) => t.settings },
  { screen: 'about', label: (t) => t.about },
]

export function DesktopFrame({ children }: { children?: React.ReactNode }) {
  const { s, exo, set, next, prev, go, toggleMute, user, t } = useStore()
  const onExercise = s.screen === 'exo'

  const onDrag = useCallback((dragY: number) => set({ dragY }), [set])
  const gestures = useDeckGestures({
    active: onExercise && !s.sheet && exo !== null,
    onNext: next,
    onPrev: prev,
    onDrag,
  })

  return (
    <div className="screen">
      <div className="topbar">
        <Wordmark />
        {/* De vrais liens, pas des boutons : on peut les ouvrir dans un
            onglet, les copier, les mettre en favori. Le clic reste géré
            par le store — la navigation est interne — mais l'adresse est
            réelle et partageable. */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: 4, marginRight: 'auto' }}>
          {NAV.map(({ screen, label }) => (
            <a
              key={screen}
              className="topbar-btn"
              href={routeOf(screen)}
              aria-current={s.screen === screen ? 'page' : undefined}
              onClick={(e) => {
                if (e.metaKey || e.ctrlKey || e.shiftKey) return
                e.preventDefault()
                go(screen)
              }}
              style={{
                textDecoration: 'none',
                color: s.screen === screen ? 'var(--sc-primary)' : undefined,
              }}
            >
              {label(t)}
            </a>
          ))}
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="topbar-btn" onClick={toggleMute}>
            <Icon name="volume" size={17} />
            {s.muted ? t.soundOff : t.soundOn}
          </button>
          {/* L'état du compte se lit depuis n'importe quel écran : connecté,
              on montre qui ; sinon, l'entrée pour se connecter. Sans ça il
              fallait ouvrir les réglages pour savoir où l'on en était. */}
          {user && !user.is_anonymous ? (
            <button
              className="topbar-btn"
              onClick={() => go('settings')}
              title={user.email ?? undefined}
              aria-label={`${t.myAccount} — ${user.email ?? ''}`}
            >
              <Icon name="user" size={17} />
              <span style={{ maxWidth: 140, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.display_name || user.email}
              </span>
            </button>
          ) : (
            <button
              className="topbar-btn"
              onClick={() => set({ screen: 'auth', authMode: 'login', authError: null })}
            >
              <Icon name="user" size={17} />
              {t.signIn}
            </button>
          )}
          <button
            className="topbar-btn"
            onClick={() => go('settings')}
            style={{ width: 40, padding: 0, justifyContent: 'center' }}
            aria-label={t.settings}
          >
            <Icon name="sliders" size={18} />
          </button>
        </div>
      </div>

      {onExercise ? (
        <div className="desk-stage">
          <Rail size="desktop" />

          <div className="desk-card" {...gestures}>
            <Loader progress={s.prog} />

            {exo ? (
              <>
                <div className="desk-card-head">
                  <button
                    className="chip"
                    onClick={() => set({ sheet: 'theme' })}
                    style={{ height: 36 }}
                  >
                    <Dot color={exo.color} />
                    <span style={{ fontSize: 15 }}>{exo.theme}</span>
                  </button>
                  <span className="eyebrow">{exo.type}</span>
                </div>

                <div
                  className="desk-card-body"
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
                    <button className="btn-primary" style={{ minHeight: 56 }} onClick={next}>
                      {t.nextExercise}
                    </button>
                  ) : null}
                </div>
              </>
            ) : (
              <div
                className="stack"
                style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: 14 }}
              >
                <span className="shimmer-bar" style={{ width: 240 }} />
                <span className="shimmer-bar" style={{ width: 180, animationDelay: '120ms' }} />
                <p style={{ fontSize: 14, color: 'var(--sc-text3)' }}>
                  {t.preparing}
                </p>
              </div>
            )}
          </div>

          {/* « À suivre aussi » a été retiré : à côté d'un exercice en
              cours, une colonne d'abonnements tire l'œil hors de la
              question. L'abonnement reste accessible par le thème et
              par les réglages. */}

          <div className="desk-nav">
            <button onClick={prev} aria-label={t.prevExercise}>
              <Icon name="chevronUp" size={24} stroke={1.9} />
            </button>
            <button onClick={next} aria-label={t.nextExercise}>
              <Icon name="chevronDown" size={24} stroke={1.9} />
            </button>
          </div>
        </div>
      ) : (
        <div style={{ flex: 1, minHeight: 0, position: 'relative' }}>
          {/* Les écrans que la maquette dessine à 1180px prennent toute
              la largeur. Ceux qu'elle ne couvre pas en desktop (création,
              niveau 2 du choix, publication) gardent la colonne. */}
          <div className={WIDE.has(s.screen) ? 'desk-column is-wide' : 'desk-column'}>
            {children}
          </div>
        </div>
      )}
    </div>
  )
}
