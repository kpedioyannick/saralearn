import { useState } from 'react'
import { Icon } from '../components/Icon'
import { NavHead } from '../components/ui'
import { useStore } from '../state/store'

/**
 * Le pseudo, exigé avant le premier exercice.
 *
 * Ce n'est PAS une connexion. La session est déjà authentifiée quand
 * cet écran s'affiche — `device_id` et le jeton en localStorage — et le
 * pseudo n'ouvre rien : il ne sert qu'à mettre un nom là où l'app en
 * affiche un, le classement et les commentaires. Deux personnes peuvent
 * porter le même, et c'est voulu : l'unicité sur une étiquette que rien
 * ne protège crée une course au nom et laisse croire à une identité
 * qu'elle ne garantit pas.
 *
 * Il n'est plus sautable. Un exercice compte — classement, commentaires,
 * progression — et tout cela s'affiche sous un nom. La sortie n'est donc
 * pas « passer » mais l'autre façon de se nommer : créer un compte. Deux
 * portes, pas une porte et une dérobade. La règle elle-même est dans le
 * store, sur l'écran `exo` : voir la garde `named || registered`.
 *
 * Le squelette est celui de l'écran de connexion : `auth-split`, la
 * promesse à gauche, la carte à droite. Les deux écrans posent la même
 * question — comment vous reconnaît-on — à deux niveaux d'engagement,
 * et se ressembler dit ça mieux qu'un texte.
 */
export function Pseudo() {
  const { s, set, setPseudo, enterFeed, t } = useStore()
  const [name, setName] = useState(s.pseudo)

  const clean = name.trim().replace(/\s+/g, ' ')
  // Deux mesures, pas une : le champ vide n'est pas une erreur — on
  // vient d'arriver — mais il ne laisse pas entrer non plus.
  const tooShort = clean.length > 0 && clean.length < 2
  const ready = clean.length >= 2

  const submit = () => {
    if (!ready) return
    setPseudo(clean)
    enterFeed()
  }

  return (
    <div className="screen">
      {/* Pas de flèche de retour : elle ne mènerait qu'au flux, qui
          renvoie ici tant qu'on n'a ni pseudo ni compte. Un bouton qui
          ne fait rien est pire que pas de bouton. */}
      <div className="desk-hide">
        <NavHead title={t.pseudoLabel} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner auth-split">
          <div className="stack" style={{ gap: 20 }}>
            <div className="auth-pitch">
              <h1 className="auth-head">{t.pseudoTitle}</h1>
              <p className="auth-line">{t.pseudoLead}</p>

              <span className="auth-keep">
                <Icon
                  name="check"
                  size={19}
                  stroke={2.2}
                  color="var(--success-500)"
                  style={{ flex: 'none', marginTop: 2 }}
                />
                <span>{t.pseudoNoPassword}</span>
              </span>
            </div>

            <div className="auth-card">
              <span className="auth-title">{t.pseudoCardTitle}</span>

              <label className="field">
                <span className="eyebrow">{t.pseudoLabel}</span>
                <input
                  className="input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && submit()}
                  placeholder={t.pseudoPlaceholder}
                  autoComplete="nickname"
                  maxLength={24}
                  autoFocus
                />
              </label>

              {tooShort && (
                <div className="auth-error">
                  <Icon
                    name="alert"
                    size={18}
                    stroke={1.9}
                    color="var(--sc-miss-line)"
                    style={{ flex: 'none', marginTop: 2 }}
                  />
                  <span>{t.pseudoTooShort}</span>
                </div>
              )}

              <button
                className="btn-primary auth-cta"
                onClick={submit}
                disabled={!ready}
                style={{ opacity: ready ? 1 : 0.5 }}
              >
                {t.letsGo}
              </button>

              {/* L'autre façon de se nommer. Elle remplace « passer » :
                  il n'y a plus de troisième porte, mais il y en a bien
                  deux, et celle-ci garde la progression d'un appareil à
                  l'autre. */}
              <div className="auth-foot">
                <button
                  className="btn-quiet"
                  style={{ padding: 0, fontSize: 14 }}
                  onClick={() =>
                    set({ screen: 'auth', authMode: 'signup', sheet: null, authError: null })
                  }
                >
                  {t.createAccount}
                </button>
              </div>
            </div>
          </div>

          {/* La colonne de droite de l'écran de connexion montre ce qu'on
              garde en créant un compte. Ici elle montre où le pseudo
              s'affiche : ce sont les deux seuls endroits, et les nommer
              vaut mieux que promettre une « personnalisation ». */}
          <aside className="stack" style={{ gap: 16 }}>
            <span className="mono">{t.pseudoWhereTitle}</span>

            <div className="keep-panel">
              {[
                { icon: 'trophy' as const, title: t.ranking, line: t.pseudoWhereRank },
                { icon: 'message' as const, title: t.comments, line: t.pseudoWhereComments },
              ].map((r) => (
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

            <span style={{ fontSize: 14, lineHeight: 1.5, color: 'var(--sc-text3)' }}>
              {t.pseudoLocal}
            </span>
          </aside>
        </div>
      </div>
    </div>
  )
}
