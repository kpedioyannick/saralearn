import { useState, type FormEvent, type PointerEvent } from 'react'
import { accepts } from '../lib/normalise'
import { useStore } from '../state/store'
import { Icon } from './Icon'

/**
 * Réponse courte — un champ, pas d'options.
 *
 * Toutes les options servies sont des graphies ACCEPTÉES : la réponse
 * est juste dès qu'elle en rejoint une après normalisation. La première
 * (`correct_index`, toujours 0) est la graphie canonique, celle qu'on
 * affiche en correction.
 *
 * L'index envoyé au store n'est donc plus un choix mais un verdict : on
 * renvoie l'index attendu quand c'est juste, un autre sinon. Le reste du
 * chemin — compteurs, tentative, enchaînement des phases — ne bouge pas,
 * et l'API continue de recalculer la justesse de son côté.
 */
export function ShortAnswer() {
  const { exo, revealed, answer, set, t } = useStore()
  const [value, setValue] = useState('')
  if (!exo) return null

  const empty = value.trim() === ''

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (revealed || empty) return
    const good = accepts(value, exo.options)
    // `chosen_index` reste borné à 0–3 côté API : on ne peut pas y glisser
    // un code particulier, juste un index qui tombe du bon côté.
    set({ typed: value.trim() })
    answer(good ? exo.correct : exo.correct === 0 ? 1 : 0)
  }

  return (
    <form className="produce" onSubmit={submit}>
      {/* La consigne au-dessus du champ, pas dedans : une indication qui
          tient dans 200px se coupe à la première traduction un peu
          longue, et elle disparaît dès la première lettre tapée. */}
      <span className="eyebrow">{t.oneWordOnly}</span>
      <div className="produce-line">
        <input
          className="produce-input"
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={revealed}
          placeholder={t.shortAnswerHint}
          aria-label={t.yourAnswer}
          autoComplete="off"
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          enterKeyHint="send"
          /* Le deck écoute le pointeur sur tout l'écran : sans ça, glisser
             dans le champ pour placer le curseur fait défiler la carte. */
          onPointerDown={(e: PointerEvent) => e.stopPropagation()}
        />
        <button
          className="produce-send"
          type="submit"
          disabled={revealed || empty}
          aria-label={t.validateAnswer}
        >
          <Icon name="send" size={20} stroke={2.2} />
        </button>
      </div>
    </form>
  )
}
