import { useStore } from '../state/store'

/**
 * La bascule de langue, en clair et partout.
 *
 * Elle vivait au fond des réglages, ce que la planche montre bien —
 * mais un visiteur anglophone qui tombe sur un catalogue français n'ira
 * pas chercher un réglage dans une langue qu'il ne lit pas. Elle
 * remonte donc dans le cadre de l'app : rail à gauche en desktop, barre
 * du haut en téléphone. Les réglages gardent la leur, plus explicite.
 *
 * Deux pastilles plutôt qu'un interrupteur qui n'afficherait que la
 * langue cible : avec deux langues, montrer l'état ET l'action dans le
 * même bouton oblige à deviner lequel des deux mots est le sien.
 *
 * `setLang` ne change pas que des libellés : un apprentissage est écrit
 * dans une langue et n'est jamais traduit, donc le catalogue servi
 * change aussi. C'est le sens du sous-titre dans les réglages.
 */
export function LangSwitch({ compact = false }: { compact?: boolean }) {
  const { s, setLang, t } = useStore()

  const LANGS = [
    { code: 'fr', court: 'FR', long: 'Français' },
    { code: 'en', court: 'EN', long: 'English' },
  ] as const

  return (
    <div className="lang-switch" role="group" aria-label={t.language}>
      {LANGS.map(({ code, court, long }) => (
        <button
          key={code}
          className={s.lang === code ? 'lang-pill is-on' : 'lang-pill'}
          onClick={() => setLang(code)}
          aria-pressed={s.lang === code}
          aria-label={long}
          title={long}
          lang={code}
        >
          {compact ? court : long}
        </button>
      ))}
    </div>
  )
}
