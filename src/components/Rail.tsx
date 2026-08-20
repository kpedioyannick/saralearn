import { useStore } from '../state/store'
import { Icon } from './Icon'

/**
 * Le rail d'actions, superposé au contenu le long du bord droit.
 *
 * Réussites et échecs se lisent : pas d'état pressé, pas de rôle
 * bouton. J'aime, j'aime pas et commentaires sont de vraies cibles.
 *
 * Le rail ne navigue pas : il n'agit que sur l'exercice sous les yeux.
 * Le classement et les réglages y ont vécu, en double — le menu « ⋯ »
 * de l'entête les sert déjà en téléphone, le rail de gauche en desktop.
 * Deux chemins vers le même écran sur un écran qui n'en demandait
 * aucun.
 *
 * Le compteur d'échecs est le seul endroit rouge de l'app : c'est un
 * chiffre, pas un jugement porté sur une réponse. Les écrans d'erreur
 * restent en ambre, sans croix.
 */
/**
 * Les deux flèches vivent DANS le rail, et en desktop seulement.
 *
 * Elles formaient `.desk-nav`, une colonne à elles au bord de l'écran :
 * une quatrième pile à côté de la carte, du rail et de la colonne de
 * droite. Passer à l'exercice suivant et aimer celui qu'on lit sont
 * deux gestes sur la même carte — ils tiennent sur la même colonne.
 *
 * Le téléphone ne les reçoit pas : il change de carte au doigt, et une
 * flèche superposée au texte y prendrait la place de la lecture. C'est
 * l'absence des deux fonctions qui le décide — `Exercise` ne les passe
 * pas.
 *
 * La montante est en PREMIER, la descendante en DERNIER : l'ordre à
 * l'écran est celui du geste, et les votes restent groupés entre les
 * deux.
 */
interface Props {
  size?: 'mobile' | 'desktop'
  onPrev?: () => void
  onNext?: () => void
}

export function Rail({ size = 'mobile', onPrev, onNext }: Props) {
  const { s, set, myVote, upCount, downCount, commentCount, vote, exo, t } = useStore()
  const glyph = size === 'desktop' ? 22 : 19

  return (
    <div className={size === 'desktop' ? 'rail rail-desktop' : 'rail'}>
      {onPrev && (
        <button className="rail-item is-button rail-nav" onClick={onPrev} aria-label={t.prevExercise}>
          <span className="rail-disc">
            <Icon name="chevronUp" size={24} stroke={1.9} />
          </span>
        </button>
      )}

      <div className="rail-item">
        <span className="rail-disc" style={{ background: 'var(--sc-primary-soft)', color: 'var(--sc-primary)' }}>
          <Icon name="check" size={glyph} stroke={2.4} />
        </span>
        <span className="rail-count">{s.win}</span>
      </div>

      <div className="rail-item">
        <span className="rail-disc" style={{ background: 'var(--sc-bad-bg)', color: 'var(--sc-bad)' }}>
          <Icon name="close" size={glyph} stroke={2.4} />
        </span>
        <span className="rail-count">{s.fail}</span>
      </div>

      {/* Un cœur plutôt qu'un pouce haut : la planche parle de « j'aime »,
          et le pouce haut faisait paire avec le pouce bas alors que les
          deux gestes n'ont pas le même poids — l'un plébiscite, l'autre
          signale un exercice fautif. */}
      <button
        className="rail-item is-button"
        onClick={() => vote(1)}
        disabled={!exo}
        aria-pressed={myVote === 1}
        aria-label={myVote === 1 ? t.voteUndo : t.voteUp}
      >
        <span
          className="rail-disc"
          style={{ color: myVote === 1 ? '#e0426d' : 'var(--sc-text)' }}
        >
          <Icon name="heart" size={glyph} fill={myVote === 1 ? 'currentColor' : 'none'} />
        </span>
        <span className="rail-count">{upCount}</span>
      </button>

      {/* Le pouce bas n'est pas décoratif : sans relecture humaine, c'est
          lui qui sort du flux un exercice fautif. Voir la quarantaine
          côté API. Revoter la même chose retire le vote. */}
      <button
        className="rail-item is-button"
        onClick={() => vote(-1)}
        disabled={!exo}
        aria-pressed={myVote === -1}
        aria-label={myVote === -1 ? t.voteUndo : t.voteDown}
      >
        <span
          className="rail-disc"
          style={{
            background: myVote === -1 ? 'var(--sc-miss-bg)' : undefined,
            color: myVote === -1 ? 'var(--sc-miss-ink)' : 'var(--sc-text)',
          }}
        >
          <Icon name="thumbDown" size={glyph} fill={myVote === -1 ? 'currentColor' : 'none'} />
        </span>
        <span className="rail-count">{downCount}</span>
      </button>

      <button
        className="rail-item is-button"
        onClick={() => set({ sheet: 'comments' })}
        disabled={!exo}
        aria-label={t.comments}
      >
        <span className="rail-disc">
          <Icon name="message" size={glyph} />
        </span>
        <span className="rail-count">{commentCount}</span>
      </button>

      {onNext && (
        <button className="rail-item is-button rail-nav" onClick={onNext} aria-label={t.nextExercise}>
          <span className="rail-disc">
            <Icon name="chevronDown" size={24} stroke={1.9} />
          </span>
        </button>
      )}
    </div>
  )
}
