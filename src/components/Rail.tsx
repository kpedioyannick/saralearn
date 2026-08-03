import { useStore } from '../state/store'
import { Icon } from './Icon'

/**
 * Réussites et échecs se lisent : pas d'état pressé, pas de rôle
 * bouton. J'aime, commentaire, classement et réglages sont de vraies
 * cibles de 44 px. Six éléments, c'est le maximum tenable.
 */
export function Rail({ size = 'mobile' }: { size?: 'mobile' | 'desktop' }) {
  const { s, set, go, myVote, upCount, downCount, commentCount, vote, exo, t } = useStore()
  const disc = size === 'desktop' ? 52 : 44
  const glyph = size === 'desktop' ? 23 : 21
  const discStyle = { width: disc, height: disc }
  // Sept éléments au lieu de six : l'espacement se resserre de 14 à 10.
  const railStyle = size === 'mobile' ? { gap: 10 } : undefined

  return (
    <div className={size === 'desktop' ? 'rail rail-desktop' : 'rail'} style={railStyle}>
      <div className="rail-item">
        <span className="rail-disc" style={{ ...discStyle, color: 'var(--success-500)' }}>
          <Icon name="circleCheck" size={glyph} />
        </span>
        <span className="rail-count">{s.win}</span>
      </div>

      <div className="rail-item">
        <span className="rail-disc" style={{ ...discStyle, color: 'var(--warning-500)' }}>
          <Icon name="undo" size={glyph} />
        </span>
        <span className="rail-count">{s.fail}</span>
      </div>

      {/* Le pouce bas n'est pas décoratif : sans relecture humaine, c'est
          lui qui sort du flux un exercice fautif. Voir la quarantaine
          côté API. Revoter la même chose retire le vote. */}
      <button
        className="rail-item is-button"
        onClick={() => vote(1)}
        disabled={!exo}
        aria-pressed={myVote === 1}
        aria-label={myVote === 1 ? t.voteUndo : t.voteUp}
      >
        <span
          className="rail-disc"
          style={{
            ...discStyle,
            background: myVote === 1 ? 'var(--sc-primary-soft)' : 'var(--sc-surface)',
            color: myVote === 1 ? 'var(--sc-primary)' : 'var(--sc-text)',
          }}
        >
          <Icon name="thumbUp" size={glyph} fill={myVote === 1 ? 'currentColor' : 'none'} />
        </span>
        <span className="rail-count">{upCount}</span>
      </button>

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
            ...discStyle,
            // Ambre, jamais rouge : le refus reste dans le registre
            // non punitif du reste de l'app.
            background: myVote === -1 ? 'var(--warning-50)' : 'var(--sc-surface)',
            color: myVote === -1 ? 'var(--warning-500)' : 'var(--sc-text)',
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
        <span className="rail-disc" style={discStyle}>
          <Icon name="message" size={glyph} />
        </span>
        <span className="rail-count">{commentCount}</span>
      </button>

      <button className="rail-item is-button" onClick={() => go('rank')} aria-label={t.ranking}>
        <span className="rail-disc" style={discStyle}>
          <Icon name="trophy" size={glyph} />
        </span>
      </button>

      {size === 'mobile' && (
        <button
          className="rail-item is-button"
          onClick={() => go('settings')}
          aria-label={t.settings}
        >
          <span className="rail-disc" style={discStyle}>
            <Icon name="sliders" size={glyph} />
          </span>
        </button>
      )}
    </div>
  )
}
