import { useState } from 'react'
import { Icon } from '../components/Icon'
import { NavHead } from '../components/ui'
import { useIsDesktop } from '../lib/useIsDesktop'
import { useStore } from '../state/store'

/**
 * Nous écrire.
 *
 * En desktop, la maquette pose le formulaire à gauche et une colonne
 * d'aide à droite : ce qu'il vaut mieux faire avant d'écrire, les
 * questions fréquentes, l'adresse. Les deux se lisent ensemble — la
 * moitié des messages n'ont pas besoin d'être envoyés.
 *
 * En téléphone, tout retombe dans la colonne, et les questions
 * fréquentes passent sous le formulaire.
 *
 * L'envoi : il n'y a pas d'endpoint de contact côté API. Plutôt que
 * d'afficher une confirmation qui ne correspond à rien, on compose le
 * message dans le logiciel de messagerie de la personne — le message
 * part vraiment, et l'écran de confirmation le dit sans mentir.
 */

const MAX = 1000

type SubjectKey = 'report' | 'idea' | 'tech' | 'other'

export function Contact() {
  const { go, user, t } = useStore()
  const isDesktop = useIsDesktop()

  const [subject, setSubject] = useState<SubjectKey>('report')
  const [name, setName] = useState(user?.display_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [body, setBody] = useState('')
  const [sent, setSent] = useState(false)

  const subjects: { key: SubjectKey; label: string; short: string }[] = [
    { key: 'report', label: t.subjectReport, short: t.subjectReport },
    { key: 'idea', label: t.subjectIdea, short: t.subjectIdeaShort },
    { key: 'tech', label: t.subjectTech, short: t.subjectTechShort },
    { key: 'other', label: t.subjectOther, short: t.subjectOther },
  ]
  const chosen = subjects.find((x) => x.key === subject) ?? subjects[0]
  const canSend = body.trim().length > 4 && email.includes('@')

  const submit = () => {
    if (!canSend) return
    const lines = [body.trim(), '', `— ${name.trim() || email.trim()}`].join('\n')
    const href =
      `mailto:${t.contactAddress}` +
      `?subject=${encodeURIComponent(`[SaraLearn] ${chosen.label}`)}` +
      `&body=${encodeURIComponent(lines)}`
    window.location.href = href
    setSent(true)
  }

  const reset = () => {
    setBody('')
    setSent(false)
  }

  if (sent) return <Sent email={email} onAgain={reset} />

  const subjectPicker = (
    <div className="field">
      <span className="eyebrow">{t.subject}</span>
      <div className="wrap" style={{ gap: 8 }}>
        {subjects.map((sub) => {
          const on = sub.key === subject
          return (
            <button
              key={sub.key}
              className={on ? 'chip is-on' : 'chip'}
              aria-pressed={on}
              onClick={() => setSubject(sub.key)}
              style={{ cursor: 'pointer', minHeight: 38 }}
            >
              {isDesktop ? sub.label : sub.short}
            </button>
          )
        })}
      </div>
    </div>
  )

  const messageField = (
    <div className="field" style={{ flex: isDesktop ? 'none' : 1, minHeight: 0 }}>
      <span
        style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between' }}
      >
        <span className="eyebrow">{t.message}</span>
        <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
          {t.charCount(body.length, MAX)}
        </span>
      </span>
      <textarea
        className="textarea"
        rows={isDesktop ? 5 : 6}
        style={{ flex: isDesktop ? 'none' : 1 }}
        maxLength={MAX}
        placeholder={t.messagePlaceholder}
        value={body}
        onChange={(e) => setBody(e.target.value)}
      />
    </div>
  )

  /* La pièce jointe n'existe pas tant que l'envoi passe par le
     logiciel de messagerie : on dit où la déposer plutôt que d'ouvrir
     un sélecteur de fichier dont on ne ferait rien. */
  const attachNote = (
    <div className="contact-attach">
      <Icon name="upload" size={18} stroke={1.9} color="var(--sc-text3)" />
      <span style={{ flex: 1 }}>{isDesktop ? t.attach : t.attachShort}</span>
      {isDesktop && (
        <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>{t.attachHint}</span>
      )}
    </div>
  )

  if (isDesktop) {
    return (
      <div className="screen">
        <div className="screen-scroll page">
          <div className="page-inner">
            <header className="page-head">
              <span className="eyebrow" style={{ color: 'var(--sc-primary)' }}>
                {t.contact}
              </span>
              <h1 className="page-title">{t.contactHead}</h1>
              <p className="page-lead">{t.contactLead}</p>
            </header>

            <div className="contact-split">
              <div className="stack" style={{ gap: 18 }}>
                {subjectPicker}

                <div className="grid-2">
                  <label className="field">
                    <span className="eyebrow">{t.yourName}</span>
                    <input
                      className="input"
                      autoComplete="name"
                      placeholder={t.namePlaceholder}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span className="eyebrow">{t.email}</span>
                    <input
                      className="input"
                      type="email"
                      autoComplete="email"
                      placeholder="vous@exemple.fr"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </label>
                </div>

                {messageField}
                {attachNote}

                <div className="stack" style={{ gap: 8 }}>
                  <button
                    className="btn-primary"
                    style={{
                      width: 'auto',
                      alignSelf: 'flex-start',
                      padding: '0 26px',
                      opacity: canSend ? 1 : 0.5,
                    }}
                    disabled={!canSend}
                    onClick={submit}
                  >
                    {t.sendMessage}
                  </button>
                  <span style={{ fontSize: 14, color: 'var(--sc-text3)' }}>
                    {t.contactPrivacy}
                  </span>
                </div>
              </div>

              <Aside />
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="screen">
      <NavHead onBack={() => go('settings')} title={t.writeToUs} />

      <div className="screen-scroll page">
        <div className="page-inner stack" style={{ gap: 16 }}>
          <p className="body" style={{ fontSize: 16 }}>
            {t.contactLeadShort}
          </p>

          {subjectPicker}

          <label className="field">
            <span className="eyebrow">{t.email}</span>
            <input
              className="input"
              type="email"
              autoComplete="email"
              placeholder="vous@exemple.fr"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>

          {messageField}
          {attachNote}
          <Aside />
        </div>
      </div>

      <div className="footer-bar">
        <button
          className="btn-primary"
          style={{ opacity: canSend ? 1 : 0.5 }}
          disabled={!canSend}
          onClick={submit}
        >
          {t.send}
        </button>
        <span style={{ textAlign: 'center', fontSize: 14, color: 'var(--sc-text3)' }}>
          {t.contactAddress}
        </span>
      </div>
    </div>
  )
}

/** La colonne d'aide : ce qui évite d'écrire, puis comment nous joindre. */
function Aside() {
  const { t } = useStore()
  const [open, setOpen] = useState<number | null>(null)

  const faq = [
    [t.faqQ1, t.faqA1],
    [t.faqQ2, t.faqA2],
    [t.faqQ3, t.faqA3],
    [t.faqQ4, t.faqA4],
  ]

  return (
    <aside className="stack" style={{ gap: 14 }}>
      <div className="contact-note">
        <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--sc-text)' }}>
          {t.beforeWriting}
        </span>
        <span style={{ fontSize: 15, lineHeight: 1.55, color: 'var(--sc-text2)' }}>
          {t.beforeWritingLine}
        </span>
      </div>

      <span className="mono">{t.faqTitle}</span>
      {faq.map(([q, a], i) => {
        const on = open === i
        return (
          <div key={q} className="faq-item">
            <button
              className="faq-q"
              aria-expanded={on}
              onClick={() => setOpen(on ? null : i)}
            >
              <span style={{ flex: 1, textAlign: 'left' }}>{q}</span>
              <Icon name={on ? 'minus' : 'plus'} size={16} stroke={2.2} color="var(--sc-text3)" />
            </button>
            {on && <p className="faq-a">{a}</p>}
          </div>
        )
      })}

      <div className="card" style={{ gap: 6 }}>
        <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--sc-text)' }}>{t.byEmail}</span>
        <a href={`mailto:${t.contactAddress}`} className="btn-link" style={{ padding: 0 }}>
          {t.contactAddress}
        </a>
        <span style={{ fontSize: 14, color: 'var(--sc-text3)' }}>{t.replyDelay}</span>
      </div>
    </aside>
  )
}

/** L'accusé de réception : ce qui vient de partir, et où l'on retourne. */
function Sent({ email, onAgain }: { email: string; onAgain: () => void }) {
  const { go, t } = useStore()

  return (
    <div className="screen">
      <NavHead title={t.messageSent} />
      <div className="screen-scroll page">
        <div className="page-inner is-narrow stack contact-sent">
          <span className="contact-sent-disc anim-pop">
            <Icon name="check" size={38} stroke={2.4} color="var(--sc-primary)" />
          </span>
          <p className="display" style={{ fontSize: 30 }}>
            {t.sentHead}
          </p>
          <p className="body" style={{ fontSize: 17, maxWidth: '30ch' }}>
            {t.sentLine(email || t.contactAddress)}
          </p>
          <p style={{ fontSize: 14, lineHeight: 1.55, color: 'var(--sc-text3)', maxWidth: '34ch' }}>
            {t.sentMailNote}
          </p>
        </div>
      </div>
      <div className="footer-bar">
        <button className="btn-primary" onClick={() => go('exo', 'q')}>
          {t.backToExercises}
        </button>
        <button className="btn-outline" onClick={onAgain}>
          {t.writeAnother}
        </button>
      </div>
    </div>
  )
}
