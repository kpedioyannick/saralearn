import { useStore, type ExoCard } from '../state/store'
import { ClozeText, clozeExpected, clozeGiven } from './Cloze'
import { Icon } from './Icon'

/**
 * Les quatre contenus de la séquence, partagés entre mobile et
 * desktop. Seules les tailles changent d'un cadre à l'autre.
 */

interface Props {
  desktop?: boolean
}

export function QuestionBlock({ desktop }: Props) {
  const { exo } = useStore()
  if (!exo) return null
  return (
    <div className="stack anim-fade-up" style={{ gap: 18 }}>
      {/* L'illustration passe AVANT la question : sur « que signifie ce
          panneau ? », c'est elle qui porte l'information. Hauteur bornée
          en unités de viewport pour que l'écran ne scrolle jamais. */}
      {exo.image && (
        <img
          src={exo.image}
          alt={exo.imageAlt ?? ''}
          className="exo-image"
          style={{ maxHeight: desktop ? 200 : '26dvh' }}
        />
      )}
      <p
        className="display"
        style={{
          // Une image occupe déjà la place : la question se fait plus
          // discrète pour que les deux tiennent ensemble.
          fontSize: exo.image ? (desktop ? 26 : 22) : desktop ? 38 : 32,
          lineHeight: desktop ? 1.2 : 1.25,
        }}
      >
        {exo.prompt}
      </p>
      {/* Un texte à trous EST le corps de la question : ses trous se
          remplissent là où on les lit, pas dans un bloc à part. */}
      {exo.typeQuestion === 'cloze' ? (
        <ClozeText desktop={desktop} />
      ) : (
        exo.body && (
          <div
            style={{
              padding: desktop ? '18px 20px' : '18px 20px',
              borderRadius: 14,
              background: desktop ? 'var(--sc-sunk)' : 'var(--sc-surface)',
              border: '1px solid var(--sc-line)',
              fontSize: desktop ? 18 : 17,
              lineHeight: 1.6,
              color: 'var(--sc-text2)',
              boxShadow: desktop ? 'none' : 'var(--shadow-sm)',
            }}
          >
            {exo.body}
          </div>
        )
      )}
    </div>
  )
}

/** Bravo : célébration dorée, anneau qui s'échappe, coche qui se trace. */
export function SuccessBlock({ desktop }: Props) {
  const { s, exo, t } = useStore()
  if (!exo) return null
  const ring = desktop ? 132 : 104
  const disc = desktop ? 112 : 88
  const glyph = desktop ? 56 : 44

  const streakLine =
    s.streak > 1 ? t.streakMany(s.streak) : t.streakOne(s.win)

  return (
    <div
      className="stack anim-fade-up"
      style={{ alignItems: 'center', gap: desktop ? 24 : 22, textAlign: 'center' }}
    >
      <div style={{ position: 'relative', width: ring, height: ring, display: 'grid', placeItems: 'center' }}>
        <span
          style={{
            position: 'absolute',
            inset: 0,
            borderRadius: 999,
            border: '2px solid var(--gold-500)',
            animation: 'ring 1100ms var(--ease-out) 120ms infinite',
          }}
        />
        <span
          className="anim-pop"
          style={{
            width: disc,
            height: disc,
            borderRadius: 999,
            background: 'var(--gold-500)',
            display: 'grid',
            placeItems: 'center',
            boxShadow: '0 8px 24px -6px rgba(200,147,46,.55)',
          }}
        >
          <svg
            width={glyph}
            height={glyph}
            viewBox="0 0 24 24"
            fill="none"
            stroke="#FFFFFF"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path
              d="M20 6 9 17l-5-5"
              strokeDasharray="32"
              style={{ animation: 'drawIn 420ms var(--ease-out) 160ms both' }}
            />
          </svg>
        </span>
      </div>

      <p className="display" style={{ fontSize: desktop ? 52 : 38, lineHeight: 1.08 }}>
        {exo.okTitle}
      </p>
      <p
        className="body"
        style={{ fontSize: desktop ? 19 : 17, lineHeight: 1.65, maxWidth: desktop ? 380 : 280 }}
      >
        {exo.okLine}
      </p>
      <span
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 9,
          height: desktop ? 38 : 32,
          padding: '0 16px',
          borderRadius: 999,
          background: desktop ? 'var(--sc-sunk)' : 'var(--sc-surface)',
          border: '1px solid var(--sc-line)',
          fontSize: desktop ? 14 : 13,
          fontWeight: 600,
          color: 'var(--sc-text3)',
        }}
      >
        {desktop && <Icon name="check" size={15} stroke={2.4} color="var(--success-500)" />}
        {streakLine}
      </span>
    </div>
  )
}

/**
 * Erreur non punitive : aucune croix, aucun rouge. Un ambre de reprise,
 * la réponse attendue en vert calme, une ligne en italique qui
 * dédramatise.
 */
/**
 * Ce que l'apprenant a répondu. Sur un QCM c'est l'option touchée ; sur
 * une réponse courte, ce qu'il a écrit ; sur un texte à trous, ce qu'il
 * a posé trou par trou. Pour ces deux derniers, la réponse donnée n'est
 * pas dans `options` — la relire dedans afficherait autre chose.
 */
function givenAnswer(
  exo: ExoCard,
  s: { chosen: number | null; typed: string; fills: (number | null)[] },
): string {
  const chosen = s.chosen !== null ? (exo.options[s.chosen] ?? '') : ''
  if (exo.typeQuestion === 'short_answer') return s.typed || chosen
  if (exo.typeQuestion === 'cloze') return clozeGiven(exo, s.fills).join(' · ')
  return chosen
}

/** Ce qu'il fallait répondre — la graphie canonique, ou un trou par trou. */
function expectedAnswer(exo: ExoCard): string {
  if (exo.typeQuestion === 'cloze') return clozeExpected(exo).join(' · ')
  return exo.options[exo.correct] ?? ''
}

export function MissBlock({ desktop }: Props) {
  const { s, exo, t } = useStore()
  if (!exo) return null
  const chosenLabel = givenAnswer(exo, s)

  return (
    <div className="stack anim-fade-up" style={{ gap: desktop ? 22 : 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: desktop ? 16 : 12 }}>
        <span
          className="anim-pop"
          style={{
            width: desktop ? 56 : 44,
            height: desktop ? 56 : 44,
            borderRadius: 999,
            background: 'var(--warning-50)',
            display: 'grid',
            placeItems: 'center',
            flex: 'none',
          }}
        >
          <Icon name="undo" size={desktop ? 28 : 22} stroke={1.9} color="var(--warning-500)" />
        </span>
        <p className="display" style={{ fontSize: desktop ? 44 : 30, lineHeight: 1.12 }}>
          {exo.koTitle}
        </p>
      </div>

      <div
        style={
          desktop
            ? { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }
            : { display: 'flex', flexDirection: 'column', gap: 10 }
        }
      >
        <div
          style={{
            padding: desktop ? '18px 20px' : '14px 16px',
            borderRadius: 12,
            background: 'var(--sc-sunk)',
            border: '1px solid var(--sc-line)',
          }}
        >
          <span className="eyebrow">{t.yourAnswer}</span>
          <p
            style={{
              margin: '5px 0 0',
              fontSize: desktop ? 19 : 17,
              fontWeight: 600,
              color: 'var(--sc-text2)',
            }}
          >
            {chosenLabel}
          </p>
        </div>
        <div
          style={{
            padding: desktop ? '18px 20px' : '14px 16px',
            borderRadius: 12,
            background: 'var(--sc-good-bg)',
            border: '1px solid var(--sc-good-line)',
          }}
        >
          <span className="eyebrow" style={{ color: 'var(--sc-good-ink)' }}>
            {t.rightAnswer}
          </span>
          <p
            style={{
              margin: '5px 0 0',
              fontSize: desktop ? 19 : 17,
              fontWeight: 700,
              color: 'var(--sc-good-ink)',
            }}
          >
            {expectedAnswer(exo)}
          </p>
        </div>
      </div>

      <p className="serif-italic" style={{ fontSize: desktop ? 21 : 18 }}>
        {exo.koLine}
      </p>
    </div>
  )
}

export function ExplanationBlock({ desktop }: Props) {
  const { exo, t } = useStore()
  if (!exo) return null
  return (
    <div className="stack anim-fade-up" style={{ gap: desktop ? 20 : 18 }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: desktop ? 11 : 10 }}>
        <Icon name="bulb" size={desktop ? 24 : 22} color="var(--gold-500)" />
        <span className="eyebrow" style={{ color: 'var(--gold-500)' }}>
          {t.explanation}
        </span>
      </span>
      <p className="display" style={{ fontSize: desktop ? 36 : 28, lineHeight: 1.22 }}>
        {exo.expTitle}
      </p>
      <p className="body" style={{ fontSize: desktop ? 19 : 17 }}>
        {exo.expText}
      </p>
      <div
        className="stack"
        style={{
          padding: desktop ? '20px 22px' : '16px 18px',
          borderRadius: 14,
          background: desktop ? 'var(--sc-sunk)' : 'var(--sc-surface)',
          border: '1px solid var(--sc-line)',
          gap: 8,
          boxShadow: desktop ? 'none' : 'var(--shadow-sm)',
        }}
      >
        <span className="eyebrow">{t.remember}</span>
        <p
          style={{
            margin: 0,
            fontSize: desktop ? 18 : 16,
            lineHeight: 1.6,
            fontWeight: 600,
            color: 'var(--sc-text)',
          }}
        >
          {exo.expTip}
        </p>
      </div>
    </div>
  )
}

export function PhaseBody({ desktop }: Props) {
  const { s } = useStore()
  switch (s.phase) {
    case 'q':
      return <QuestionBlock desktop={desktop} />
    case 'ok':
      return <SuccessBlock desktop={desktop} />
    case 'ko':
      return <MissBlock desktop={desktop} />
    case 'exp':
      return <ExplanationBlock desktop={desktop} />
  }
}
