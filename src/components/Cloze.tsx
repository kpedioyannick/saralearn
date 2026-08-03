import { Fragment } from 'react'
import { useStore, type ExoCard } from '../state/store'

/**
 * Texte à trous.
 *
 * Le texte vit dans le bloc question, les candidats dans le pied : un
 * seul composant ne peut pas peindre les deux, ils sont donc séparés et
 * se retrouvent sur l'état partagé (`fills`, `blank`).
 *
 * Chaque trou porte SES candidats — `option.blank` dit à quel trou une
 * proposition appartient, `option.correct` si elle est la bonne. Jamais
 * de banque commune : un distracteur ciblé fait travailler, un
 * distracteur mutualisé se devine par élimination.
 */

/** Le caractère que les rédacteurs posent à la place d'un trou (U+2026). */
const HOLE = '…'

/** Les segments de texte : n trous, n + 1 segments. */
function segments(body: string | undefined): string[] {
  return (body ?? '').split(HOLE)
}

/** Le nombre de trous du texte. */
export function blankCount(exo: ExoCard): number {
  return Math.max(0, segments(exo.body).length - 1)
}

/** Le libellé posé dans chaque trou, dans l'ordre du texte. */
export function clozeGiven(exo: ExoCard, fills: (number | null)[]): string[] {
  return Array.from({ length: blankCount(exo) }, (_, i) => {
    const at = fills[i]
    return at == null ? HOLE : (exo.opts[at]?.label ?? HOLE)
  })
}

/** Ce qu'il fallait poser, trou par trou. */
export function clozeExpected(exo: ExoCard): string[] {
  return Array.from(
    { length: blankCount(exo) },
    (_, i) => exo.opts.find((o) => o.blank === i && o.correct)?.label ?? HOLE,
  )
}

/**
 * Le texte et ses trous — remplace le corps de la question. Un trou se
 * rouvre d'un tap, rempli ou non : se corriger doit être aussi simple
 * que répondre.
 */
export function ClozeText({ desktop }: { desktop?: boolean }) {
  const { s, exo, revealed, set } = useStore()
  if (!exo) return null

  const parts = segments(exo.body)
  // Un `cloze` sans trou est une erreur de rédaction, pas une raison de
  // ne rien afficher : le texte reste lisible.
  if (parts.length < 2) return <p className="cloze-text">{exo.body}</p>

  const total = parts.length - 1
  const given = clozeGiven(exo, s.fills)

  return (
    <p className={desktop ? 'cloze-text is-desktop' : 'cloze-text'}>
      {parts.map((part, i) => {
        if (i >= total) return <Fragment key={i}>{part}</Fragment>
        const filled = s.fills[i] != null
        const active = !revealed && s.blank === i
        return (
          <Fragment key={i}>
            {part}
            <button
              type="button"
              className={
                'cloze-blank' + (filled ? ' is-filled' : '') + (active ? ' is-active' : '')
              }
              onClick={() => set({ blank: i })}
              disabled={revealed}
              aria-current={active ? 'true' : undefined}
            >
              {given[i]}
            </button>
          </Fragment>
        )
      })}
    </p>
  )
}

/**
 * Les candidats du trou courant — et eux seuls. Poser une réponse ouvre
 * le trou suivant ; le dernier trou rempli vaut soumission.
 */
export function ClozePicks() {
  const { s, exo, revealed, answer, set, t } = useStore()
  if (!exo) return null

  const total = blankCount(exo)
  if (total === 0) return null

  const at = Math.min(Math.max(0, s.blank), total - 1)
  const candidates = exo.opts
    .map((option, index) => ({ option, index }))
    .filter(({ option }) => option.blank === at)

  const pick = (index: number) => {
    if (revealed) return
    const fills = Array.from({ length: total }, (_, i) =>
      i === at ? index : (s.fills[i] ?? null),
    )

    // Le trou suivant s'ouvre de lui-même : le premier vide après celui
    // qu'on vient de poser, sinon le premier vide tout court.
    const after = fills.findIndex((f, i) => i > at && f === null)
    const first = fills.indexOf(null)
    set({ fills, blank: after >= 0 ? after : first >= 0 ? first : at })

    if (first < 0 && after < 0) {
      const good = fills.every((f) => f !== null && exo.opts[f]?.correct === true)
      // Même verdict que pour une option : on renvoie l'index attendu
      // quand tout est juste, un autre sinon. `correct_index` n'a pas de
      // sens ici, mais il reste ce que l'API compare.
      answer(good ? exo.correct : exo.correct === 0 ? 1 : 0)
    }
  }

  return (
    <div className="produce">
      <span className="eyebrow">{t.blankOf(at + 1, total)}</span>
      {/* Un trou sans candidat est une erreur de données : on n'invente
          pas de réponse, les autres trous restent atteignables. */}
      <div className="cloze-picks">
        {candidates.map(({ option, index }) => (
          <button
            key={index}
            type="button"
            className="cloze-pick"
            onClick={() => pick(index)}
            disabled={revealed}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  )
}
