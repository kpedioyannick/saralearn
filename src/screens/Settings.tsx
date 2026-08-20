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
  const { s, go, set, toggleDark, toggleMute, setLang, user, logout, t } = useStore()

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
            {/* La langue ouvre la page, à la place des apprentissages, qui
                se joignent par le rail et le menu — ils n'ont jamais été
                un réglage. Elle vient en premier parce qu'elle décide de
                tout ce qu'on lira ensuite : un thème est écrit dans une
                langue et n'est jamais traduit, changer de langue change
                donc le catalogue servi, pas seulement les libellés. */}
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

              {/* La page publique reste accessible depuis l'intérieur :
                  c'est elle qu'on envoie à quelqu'un pour lui expliquer
                  l'app, et sans cette entrée il fallait connaître l'URL. */}
              <button className="settings-row" onClick={() => go('home')}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Icon name="home" size={20} color="var(--sc-text)" />
                  <span className="stack">
                    <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--sc-text)' }}>
                      {t.homeHow}
                    </span>
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>{t.homeKicker}</span>
                  </span>
                </span>
                <Icon name="chevronRight" size={18} stroke={2} color="var(--sc-text3)" />
              </button>

              {/* Nous écrire vit ici et non dans un pied de page : c'est
                  d'ici qu'on part quand quelque chose ne va pas. */}
              <button className="settings-row" onClick={() => go('contact')}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Icon name="mail" size={20} color="var(--sc-text)" />
                  <span className="stack">
                    <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--sc-text)' }}>
                      {t.writeToUs}
                    </span>
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>{t.replyDelay}</span>
                  </span>
                </span>
                <Icon name="chevronRight" size={18} stroke={2} color="var(--sc-text3)" />
              </button>
            </section>

            <section className="page-card span-all">
              <span className="eyebrow">{t.account}</span>

              {/* Le pseudo passe avant le compte : il vaut pour tout le
                  monde, connecté ou non, alors que le bloc du dessous ne
                  concerne que ceux qui ont un email. */}
              <button className="settings-row" onClick={() => go('pseudo')}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <Icon name="user" size={20} color="var(--sc-text)" />
                  <span className="stack">
                    <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--sc-text)' }}>
                      {t.pseudoLabel}
                    </span>
                    <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
                      {user?.display_name || t.pseudoNone}
                    </span>
                  </span>
                </span>
                <Icon name="chevronRight" size={18} stroke={2} color="var(--sc-text3)" />
              </button>

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
