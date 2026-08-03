import { Icon } from '../components/Icon'
import { NavHead, Toggle } from '../components/ui'
import { Wordmark } from '../components/Wordmark'
import { useStore } from '../state/store'

/**
 * Réglages.
 *
 * En mobile, la liste verticale d'origine : une section après l'autre,
 * sous une barre de retour.
 *
 * En desktop, les mêmes sections deviennent des cartes posées sur deux
 * colonnes, sous un vrai titre de page. Rien n'est ajouté ni retiré —
 * c'est la même matière, à qui on rend la largeur de l'écran. Le compte
 * traverse toute la grille : c'est la décision la moins fréquente et la
 * plus conséquente de la page, elle ne doit pas se perdre dans un coin.
 */
export function Settings() {
  const { s, go, set, toggleDark, toggleMute, setLang, themes, user, logout, t } = useStore()

  const mine = themes.filter((x) => x.subscribed)
  const signedIn = user !== null && !user.is_anonymous

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('exo', 'q')} title={t.settings} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner">
          <header className="page-head">
            <h1 className="page-title">{t.settings}</h1>
            <p className="page-lead">{t.settingsLead}</p>
          </header>

          <div className="page-grid">
            {/* Le choix des thèmes a son propre écran : c'est ce qu'on vient
                faire dans l'app, pas une option à régler. Il reste joignable
                d'ici, mais il ne se règle plus ici. */}
            <section className="page-card">
              <span className="eyebrow">{t.themes}</span>
              <button className="settings-row" onClick={() => go('themes')}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Icon name="sparkle" size={20} color="var(--sc-text)" />
                  <span className="stack">
                    <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--sc-text)' }}>
                      {t.myThemes}
                    </span>
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                      {mine.length > 0 ? t.themesCount(mine.length) : t.noThemeFollowed}
                    </span>
                  </span>
                </span>
                <Icon name="chevronRight" size={18} stroke={2} color="var(--sc-text3)" />
              </button>
            </section>

            <section className="page-card">
              <span className="eyebrow">{t.about}</span>
              <button className="settings-row" onClick={() => go('about')}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Icon name="bulb" size={20} color="var(--sc-text)" />
                  <span className="stack">
                    <Wordmark size={17} />
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>{t.slogan}</span>
                  </span>
                </span>
                <Icon name="chevronRight" size={18} stroke={2} color="var(--sc-text3)" />
              </button>
            </section>

            <section className="page-card">
              <span className="eyebrow">{t.audio}</span>
              <button className="settings-row" onClick={toggleMute} aria-pressed={!s.muted}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Icon name="volume" size={20} color="var(--sc-text)" />
                  <span className="stack">
                    <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--sc-text)' }}>
                      {t.feedbackSounds}
                    </span>
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                      {t.feedbackSoundsSub}
                    </span>
                  </span>
                </span>
                <Toggle on={!s.muted} />
              </button>

              <button className="settings-row" onClick={toggleDark} aria-pressed={s.dark}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Icon name="moon" size={20} color="var(--sc-text)" />
                  <span className="stack">
                    <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--sc-text)' }}>
                      {t.darkMode}
                    </span>
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                      {s.dark ? t.darkOn : t.darkOff}
                    </span>
                  </span>
                </span>
                <Toggle on={s.dark} />
              </button>
            </section>

            {/* Changer de langue change aussi le catalogue servi : un thème
                est écrit dans une langue, il n'est jamais traduit. */}
            <section className="page-card">
              <span className="eyebrow">{t.language}</span>
              <div className="segmented" style={{ margin: 0 }}>
                <button
                  className={s.lang === 'fr' ? 'segment is-on' : 'segment'}
                  onClick={() => setLang('fr')}
                  aria-pressed={s.lang === 'fr'}
                >
                  Français
                </button>
                <button
                  className={s.lang === 'en' ? 'segment is-on' : 'segment'}
                  onClick={() => setLang('en')}
                  aria-pressed={s.lang === 'en'}
                >
                  English
                </button>
              </div>
              <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>{t.languageSub}</span>
            </section>

            <section className="page-card span-all">
              <span className="eyebrow">{t.account}</span>
              <div className="card">
                {signedIn && user ? (
                  <>
                    <p
                      style={{
                        margin: 0,
                        fontSize: 15,
                        lineHeight: 1.6,
                        color: 'var(--sc-text2)',
                      }}
                    >
                      {t.signedInAs} <strong>{user.email}</strong>. {t.signedInSub}
                    </p>
                    {/* Sans cette sortie, un compte créé sur un appareil
                        partagé y restait ouvert définitivement. */}
                    <div className="account-actions">
                      <button
                        className="btn-outline"
                        style={{ minHeight: 44 }}
                        onClick={() => void logout()}
                      >
                        {t.signOut}
                      </button>
                    </div>
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>{t.signOutSub}</span>
                  </>
                ) : (
                  <>
                    <p
                      style={{
                        margin: 0,
                        fontSize: 15,
                        lineHeight: 1.6,
                        color: 'var(--sc-text2)',
                      }}
                    >
                      {t.playingAnonymously}
                    </p>
                    <div className="account-actions">
                      <button
                        className="btn-primary"
                        style={{ minHeight: 48, fontSize: 15 }}
                        onClick={() =>
                          set({ screen: 'auth', authMode: 'signup', sheet: null, authError: null })
                        }
                      >
                        {t.createAccount}
                      </button>
                      <button
                        className="btn-outline"
                        style={{ minHeight: 44 }}
                        onClick={() =>
                          set({ screen: 'auth', authMode: 'login', sheet: null, authError: null })
                        }
                      >
                        {t.signIn}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
