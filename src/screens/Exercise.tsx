import { useCallback } from 'react'
import { ClozePicks } from '../components/Cloze'
import { Icon } from '../components/Icon'
import { OptionButton } from '../components/OptionButton'
import { ShortAnswer } from '../components/ShortAnswer'
import { PhaseBody } from '../components/PhaseBlocks'
import { Rail } from '../components/Rail'
import { Loader } from '../components/ui'
import { useDeckGestures } from '../lib/useDeckGestures'
import { useStore } from '../state/store'

export function Exercise() {
  const { s, exo, set, next, prev, ready, offline, t } = useStore()

  const onDrag = useCallback((dragY: number) => set({ dragY }), [set])
  const gestures = useDeckGestures({
    active: s.screen === 'exo' && !s.sheet && exo !== null,
    onNext: next,
    onPrev: prev,
    onDrag,
  })

  // Le garde vient après les hooks — leur ordre ne doit jamais dépendre
  // d'une condition.
  if (!exo) return <Waiting ready={ready} offline={offline} />

  const showHint = s.hint && s.phase === 'q'

  return (
    <div className="screen exo" {...gestures}>
      <Loader progress={s.prog} />

      <div className="exo-head">
        <button className="chip" onClick={() => set({ sheet: 'theme' })}>
          <span className="dot" style={{ width: 10, height: 10, background: exo.color }} />
          <span>{exo.theme}</span>
          <Icon name="chevronRight" size={14} stroke={2} color="var(--sc-text3)" />
        </button>
        <span className="eyebrow">{exo.type}</span>
      </div>

      <div className="exo-body" style={{ transform: `translateY(${s.dragY}px)` }}>
        <PhaseBody />
      </div>

      <div className="exo-foot">
        {showHint && (
          <div className="swipe-hint">
            <span>
              <Icon name="arrowDown" size={16} stroke={2} />
              {t.swipeHint}
            </span>
          </div>
        )}

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
          <button className="btn-primary" style={{ width: 298 }} onClick={next}>
            <Icon
              name="arrowDown"
              size={18}
              stroke={2}
              style={{ animation: 'bob 1600ms ease-in-out infinite' }}
            />
            {t.nextExercise}
          </button>
        ) : null}
      </div>

      <Rail />
    </div>
  )
}

/**
 * Le feed n'a pas encore répondu — ou plus personne ne répond. Dans les
 * deux cas on le dit, plutôt que de laisser un écran vide.
 */
function Waiting({ ready, offline }: { ready: boolean; offline: boolean }) {
  const { t } = useStore()
  return (
    <div
      className="screen"
      style={{ justifyContent: 'center', alignItems: 'center', gap: 18, padding: '0 40px' }}
    >
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
          <span className="shimmer-bar" style={{ width: 200 }} />
          <span className="shimmer-bar" style={{ width: 150, animationDelay: '120ms' }} />
          <p style={{ fontSize: 14, color: 'var(--sc-text3)' }}>{t.preparing}</p>
        </>
      )}
    </div>
  )
}
