import { useCallback } from 'react'
import { AudioBar } from '../components/AudioBar'
import { ClozePicks } from '../components/Cloze'
import { Icon } from '../components/Icon'
import { MoreMenu } from '../components/MobileBar'
import { OptionButton } from '../components/OptionButton'
import { ShortAnswer } from '../components/ShortAnswer'
import { PhaseBody } from '../components/PhaseBlocks'
import { Rail } from '../components/Rail'
import { Loader, PreparingText, useAttente } from '../components/ui'
import { useDeckGestures } from '../lib/useDeckGestures'
import { useStore } from '../state/store'

export function Exercise() {
  const { s, exo, set, next, prev, advance, ready, offline, goCreate, subscribedIds, toggleSubscribe, t } =
    useStore()

  const onDrag = useCallback((dragY: number) => set({ dragY }), [set])
  const gestures = useDeckGestures({
    active: s.screen === 'exo' && !s.sheet && exo !== null,
    onNext: next,
    onPrev: prev,
    onDrag,
  })

  // Le garde vient après les hooks — leur ordre ne doit jamais dépendre
  // d'une condition.
  // Le quiz partagé est fini : on le dit, au lieu de laisser tourner un
  // écran de chargement qui n'attend plus rien.
  if (!exo && s.code && s.codeDone) return <CodeDone />
  if (!exo) return <Waiting ready={ready} offline={offline} />

  const showHint = s.hint && s.phase === 'q'
  const celebrating = s.phase === 'ok'
  const followed = subscribedIds.has(exo.themeId)

  return (
    <div className={celebrating ? 'screen exo is-ok' : 'screen exo'} {...gestures}>
      {/* Le bandeau de lecture prend la bande du haut, le loader se
          resserre juste dessous. Les deux sont dans le flux : la barre
          du haut, fixe, passait par-dessus les segments du loader. */}
      <div className="exo-top">
        {/* Le quiz ouvert par un code ferme le flux : on dit lequel, et
            on donne la sortie. Sans ce bandeau, la disparition des
            autres apprentissages ne s'explique pas. */}
        <CodeBanner />

        {/* TOUT LE HAUT TIENT SUR LA LIGNE DE L'ORBE. La pastille
            d'apprentissage, le « + » et les trois points formaient une
            bande à eux seuls, sous le bandeau : 58 px pris sur la
            lecture, à côté d'un orbe de 44 px qui laissait sa ligne
            aux trois quarts vide. Ils la partagent désormais.
            C'est autant de rendu à la question — et depuis que chaque
            carte porte une photo, c'est la question qui manquait de
            place. */}
        <div className="exo-bar">
          <AudioBar />
          {/* La félicitation prend l'écran entier : ni pastille
              d'apprentissage ni bouton d'ajout ne doivent la partager.
              L'orbe, lui, reste — il lit la félicitation. */}
          {!celebrating && (
            <>
              <button className="chip" onClick={() => set({ sheet: 'theme' })}>
                <span className="dot" style={{ width: 7, height: 7, background: exo.color }} />
                <span>{exo.theme}</span>
                <span
                  className="chip-sub"
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleSubscribe(exo.themeId)
                  }}
                >
                  {followed ? t.followed : t.follow}
                </span>
              </button>
              {/* Le feed n'a plus de barre du haut : les trois points la
                  suivent ici, à droite du « + », comme sur la planche. */}
              <div className="exo-bar-acts">
                <button className="round-add" onClick={() => goCreate(1)} aria-label={t.shareKnowledge}>
                  <Icon name="plus" size={22} stroke={2.2} />
                </button>
                <MoreMenu withLang />
              </div>
            </>
          )}
        </div>

        <Loader progress={s.prog} />
      </div>

      {/* `data-scroll` déclare la zone de lecture au geste du deck : tant
          qu'il reste du texte à découvrir, le geste lui appartient. */}
      <div
        className="exo-body"
        data-scroll
        style={{ transform: `translateY(${s.dragY}px)` }}
      >
        <PhaseBody />
      </div>

      <div className="exo-foot">
        {/* Répondre change de geste selon le type : on tape une réponse,
            on comble un trou, ou on choisit parmi des options. */}
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
          /* Réussite et erreur : la seule sortie, depuis qu'aucun
             minuteur ne passe à l'explication tout seul. */
          <button className="btn-primary" onClick={advance}>
            {t.seeExplanation}
          </button>
        )}

        {/* L'indice passe sous les réponses : c'est ce qu'on fait APRÈS
            avoir répondu, et au-dessus il poussait la question vers le
            haut de l'écran à chaque première carte. */}
        {showHint && (
          <div className="swipe-hint">
            <span>
              <Icon name="arrowUp" size={16} stroke={2} />
              {t.swipeHint}
            </span>
          </div>
        )}
      </div>

      {!celebrating && <Rail />}
    </div>
  )
}

/**
 * Le feed n'a pas encore répondu — ou plus personne ne répond. Dans les
 * deux cas on le dit, plutôt que de laisser un écran vide.
 */
/**
 * Le bandeau du quiz ouvert par un code.
 *
 * Il vit hors de l'écran d'exercice parce qu'il doit survivre à son
 * absence : un quiz partagé a peu de questions — quatre, parfois — et
 * une fois épuisées l'app retombe sur l'écran d'attente. Sans ce
 * bandeau là aussi, on se retrouve devant « on prépare tes exercices… »
 * sans bandeau, sans sortie, et sans comprendre : enfermé.
 */
export function CodeBanner() {
  const { s, leaveCode, t } = useStore()
  if (!s.code) return null
  return (
    <div className="code-banner">
      <span className="code-banner-name">
        <span className="mono">{t.codeBanner}</span>
        {s.codeTitle && <b>{s.codeTitle}</b>}
      </span>
      <button className="code-banner-out" onClick={leaveCode}>
        {t.codeLeave}
      </button>
    </div>
  )
}

/** La fin d'un quiz partagé — un vrai terminus, pas une attente. */
function CodeDone() {
  const { s, restartCode, leaveCode, t } = useStore()
  return (
    <div className="screen">
      <div style={{ padding: 12 }}>
        <CodeBanner />
      </div>

      <div
        className="stack"
        style={{ flex: 1, justifyContent: 'center', alignItems: 'center', gap: 14, padding: '0 32px', textAlign: 'center' }}
      >
        <Icon name="circleCheck" size={40} color="var(--sc-primary)" />
        <p className="display" style={{ fontSize: 26 }}>
          {t.codeDoneTitle}
        </p>
        <p className="body" style={{ fontSize: 16, color: 'var(--sc-text2)', maxWidth: '34ch' }}>
          {s.codeTitle ? `« ${s.codeTitle} » — ${t.codeDoneLine}` : t.codeDoneLine}
        </p>

        <div className="stack" style={{ gap: 10, width: '100%', maxWidth: 320, marginTop: 8 }}>
          <button className="btn-primary" onClick={restartCode}>
            {t.codeRestart}
          </button>
          <button className="btn-outline" onClick={leaveCode}>
            {t.codeLeave}
          </button>
        </div>
      </div>
    </div>
  )
}

function Waiting({ ready, offline }: { ready: boolean; offline: boolean }) {
  const { s, t } = useStore()
  // L'attente n'est un chargement que le premier quart de seconde : passé
  // ça, le serveur ÉCRIT les questions de l'apprentissage ouvert. La
  // barre du haut suit le temps écoulé — voir `useAttente`.
  const attente = useAttente(!(offline && ready))
  return (
    <div
      className="screen"
      style={{ justifyContent: 'center', alignItems: 'center', gap: 18, padding: '0 40px' }}
    >
      {/* Posé en haut, hors du centrage, sinon il flotterait au milieu
          de l'écran d'attente. */}
      {s.code && (
        <div style={{ position: 'absolute', top: 12, left: 12, right: 12 }}>
          <CodeBanner />
        </div>
      )}
      {offline && ready ? (
        <>
          <Icon name="alert" size={32} color="var(--sc-text3)" />
          <p className="display" style={{ fontSize: 26, textAlign: 'center' }}>
            {t.serverDown}
          </p>
          <p className="body" style={{ textAlign: 'center', fontSize: 16 }}>
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
        <>
          <Loader progress={attente.progress} />
          <PreparingText label={t.preparing} longLabel={t.preparingLong} long={attente.long} />
        </>
      )}
    </div>
  )
}
