import { useEffect, useRef, useState } from 'react'
import type { Dict } from '../i18n'
import { type Screen, routeOf, useStore } from '../state/store'
import { Icon } from './Icon'
import { LangSwitch } from './LangSwitch'
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
 * (`.nav-head`) : elle ne décale aucun contenu.
 *
 * Le feed d'exercices fait exception depuis la planche 4c : sa bande du
 * haut est prise par le bandeau de lecture, et c'est `.exo-bar` — la
 * ligne de l'orbe, que la pastille et les boutons partagent — qui porte
 * les trois points, à droite du « + ». Voir `MoreMenu`, qui sert les
 * deux.
 */
const LINKS: { screen: Screen; label: (t: Dict) => string }[] = [
  { screen: 'themes', label: (t) => t.myLearnings },
  { screen: 'shared', label: (t) => t.whatIShare },
  { screen: 'rank', label: (t) => t.ranking },
  { screen: 'settings', label: (t) => t.settings },
  { screen: 'about', label: (t) => t.about },
]

/**
 * Les trois points et ce qu'ils cachent.
 *
 * `withLang` ajoute la bascule de langue dans le menu. Elle est en clair
 * dans la barre du haut — quelqu'un qui ne lit pas le français ne
 * devinera pas que « ⋮ » cache sa langue — mais le feed n'a plus de
 * barre où la poser, et le menu vaut mieux que rien.
 */
export function MoreMenu({ withLang = false }: { withLang?: boolean }) {
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
    <div className="more-menu" ref={box}>
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

          {withLang && (
            <div className="mobile-menu-lang">
              <LangSwitch compact />
            </div>
          )}

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

export function MobileBar() {
  const { go } = useStore()

  return (
    <div className="mobile-bar">
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

      {/* En clair dans la barre, pas dans le menu : quelqu'un qui ne lit
          pas le français ne devinera pas que « ⋮ » cache sa langue. */}
      <LangSwitch compact />

      <MoreMenu />
    </div>
  )
}
