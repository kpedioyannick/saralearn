/**
 * Client de l'API Sara.
 *
 * L'app ouvre sur un exercice, sans compte : au premier lancement on
 * ouvre une session anonyme liée à un identifiant d'appareil, et le
 * jeton est conservé. Créer un compte plus tard ne perd rien.
 */

const BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8010'
const TOKEN_KEY = 'sara.token'
const DEVICE_KEY = 'sara.device'

export interface ApiOption {
  label: string
  feedback: string | null
  /**
   * Les deux champs suivants n'existent que pour `cloze` : un texte à
   * trous porte tous ses candidats dans la même liste, chacun disant à
   * quel trou il appartient et s'il est le bon. `correct_index` ne peut
   * pas l'exprimer — il n'y a pas une bonne réponse, mais une par trou.
   */
  blank?: number
  correct?: boolean
}

export interface ApiExercise {
  id: number
  theme_id: number
  theme: string
  color: string
  type_question:
    | 'qcm'
    | 'true_false'
    | 'complete'
    | 'find_error'
    | 'reorder'
    | 'short_answer'
    | 'cloze'
  prompt: string
  body: string | null
  image: string | null
  image_alt: string | null
  // Le crédit du photographe. Les conditions de l'API Unsplash imposent
  // de l'afficher avec un lien dès qu'une de leurs photos est montrée —
  // ce n'est pas une politesse, c'est la contrepartie du service.
  image_credit: string | null
  image_credit_url: string | null
  image_source: string | null
  options: ApiOption[]
  correct_index: number
  ok_title: string | null
  ok_line: string | null
  ko_title: string | null
  ko_line: string | null
  exp_title: string | null
  exp_text: string
  up_count: number
  down_count: number
  my_vote: -1 | 0 | 1 | null
  comment_count: number
}

export interface ApiUser {
  id: number
  lang: 'fr' | 'en'
  display_name: string | null
  email: string | null
  is_anonymous: boolean
  is_admin: boolean
  muted: boolean
  dark: boolean | null
}

export interface ApiCategory {
  id: number
  slug: string
  label: string
  color: string
}

export interface ApiTheme {
  id: number
  slug: string
  /** Le code de partage, six caractères. */
  code: string | null
  title: string
  description: string | null
  color: string | null
  category_id: number
  category_label: string | null
  visibility: 'private' | 'pending' | 'public'
  exercise_count: number
  subscriber_count: number
  /** Consignes de génération retenues — les chapitres non écartés. */
  prompt_count: number
  /** Personnes ayant répondu à au moins un exercice de cet apprentissage. */
  learner_count: number
  /**
   * Combien d'articles descendent directement de celui-ci — le poids du
   * sujet dans l'arbre de Wikipédia, et l'ordre de repos du catalogue.
   */
  child_count: number
  /**
   * L'étage dans l'arbre : 0 pour l'article racine du thème, 1 pour ses
   * piliers. Le tri s'en sert AVANT le poids, pour que la racine ouvre
   * sa catégorie — voir `byWeight`.
   */
  depth: number
  /** Le chapitre dont celui-ci descend — `null` à la racine du thème. */
  parent_id: number | null
  tags: string[]
  is_owner: boolean
  subscribed: boolean
}

/**
 * Un chapitre du programme d'une connaissance.
 *
 * Les trois champs de rédaction n'arrivent qu'au second appel : tant que
 * `type_question` est nul et qu'il n'y a pas d'`error`, le prompt est
 * encore en train de s'écrire. C'est ce qui donne la progression, sans
 * qu'il ait fallu une colonne d'état de plus.
 */
export interface ApiChapter {
  id: number
  position: number
  title: string
  description: string | null
  /** Le prompt écrit pour ce chapitre — nul tant qu'il ne l'est pas. */
  generated_prompt: string | null
  type_question: 'qcm' | 'complete' | 'find_error' | 'short_answer' | 'cloze' | null
  example: {
    prompt: string
    options: string[]
    correct_index: number
    exp_text: string | null
  } | null
  status: 'draft' | 'validated' | 'rejected'
  error: string | null
}

export interface ApiKnowledge {
  theme_id: number
  title: string
  description: string | null
  category_id: number
  category_label: string
  /** La catégorie a été créée par le modèle : elle attend d'être retenue. */
  category_is_new: boolean
  tags: string[]
  chapters: ApiChapter[]
}

export interface ApiAttempt {
  is_correct: boolean | null
  win: number
  fail: number
  streak: number
}

export interface ApiProgress {
  theme_id: number
  name: string
  passed: number
  total: number
  pct: number
}

export interface ApiRankRow {
  rank: number
  user_id: number
  name: string
  points: number
  passed: number
  is_me: boolean
}

export interface ApiComment {
  id: number
  body: string
  author: string
  created_at: string
}

export interface ApiSettings {
  muted: boolean
  dark: boolean | null
  lang: 'fr' | 'en'
  theme_ids: number[]
  /** Le pseudo. `null` tant que personne ne l'a posé. */
  display_name: string | null
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message)
  }
}

/** Un identifiant d'appareil stable — c'est lui qui porte la session anonyme. */
function deviceId(): string {
  let id = localStorage.getItem(DEVICE_KEY)
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem(DEVICE_KEY, id)
  }
  return id
}

function token(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

function setToken(value: string): void {
  localStorage.setItem(TOKEN_KEY, value)
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  retry = true,
): Promise<T> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['content-type'] = 'application/json'
  const t = token()
  if (t) headers.authorization = `Bearer ${t}`

  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  // Jeton expiré ou base réinitialisée : on rouvre une session anonyme
  // et on rejoue une fois, plutôt que de renvoyer l'utilisateur à un écran vide.
  if (res.status === 401 && retry) {
    await openSession()
    return request<T>(method, path, body, false)
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const payload = await res.json()
      if (typeof payload?.detail === 'string') detail = payload.detail
    } catch {
      /* réponse sans corps JSON */
    }
    throw new ApiError(res.status, detail)
  }

  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

/**
 * La voix, à part : la réponse est un MP3, pas du JSON.
 *
 * Même réflexe de session que `request` — un jeton expiré rouvre une
 * session anonyme et rejoue une fois, sinon la voix se tairait
 * définitivement là où le reste de l'app se rétablit tout seul.
 */
async function requestAudio(
  path: string,
  body: unknown,
  retry = true,
): Promise<Blob> {
  const headers: Record<string, string> = { 'content-type': 'application/json' }
  const t = token()
  if (t) headers.authorization = `Bearer ${t}`

  const res = await fetch(BASE + path, { method: 'POST', headers, body: JSON.stringify(body) })

  if (res.status === 401 && retry) {
    await openSession()
    return requestAudio(path, body, false)
  }
  // Le message porte le code : `speech.ts` distingue le 501 — pas de clé
  // sur ce déploiement, inutile de réessayer — d'une panne passagère.
  if (!res.ok) throw new ApiError(res.status, `tts ${res.status}`)
  return res.blob()
}

/** Ouvre (ou retrouve) la session anonyme de cet appareil. */
export async function openSession(lang: 'fr' | 'en' = 'en'): Promise<ApiUser> {
  const res = await request<{ token: string; user: ApiUser }>(
    'POST',
    '/auth/anonymous',
    { device_id: deviceId(), lang },
    false,
  )
  setToken(res.token)
  return res.user
}

export const api = {
  /** Le texte lu à voix haute, en MP3. Voir `lib/speech.ts`. */
  tts: (text: string, lang: 'fr' | 'en', rate = 1): Promise<Blob> =>
    requestAudio('/tts', { text, lang, rate }),

  async start(lang: 'fr' | 'en' = 'en'): Promise<ApiUser> {
    if (!token()) return openSession(lang)
    try {
      return await request<ApiUser>('GET', '/auth/me')
    } catch {
      return openSession(lang)
    }
  },

  signup: async (
    email: string,
    password: string,
    lang: 'fr' | 'en' = 'en',
    displayName?: string,
  ) => {
    const res = await request<{ token: string; user: ApiUser }>('POST', '/auth/signup', {
      email,
      password,
      lang,
      display_name: displayName ?? null,
    })
    setToken(res.token)
    return res.user
  },

  login: async (email: string, password: string) => {
    const res = await request<{ token: string; user: ApiUser }>('POST', '/auth/login', {
      email,
      password,
    })
    setToken(res.token)
    return res.user
  },

  /**
   * Se déconnecter, c'est reprendre une session anonyme — l'app reste
   * jouable, on ne renvoie personne vers un écran vide.
   *
   * Le jeton part d'abord : si l'ouverture de la session échoue, on
   * reste déconnecté plutôt que de garder un accès au compte. Le
   * device_id n'a pas besoin de tourner ici, le compte a lâché le sien
   * en se créant (voir POST /auth/signup côté API).
   */
  logout: async (lang: 'fr' | 'en' = 'en'): Promise<ApiUser> => {
    localStorage.removeItem(TOKEN_KEY)
    return openSession(lang)
  },

  /**
   * Le flux. `code` le ferme sur une seule connaissance, même privée :
   * c'est le partage par code, et rien d'autre n'est servi tant qu'il
   * est là.
   */
  feed: (n = 5, code?: string | null) =>
    request<ApiExercise[]>(
      'GET',
      `/feed?n=${n}${code ? `&code=${encodeURIComponent(code)}` : ''}`,
    ),

  attempt: (exerciseId: number, chosenIndex: number | null, answerMs?: number) =>
    request<ApiAttempt>('POST', '/attempts', {
      exercise_id: exerciseId,
      chosen_index: chosenIndex,
      answer_ms: answerMs ?? null,
    }),

  vote: (id: number, value: -1 | 0 | 1) =>
    request<ApiExercise>('POST', `/exercises/${id}/vote`, { value }),

  comments: (id: number) => request<ApiComment[]>('GET', `/exercises/${id}/comments`),
  addComment: (id: number, body: string) =>
    request<ApiComment>('POST', `/exercises/${id}/comments`, { body }),

  categories: () => request<ApiCategory[]>('GET', '/categories'),

  credits: () =>
    request<{
      signs: {
        license: string
        attribution: string
        count: number
        country: string
        example_url: string
      }[]
    }>('GET', '/credits'),
  themes: (mine = false) => request<ApiTheme[]>('GET', `/themes?mine=${mine}`),
  subscribe: (id: number) => request<ApiTheme>('POST', `/themes/${id}/subscribe`),
  unsubscribe: (id: number) => request<ApiTheme>('DELETE', `/themes/${id}/subscribe`),

  progression: () => request<ApiProgress[]>('GET', '/progression'),
  rankGlobal: () => request<ApiRankRow[]>('GET', '/rank/global'),
  rankTheme: (id: number) => request<ApiRankRow[]>('GET', `/rank/theme/${id}`),

  settings: () => request<ApiSettings>('GET', '/settings'),
  saveSettings: (patch: Partial<ApiSettings>) =>
    request<ApiSettings>('PUT', '/settings', patch),

  createTheme: (payload: {
    title: string
    category_id: number
    description?: string | null
    source_markdown?: string | null
    tags?: string[]
    lang?: 'fr' | 'en'
  }) => request<ApiTheme>('POST', '/themes', payload),

  /**
   * Le brouillon se crée au dépôt (étape 1), mais son classement se
   * choisit à l'étape 2 : sans cet appel, la catégorie retenue par
   * l'auteur ne quittait jamais le navigateur.
   */
  updateTheme: (
    themeId: number,
    patch: {
      title?: string
      category_id?: number
      description?: string | null
      tags?: string[]
    },
  ) => request<ApiTheme>('PATCH', `/themes/${themeId}`, patch),

  generationStatus: (themeId: number) =>
    request<{ running: boolean; requested: number; produced: number; validated: number }>(
      'GET',
      `/themes/${themeId}/generation`,
    ),

  /** Retrouver une connaissance par son code — même privée. */
  themeByCode: (code: string) =>
    request<ApiTheme>('GET', `/themes/by-code/${encodeURIComponent(code)}`),

  themeExercises: (themeId: number, state?: string) =>
    request<ApiExercise[]>(
      'GET',
      `/themes/${themeId}/exercises${state ? `?state=${state}` : ''}`,
    ),

  patchExercise: (id: number, patch: { state?: string }) =>
    request<ApiExercise>('PATCH', `/exercises/${id}`, patch),

  publish: (themeId: number, isPublic: boolean) =>
    request<ApiTheme>('POST', `/themes/${themeId}/publish`, { public: isPublic }),

  // ----- Connaissance : d'un sujet écrit, un programme ------------------

  /**
   * Un sujet entre, une connaissance en brouillon en sort.
   *
   * L'appel est long — le modèle écrit la présentation et le programme
   * d'un trait. Tout est déjà en base au retour : le thème, ses
   * chapitres et la catégorie, en brouillon. Une création interrompue se
   * reprend par `knowledge(id)`.
   */
  outline: (subject: string, lang?: 'fr' | 'en') =>
    request<ApiKnowledge>('POST', '/knowledge/outline', { subject, lang: lang ?? null }),

  knowledge: (themeId: number) => request<ApiKnowledge>('GET', `/knowledge/${themeId}`),

  /**
   * Lance la rédaction d'un prompt par chapitre — un appel au modèle
   * chacun, en tâches de fond. La réponse revient tout de suite ; c'est
   * `knowledge(id)` qu'on interroge ensuite pour suivre.
   *
   * Sans `force`, seuls les chapitres sans prompt sont traités : relancer
   * après un échec partiel ne réécrit pas ce que l'auteur a corrigé.
   */
  writePrompts: (themeId: number, force = false) =>
    request<ApiKnowledge>('POST', `/knowledge/${themeId}/prompts?force=${force}`),

  /** Les exercices, écrits depuis les prompts de chapitre retenus. */
  generateFromChapters: (themeId: number, count: number) =>
    request<unknown>('POST', `/knowledge/${themeId}/generate`, { count }),

  patchChapter: (
    id: number,
    patch: {
      status?: 'draft' | 'validated' | 'rejected'
      title?: string
      description?: string | null
      type_question?: ApiChapter['type_question']
      generated_prompt?: string
    },
  ) => request<ApiChapter>('PATCH', `/chapters/${id}`, patch),
}
