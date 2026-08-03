import type { ReactNode } from 'react'
import { Icon } from './Icon'

/** Barre du haut : donne le rythme, n'empêche jamais de swiper. */
export function Loader({ progress }: { progress: number }) {
  return (
    <div className="loader">
      <div className="loader-fill" style={{ width: `${Math.round(progress * 100)}%` }} />
    </div>
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
