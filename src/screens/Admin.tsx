import { useCallback, useEffect, useState, type CSSProperties } from 'react'
import { Icon } from '../components/Icon'
import { Dot, NavHead } from '../components/ui'
import { useStore } from '../state/store'

/**
 * Administration — la file de relecture.
 *
 * Trois choses vivaient en base sans jamais remonter à l'écran : les
 * thèmes `pending` déposés par les utilisateurs, les exercices que le
 * vote a écartés du flux, et les commentaires que le cahier des charges
 * dit « envoyés à l'admin ». Cet écran est leur seule fenêtre.
 *
 * Il s'ouvre par `#admin` et se ferme en effaçant le fragment. Il n'est
 * pas dans la machine d'écrans du store : ce n'est pas une étape du
 * parcours, c'est un calque qu'on ouvre exprès et qu'on referme. À
 * l'ouverture, on gare l'app sur un écran statique — sinon le flux
 * continue de tourner derrière et consigne des exercices « passés »
 * que personne n'a vus.
 *
 * Il ne passe pas par `src/lib/api.ts` : le client de l'app porte la
 * session du joueur, pas celle de l'admin, et un 403 d'admin ne doit
 * surtout pas déclencher sa réouverture automatique de session.
 */

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8010'
const TOKEN_KEY = 'sara.token'
// sessionStorage et non localStorage : le jeton de service ouvre tout
// le domaine admin. Il meurt avec l'onglet, comme une session d'astreinte.
const ADMIN_KEY = 'sara.admin'

interface Summary {
  pending_themes: number
  quarantined: number
  comments: number
  unread_comments: number
  identified: boolean
  display_name: string | null
}

interface AdminTheme {
  id: number
  title: string
  slug: string
  description: string | null
  lang: 'fr' | 'en'
  visibility: 'private' | 'pending' | 'public'
  category_label: string
  color: string
  owner_id: number | null
  owner_name: string | null
  exercise_count: number
  subscriber_count: number
  created_at: string
  submitted_at: string | null
}

interface AdminExercise {
  id: number
  theme_id: number
  theme_title: string
  color: string
  type_question: string
  state: 'draft' | 'validated' | 'rejected'
  prompt: string
  up_count: number
  down_count: number
  votes: number
  down_pct: number
  comment_count: number
}

interface AdminComment {
  id: number
  body: string
  created_at: string
  is_read: boolean
  author: string
  user_id: number
  exercise_id: number
  exercise_prompt: string
  theme_id: number
  theme_title: string
}

class AdminError extends Error {
  constructor(readonly status: number, message: string) {
    super(message)
  }
}

async function call<T>(method: string, path: string): Promise<T> {
  const headers: Record<string, string> = {}
  const bearer = localStorage.getItem(TOKEN_KEY)
  if (bearer) headers.authorization = `Bearer ${bearer}`
  const service = sessionStorage.getItem(ADMIN_KEY)
  if (service) headers['x-admin-token'] = service

  const res = await fetch(`${BASE}/admin${path}`, { method, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const payload = await res.json()
      if (typeof payload?.detail === 'string') detail = payload.detail
    } catch {
      /* réponse sans corps JSON */
    }
    throw new AdminError(res.status, detail)
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}

const TEXT = {
  fr: {
    tabThemes: 'Thèmes',
    tabExercises: 'Exercices',
    tabComments: 'Avis',
    subtitleAdmin: (name: string) => `Connecté comme ${name}`,
    subtitleToken: 'Ouvert par le jeton de service',
    loading: 'Chargement…',
    noPending: 'Aucun thème en attente de relecture.',
    noQuarantine: 'Aucun exercice écarté par les votes.',
    noComments: 'Aucun commentaire pour le moment.',
    exercises: (n: number) => `${n} exercice${n > 1 ? 's' : ''} en ligne`,
    subscribers: (n: number) => `${n} abonné${n > 1 ? 's' : ''}`,
    emptyTheme: 'Aucun exercice validé — publier ce thème afficherait un flux vide.',
    by: (name: string | null) => (name ? `Par ${name}` : 'Auteur inconnu'),
    submitted: 'Déposé le',
    approve: 'Publier',
    reject: 'Refuser',
    rejectHint: 'Refuser le rend privé : son auteur le garde et peut redemander.',
    withdraw: 'Retirer du flux',
    restore: 'Remettre en ligne',
    restoreHint: 'Les votes restent : sans correction, il repartira en quarantaine.',
    markRead: 'Marquer lu',
    remove: 'Supprimer',
    confirmDelete: 'Supprimer ce commentaire ? C’est définitif.',
    unread: 'Non lu',
    onAir: 'En ligne',
    offAir: 'Hors flux',
    dropped: 'Écarté',
    votes: (down: number, total: number) => `${down} sur ${total} pouces baissés`,
    deniedTitle: 'Accès réservé',
    deniedLine:
      "Cet écran demande un compte administrateur. À défaut, colle le jeton de service du serveur — il n'est gardé que le temps de l'onglet.",
    tokenPlaceholder: 'Jeton de service',
    tokenOpen: 'Ouvrir',
    forget: 'Oublier le jeton',
    retry: 'Réessayer',
  },
  en: {
    tabThemes: 'Themes',
    tabExercises: 'Exercises',
    tabComments: 'Feedback',
    subtitleAdmin: (name: string) => `Signed in as ${name}`,
    subtitleToken: 'Opened with the service token',
    loading: 'Loading…',
    noPending: 'No theme waiting for review.',
    noQuarantine: 'No exercise pushed out by votes.',
    noComments: 'No comments yet.',
    exercises: (n: number) => `${n} live exercise${n > 1 ? 's' : ''}`,
    subscribers: (n: number) => `${n} subscriber${n > 1 ? 's' : ''}`,
    emptyTheme: 'No validated exercise — publishing this theme would show an empty feed.',
    by: (name: string | null) => (name ? `By ${name}` : 'Unknown author'),
    submitted: 'Submitted',
    approve: 'Publish',
    reject: 'Decline',
    rejectHint: 'Declining makes it private again: the author keeps it and can ask again.',
    withdraw: 'Pull from feed',
    restore: 'Put back online',
    restoreHint: 'Votes are kept: without a fix it will be quarantined again.',
    markRead: 'Mark read',
    remove: 'Delete',
    confirmDelete: 'Delete this comment? This cannot be undone.',
    unread: 'Unread',
    onAir: 'Live',
    offAir: 'Out of feed',
    dropped: 'Dropped',
    votes: (down: number, total: number) => `${down} of ${total} thumbs down`,
    deniedTitle: 'Admins only',
    deniedLine:
      "This screen needs an administrator account. Otherwise paste the server's service token — it is kept for this tab only.",
    tokenPlaceholder: 'Service token',
    tokenOpen: 'Open',
    forget: 'Forget the token',
    retry: 'Try again',
  },
}

type Tab = 'themes' | 'exercises' | 'comments'

/** SQLite écrit en UTC sans fuseau : sans le Z, le navigateur décale d'une heure. */
function fmtDate(raw: string | null, lang: 'fr' | 'en'): string {
  if (!raw) return '—'
  const d = new Date(`${raw.replace(' ', 'T')}Z`)
  if (Number.isNaN(d.getTime())) return raw
  return d.toLocaleDateString(lang === 'en' ? 'en-GB' : 'fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function Badge({ label, tone }: { label: string; tone: 'good' | 'miss' | 'quiet' }) {
  const bg =
    tone === 'good' ? 'var(--sc-good-bg)' : tone === 'miss' ? 'var(--sc-miss-bg)' : 'var(--sc-sunk)'
  const ink =
    tone === 'good' ? 'var(--sc-good-ink)' : tone === 'miss' ? 'var(--sc-miss-ink)' : 'var(--sc-text3)'
  return (
    <span
      style={{
        flex: 'none',
        padding: '3px 9px',
        borderRadius: 'var(--r-pill)',
        background: bg,
        color: ink,
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
      }}
    >
      {label}
    </span>
  )
}

const ACTIONS: CSSProperties = { display: 'flex', gap: 10, flexWrap: 'wrap' }
const ACTION_BTN: CSSProperties = {
  flex: '1 1 130px',
  minHeight: 44,
  fontSize: 15,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 8,
}
const META: CSSProperties = { fontSize: 12.5, color: 'var(--sc-text3)' }
// `anywhere` plutôt qu'une troncature : un titre ou un commentaire posé
// par un utilisateur peut être un mot de 60 caractères, et rien ne doit
// pousser l'écran à scroller de côté.
const FLOW: CSSProperties = { overflowWrap: 'anywhere', minWidth: 0 }

function AdminPanel() {
  const { s, go, t } = useStore()
  const x = TEXT[s.lang]

  const [tab, setTab] = useState<Tab>('themes')
  const [summary, setSummary] = useState<Summary | null>(null)
  const [themes, setThemes] = useState<AdminTheme[]>([])
  const [exercises, setExercises] = useState<AdminExercise[]>([])
  const [comments, setComments] = useState<AdminComment[]>([])
  const [busy, setBusy] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [denied, setDenied] = useState(false)
  const [draft, setDraft] = useState('')
  const [hasToken, setHasToken] = useState(() => Boolean(sessionStorage.getItem(ADMIN_KEY)))

  // On gare le flux : sa machine de phases ne tourne que sur l'écran
  // « exo », et derrière ce calque elle enchaînerait les exercices en
  // les consignant comme passés au swipe.
  useEffect(() => {
    go('about')
  }, [go])

  const load = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      const sum = await call<Summary>('GET', '/summary')
      setDenied(false)
      setSummary(sum)
      if (tab === 'themes') setThemes(await call<AdminTheme[]>('GET', '/themes/pending'))
      if (tab === 'exercises')
        setExercises(await call<AdminExercise[]>('GET', '/exercises/quarantine'))
      if (tab === 'comments') setComments(await call<AdminComment[]>('GET', '/comments'))
    } catch (err) {
      if (err instanceof AdminError && err.status === 403) setDenied(true)
      else setError(err instanceof Error ? err.message : 'Erreur inconnue.')
    } finally {
      setBusy(false)
    }
  }, [tab])

  useEffect(() => {
    void load()
  }, [load])

  const act = useCallback(
    (method: string, path: string) => {
      void call(method, path)
        .then(load)
        .catch((err: unknown) => {
          if (err instanceof AdminError && err.status === 403) setDenied(true)
          else setError(err instanceof Error ? err.message : 'Erreur inconnue.')
        })
    },
    [load],
  )

  const close = useCallback(() => {
    // replaceState plutôt que hash = '' : revenir en arrière ne doit pas
    // rouvrir l'admin. Il faut alors prévenir l'écoute à la main.
    window.history.replaceState(null, '', window.location.pathname + window.location.search)
    window.dispatchEvent(new Event('hashchange'))
    go('exo', 'q')
  }, [go])

  const subtitle = summary
    ? summary.identified
      ? x.subtitleAdmin(summary.display_name ?? '—')
      : x.subtitleToken
    : undefined

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: 'themes', label: x.tabThemes, count: summary?.pending_themes ?? 0 },
    { key: 'exercises', label: x.tabExercises, count: summary?.quarantined ?? 0 },
    { key: 'comments', label: x.tabComments, count: summary?.unread_comments ?? 0 },
  ]

  return (
    <div className="screen" style={{ zIndex: 40 }}>
      {/* Le reste de l'app passe par le cadre vertical de DesktopFrame ;
          ce calque le double, alors il garde sa propre colonne. Sans
          elle, un bouton fait 900 px de large sur un écran de bureau. */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          minHeight: 0,
          width: '100%',
          maxWidth: 560,
          margin: '0 auto',
        }}
      >
        <NavHead onBack={close} title={t.admin} subtitle={denied ? undefined : subtitle} />

      {!denied && (
        <div className="segmented" style={{ gridTemplateColumns: '1fr 1fr 1fr' }}>
          {tabs.map((it) => (
            <button
              key={it.key}
              className={tab === it.key ? 'segment is-on' : 'segment'}
              onClick={() => setTab(it.key)}
              aria-pressed={tab === it.key}
              style={{ fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
            >
              <span>{it.label}</span>
              {it.count > 0 && (
                <span
                  style={{
                    minWidth: 20,
                    padding: '0 6px',
                    borderRadius: 'var(--r-pill)',
                    background: 'var(--sc-primary)',
                    color: 'var(--sc-on-primary)',
                    fontSize: 11,
                    fontWeight: 800,
                    lineHeight: '18px',
                  }}
                >
                  {it.count}
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      <div
        className="screen-scroll stack"
        style={{ padding: denied ? '10px 22px 30px' : '2px 22px 30px', gap: 12 }}
      >
        {denied && (
          <div className="card">
            <span className="eyebrow">{x.deniedTitle}</span>
            <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: 'var(--sc-text2)' }}>
              {x.deniedLine}
            </p>
            <div className="field">
              <input
                className="input"
                type="password"
                value={draft}
                autoComplete="off"
                placeholder={x.tokenPlaceholder}
                onChange={(e) => setDraft(e.target.value)}
              />
              <button
                className="btn-primary"
                style={{ minHeight: 48, fontSize: 16 }}
                onClick={() => {
                  sessionStorage.setItem(ADMIN_KEY, draft.trim())
                  setHasToken(true)
                  setDraft('')
                  void load()
                }}
              >
                {x.tokenOpen}
              </button>
            </div>
            {hasToken && (
              <button
                className="btn-quiet"
                onClick={() => {
                  sessionStorage.removeItem(ADMIN_KEY)
                  setHasToken(false)
                  void load()
                }}
              >
                {x.forget}
              </button>
            )}
          </div>
        )}

        {error && !denied && (
          <div className="card">
            <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: 'var(--sc-miss-ink)', ...FLOW }}>
              {error}
            </p>
            <button className="btn-outline" onClick={() => void load()}>
              {x.retry}
            </button>
          </div>
        )}

        {busy && !denied && (
          <p className="serif-italic" style={{ fontSize: 16, color: 'var(--sc-text3)' }}>
            {x.loading}
          </p>
        )}

        {!busy && !denied && !error && tab === 'themes' && (
          <>
            {themes.length === 0 ? (
              <p className="serif-italic" style={{ fontSize: 16, color: 'var(--sc-text3)' }}>
                {x.noPending}
              </p>
            ) : (
              // La règle du geste se dit une fois en tête de file, pas
              // sous chaque carte : répétée, elle ne se lit plus.
              <span style={{ ...META, marginBottom: 2 }}>{x.rejectHint}</span>
            )}
            {themes.map((th) => (
              <article className="card" key={th.id}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8, ...FLOW }}>
                  <Dot color={th.color} />
                  <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--sc-text)', ...FLOW }}>
                    {th.title}
                  </span>
                  <Badge label={th.lang.toUpperCase()} tone="quiet" />
                </span>
                <span style={META}>
                  {th.category_label} · {x.exercises(th.exercise_count)} ·{' '}
                  {x.subscribers(th.subscriber_count)}
                </span>
                {th.description && (
                  <p
                    style={{
                      margin: 0,
                      fontSize: 14,
                      lineHeight: 1.6,
                      color: 'var(--sc-text2)',
                      ...FLOW,
                    }}
                  >
                    {th.description}
                  </p>
                )}
                {th.exercise_count === 0 && (
                  <span
                    className="card-sunk"
                    style={{
                      fontSize: 13,
                      color: 'var(--sc-miss-ink)',
                      background: 'var(--sc-miss-bg)',
                      borderColor: 'var(--sc-miss-line)',
                      ...FLOW,
                    }}
                  >
                    {x.emptyTheme}
                  </span>
                )}
                <span style={META}>
                  {x.by(th.owner_name)} · {x.submitted} {fmtDate(th.submitted_at ?? th.created_at, s.lang)}
                </span>
                <div style={ACTIONS}>
                  <button
                    className="btn-primary"
                    style={ACTION_BTN}
                    onClick={() => act('POST', `/themes/${th.id}/approve`)}
                  >
                    <Icon name="globe" size={17} stroke={2} />
                    {x.approve}
                  </button>
                  <button
                    className="btn-outline"
                    style={ACTION_BTN}
                    onClick={() => act('POST', `/themes/${th.id}/reject`)}
                  >
                    {x.reject}
                  </button>
                </div>
              </article>
            ))}
          </>
        )}

        {!busy && !denied && !error && tab === 'exercises' && (
          <>
            {exercises.length === 0 ? (
              <p className="serif-italic" style={{ fontSize: 16, color: 'var(--sc-text3)' }}>
                {x.noQuarantine}
              </p>
            ) : (
              <span style={{ ...META, marginBottom: 2 }}>{x.restoreHint}</span>
            )}
            {exercises.map((e) => (
              <article className="card" key={e.id}>
                <span
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 10,
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: 8, ...FLOW }}>
                    <Dot color={e.color} />
                    <span style={{ ...META, fontWeight: 600, ...FLOW }}>{e.theme_title}</span>
                  </span>
                  <Badge
                    label={e.state === 'validated' ? x.onAir : e.state === 'draft' ? x.offAir : x.dropped}
                    tone={e.state === 'validated' ? 'good' : 'miss'}
                  />
                </span>
                <p style={{ margin: 0, fontSize: 15, lineHeight: 1.5, color: 'var(--sc-text)', ...FLOW }}>
                  {e.prompt}
                </p>
                <span
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: 13,
                    fontWeight: 600,
                    color: 'var(--sc-miss-ink)',
                  }}
                >
                  <Icon name="thumbDown" size={15} stroke={1.9} />
                  {x.votes(e.down_count, e.votes)} · {e.down_pct} %
                </span>
                <div style={ACTIONS}>
                  <button
                    className="btn-outline"
                    style={ACTION_BTN}
                    onClick={() => act('POST', `/exercises/${e.id}/withdraw`)}
                  >
                    {x.withdraw}
                  </button>
                  {e.state !== 'validated' && (
                    <button
                      className="btn-outline"
                      style={ACTION_BTN}
                      onClick={() => act('POST', `/exercises/${e.id}/restore`)}
                    >
                      {x.restore}
                    </button>
                  )}
                </div>
              </article>
            ))}
          </>
        )}

        {!busy && !denied && !error && tab === 'comments' && (
          <>
            {comments.length === 0 && (
              <p className="serif-italic" style={{ fontSize: 16, color: 'var(--sc-text3)' }}>
                {x.noComments}
              </p>
            )}
            {comments.map((k) => (
              <article className="card" key={k.id}>
                <span
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 10,
                  }}
                >
                  <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--sc-text)', ...FLOW }}>
                    {k.author}
                  </span>
                  {!k.is_read && <Badge label={x.unread} tone="miss" />}
                </span>
                <p style={{ margin: 0, fontSize: 15, lineHeight: 1.6, color: 'var(--sc-text2)', ...FLOW }}>
                  {k.body}
                </p>
                <span className="card-sunk" style={{ ...META, ...FLOW }}>
                  {k.theme_title} — {k.exercise_prompt}
                </span>
                <span style={META}>{fmtDate(k.created_at, s.lang)}</span>
                <div style={ACTIONS}>
                  {!k.is_read && (
                    <button
                      className="btn-outline"
                      style={ACTION_BTN}
                      onClick={() => act('POST', `/comments/${k.id}/read`)}
                    >
                      <Icon name="check" size={16} stroke={2.2} />
                      {x.markRead}
                    </button>
                  )}
                  <button
                    className="btn-outline"
                    style={{ ...ACTION_BTN, color: 'var(--sc-miss-ink)' }}
                    onClick={() => {
                      // Une suppression ne se rattrape pas : on demande.
                      if (window.confirm(x.confirmDelete)) act('DELETE', `/comments/${k.id}`)
                    }}
                  >
                    <Icon name="trash" size={16} stroke={1.9} />
                    {x.remove}
                  </button>
                </div>
              </article>
            ))}
          </>
        )}
        </div>
      </div>
    </div>
  )
}

/**
 * Le calque n'existe que sur `#admin`. Le composant extérieur ne monte
 * rien tant que le fragment n'y est pas : aucun état, aucune requête,
 * aucun coût pour les 99,9 % de sessions qui ne sont pas des relectures.
 */
export function Admin() {
  const [open, setOpen] = useState(
    () => typeof window !== 'undefined' && window.location.hash === '#admin',
  )

  useEffect(() => {
    const sync = () => setOpen(window.location.hash === '#admin')
    window.addEventListener('hashchange', sync)
    sync()
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  return open ? <AdminPanel /> : null
}
