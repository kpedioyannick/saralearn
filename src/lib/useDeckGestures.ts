import { useCallback, useEffect, useRef, type PointerEvent as ReactPointerEvent } from 'react'

/**
 * Le geste est entièrement contrôlé — pas de scroll-snap CSS. Bloquer
 * un scroll natif en cours de geste produit une saccade sur iOS, et le
 * deck doit pouvoir refuser un swipe à tout moment.
 *
 * Trois entrées équivalentes : pointeur, molette, flèches.
 */

const DRAG_LIMIT = 70
const DRAG_FACTOR = 0.45
const DRAG_THRESHOLD = 48
const WHEEL_COOLDOWN = 700
const WHEEL_MIN_DELTA = 24

interface Options {
  active: boolean
  onNext: () => void
  onPrev: () => void
  onDrag: (dy: number) => void
}

export function useDeckGestures({ active, onNext, onPrev, onDrag }: Options) {
  const start = useRef(0)
  const dragging = useRef(false)
  const wheelAt = useRef(0)

  const onPointerDown = useCallback((e: ReactPointerEvent) => {
    start.current = e.clientY
    dragging.current = true
  }, [])

  const onPointerMove = useCallback(
    (e: ReactPointerEvent) => {
      if (!dragging.current) return
      const dy = (e.clientY - start.current) * DRAG_FACTOR
      onDrag(Math.max(-DRAG_LIMIT, Math.min(DRAG_LIMIT, dy)))
    },
    [onDrag],
  )

  const onPointerUp = useCallback(
    (e: ReactPointerEvent) => {
      if (!dragging.current) return
      dragging.current = false
      const dy = e.clientY - start.current
      onDrag(0)
      if (dy < -DRAG_THRESHOLD) onNext()
      else if (dy > DRAG_THRESHOLD) onPrev()
    },
    [onDrag, onNext, onPrev],
  )

  useEffect(() => {
    if (!active) return

    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      if (target && /^(INPUT|TEXTAREA)$/.test(target.tagName)) return
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        onNext()
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        onPrev()
      }
    }

    const onWheel = (e: WheelEvent) => {
      const now = Date.now()
      if (now - wheelAt.current < WHEEL_COOLDOWN || Math.abs(e.deltaY) < WHEEL_MIN_DELTA) return
      wheelAt.current = now
      if (e.deltaY > 0) onNext()
      else onPrev()
    }

    window.addEventListener('keydown', onKey)
    window.addEventListener('wheel', onWheel, { passive: true })
    return () => {
      window.removeEventListener('keydown', onKey)
      window.removeEventListener('wheel', onWheel)
    }
  }, [active, onNext, onPrev])

  return { onPointerDown, onPointerMove, onPointerUp, onPointerLeave: onPointerUp }
}
