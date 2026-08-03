import { useEffect, useRef, useState } from 'react'
import type { Dict } from '../i18n'
import { type Screen, routeOf, useStore } from '../state/store'
import { Icon } from './Icon'
import { Wordmark } from './Wordmark'

/**
 * Barre du haut, sur téléphone.
 *
 * Le desktop a ses quatre liens en clair dans la barre ; sur téléphone
 * la place manque, et l'app n'affichait alors ni sa marque ni aucun
 * moyen d'atteindre le classement ou « à propos » sans passer par les
 * réglages. Trois points suffisent, à condition que ce qu'ils cachent
 * soit court : quatre destinations et l'état du compte, rien de plus.
 *
 * La barre se pose dans la bande que chaque écran réserve déjà en haut
 * (`.nav-head`, `.exo-head`) : elle ne décale aucun contenu.
 */
const LINKS: { screen: Screen; label: (t: Dict) => string }[] = [
  { screen: 'themes', label: (t) => t.myThemes },
  { screen: 'rank', label: (t) => t.ranking },
  { screen: 'settings', label: (t) => t.settings },
  { screen: 'about', label: (t) => t.about },
]

export function MobileBar() {
  const { s, go, set, user, t } = useStore()
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  // Un menu qui ne se ferme pas au clic à côté est un piège : sur
  // téléphone il n'y a pas d'Échap sous la main.
  useEffect(() => {
    if (!open) return
    const away = (e: PointerEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('pointerdown', away)
    window.addEventListener('keydown', esc)
    return () => {
      window.removeEventListener('pointerdown', away)
      window.removeEventListener('keydown', esc)
    }
  }, [open])

  const signedIn = user !== null && !user.is_anonymous

  return (
    <div className="mobile-bar" ref={box}>
      <a
        className="mobile-bar-mark"
        href={routeOf('exo')}
        onClick={(e) => {
          e.preventDefault()
          go('exo', 'q')
        }}
      >
        <Wordmark size={20} />
      </a>

      <button
        className="mobile-bar-btn"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t.menu}
      >
        <Icon name="dots" size={20} />
      </button>

      {open && (
        <div className="mobile-menu" role="menu">
          {LINKS.map(({ screen, label }) => (
            <a
              key={screen}
              role="menuitem"
              className={s.screen === screen ? 'mobile-menu-item is-on' : 'mobile-menu-item'}
              href={routeOf(screen)}
              onClick={(e) => {
                e.preventDefault()
                setOpen(false)
                go(screen)
              }}
            >
              {label(t)}
            </a>
          ))}

          <hr className="mobile-menu-rule" />

          {signedIn && user ? (
            <span className="mobile-menu-account">
              <Icon name="user" size={15} color="var(--sc-text3)" />
              {user.display_name || user.email}
            </span>
          ) : (
            <a
              role="menuitem"
              className="mobile-menu-item"
              href={routeOf('auth')}
              onClick={(e) => {
                e.preventDefault()
                setOpen(false)
                set({ screen: 'auth', authMode: 'login', sheet: null, authError: null })
              }}
            >
              {t.signIn}
            </a>
          )}
        </div>
      )}
    </div>
  )
}
