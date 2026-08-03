import { useState } from 'react'
import { Icon } from '../components/Icon'
import { NavHead } from '../components/ui'
import type { Lang } from '../i18n'
import { useStore } from '../state/store'

/**
 * Inscription et connexion sur le même écran — l'app reste jouable sans
 * compte.
 *
 * En desktop, la maquette pose deux colonnes : la promesse à gauche,
 * en gros, et le formulaire dans une carte posée à droite. On demande
 * un email au moment où l'on explique pourquoi ; les deux se lisent
 * ensemble plutôt que l'un après l'autre.
 *
 * En téléphone, tout retombe dans la colonne : même contenu, même
 * ordre, sans la carte.
 */
export function Auth() {
  const { s, set, go, submitAuth, t } = useStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  // Le compte naît avec la langue de l'appareil ; l'inscription est le
  // moment de la confirmer, puisqu'elle fixe le catalogue servi.
  const [lang, setLangChoice] = useState<Lang>(s.lang)

  const signup = s.authMode === 'signup'
  const canSubmit = email.includes('@') && password.length >= 8 && !busy

  const submit = async () => {
    if (!canSubmit) return
    setBusy(true)
    const ok = await submitAuth(email.trim(), password, lang)
    setBusy(false)
    if (ok) go('settings')
  }

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('settings')} title={signup ? t.createAccount : t.signIn} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner auth-split">
          <div className="auth-pitch">
            <h1 className="auth-head">{signup ? t.keepProgress : t.welcomeBack}</h1>
            <p className="auth-line">{signup ? t.keepProgressLine : t.welcomeBackLine}</p>

            <span className="auth-keep">
              <Icon
                name="check"
                size={19}
                stroke={2.2}
                color="var(--success-500)"
                style={{ flex: 'none', marginTop: 2 }}
              />
              <span>{signup ? t.mergeSignup : t.mergeLogin}</span>
            </span>
          </div>

          <div className="auth-card">
            <span className="auth-title">{signup ? t.createAccount : t.signIn}</span>

            <label className="field">
              <span className="eyebrow">{t.email}</span>
              <input
                className="input"
                type="email"
                placeholder="toi@exemple.fr"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>

            <label className="field">
              <span className="eyebrow">{t.password}</span>
              <input
                className="input"
                type="password"
                placeholder={signup ? t.passwordHint : '••••••••'}
                autoComplete={signup ? 'new-password' : 'current-password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && void submit()}
              />
            </label>

            {/* Seulement à l'inscription : à la connexion, c'est la langue
                enregistrée sur le compte qui fait foi, pas celle de l'appareil. */}
            {signup && (
              <div className="field">
                <span className="eyebrow">{t.signupLang}</span>
                <div className="segmented" style={{ margin: 0 }}>
                  <button
                    className={lang === 'fr' ? 'segment is-on' : 'segment'}
                    onClick={() => setLangChoice('fr')}
                    aria-pressed={lang === 'fr'}
                  >
                    Français
                  </button>
                  <button
                    className={lang === 'en' ? 'segment is-on' : 'segment'}
                    onClick={() => setLangChoice('en')}
                    aria-pressed={lang === 'en'}
                  >
                    English
                  </button>
                </div>
              </div>
            )}

            {/* L'erreur dit ce qui s'est passé et comment le régler — pas d'excuse, pas de vague. */}
            {s.authError && (
              <div className="auth-error">
                <Icon
                  name="alert"
                  size={18}
                  stroke={1.9}
                  color="var(--sc-miss-line)"
                  style={{ flex: 'none', marginTop: 2 }}
                />
                <span>{s.authError}</span>
              </div>
            )}

            <button
              className="btn-primary auth-cta"
              onClick={() => void submit()}
              disabled={!canSubmit}
              style={{ opacity: canSubmit ? 1 : 0.5 }}
            >
              {busy ? t.oneMoment : signup ? t.createMyAccount : t.signIn}
            </button>

            <div className="auth-foot">
              <button
                className="btn-link"
                style={{ padding: 0 }}
                onClick={() => set({ authMode: signup ? 'login' : 'signup', authError: null })}
              >
                {signup ? t.haveAccount : t.noAccount}
              </button>
              <button
                className="btn-quiet"
                style={{ padding: 0, fontSize: 14 }}
                onClick={() => go('exo', 'q')}
              >
                {t.continueWithout}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
