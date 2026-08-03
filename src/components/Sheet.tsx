import { useState } from 'react'
import { useIsDesktop } from '../lib/useIsDesktop'
import { useStore } from '../state/store'
import { Icon } from './Icon'
import { Avatar, Dot, Meter } from './ui'

/**
 * Feuille du bas sur mobile, panneau latéral de 440 px sur desktop —
 * même contenu, même état.
 */
export function Sheet() {
  const { s, exo, set, go, themes, progression, comments, toggleSubscribe, sendComment, t } =
    useStore()
  const isDesktop = useIsDesktop()
  const [draft, setDraft] = useState('')

  if (!s.sheet || !exo) return null

  const close = () => set({ sheet: null })
  const theme = themes.find((x) => x.id === exo.themeId)
  const subscribed = theme?.subscribed ?? false
  const progress = progression.find((p) => p.theme_id === exo.themeId)

  const submit = () => {
    sendComment(draft)
    setDraft('')
  }

  const themePanel = (
    <div className="stack panel-body" style={{ gap: 16 }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <Dot color={exo.color} size={12} />
        <span className="display" style={{ fontSize: isDesktop ? 34 : 28 }}>
          {exo.theme}
        </span>
      </span>
      <p className="body" style={{ fontSize: 16, lineHeight: 1.65 }}>
        {t.themeBlurb(exo.theme)}
      </p>

      <div style={{ display: 'flex', gap: 10 }}>
        <Stat value={String(theme?.exercise_count ?? 0)} label={t.exercises} />
        <Stat value={String(theme?.subscriber_count ?? 0)} label={t.subscribers} />
      </div>

      {progress && (
        <div className="card-sunk stack" style={{ gap: 9 }}>
          <span className="eyebrow">{t.yourProgressHere}</span>
          <span
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}
          >
            <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--sc-text)' }}>
              {progress.passed}/{progress.total} {t.passed}
            </span>
            <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--gold-700)' }}>
              {progress.pct} %
            </span>
          </span>
          <Meter
            pct={progress.pct}
            fill={progress.pct >= 80 ? 'var(--gold-500)' : 'var(--sc-primary)'}
          />
        </div>
      )}

      <div className="stack" style={{ gap: 10, marginTop: isDesktop ? 'auto' : 0 }}>
        <button
          className="btn-primary"
          onClick={() => toggleSubscribe(exo.themeId)}
          style={{
            background: subscribed ? 'var(--sc-sunk)' : 'var(--sc-primary)',
            color: subscribed ? 'var(--sc-text2)' : 'var(--sc-on-primary)',
          }}
        >
          {subscribed ? t.subscribed : t.subscribe}
        </button>
        <button className="btn-link" onClick={() => go('rankOne')}>
          {t.seeThemeRanking}
        </button>
      </div>
    </div>
  )

  const commentsPanel = (
    <div className="stack" style={{ gap: 14, minHeight: 0, flex: 1 }}>
      {!isDesktop && (
        <span style={{ fontSize: 17, fontWeight: 700, color: 'var(--sc-text)' }}>
          {comments.length} {t.comments.toLowerCase()}
        </span>
      )}
      <div className="stack panel-body" style={{ gap: isDesktop ? 18 : 14 }}>
        {comments.length === 0 && (
          <p className="serif-italic" style={{ fontSize: 16 }}>
            {t.noComments}
          </p>
        )}
        {comments.map((c) => (
          <div key={c.id} style={{ display: 'flex', gap: 12 }}>
            <Avatar name={c.author} color="var(--sc-primary)" size={isDesktop ? 38 : 34} />
            <span className="stack" style={{ gap: 3 }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--sc-text)' }}>
                {c.author}
              </span>
              <span style={{ fontSize: 15, lineHeight: 1.55, color: 'var(--sc-text2)' }}>
                {c.body}
              </span>
            </span>
          </div>
        ))}
      </div>
      <div className="comment-bar">
        <input
          className="comment-input"
          placeholder={t.addComment}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
        />
        <button className="comment-send" onClick={submit} aria-label={t.send}>
          <Icon name="send" size={19} stroke={2} />
        </button>
      </div>
    </div>
  )

  const body = s.sheet === 'theme' ? themePanel : commentsPanel
  const title = s.sheet === 'comments' ? `${comments.length} ${t.comments.toLowerCase()}` : t.themes

  if (isDesktop) {
    return (
      <div className="scrim scrim-desktop" onClick={close} role="presentation">
        <div
          className="panel"
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-label={title}
        >
          <div className="panel-head">
            <span style={{ fontSize: 17, fontWeight: 700, color: 'var(--sc-text)' }}>
              {title}
            </span>
            <button className="panel-close" onClick={close} aria-label={t.close}>
              <Icon name="close" size={18} stroke={2} />
            </button>
          </div>
          {body}
        </div>
      </div>
    )
  }

  return (
    <div className="scrim" onClick={close} role="presentation">
      <div
        className="sheet"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <span className="sheet-grip" />
        {body}
      </div>
    </div>
  )
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <span
      className="stack"
      style={{
        flex: 1,
        padding: '12px 14px',
        borderRadius: 12,
        background: 'var(--sc-sunk)',
        gap: 2,
      }}
    >
      <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--sc-text)' }}>{value}</span>
      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--sc-text3)' }}>{label}</span>
    </span>
  )
}
