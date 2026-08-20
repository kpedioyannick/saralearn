import { useEffect, useState, type ReactNode } from 'react'
import { Icon } from './Icon'

/**
 * Barre du haut : donne le rythme, n'empêche jamais de swiper.
 *
 * Un seul segment. Il y en a eu trois, remplis sur `i % 3` : ça se
 * lisait « 2 sur 3 », donc une série qui finit, alors que le compteur
 * bouclait indéfiniment. Le seul repère qu'un fil sans fin puisse
 * donner honnêtement, c'est où en est l'écran qu'on a sous les yeux.
 *
 * `segments` reste un paramètre : une série vraiment finie — un quiz
 * ouvert par un code — aurait de quoi le justifier.
 */
export function Loader({
  progress,
  step = 0,
  segments = 1,
}: {
  progress: number
  step?: number
  segments?: number
}) {
  return (
    <div className="loader">
      {Array.from({ length: segments }, (_, i) => (
        <div key={i} className="loader-seg">
          <div
            className="loader-fill"
            style={{
              width: i < step ? '100%' : i === step ? `${Math.round(progress * 100)}%` : '0%',
            }}
          />
        </div>
      ))}
    </div>
  )
}

/**
 * L'attente, montrée honnêtement.
 *
 * Ce n'est pas un chargement : quand un apprentissage n'a pas encore de
 * questions, le serveur les ÉCRIT pendant la requête — une trentaine de
 * secondes. Trois barres qui scintillent ne disent pas ça. Elles ne
 * disent même pas que quelque chose avance : elles bouclent à l'identique
 * qu'il reste une seconde ou une minute, et au bout de dix secondes elles
 * se lisent comme une panne.
 *
 * D'où la même barre du haut que pendant un exercice, remplie par le
 * temps écoulé. Elle est asymptotique — `1 - exp(-t/τ)` — et n'atteint
 * donc JAMAIS le bout : on ne connaît pas la durée, et une barre qui
 * arrive à 100 % sur une attente qui continue est un mensonge que
 * l'utilisateur repère tout de suite. Elle ralentit, elle avance encore,
 * elle disparaît quand l'exercice arrive.
 *
 * Le texte change en route : au bout de six secondes, dire ce qui se
 * passe vaut mieux que répéter « on prépare ».
 */
export function useAttente(actif: boolean): { progress: number; long: boolean } {
  const [ms, setMs] = useState(0)

  useEffect(() => {
    if (!actif) {
      setMs(0)
      return
    }
    const debut = performance.now()
    const id = window.setInterval(() => setMs(performance.now() - debut), 200)
    return () => window.clearInterval(id)
  }, [actif])

  // τ = 12 s : à moitié remplie vers huit secondes, aux trois quarts vers
  // vingt, jamais au bout.
  return { progress: 1 - Math.exp(-ms / 12000), long: ms > 6000 }
}

/** Le corps de l'attente : les barres qui scintillent, et la phrase. */
export function PreparingText({
  label,
  longLabel,
  long,
}: {
  label: string
  longLabel: string
  long: boolean
}) {
  return (
    <>
      <span className="shimmer-bar" style={{ width: 200 }} />
      <span className="shimmer-bar" style={{ width: 150, animationDelay: '120ms' }} />
      <p
        style={{
          fontSize: 14,
          color: 'var(--sc-text3)',
          textAlign: 'center',
          maxWidth: '32ch',
        }}
      >
        {long ? longLabel : label}
      </p>
    </>
  )
}

export function StatusBar() {
  return (
    <div className="status-bar">
      <span>9:41</span>
      <span className="status-bar-icons">
        <Icon name="signal" width={17} height={12} stroke={1.6} />
        <Icon name="battery" width={22} height={12} stroke={1.3} />
      </span>
    </div>
  )
}

export function NavHead({
  onBack,
  title,
  subtitle,
  children,
}: {
  onBack?: () => void
  title?: ReactNode
  subtitle?: string
  children?: ReactNode
}) {
  return (
    <div className="nav-head">
      {onBack && (
        <button className="icon-btn" onClick={onBack} aria-label="Back">
          <Icon name="chevronLeft" size={22} stroke={1.9} />
        </button>
      )}
      {title && (
        <span className="stack" style={{ flex: 1 }}>
          <span className="nav-title">{title}</span>
          {subtitle && (
            <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>{subtitle}</span>
          )}
        </span>
      )}
      {children}
    </div>
  )
}

/**
 * Le retour, en desktop.
 *
 * Le rail ne porte que ses six destinations. Un écran ouvert DEPUIS
 * l'une d'elles — le catalogue, le détail d'une connaissance que je
 * partage, « à propos », la publication — n'y a aucune entrée : sa
 * flèche de retour vit dans `NavHead`, que `.desk-hide` masque au-delà
 * de 1024 px. Il ne restait alors que le Précédent du navigateur, et
 * rien à l'écran ne disait qu'on était descendu d'un cran.
 *
 * `label` nomme la destination plutôt que le geste : « ← Ce que je
 * partage » dit où l'on retombe, « ← Retour » demande de s'en souvenir.
 *
 * Le bouton se pose en premier enfant de `.page-inner` — l'en-tête qui
 * le suit rend alors la bande qu'il réservait en haut, sinon la page
 * commencerait 90 px plus bas que les autres.
 */
export function PageBack({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button className="page-back" onClick={onClick}>
      <Icon name="chevronLeft" size={17} stroke={2} />
      {label}
    </button>
  )
}

/**
 * Les pourcentages n'apparaissent que sur progression et classement —
 * jamais pendant un exercice.
 */
export function Meter({ pct, fill }: { pct: number; fill?: string }) {
  return (
    <span className="meter">
      <span
        className="meter-fill"
        style={{ width: `${pct}%`, background: fill ?? 'var(--sc-primary)' }}
      />
    </span>
  )
}

export function meterColor(pct: number): string {
  return pct >= 80 ? 'var(--gold-500)' : 'var(--sc-primary)'
}

export function Toggle({ on }: { on: boolean }) {
  return (
    <span
      className="toggle-track"
      style={{ background: on ? 'var(--success-500)' : 'var(--sc-line)' }}
    >
      <span
        className="toggle-knob"
        style={{ transform: on ? 'translateX(22px)' : 'translateX(0)' }}
      />
    </span>
  )
}

export function Checkbox({ on }: { on: boolean }) {
  return (
    <span
      className="checkbox"
      style={{
        background: on ? 'var(--sc-primary)' : 'transparent',
        borderColor: on ? 'var(--sc-primary)' : 'var(--sc-line)',
      }}
    >
      <Icon
        name="check"
        size={14}
        stroke={3}
        color="var(--sc-on-primary)"
        opacity={on ? 1 : 0}
      />
    </span>
  )
}

export function TileCheck() {
  return (
    <span className="tile-check">
      <Icon name="check" size={14} stroke={3} color="var(--sc-on-primary)" />
    </span>
  )
}

export function Dot({ color, size = 10 }: { color: string; size?: number }) {
  return <span className="dot" style={{ width: size, height: size, background: color }} />
}

const CONFETTI_COLORS = [
  'var(--confetti-1)',
  'var(--confetti-2)',
  'var(--confetti-3)',
  'var(--confetti-4)',
  'var(--confetti-5)',
  'var(--confetti-6)',
]

/**
 * Les confettis de la félicitation.
 *
 * Ils sont calculés une fois pour toutes, pas tirés au sort : une
 * réussite doit tomber pareil à chaque fois, sinon la célébration
 * clignote différemment d'un exercice à l'autre et l'œil le voit.
 */
const CONFETTI = Array.from({ length: 34 }, (_, i) => ({
  left: `${((i * 6.2 + (i % 3) * 2.1) % 96) + 2}%`,
  width: [6, 8, 10, 12][i % 4],
  height: [9, 13, 17][i % 3],
  round: i % 5 === 0,
  color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
  duration: `${2.6 + (i % 6) * 0.35}s`,
  delay: `${(i % 9) * 0.28}s`,
}))

export function Confetti() {
  return (
    <div className="confetti" aria-hidden="true">
      {CONFETTI.map((c, i) => (
        <span
          key={i}
          style={{
            left: c.left,
            width: c.width,
            height: c.height,
            borderRadius: c.round ? 999 : 2,
            background: c.color,
            animationDuration: c.duration,
            animationDelay: c.delay,
          }}
        />
      ))}
    </div>
  )
}

export function Avatar({ name, color, size = 34 }: { name: string; color: string; size?: number }) {
  return (
    <span
      style={{
        width: size,
        height: size,
        borderRadius: 999,
        flex: 'none',
        display: 'grid',
        placeItems: 'center',
        fontSize: size > 34 ? 15 : 14,
        fontWeight: 700,
        color: '#FFFFFF',
        background: color,
      }}
    >
      {name.charAt(0)}
    </span>
  )
}
