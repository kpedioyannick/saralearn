import { useState } from 'react'
import { Icon } from '../components/Icon'
import { Meter, NavHead, PageBack } from '../components/ui'
import type { Lang } from '../i18n'
import { useIsDesktop } from '../lib/useIsDesktop'
import { useStore } from '../state/store'

/**
 * Inscription et connexion sur le même écran — l'app reste jouable sans
 * compte.
 *
 * En desktop, la maquette pose deux colonnes : le formulaire à gauche,
 * et à droite ce qu'un compte conserve — apprentissages suivis,
 * exercices réussis, progression locale. C'est l'argument de la page,
 * et il est chiffré sur les données réelles de l'appareil plutôt
 * qu'écrit en général : « 6 apprentissages suivis » convainc, « vos
 * données vous suivent » non.
 *
 * En téléphone, tout retombe dans la colonne : le formulaire d'abord,
 * ce qu'on garde ensuite.
 */
export function Auth() {
  const { s, set, go, submitAuth, themes, progression, subscribedIds, t } = useStore()
  const isDesktop = useIsDesktop()
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

  const form = (
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

      <span style={{ fontSize: 14, color: 'var(--sc-text3)' }}>{t.legalLine}</span>
    </div>
  )

  const followed = themes.filter((x) => subscribedIds.has(x.id))
  const passed = progression.reduce((n, p) => n + p.passed, 0)
  const toRedo = progression.reduce((n, p) => n + (p.total - p.passed), 0)
  const created = themes.filter((x) => x.is_owner).length
  const top = [...progression].sort((a, b) => b.pct - a.pct).slice(0, 2)
  const nothing = followed.length === 0 && passed === 0 && created === 0

  const rows: { icon: 'grid' | 'check' | 'sparkle'; title: string; line: string }[] = []
  if (followed.length > 0) {
    rows.push({
      icon: 'grid',
      title: t.keepThemes(followed.length),
      line: t.keepThemesLine(
        followed
          .slice(0, 3)
          .map((x) => x.title)
          .join(', '),
      ),
    })
  }
  if (passed > 0) {
    rows.push({ icon: 'check', title: t.keepPassed(passed), line: t.keepPassedLine(toRedo) })
  }
  if (created > 0) {
    rows.push({ icon: 'sparkle', title: t.keepCreated(created), line: t.keepCreatedLine })
  }

  const keep = (
    <aside className="stack" style={{ gap: 16 }}>
      <span className="mono">{t.whatYouKeep}</span>

      {nothing ? (
        <p className="body" style={{ fontSize: 16 }}>
          {t.nothingKeptYet}
        </p>
      ) : (
        <div className="keep-panel">
          {rows.map((r) => (
            <div key={r.title} className="keep-row">
              <span className="keep-disc">
                <Icon name={r.icon} size={18} />
              </span>
              <span className="stack" style={{ flex: 1, gap: 4 }}>
                <span style={{ fontSize: 16, fontWeight: 500, color: 'var(--sc-text)' }}>
                  {r.title}
                </span>
                <span style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--sc-text2)' }}>
                  {r.line}
                </span>
              </span>
            </div>
          ))}
        </div>
      )}

      {top.length > 0 && (
        <div className="keep-local">
          <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--sc-text)' }}>
            {t.localProgress}
          </span>
          {top.map((p) => (
            <div key={p.theme_id} className="stack" style={{ gap: 8 }}>
              <span
                style={{ display: 'flex', justifyContent: 'space-between', gap: 10, fontSize: 15 }}
              >
                <span>{p.name}</span>
                <span
                  style={{
                    flex: 'none',
                    whiteSpace: 'nowrap',
                    color: 'var(--sc-primary)',
                    fontWeight: 700,
                  }}
                >
                  {p.pct} %
                </span>
              </span>
              <Meter pct={p.pct} />
            </div>
          ))}
          <span style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--sc-text3)' }}>
            {t.localProgressWarn}
          </span>
        </div>
      )}
    </aside>
  )

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('settings')} title={signup ? t.createAccount : t.signIn} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner auth-split">
          <PageBack onClick={() => go('settings')} label={t.settings} />

          <div className="stack" style={{ gap: isDesktop ? 26 : 20 }}>
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

            {form}
          </div>

          {keep}
        </div>
      </div>
    </div>
  )
}
