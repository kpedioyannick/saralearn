import { useCallback, useEffect, useRef, type PointerEvent as ReactPointerEvent } from 'react'

/**
 * Le geste est entièrement contrôlé — pas de scroll-snap CSS. Bloquer
 * un scroll natif en cours de geste produit une saccade sur iOS, et le
 * deck doit pouvoir refuser un swipe à tout moment.
 *
 * Trois entrées équivalentes : pointeur, molette, flèches.
 *
 * Le deck cède la main à la lecture. Une question ou une explication
 * plus haute que son cadre défile dans sa zone (`[data-scroll]`), et
 * tant qu'il reste du texte à découvrir dans le sens du geste, ce geste
 * appartient au texte. Le deck ne reprend qu'au bord — on lit jusqu'au
 * bout, puis on passe. Sans cette règle, une seule crantée de molette
 * au-dessus d'un texte long changeait d'exercice, et l'app perdait la
 * question qu'on était en train de lire.
 */

const DRAG_LIMIT = 70
const DRAG_FACTOR = 0.45
const DRAG_THRESHOLD = 48
const WHEEL_COOLDOWN = 700
const WHEEL_MIN_DELTA = 24
/** `scrollTop` est fractionnaire dès qu'on zoome : le bord a une marge. */
const EDGE = 1

interface Options {
  active: boolean
  onNext: () => void
  onPrev: () => void
  onDrag: (dy: number) => void
}

/**
 * La zone de lecture sous le pointeur — et seulement si elle a
 * réellement de quoi défiler. Un texte court n'en est pas une : le
 * geste doit alors filer au deck sans détour.
 */
function scrollZone(target: EventTarget | null): HTMLElement | null {
  let el: Element | null = target instanceof Element ? target : null
  while (el) {
    if (
      el instanceof HTMLElement &&
      el.dataset.scroll !== undefined &&
      el.scrollHeight > el.clientHeight + EDGE
    ) {
      return el
    }
    el = el.parentElement
  }
  return null
}

/**
 * Le bord est-il atteint dans le sens du geste ? `dy` suit le doigt :
 * négatif, il monte — on demande la suite, et c'est le bas du texte
 * qu'il faut avoir atteint.
 */
function atEdge(zone: HTMLElement, dy: number): boolean {
  return dy < 0
    ? zone.scrollTop + zone.clientHeight >= zone.scrollHeight - EDGE
    : zone.scrollTop <= EDGE
}

export function useDeckGestures({ active, onNext, onPrev, onDrag }: Options) {
  const start = useRef(0)
  const dragging = useRef(false)
  const wheelAt = useRef(0)
  const zone = useRef<HTMLElement | null>(null)
  /**
   * Ce que la lecture a déjà absorbé du geste, en pixels signés. Le
   * reste seul fait bouger la carte : c'est ce qui permet à un même
   * mouvement continu de défiler le texte puis, une fois le bas atteint,
   * de devenir un swipe — sans relever le doigt.
   */
  const eaten = useRef(0)

  const onPointerDown = useCallback((e: ReactPointerEvent) => {
    start.current = e.clientY
    eaten.current = 0
    zone.current = scrollZone(e.target)
    dragging.current = true
  }, [])

  const onPointerMove = useCallback(
    (e: ReactPointerEvent) => {
      if (!dragging.current) return
      const raw = e.clientY - start.current

      const z = zone.current
      if (z) {
        // Ce qui n'a pas encore servi part dans le texte ; la zone n'en
        // prend que ce qu'elle peut, et rend le reste au deck. Relire
        // `scrollTop` après l'avoir posé est le seul moyen fiable de
        // savoir combien elle a pris : le navigateur borne pour nous.
        const before = z.scrollTop
        z.scrollTop = before - (raw - eaten.current)
        eaten.current += before - z.scrollTop
      }

      const dy = (raw - eaten.current) * DRAG_FACTOR
      onDrag(Math.max(-DRAG_LIMIT, Math.min(DRAG_LIMIT, dy)))
    },
    [onDrag],
  )

  const onPointerUp = useCallback(
    (e: ReactPointerEvent) => {
      if (!dragging.current) return
      dragging.current = false
      const dy = e.clientY - start.current - eaten.current
      onDrag(0)
      if (dy < -DRAG_THRESHOLD) onNext()
      else if (dy > DRAG_THRESHOLD) onPrev()
    },
    [onDrag, onNext, onPrev],
  )

  /**
   * Un geste annulé n'est pas un geste fini : le système l'a repris —
   * appel entrant, retour arrière au bord de l'écran. On repose la
   * carte sans changer d'exercice.
   */
  const onPointerCancel = useCallback(() => {
    if (!dragging.current) return
    dragging.current = false
    onDrag(0)
  }, [onDrag])

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
      // `deltaY` positif descend dans le texte, donc vers le bas : c'est
      // l'inverse du doigt, d'où le signe rendu à `atEdge`. Tant que le
      // texte a de quoi défiler dans ce sens, on laisse le navigateur le
      // faire et on ne change pas de carte.
      const z = scrollZone(e.target)
      if (z && !atEdge(z, -e.deltaY)) return

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

  return {
    onPointerDown,
    onPointerMove,
    onPointerUp,
    onPointerLeave: onPointerUp,
    onPointerCancel,
  }
}
