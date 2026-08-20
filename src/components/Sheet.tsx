import { useState, type ReactNode } from 'react'
import type { ApiChapter, ApiKnowledge, ApiTheme } from '../lib/api'
import { useIsDesktop } from '../lib/useIsDesktop'
import { useStore } from '../state/store'
import { Icon } from './Icon'
import { Avatar, Dot, Meter } from './ui'

/**
 * Feuille du bas sur mobile, panneau latéral de 440 px sur desktop —
 * même contenu, même état.
 */
export function Sheet() {
  const {
    s, exo, set, go, themes, myThemes, progression, comments, sheetKnowledge,
    sheetLoading, toggleSubscribe, sendComment, t,
  } = useStore()
  const isDesktop = useIsDesktop()
  const [draft, setDraft] = useState('')

  const close = () => set({ sheet: null, sheetThemeId: null })

  // La fiche d'auteur ne dépend pas de l'exercice courant : elle s'ouvre
  // depuis une liste, là où `exo` peut être nul. Elle est donc traitée
  // avant la garde ci-dessous, qui ne vaut que pour les deux feuilles du
  // flux d'exercices.
  if (s.sheet === 'myTheme') {
    const th = myThemes.find((x) => x.id === s.sheetThemeId) ?? null
    if (!th) return null
    return (
      <SheetFrame title={t.themeDetail} isDesktop={isDesktop} close={close} t={t}>
        <MyThemePanel
          th={th}
          k={sheetKnowledge}
          loading={sheetLoading}
          isDesktop={isDesktop}
          t={t}
        />
      </SheetFrame>
    )
  }

  if (!s.sheet || !exo) return null
  const theme = themes.find((x) => x.id === exo.themeId)
  const subscribed = theme?.subscribed ?? false
  const progress = progression.find((p) => p.theme_id === exo.themeId)

  const submit = () => {
    sendComment(draft)
    setDraft('')
  }

  /**
   * Le panneau d'apprentissage.
   *
   * L'abonnement remonte en tête, à côté du titre : c'est la raison
   * première d'ouvrir cette feuille, et il était en bas, sous la
   * progression — il fallait faire défiler pour s'abonner.
   */
  const themePanel = (
    <div className="stack panel-body" style={{ gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        <span className="stack" style={{ flex: 1, gap: 6 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Dot color={exo.color} size={10} />
            <span
              className="display"
              style={{ fontSize: isDesktop ? 30 : 26, fontWeight: 700 }}
            >
              {exo.theme}
            </span>
          </span>
          <span style={{ fontSize: 15, color: 'var(--sc-text2)' }}>
            {theme?.category_label ? `${theme.category_label} · ` : ''}
            {t.exercisesCount(theme?.exercise_count ?? 0)} ·{' '}
            {theme?.subscriber_count ?? 0} {t.subscribers}
          </span>
        </span>
        <button
          className="btn-primary"
          onClick={() => toggleSubscribe(exo.themeId)}
          style={{
            width: 'auto',
            minHeight: 46,
            padding: '0 18px',
            fontSize: 16,
            background: subscribed ? 'var(--sc-veil)' : 'var(--sc-primary)',
            color: subscribed ? 'var(--sc-text2)' : 'var(--sc-on-primary)',
          }}
        >
          {subscribed ? t.followed : t.subscribeShort}
        </button>
      </div>

      {theme && theme.tags.length > 0 && (
        <div className="wrap" style={{ gap: 8 }}>
          {theme.tags.map((tag) => (
            <span key={tag} className="chip" style={{ cursor: 'default', minHeight: 32 }}>
              {tag}
            </span>
          ))}
        </div>
      )}

      <p className="body" style={{ fontSize: 16 }}>
        {theme?.description || t.themeBlurb(exo.theme)}
      </p>

      {progress && (
        <div className="stack" style={{ gap: 8 }}>
          <span
            style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}
          >
            <span style={{ fontSize: 15, color: 'var(--sc-text2)' }}>{t.yourProgressHere}</span>
            <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--sc-primary)' }}>
              {progress.pct} %
            </span>
          </span>
          <Meter pct={progress.pct} />
          <span style={{ fontSize: 13, color: 'var(--sc-text3)' }}>
            {progress.passed}/{progress.total} {t.passed}
          </span>
        </div>
      )}

      <button
        className="btn-outline"
        style={{ marginTop: isDesktop ? 'auto' : 0 }}
        onClick={() => go('rankOne')}
      >
        {t.seeThemeRanking}
      </button>
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
  const title =
    s.sheet === 'comments' ? `${comments.length} ${t.comments.toLowerCase()}` : t.learnings

  return (
    <SheetFrame title={title} isDesktop={isDesktop} close={close} t={t}>
      {body}
    </SheetFrame>
  )
}

type Dict = ReturnType<typeof useStore>['t']

/**
 * Un prompt de la fiche d'auteur.
 *
 * Le texte est replié à trois lignes par défaut. Déplié, un prompt fait
 * dix à quinze lignes de monospace ; trois de suite et la fiche devient
 * un mur qu'on ne parcourt plus. Replié, on lit la liste ; on ouvre
 * celui qu'on veut relire.
 */
function PromptCard({ c, rank, t }: { c: ApiChapter; rank: number; t: Dict }) {
  const [open, setOpen] = useState(false)
  const out = c.status === 'rejected'
  const text = c.generated_prompt
  // Le repli ne vaut que si le texte déborde. Sous ce seuil, le bouton
  // « voir tout » n'ouvrirait rien — et un bouton qui ne fait rien est
  // pire qu'une ligne de plus.
  const long = (text?.length ?? 0) > 150

  return (
    <div className={out ? 'prompt-card is-out' : 'prompt-card'}>
      <div className="prompt-card-head">
        <span className="prompt-rank">{rank}</span>
        <span className="prompt-card-title">
          <span className="prompt-name">{c.title}</span>
          {c.description && <span className="prompt-desc">{c.description}</span>}
        </span>
        {out ? (
          <span className="prompt-card-tag">{t.chapterRejected}</span>
        ) : (
          c.type_question && <span className="prompt-kind">{t[c.type_question]}</span>
        )}
      </div>

      {text ? (
        <>
          <p className={long && !open ? 'prompt-card-text is-clamped' : 'prompt-card-text'}>
            {text}
          </p>
          {long && (
            <button className="prompt-more" onClick={() => setOpen((v) => !v)}>
              {open ? t.showLess : t.showAll}
            </button>
          )}
        </>
      ) : (
        <p className="prompt-card-text is-empty">{t.promptNotWritten}</p>
      )}
    </div>
  )
}

/**
 * L'enveloppe : feuille du bas en téléphone, panneau de 440 px en
 * desktop. Elle était écrite en double au pied de `Sheet` ; la fiche
 * d'auteur en aurait fait un troisième exemplaire.
 */
function SheetFrame({
  title,
  isDesktop,
  close,
  t,
  children,
}: {
  title: string
  isDesktop: boolean
  close: () => void
  t: Dict
  children: ReactNode
}) {
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
          {children}
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
        {children}
      </div>
    </div>
  )
}

/**
 * La fiche d'un apprentissage que j'ai créé : ce qu'il est, et les
 * consignes qui l'écrivent.
 *
 * Les chiffres sont ceux de la ligne qu'on vient de toucher — ils
 * viennent avec la liste. Les prompts, eux, sont chargés à l'ouverture :
 * ils ne servent qu'ici, et les demander pour toute la liste coûterait
 * un appel par apprentissage.
 */
function MyThemePanel({
  th,
  k,
  loading,
  isDesktop,
  t,
}: {
  th: ApiTheme
  k: ApiKnowledge | null
  loading: boolean
  isDesktop: boolean
  t: Dict
}) {
  const { resumeDraft } = useStore()

  // Les chapitres écartés restent en base pour ne pas être reproposés.
  // On les montre en dernier et en gris plutôt que de les cacher : un
  // auteur qui compte ses prompts doit retrouver celui qu'il a retiré.
  const chapters = [...(k?.chapters ?? [])].sort(
    (a, b) => Number(a.status === 'rejected') - Number(b.status === 'rejected'),
  )

  const status =
    th.visibility === 'public'
      ? t.publicLabel
      : th.visibility === 'pending'
        ? t.pendingLabel
        : t.privateLabel

  return (
    <div className="stack panel-body sheet-doc">
      {/* L'en-tête : d'abord ce que c'est, ensuite comment ça s'appelle.
          Le statut vient en premier parce qu'un auteur ouvre sa fiche
          pour savoir si elle est en ligne, pas pour relire son titre. */}
      <div className="sheet-hero">
        <span
          className={
            th.visibility === 'public' ? 'share-badge' : 'share-badge is-private'
          }
        >
          {status}
        </span>
        <h2 className="sheet-title" style={{ fontSize: isDesktop ? 26 : 23 }}>
          {th.title}
        </h2>
        <span className="sheet-sub">
          {th.category_label ?? ''}
        </span>
        {th.description && <p className="sheet-lead">{th.description}</p>}
      </div>

      {/* Trois chiffres sur une seule ligne, séparés par un filet. Les
          cartes de `share-grid` sont posées sur deux colonnes : à trois
          mesures, la dernière se retrouvait seule sur sa rangée. */}
      <div className="sheet-stats">
        <span className="sheet-stat">
          <b>{th.prompt_count}</b>
          <span>{t.promptsShort}</span>
        </span>
        <span className="sheet-stat">
          <b>{th.exercise_count}</b>
          <span>{t.exercises.toLowerCase()}</span>
        </span>
        <span className="sheet-stat">
          <b>{th.learner_count}</b>
          <span>{t.learnersShort}</span>
        </span>
      </div>

      <div className="stack" style={{ gap: 10 }}>
        <span className="sheet-section">
          <span className="mono">{t.promptsList}</span>
          {chapters.length > 0 && <span className="sheet-count">{chapters.length}</span>}
        </span>

        {loading && <p className="serif-italic">{t.oneMoment}</p>}

        {!loading && chapters.length === 0 && (
          <p className="serif-italic">{t.noPromptYet}</p>
        )}

        {chapters.map((c, i) => (
          <PromptCard key={c.id} c={c} rank={i + 1} t={t} />
        ))}
      </div>

      {/* La fiche était en lecture seule : elle montrait « 5 prompts,
          0 exercice, prompt pas encore écrit » et ne proposait rien.
          Un auteur y arrivait pour reprendre son travail et n'avait
          aucune porte — ni pour écrire les prompts, ni pour relire les
          questions déjà produites. `resumeDraft` rouvre la création à
          l'étape où elle s'est arrêtée. */}
      <button className="btn-primary" onClick={() => void resumeDraft(th.id)}>
        {t.resumeCreation}
      </button>
    </div>
  )
}
