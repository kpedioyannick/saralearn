import { useStore } from '../state/store'
import { Icon } from './Icon'

/**
 * Ne jamais afficher la répartition des réponses option par option :
 * ça donnerait la solution. Les quatre états ci-dessous sont les
 * seules informations révélées, et seulement après la réponse.
 */
export function OptionButton({ label, index }: { label: string; index: number }) {
  const { s, exo, revealed, answer } = useStore()
  if (!exo) return null

  let background = 'var(--sc-surface)'
  let borderColor = 'var(--sc-line)'
  let color = 'var(--sc-text)'
  let borderWidth = 1

  if (revealed) {
    if (index === exo.correct) {
      background = 'var(--sc-good-bg)'
      borderColor = 'var(--sc-good-line)'
      color = 'var(--sc-good-ink)'
      borderWidth = 2
    } else if (index === s.chosen) {
      background = 'var(--sc-miss-bg)'
      borderColor = 'var(--sc-miss-line)'
      color = 'var(--sc-miss-ink)'
    } else {
      background = 'transparent'
      color = 'var(--sc-text3)'
    }
  }

  return (
    <button
      className="option"
      onClick={() => answer(index)}
      disabled={revealed}
      style={{ background, borderColor, borderWidth, color }}
    >
      <span>{label}</span>
      {revealed && index === exo.correct && <Icon name="check" size={18} stroke={2.6} />}
    </button>
  )
}
