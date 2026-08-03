import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { BLOCKING_LOADER, PACE } from '../config'
import { DURATIONS, type Exercise, type ExerciseType } from '../data/content'
import { dict, detectLang, type Lang } from '../i18n'
import { play, unlock } from '../lib/audio'
import {
  api,
  type ApiCategory,
  type ApiComment,
  type ApiExercise,
  type ApiOption,
  type ApiProgress,
  type ApiRankRow,
  type ApiTheme,
  type ApiUser,
} from '../lib/api'

export type Screen =
  | 'exo'
  | 'onb1'
  | 'onb2'
  | 'onb3'
  | 'picker'
  | 'picker2'
  | 'settings'
  | 'themes'
  | 'rank'
  | 'rankOne'
  | 'create'
  | 'publish'
  | 'auth'
  | 'about'

export type Phase = 'q' | 'ok' | 'ko' | 'exp'
export type Sheet = 'theme' | 'comments' | null



/**
 * La carte telle que les écrans la lisent. `type` est le libellé
 * traduit, montré en tête d'exercice ; `typeQuestion` est le type brut,
 * et c'est lui seul qui décide de la façon de répondre.
 */
export type ExoCard = Exercise & {
  id: number
  themeId: number
  image: string | null
  imageAlt: string | null
  typeQuestion: ApiExercise['type_question']
  /**
   * Les options entières. `options` n'en garde que les libellés, ce qui
   * suffit à un QCM mais perd `blank` et `correct` — les deux champs
   * dont un texte à trous a besoin.
   */
  opts: ApiOption[]
}

/**
 * L'API parle en snake_case et le front en camelCase depuis la maquette.
 * Cet adaptateur évite de propager le renommage dans tous les écrans.
 */
function adapt(e: ApiExercise, lang: Lang): ExoCard {
  const t = dict(lang)
  return {
    id: e.id,
    themeId: e.theme_id,
    theme: e.theme,
    color: e.color,
    type: t[e.type_question] as ExerciseType,
    typeQuestion: e.type_question,
    opts: e.options,
    prompt: e.prompt,
    body: e.body ?? undefined,
    image: e.image,
    imageAlt: e.image_alt,
    options: e.options.map((o) => o.label),
    correct: e.correct_index,
    okTitle: e.ok_title ?? 'Bien vu.',
    okLine: e.ok_line ?? '',
    koTitle: e.ko_title ?? 'Presque.',
    koLine: e.ko_line ?? '',
    expTitle: e.exp_title ?? '',
    expText: e.exp_text,
    expTip: e.exp_tip ?? '',
  }
}

type Flags = Record<string | number, boolean>

interface State {
  dark: boolean
  muted: boolean
  lang: Lang
  screen: Screen
  phase: Phase
  i: number
  chosen: number | null
  /**
   * Ce que l'apprenant a PRODUIT, quand répondre n'est plus choisir une
   * option. `typed` porte la saisie d'une `short_answer`, `fills` le
   * candidat posé dans chaque trou d'un `cloze` (index dans `exo.opts`,
   * `null` tant que le trou est vide) et `blank` le trou en cours.
   * Ils survivent à la réponse : l'écran d'erreur montre la réponse
   * donnée, et pour ces deux types elle n'est pas dans `options`.
   */
  typed: string
  fills: (number | null)[]
  blank: number
  win: number
  fail: number
  streak: number
  prog: number
  sheet: Sheet
  hint: boolean
  dragY: number
  tab: 'forces' | 'others'
  rankTheme: number
  createStep: number
  genCount: number
  genLoading: boolean
  toast: boolean
  typesOn: Flags
  tagsOff: Flags
  validated: number
  authMode: 'signup' | 'login'
  pubPublic: boolean
  published: boolean
  authError: string | null
  /** Catégories cochées à l'inscription : filtre l'écran suivant, rien de plus. */
  onbCategories: number[]
  /** Le thème en cours de création, une fois déposé côté serveur. */
  draftThemeId: number | null
  draftTitle: string
  draftDescription: string
  draftMarkdown: string
  draftTags: string[]
  draftCategoryId: number
  draftSubCategoryId: number | null
  genError: string | null
}

const PREFS_KEY = 'sara.prefs'

function readPrefs(): { dark: boolean; muted: boolean; lang: Lang } {
  const fallback = {
    dark:
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches,
    muted: false,
    lang: detectLang(),
  }
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (!raw) return fallback
    const parsed = JSON.parse(raw) as Partial<typeof fallback>
    return {
      dark: typeof parsed.dark === 'boolean' ? parsed.dark : fallback.dark,
      muted: typeof parsed.muted === 'boolean' ? parsed.muted : fallback.muted,
      lang: parsed.lang === 'en' || parsed.lang === 'fr' ? parsed.lang : fallback.lang,
    }
  } catch {
    return fallback
  }
}

const PHASES: Phase[] = ['q', 'ok', 'ko', 'exp']

/** Une carte fraîche : tout ce qui porte une réponse en cours repart à zéro. */
const NO_ANSWER: Pick<State, 'chosen' | 'typed' | 'fills' | 'blank'> = {
  chosen: null,
  typed: '',
  fills: [],
  blank: 0,
}

/**
 * L'adresse publique de chaque écran. Elle est en anglais et lisible :
 * une URL se partage et se tape, alors que `Screen` est un identifiant
 * interne hérité de la maquette. Les deux sont séparés pour qu'on
 * puisse renommer l'un sans casser les liens de l'autre.
 */
const ROUTES: Record<Screen, string> = {
  exo: 'exercise',
  onb1: 'welcome',
  onb2: 'categories',
  onb3: 'subcategories',
  picker: 'add-themes',
  picker2: 'all-themes',
  settings: 'settings',
  themes: 'themes',
  rank: 'leaderboard',
  rankOne: 'leaderboard-theme',
  create: 'create',
  publish: 'publish',
  auth: 'sign-in',
  about: 'about',
}

const BY_ROUTE = Object.entries(ROUTES) as [Screen, string][]

export function routeOf(screen: Screen, phase?: Phase): string {
  const base = `#${ROUTES[screen]}`
  return screen === 'exo' && phase && phase !== 'q' ? `${base}/${phase}` : base
}

/** Index des écrans par fragment d'URL : #settings, #exercise/ko … */
function fromHash(): { screen: Screen; phase: Phase } | null {
  if (typeof window === 'undefined') return null
  const [s, p] = window.location.hash.replace(/^#/, '').split('/')
  const hit = BY_ROUTE.find(([, route]) => route === s)
  if (!hit) return null
  return { screen: hit[0], phase: PHASES.find((x) => x === p) ?? 'q' }
}

function initialState(): State {
  const prefs = readPrefs()
  const entry = fromHash()
  return {
    dark: prefs.dark,
    muted: prefs.muted,
    lang: prefs.lang,
    screen: entry?.screen ?? 'exo',
    phase: entry?.phase ?? 'q',
    i: 0,
    ...NO_ANSWER,
    win: 0,
    fail: 0,
    streak: 0,
    prog: 0,
    sheet: null,
    hint: !entry,
    dragY: 0,
    tab: 'forces',
    rankTheme: 0,
    createStep: 1,
    genCount: 20,
    genLoading: false,
    toast: false,
    typesOn: { 0: true, 1: true },
    tagsOff: {},
    validated: 0,
    authMode: 'signup',
    pubPublic: false,
    published: false,
    authError: null,
    onbCategories: [],
    draftThemeId: null,
    draftTitle: '',
    draftDescription: '',
    draftMarkdown: '',
    draftTags: [],
    draftCategoryId: 0,
    draftSubCategoryId: null,
    genError: null,
  }
}

export interface Store {
  s: State
  exo: ExoCard | null
  deckSize: number
  ready: boolean
  offline: boolean
  user: ApiUser | null
  categories: ApiCategory[]
  themes: ApiTheme[]
  progression: ApiProgress[]
  rankRows: ApiRankRow[]
  comments: ApiComment[]
  revealed: boolean
  set: (patch: Partial<State> | ((prev: State) => Partial<State>)) => void
  toggleFlag: (key: 'typesOn', id: string | number) => void
  hideFlag: (key: 'tagsOff', id: string | number) => void
  answer: (index: number) => void
  next: () => void
  prev: () => void
  go: (screen: Screen, phase?: Phase) => void
  goCreate: (step: number) => void
  generate: () => void
  t: ReturnType<typeof dict>
  setLang: (lang: Lang) => void
  toggleDark: () => void
  toggleMute: () => void
  vote: (value: -1 | 1) => void
  myVote: -1 | 0 | 1 | null
  upCount: number
  downCount: number
  commentCount: number
  subscribedIds: Set<number>
  toggleSubscribe: (themeId: number) => void
  sendComment: (body: string) => void
  submitAuth: (email: string, password: string, lang?: Lang) => Promise<boolean>
  logout: () => Promise<boolean>
  draftExercises: ApiExercise[]
  createDraft: () => Promise<boolean>
  startGeneration: (types: string[], blooms: string[], count: number) => Promise<void>
  reviewExercise: (id: number, state: 'validated' | 'rejected') => void
  publishDraft: (isPublic: boolean) => Promise<void>
}

const StoreContext = createContext<Store | null>(null)

export function StoreProvider({ children }: { children: ReactNode }) {
  const [s, setS] = useState<State>(initialState)
  const [deck, setDeck] = useState<ApiExercise[]>([])
  const [user, setUser] = useState<ApiUser | null>(null)
  const [categories, setCategories] = useState<ApiCategory[]>([])
  const [themes, setThemes] = useState<ApiTheme[]>([])
  const [progression, setProgression] = useState<ApiProgress[]>([])
  const [rankRows, setRankRows] = useState<ApiRankRow[]>([])
  const [comments, setComments] = useState<ApiComment[]>([])
  const [draftExercises, setDraftExercises] = useState<ApiExercise[]>([])
  const [ready, setReady] = useState(false)
  const [offline, setOffline] = useState(false)

  const phaseStart = useRef<number>(performance.now())
  const ended = useRef(false)
  const answeredAt = useRef<number>(performance.now())
  const live = useRef(s)
  live.current = s
  const liveDeck = useRef(deck)
  liveDeck.current = deck
  const fetching = useRef(false)

  const set = useCallback<Store['set']>((patch) => {
    setS((prev) => ({ ...prev, ...(typeof patch === 'function' ? patch(prev) : patch) }))
  }, [])

  /**
   * L'adresse suit l'écran. Sans ça, `#settings` ouvrait bien les
   * réglages au chargement, mais l'URL restait figée ensuite : impossible
   * de copier un lien vers l'endroit où l'on se trouve, et le bouton
   * Précédent du navigateur sortait de l'app.
   *
   * replaceState pendant un exercice : les phases d'une même carte ne
   * sont pas des étapes de navigation, les empiler ferait remonter le
   * Précédent une par une.
   */
  useEffect(() => {
    if (typeof window === 'undefined') return
    const next = routeOf(s.screen, s.phase)
    if (window.location.hash === next) return
    const url = window.location.pathname + window.location.search + next
    if (s.screen === 'exo' && s.phase !== 'q') window.history.replaceState(null, '', url)
    else window.history.pushState(null, '', url)
  }, [s.screen, s.phase])

  // Le Précédent du navigateur ramène à l'écran précédent, pas hors de l'app.
  useEffect(() => {
    if (typeof window === 'undefined') return
    const sync = () => {
      const entry = fromHash()
      if (entry) set({ screen: entry.screen, phase: entry.phase, sheet: null })
    }
    window.addEventListener('popstate', sync)
    return () => window.removeEventListener('popstate', sync)
  }, [set])

  useEffect(() => {
    try {
      localStorage.setItem(
        PREFS_KEY,
        JSON.stringify({ dark: s.dark, muted: s.muted, lang: s.lang }),
      )
    } catch {
      /* stockage indisponible */
    }
  }, [s.dark, s.muted, s.lang])

  // ----------------------------------------------------------------
  // Chargement initial
  // ----------------------------------------------------------------

  const loadMore = useCallback(async () => {
    if (fetching.current) return
    fetching.current = true
    try {
      const batch = await api.feed(5)
      setDeck((prev) => {
        const seen = new Set(prev.map((e) => e.id))
        return [...prev, ...batch.filter((e) => !seen.has(e.id))]
      })
      setOffline(false)
    } catch {
      setOffline(true)
    } finally {
      fetching.current = false
    }
  }, [])

  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const me = await api.start(live.current.lang)
        if (!alive) return
        setUser(me)
        set({ muted: me.muted, lang: me.lang, ...(me.dark === null ? {} : { dark: me.dark }) })
        const [feed, cats] = await Promise.all([api.feed(5), api.categories()])
        if (!alive) return
        setDeck(feed)
        setCategories(cats)
        setOffline(false)
      } catch {
        if (alive) setOffline(true)
      } finally {
        if (alive) setReady(true)
      }
    })()
    return () => {
      alive = false
    }
  }, [set])

  // Précharge quand il ne reste que deux cartes : au-delà on gaspillerait
  // de la data pour des exercices peut-être jamais atteints.
  useEffect(() => {
    if (ready && deck.length > 0 && s.i >= deck.length - 2) void loadMore()
  }, [ready, s.i, deck.length, loadMore])

  const exo = deck[s.i] ? adapt(deck[s.i], s.lang) : null

  // ----------------------------------------------------------------
  // Machine de phases
  // ----------------------------------------------------------------

  const setPhase = useCallback(
    (phase: Phase) => {
      phaseStart.current = performance.now()
      ended.current = false
      set({ phase, prog: 0 })
    },
    [set],
  )

  const next = useCallback(() => {
    const cur = live.current
    if (BLOCKING_LOADER && cur.phase === 'q' && cur.prog < 1) return
    set((prev) => ({
      i: Math.min(prev.i + 1, Math.max(0, liveDeck.current.length - 1) + 1),
      ...NO_ANSWER,
      hint: false,
      screen: 'exo',
    }))
    setPhase('q')
  }, [set, setPhase])

  const prev = useCallback(() => {
    set((p) => ({ i: Math.max(0, p.i - 1), ...NO_ANSWER, screen: 'exo' }))
    setPhase('q')
  }, [set, setPhase])

  const endPhase = useCallback(() => {
    if (ended.current) return
    ended.current = true
    const phase = live.current.phase
    if (phase === 'ok' || phase === 'ko') {
      setPhase('exp')
      play('exp', live.current.muted)
    } else if (phase === 'exp') {
      next()
    }
  }, [next, setPhase])

  useEffect(() => {
    let raf = 0
    const tick = () => {
      raf = requestAnimationFrame(tick)
      const cur = live.current
      if (cur.screen !== 'exo') return
      const total = DURATIONS[cur.phase] * PACE
      const p = Math.min(1, (performance.now() - phaseStart.current) / total)
      if (Math.abs(p - cur.prog) > 0.004 || (p === 1 && cur.prog !== 1)) set({ prog: p })
      if (p >= 1) endPhase()
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [endPhase, set])

  const answer = useCallback(
    (index: number) => {
      const cur = live.current
      const card = liveDeck.current[cur.i]
      if (cur.chosen !== null || !card) return
      unlock()

      // Retour immédiat : la bonne réponse est déjà dans la charge du feed.
      // L'enregistrement part en arrière-plan — l'app ne doit jamais
      // attendre le réseau pour féliciter.
      const good = index === card.correct_index
      set((p) => ({
        chosen: index,
        win: p.win + (good ? 1 : 0),
        fail: p.fail + (good ? 0 : 1),
        streak: good ? p.streak + 1 : 0,
        hint: false,
      }))
      play(good ? 'ok' : 'ko', cur.muted)
      setPhase(good ? 'ok' : 'ko')

      const ms = Math.round(performance.now() - answeredAt.current)
      void api
        .attempt(card.id, index, ms)
        .then((r) => set({ win: r.win, fail: r.fail, streak: r.streak }))
        .catch(() => setOffline(true))
    },
    [set, setPhase],
  )

  // Un exercice quitté sans réponse est consigné : c'est ce qui nourrit
  // l'anti-répétition côté serveur.
  const lastSkipped = useRef<number | null>(null)
  useEffect(() => {
    const card = liveDeck.current[s.i]
    answeredAt.current = performance.now()
    return () => {
      const cur = live.current
      if (card && cur.chosen === null && lastSkipped.current !== card.id) {
        lastSkipped.current = card.id
        void api.attempt(card.id, null).catch(() => undefined)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.i])

  const go = useCallback(
    (screen: Screen, phase?: Phase) => {
      if (screen !== 'exo') {
        set({ screen, sheet: null })
        return
      }
      const cur = live.current
      const card = liveDeck.current[cur.i]
      let chosen: number | null = null
      if (card) {
        if (phase === 'ko') chosen = (card.correct_index + 1) % card.options.length
        else if (phase === 'ok' || phase === 'exp') chosen = card.correct_index
      }
      set({ screen: 'exo', sheet: null, ...NO_ANSWER, chosen, hint: false })
      setPhase(phase ?? 'q')
    },
    [set, setPhase],
  )

  // ----------------------------------------------------------------
  // Données par écran, chargées à l'ouverture
  // ----------------------------------------------------------------

  useEffect(() => {
    if (!ready) return
    // « Mes thèmes » porte désormais la liste et la progression, mais
    // les réglages en gardent le décompte : les deux écrans ont besoin
    // des mêmes données. Oublier 'themes' ici laissait la page vide sur
    // un lien direct — elle ne se remplissait qu'en passant par les
    // réglages, qui avaient chargé pour elle.
    if (s.screen === 'settings' || s.screen === 'themes') {
      void api.progression().then(setProgression).catch(() => undefined)
      void api.themes().then(setThemes).catch(() => undefined)
    }
    if (s.screen === 'rank') {
      if (s.tab === 'forces') {
        void api.progression().then(setProgression).catch(() => undefined)
      } else {
        // La maquette pose un sélecteur de thème à côté du classement :
        // 0 = tous thèmes confondus, sinon le classement de ce thème.
        const call = s.rankTheme ? api.rankTheme(s.rankTheme) : api.rankGlobal()
        void call.then(setRankRows).catch(() => undefined)
        void api.themes().then(setThemes).catch(() => undefined)
      }
    }
    if (s.screen === 'rankOne' && exo) {
      void api.rankTheme(exo.themeId).then(setRankRows).catch(() => undefined)
    }
    if (s.screen === 'picker' || s.screen === 'picker2' || s.screen === 'onb2' || s.screen === 'onb3') {
      void api.themes().then(setThemes).catch(() => undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, s.screen, s.tab, s.rankTheme])

  useEffect(() => {
    if (s.sheet === 'comments' && exo) {
      void api.comments(exo.id).then(setComments).catch(() => undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.sheet])

  // ----------------------------------------------------------------
  // Actions
  // ----------------------------------------------------------------

  const patchCard = useCallback((updated: ApiExercise) => {
    setDeck((prev) => prev.map((e) => (e.id === updated.id ? updated : e)))
  }, [])

  /**
   * Revoter la même chose retire le vote : c'est le comportement attendu
   * d'un pouce, et se dédire doit être aussi simple que voter.
   */
  const vote = useCallback(
    (value: -1 | 1) => {
      const card = liveDeck.current[live.current.i]
      if (!card) return
      const next = card.my_vote === value ? 0 : value

      // Bascule optimiste : le pouce réagit au doigt, pas au réseau.
      patchCard({
        ...card,
        my_vote: next,
        up_count:
          card.up_count - (card.my_vote === 1 ? 1 : 0) + (next === 1 ? 1 : 0),
        down_count:
          card.down_count - (card.my_vote === -1 ? 1 : 0) + (next === -1 ? 1 : 0),
      })
      void api
        .vote(card.id, next)
        .then(patchCard)
        .catch(() => patchCard(card))
    },
    [patchCard],
  )

  const toggleSubscribe = useCallback((themeId: number) => {
    setThemes((prev) =>
      prev.map((t) => (t.id === themeId ? { ...t, subscribed: !t.subscribed } : t)),
    )
    const target = themes.find((t) => t.id === themeId)
    const call = target?.subscribed ? api.unsubscribe : api.subscribe
    void call(themeId)
      .then((t) => setThemes((prev) => prev.map((x) => (x.id === t.id ? t : x))))
      .catch(() => undefined)
  }, [themes])

  const sendComment = useCallback(
    (body: string) => {
      const card = liveDeck.current[live.current.i]
      if (!card || !body.trim()) return
      void api
        .addComment(card.id, body.trim())
        .then((c) => setComments((prev) => [c, ...prev]))
        .catch(() => undefined)
    },
    [],
  )

  /**
   * Changer de langue change le catalogue, pas seulement les libellés :
   * on vide le deck et on redemande un feed dans la nouvelle langue.
   */
  const setLang = useCallback(
    (lang: Lang) => {
      set({ lang, i: 0, ...NO_ANSWER, prog: 0, phase: 'q' })
      setDeck([])
      void api
        .saveSettings({ lang })
        .then(() => Promise.all([api.feed(5), api.categories(), api.themes()]))
        .then(([feed, cats, ths]) => {
          setDeck(feed)
          setCategories(cats)
          setThemes(ths)
        })
        .catch(() => setOffline(true))
    },
    [set],
  )

  const toggleDark = useCallback(() => {
    set((p) => {
      void api.saveSettings({ dark: !p.dark }).catch(() => undefined)
      return { dark: !p.dark }
    })
  }, [set])

  const toggleMute = useCallback(() => {
    unlock()
    set((p) => {
      void api.saveSettings({ muted: !p.muted }).catch(() => undefined)
      return { muted: !p.muted }
    })
  }, [set])

  /**
   * Tout ce qui dépend de QUI est connecté. Abonnements, progression et
   * compteurs appartiennent au compte : après une connexion — qui
   * fusionne la session anonyme — comme après une déconnexion, les
   * garder à l'écran afficherait les chiffres de quelqu'un d'autre.
   */
  const reloadSession = useCallback(async () => {
    set({ i: 0, ...NO_ANSWER, prog: 0, phase: 'q', win: 0, fail: 0, streak: 0 })
    setDeck([])
    setThemes([])
    setProgression([])
    try {
      const [feed, cats, ths] = await Promise.all([api.feed(5), api.categories(), api.themes()])
      setDeck(feed)
      setCategories(cats)
      setThemes(ths)
      setOffline(false)
    } catch {
      setOffline(true)
    }
  }, [set])

  const submitAuth = useCallback(
    async (email: string, password: string, lang?: Lang) => {
      const mode = live.current.authMode
      try {
        const me =
          mode === 'signup'
            ? await api.signup(email, password, lang ?? live.current.lang)
            : await api.login(email, password)
        setUser(me)
        // La langue du compte fait foi : à la connexion elle peut différer
        // de celle choisie sur cet appareil, et c'est elle qui décide du
        // catalogue rechargé juste après.
        set({
          authError: null,
          muted: me.muted,
          lang: me.lang,
          ...(me.dark === null ? {} : { dark: me.dark }),
        })
        await reloadSession()
        return true
      } catch (err) {
        set({
          authError:
            err instanceof Error ? err.message : "La connexion n'a pas abouti.",
        })
        return false
      }
    },
    [set, reloadSession],
  )

  /**
   * Déconnexion : on retombe sur une session anonyme, jamais sur un
   * écran vide. L'app doit rester jouable — c'est sa promesse d'entrée.
   */
  const logout = useCallback(async () => {
    try {
      const me = await api.logout(live.current.lang)
      setUser(me)
      set({ screen: 'settings', sheet: null, authError: null })
      await reloadSession()
      return true
    } catch {
      setOffline(true)
      return false
    }
  }, [set, reloadSession])

  const goCreate = useCallback(
    (step: number) => set({ screen: 'create', createStep: step, sheet: null, genLoading: false }),
    [set],
  )

  const toastTimer = useRef<number>()
  const pollTimer = useRef<number>()

  /** Étape 1 : le dépôt crée le thème côté serveur, en privé. */
  const createDraft = useCallback(async () => {
    const cur = live.current
    if (cur.draftThemeId) return true
    try {
      const theme = await api.createTheme({
        title: cur.draftTitle.trim() || 'Nouveau thème',
        category_id: cur.draftCategoryId || 1,
        sub_category_id: cur.draftSubCategoryId,
        description: cur.draftDescription || null,
        source_markdown: cur.draftMarkdown || null,
        tags: cur.draftTags,
      })
      set({ draftThemeId: theme.id, genError: null })
      return true
    } catch (err) {
      set({ genError: err instanceof Error ? err.message : 'Création impossible.' })
      return false
    }
  }, [set])

  /** Étape 3 : lancement réel, puis suivi jusqu'à la fin des rédactions. */
  const startGeneration = useCallback(
    async (types: string[], blooms: string[], count: number) => {
      const themeId = live.current.draftThemeId
      if (!themeId) return
      set({ screen: 'create', createStep: 4, genLoading: true, toast: false, genError: null })
      try {
        await api.generate(themeId, types, blooms, count)
      } catch (err) {
        set({
          genLoading: false,
          genError: err instanceof Error ? err.message : 'La génération a échoué.',
        })
        return
      }

      const poll = async () => {
        try {
          const st = await api.generationStatus(themeId)
          const drafts = await api.themeExercises(themeId, 'draft')
          setDraftExercises(drafts)
          if (st.running) {
            pollTimer.current = window.setTimeout(() => void poll(), 3000)
            return
          }
          set({ genLoading: false, toast: drafts.length > 0, genCount: st.produced })
          if (drafts.length === 0) {
            set({ genError: "Le modèle n'a rien produit d'exploitable. Réessaie." })
          }
          window.clearTimeout(toastTimer.current)
          toastTimer.current = window.setTimeout(() => set({ toast: false }), 3200)
        } catch {
          set({ genLoading: false, genError: 'Le suivi de génération a été interrompu.' })
        }
      }
      pollTimer.current = window.setTimeout(() => void poll(), 2000)
    },
    [set],
  )

  /** Étape 4 : valider ou écarter, un par un. */
  const reviewExercise = useCallback(
    (id: number, state: 'validated' | 'rejected') => {
      setDraftExercises((prev) => prev.filter((e) => e.id !== id))
      if (state === 'validated') set((p) => ({ validated: p.validated + 1 }))
      void api.patchExercise(id, { state }).catch(() => undefined)
    },
    [set],
  )

  const publishDraft = useCallback(
    async (isPublic: boolean) => {
      const themeId = live.current.draftThemeId
      if (!themeId) return
      try {
        await api.publish(themeId, isPublic)
        set({ published: true })
        const fresh = await api.themes()
        setThemes(fresh)
      } catch (err) {
        set({ genError: err instanceof Error ? err.message : 'Publication impossible.' })
      }
    },
    [set],
  )

  // Conservé pour le bouton « Générer » de la maquette, qui déclenche
  // le lancement avec les types cochés.
  const generate = useCallback(() => {
    const cur = live.current
    const types = ['qcm', 'find_error', 'true_false', 'complete', 'reorder'].filter(
      (_, i) => cur.typesOn[i],
    )
    void startGeneration(types.length ? types : ['qcm'], ['remember', 'understand'], cur.genCount)
  }, [startGeneration])

  useEffect(
    () => () => {
      window.clearTimeout(toastTimer.current)
      window.clearTimeout(pollTimer.current)
    },
    [],
  )

  const toggleFlag = useCallback<Store['toggleFlag']>(
    (key, id) => set((p) => ({ [key]: { ...p[key], [id]: !p[key][id] } }) as Partial<State>),
    [set],
  )

  const hideFlag = useCallback<Store['hideFlag']>(
    (key, id) => set((p) => ({ [key]: { ...p[key], [id]: true } }) as Partial<State>),
    [set],
  )

  const card = deck[s.i] ?? null
  const subscribedIds = useMemo(
    () => new Set(themes.filter((t) => t.subscribed).map((t) => t.id)),
    [themes],
  )

  const value = useMemo<Store>(
    () => ({
      s,
      exo,
      deckSize: deck.length,
      ready,
      offline,
      user,
      categories,
      themes,
      progression,
      rankRows,
      comments,
      revealed: s.chosen !== null,
      set,
      toggleFlag,
      hideFlag,
      answer,
      next,
      prev,
      go,
      goCreate,
      generate,
      t: dict(s.lang),
      setLang,
      toggleDark,
      toggleMute,
      vote,
      myVote: card?.my_vote ?? null,
      upCount: card?.up_count ?? 0,
      downCount: card?.down_count ?? 0,
      commentCount: card?.comment_count ?? 0,
      subscribedIds,
      toggleSubscribe,
      sendComment,
      submitAuth,
      logout,
      draftExercises,
      createDraft,
      startGeneration,
      reviewExercise,
      publishDraft,
    }),
    [
      s, exo, deck.length, ready, offline, user, categories, themes, progression,
      rankRows, comments, set, toggleFlag, hideFlag, answer, next, prev, go,
      goCreate, generate, setLang, toggleDark, toggleMute, vote, card, subscribedIds,
      toggleSubscribe, sendComment, submitAuth, logout, draftExercises, createDraft,
      startGeneration, reviewExercise, publishDraft,
    ],
  )

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}

export function useStore(): Store {
  const store = useContext(StoreContext)
  if (!store) throw new Error('useStore doit être appelé dans un <StoreProvider>')
  return store
}
