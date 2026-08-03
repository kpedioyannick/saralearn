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
  type_bloom: 'remember' | 'understand' | 'apply' | 'analyze'
  prompt: string
  body: string | null
  image: string | null
  image_alt: string | null
  options: ApiOption[]
  correct_index: number
  ok_title: string | null
  ok_line: string | null
  ko_title: string | null
  ko_line: string | null
  exp_title: string | null
  exp_text: string
  exp_tip: string | null
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

export interface ApiSubCategory {
  id: number
  slug: string
  label: string
  color: string | null
}

export interface ApiCategory {
  id: number
  slug: string
  label: string
  color: string
  sub_categories: ApiSubCategory[]
}

export interface ApiTheme {
  id: number
  slug: string
  title: string
  description: string | null
  color: string | null
  category_id: number
  category_label: string | null
  sub_category_id: number | null
  sub_category_label: string | null
  visibility: 'private' | 'pending' | 'public'
  exercise_count: number
  subscriber_count: number
  tags: string[]
  is_owner: boolean
  subscribed: boolean
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

/** Ouvre (ou retrouve) la session anonyme de cet appareil. */
export async function openSession(lang: 'fr' | 'en' = 'fr'): Promise<ApiUser> {
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
  async start(lang: 'fr' | 'en' = 'fr'): Promise<ApiUser> {
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
    lang: 'fr' | 'en' = 'fr',
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
  logout: async (lang: 'fr' | 'en' = 'fr'): Promise<ApiUser> => {
    localStorage.removeItem(TOKEN_KEY)
    return openSession(lang)
  },

  feed: (n = 5) => request<ApiExercise[]>('GET', `/feed?n=${n}`),

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
    sub_category_id?: number | null
    description?: string | null
    source_markdown?: string | null
    tags?: string[]
    lang?: 'fr' | 'en'
  }) => request<ApiTheme>('POST', '/themes', payload),

  generate: (themeId: number, types: string[], blooms: string[], count: number) =>
    request<unknown>('POST', `/themes/${themeId}/generate`, { types, blooms, count }),

  generationStatus: (themeId: number) =>
    request<{ running: boolean; requested: number; produced: number; validated: number }>(
      'GET',
      `/themes/${themeId}/generation`,
    ),

  themeExercises: (themeId: number, state?: string) =>
    request<ApiExercise[]>(
      'GET',
      `/themes/${themeId}/exercises${state ? `?state=${state}` : ''}`,
    ),

  patchExercise: (id: number, patch: { state?: string }) =>
    request<ApiExercise>('PATCH', `/exercises/${id}`, patch),

  publish: (themeId: number, isPublic: boolean) =>
    request<ApiTheme>('POST', `/themes/${themeId}/publish`, { public: isPublic }),
}
