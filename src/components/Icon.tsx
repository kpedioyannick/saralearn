import type { CSSProperties, ReactNode } from 'react'

/**
 * Toutes les icônes de la maquette, en un seul jeu : trait de 1.75,
 * bouts et jointures arrondis, viewBox 24. Elles héritent de la
 * couleur du parent via currentColor.
 */

export type IconName =
  | 'check'
  | 'circleCheck'
  | 'undo'
  | 'heart'
  | 'thumbUp'
  | 'thumbDown'
  | 'message'
  | 'trophy'
  | 'sliders'
  | 'chevronRight'
  | 'chevronLeft'
  | 'chevronDown'
  | 'chevronUp'
  | 'arrowDown'
  | 'bulb'
  | 'moon'
  | 'volume'
  | 'plus'
  | 'minus'
  | 'sparkle'
  | 'lock'
  | 'globe'
  | 'user'
  | 'dots'
  | 'file'
  | 'text'
  | 'mic'
  | 'pencil'
  | 'trash'
  | 'alert'
  | 'close'
  | 'send'
  | 'signal'
  | 'battery'

const PATHS: Record<IconName, ReactNode> = {
  check: <path d="M20 6 9 17l-5-5" />,
  circleCheck: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="m8.5 12 2.3 2.3L15.5 9.7" />
    </>
  ),
  undo: (
    <>
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
    </>
  ),
  heart: <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z" />,
  message: <path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z" />,
  // Pouces dessinés dans le même trait que le reste du jeu : 1.75,
  // bouts arrondis. Le pouce bas est le pouce haut retourné, pour que
  // les deux se lisent comme une paire et non comme deux symboles.
  thumbUp: (
    <>
      <path d="M7 22V11l4.5-8a2 2 0 0 1 2.9 2.4L13 10h5.6a2 2 0 0 1 2 2.4l-1.5 7A2.5 2.5 0 0 1 16.6 22Z" />
      <path d="M7 11H4.5A1.5 1.5 0 0 0 3 12.5v8A1.5 1.5 0 0 0 4.5 22H7" />
    </>
  ),
  thumbDown: (
    <>
      <path d="M17 2v11l-4.5 8a2 2 0 0 1-2.9-2.4L11 14H5.4a2 2 0 0 1-2-2.4l1.5-7A2.5 2.5 0 0 1 7.4 2Z" />
      <path d="M17 13h2.5A1.5 1.5 0 0 0 21 11.5v-8A1.5 1.5 0 0 0 19.5 2H17" />
    </>
  ),
  trophy: (
    <>
      <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16" />
      <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0V2Z" />
    </>
  ),
  sliders: (
    <>
      <path d="M20 7h-9M14 17H5" />
      <circle cx="17" cy="17" r="3" />
      <circle cx="7" cy="7" r="3" />
    </>
  ),
  chevronRight: <path d="m9 18 6-6-6-6" />,
  chevronLeft: <path d="m15 18-6-6 6-6" />,
  chevronDown: <path d="m6 9 6 6 6-6" />,
  chevronUp: <path d="m18 15-6-6-6 6" />,
  arrowDown: <path d="m5 12 7 7 7-7M12 5v14" />,
  bulb: (
    <>
      <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.8.8 1.3 1.5 1.5 2.5" />
      <path d="M9 18h6M10 22h4" />
    </>
  ),
  moon: <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />,
  volume: (
    <>
      <path d="M11 4.7 6.3 9H2v6h4.3l4.7 4.3V4.7Z" />
      <path d="M15.5 8.5a5 5 0 0 1 0 7" />
    </>
  ),
  plus: <path d="M5 12h14M12 5v14" />,
  minus: <path d="M5 12h14" />,
  sparkle: <path d="m12 3-1.9 5.8L4.3 10.7l5.8 1.9L12 18.4l1.9-5.8 5.8-1.9-5.8-1.9L12 3Z" />,
  lock: (
    <>
      <rect x="3" y="11" width="18" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
    </>
  ),
  globe: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18" />
    </>
  ),
  user: (
    <>
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4.2 3.6-6.5 8-6.5s8 2.3 8 6.5" />
    </>
  ),
  /* Les trois points sont pleins : en contour, à 3 px de rayon, ils
     bavent et se lisent comme des cercles vides. */
  dots: (
    <>
      <circle cx="12" cy="5" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none" />
      <circle cx="12" cy="19" r="1.6" fill="currentColor" stroke="none" />
    </>
  ),
  file: (
    <>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
      <path d="M14 2v6h6" />
    </>
  ),
  text: <path d="M4 7V5h16v2M9 20h6M12 5v15" />,
  mic: (
    <>
      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3" />
    </>
  ),
  pencil: <path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />,
  trash: <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />,
  alert: (
    <>
      <path d="M12 9v4M12 17h.01" />
      <circle cx="12" cy="12" r="9" />
    </>
  ),
  close: <path d="m18 6-12 12M6 6l12 12" />,
  send: <path d="M5 12h14M12 5l7 7-7 7" />,
  signal: <path d="M1 9v2M5 6.5V11M9 4v7M13 1.5V11" />,
  battery: (
    <>
      <rect x="1" y="2" width="17" height="8" rx="2.4" />
      <rect x="2.8" y="3.8" width="11" height="4.4" rx="1.2" fill="currentColor" stroke="none" />
      <path d="M19.6 4.6v2.8" strokeWidth="1.8" />
    </>
  ),
}

const VIEWBOX: Partial<Record<IconName, string>> = {
  signal: '0 0 17 12',
  battery: '0 0 22 12',
}

interface Props {
  name: IconName
  size?: number
  width?: number
  height?: number
  stroke?: number
  fill?: string
  color?: string
  style?: CSSProperties
  className?: string
  opacity?: number
}

export function Icon({
  name,
  size = 21,
  width,
  height,
  stroke = 1.75,
  fill = 'none',
  color,
  style,
  className,
  opacity,
}: Props) {
  return (
    <svg
      width={width ?? size}
      height={height ?? size}
      viewBox={VIEWBOX[name] ?? '0 0 24 24'}
      fill={fill}
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={{ color, flex: 'none', opacity, ...style }}
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  )
}
