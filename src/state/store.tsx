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
import { AUTO_ADVANCE, BLOCKING_LOADER, PACE } from '../config'
import { DURATIONS, type Exercise, type ExerciseType } from '../data/content'
import { dict, defaultLang, type Lang } from '../i18n'
import { readingMs, spokenText } from '../lib/spoken'
import { play, unlock } from '../lib/audio'
import {
  api,
  type ApiCategory,
  type ApiComment,
  type ApiExercise,
  type ApiKnowledge,
  type ApiOption,
  type ApiStep,
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
  /** L'accueil public : ce que voit quelqu'un qui n'est pas encore entré. */
  | 'home'
  /** Ce que je partage — la liste de mes connaissances publiées. */
  | 'shared'
  /** Le détail d'une connaissance partagée. */
  | 'sharedOne'
  /** Nous écrire : formulaire de contact et questions fréquentes. */
  | 'contact'
  /** Le pseudo, exigé avant le premier exercice — sauf si on a un compte. */
  | 'pseudo'

export type Phase = 'q' | 'ok' | 'ko' | 'exp'
export type Sheet = 'theme' | 'comments' | 'myTheme' | null



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
  /** Le photographe, son profil, et la banque d'où vient la photo —
   *  affichés sous elle. Les trois banques exigent d'être nommées, et
   *  `imageSource` est le seul moyen de savoir laquelle : l'URL ne le dit
   *  pas, celle de Pixabay étant rapatriée chez nous. Nuls pour un
   *  pictogramme, qui n'a rien à créditer. */
  imageCredit: string | null
  imageCreditUrl: string | null
  imageSource: string | null
  typeQuestion: ApiExercise['type_question']
  /**
   * Les options entières. `options` n'en garde que les libellés, ce qui
   * suffit à un QCM mais perd `blank` et `correct` — les deux champs
   * dont un texte à trous a besoin.
   */
  opts: ApiOption[]
  /**
   * L'explication découpée, une étape par image.
   *
   * Le découpage vient de l'API, PAS DU FRONT. Il le faisait lui-même,
   * phrase par phrase, dans chaque langue séparément : 14 cartes sur 261
   * n'avaient alors pas le même nombre d'étapes en français et en
   * anglais, et l'image d'une étape s'y serait décalée. Le rang est
   * désormais figé en base.
   *
   * Vide sur un serveur d'avant la migration 032 — l'explication
   * s'affiche alors d'un bloc, comme avant.
   */
  steps: ApiStep[]
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
    imageCredit: e.image_credit,
    imageCreditUrl: e.image_credit_url,
    imageSource: e.image_source,
    options: e.options.map((o) => o.label),
    correct: e.correct_index,
    okTitle: e.ok_title ?? 'Bien vu.',
    okLine: e.ok_line ?? '',
    koTitle: e.ko_title ?? 'Presque.',
    koLine: e.ko_line ?? '',
    expTitle: e.exp_title ?? '',
    expText: e.exp_text,
    steps: e.steps ?? [],
  }
}

type Flags = Record<string | number, boolean>

interface State {
  dark: boolean
  muted: boolean
  lang: Lang
  screen: Screen
  phase: Phase
  /**
   * L'étape de l'explication qu'on lit. Remise à zéro à chaque
   * changement de phase et de carte — une explication commence toujours
   * par son premier pas.
   */
  step: number
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
  /** Vrai quand on a été emmené au catalogue faute d'abonnement. */
  sentToPicker: boolean
  typesOn: Flags
  tagsOff: Flags
  validated: number
  authMode: 'signup' | 'login'
  pubPublic: boolean
  published: boolean
  authError: string | null
  /** Le thème en cours de création, une fois déposé côté serveur. */
  draftThemeId: number | null
  draftTitle: string
  draftDescription: string
  draftMarkdown: string
  draftTags: string[]
  draftCategoryId: number
  genError: string | null
  /**
   * Le sujet écrit par l'auteur — « les fonctions PHP ». Une phrase, pas
   * un cours : c'est le modèle qui écrira la présentation et le
   * programme à partir de là.
   */
  subject: string
  /**
   * La connaissance proposée, telle qu'elle est en base. Elle y est déjà
   * quand elle arrive ici : l'écran ne fait que la relire, ce qui permet
   * de reprendre une création interrompue.
   */
  knowledge: ApiKnowledge | null
  /** Un appel au modèle est en cours — présentation ou prompts. */
  thinking: boolean
  /**
   * Le rail desktop, déployé ou replié. Il vit dans l'état plutôt que
   * dans le composant parce que la préférence traverse les écrans :
   * replier le rail sur les exercices doit le laisser replié dans les
   * réglages.
   */
  railOpen: boolean
  /** La connaissance partagée qu'on regarde en détail. */
  sharedThemeId: number | null
  /**
   * Le pseudo. Il ne sert qu'à l'affichage — classement et commentaires
   * — et n'ouvre rien : ce qui authentifie reste le jeton. Mais il est
   * devenu obligatoire pour entrer dans le flux, à moins d'avoir un
   * compte : voir la garde `named || registered` plus bas.
   */
  pseudo: string
  /**
   * Le quiz sur lequel le flux est fermé, ouvert par un code de partage.
   * `null` = le flux normal. Il ne s'enregistre nulle part : on entre
   * par un lien, on en sort en le quittant.
   */
  code: string | null
  codeTitle: string
  /**
   * Le quiz partagé est épuisé : le serveur ne rend plus rien de neuf.
   * Un quiz de quatre questions y arrive en quatre swipes, et l'app
   * affichait alors « on prépare tes exercices… » — un mensonge, il n'y
   * a rien à préparer. On le dit, et on propose de recommencer.
   */
  codeDone: boolean
  /**
   * Ce qu'on voulait faire avant d'être renvoyé vers l'inscription.
   * `'create'` y ramène une fois le compte créé, sinon on rendrait le
   * compte pour rien et il faudrait retrouver le bouton soi-même.
   */
  afterAuth: 'create' | null
  /**
   * L'apprentissage dont la feuille d'auteur est ouverte.
   *
   * Séparé de `sharedThemeId` : celui-là commande un ÉCRAN, celui-ci une
   * feuille par-dessus l'écran courant. Les confondre ferait naviguer la
   * page derrière la feuille au moment de l'ouvrir.
   */
  sheetThemeId: number | null
}

/**
 * Le code de partage lu dans l'adresse — `?code=K7F2QM`.
 *
 * En paramètre de requête et non dans le fragment : le fragment porte
 * déjà l'écran (`#exercise`), et le store le réécrit à chaque
 * navigation. Le `search`, lui, est conservé tel quel (voir le
 * `pushState` plus bas), donc le code survit au passage d'un écran à
 * l'autre sans qu'on ait à le porter.
 */
function codeFromUrl(): string | null {
  if (typeof window === 'undefined') return null
  const raw = new URLSearchParams(window.location.search).get('code')
  return raw && raw.trim() ? raw.trim().toUpperCase() : null
}

const PREFS_KEY = 'sara.prefs'

function readPrefs(): {
  dark: boolean
  muted: boolean
  lang: Lang
  pseudo: string
} {
  const fallback = {
    dark:
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches,
    muted: false,
    lang: defaultLang(),
    pseudo: '',
  }
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (!raw) return fallback
    const parsed = JSON.parse(raw) as Partial<typeof fallback>
    return {
      dark: typeof parsed.dark === 'boolean' ? parsed.dark : fallback.dark,
      muted: typeof parsed.muted === 'boolean' ? parsed.muted : fallback.muted,
      lang: parsed.lang === 'en' || parsed.lang === 'fr' ? parsed.lang : fallback.lang,
      pseudo: typeof parsed.pseudo === 'string' ? parsed.pseudo : fallback.pseudo,
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
  onb2: 'discover',
  onb3: 'refine',
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
  home: 'home',
  shared: 'shared',
  sharedOne: 'shared-one',
  contact: 'contact',
  pseudo: 'name',
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
    pseudo: prefs.pseudo,
    code: codeFromUrl(),
    codeTitle: '',
    codeDone: false,
    afterAuth: null,
    screen: entry?.screen ?? 'exo',
    phase: entry?.phase ?? 'q',
    step: 0,
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
    sentToPicker: false,
    typesOn: { 0: true, 1: true },
    tagsOff: {},
    validated: 0,
    authMode: 'signup',
    pubPublic: false,
    published: false,
    authError: null,
    draftThemeId: null,
    draftTitle: '',
    draftDescription: '',
    draftMarkdown: '',
    draftTags: [],
    draftCategoryId: 0,
    genError: null,
    subject: '',
    knowledge: null,
    thinking: false,
    railOpen: false,
    sharedThemeId: null,
    sheetThemeId: null,
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
  /**
   * Les apprentissages dont je suis l'auteur. Ils viennent d'un appel
   * distinct (`?mine=true`) et vivent à côté du catalogue : « ce que je
   * partage » et « ce que je peux suivre » ne sont pas la même liste,
   * et filtrer l'une pour obtenir l'autre raterait mes brouillons
   * privés, que le catalogue public ne sert pas.
   */
  myThemes: ApiTheme[]
  sharedExercises: ApiExercise[]
  /** Le programme de l'apprentissage montré dans la feuille d'auteur. */
  sheetKnowledge: ApiKnowledge | null
  sheetLoading: boolean
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
  /** Quitte le quiz ouvert par un code de partage. */
  leaveCode: () => void
  /** Rejoue depuis le début le quiz ouvert par un code. */
  restartCode: () => void
  /** Passe à la phase suivante, à la demande. */
  advance: () => void
  /** Passe à l'étape suivante de l'explication depuis le rang donné.
   *  Le rang sert de garde : deux sources avancent l'écran — la voix et
   *  le minuteur — et la seconde arrivée ne doit rien faire. */
  avancerEtape: (depuis: number) => void
  /** Va droit à une étape : les pastilles de l'explication. */
  allerEtape: (rang: number) => void
  /** Rouvre la relecture d'un apprentissage déjà généré. */
  resumeDraft: (themeId: number) => Promise<void>
  /** Pose le pseudo — en base et en local. */
  setPseudo: (name: string) => void
  /** Entre dans le flux, en demandant le pseudo une seule fois. */
  enterFeed: () => void
  /** Ouvre la feuille d'auteur sur un apprentissage que j'ai créé. */
  openMyTheme: (themeId: number) => void
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
  /** Étape 1 : le sujet part au modèle, la connaissance revient. */
  proposeKnowledge: () => Promise<boolean>
  /** Étape 3 : la rédaction d'un prompt par chapitre, puis le suivi. */
  writePrompts: (force?: boolean) => Promise<boolean>
  generateFromChapters: () => Promise<void>
  /** Prépare les questions puis écrit les exercices, d'un seul geste. */
  startWriting: () => Promise<void>
  reviewChapter: (
    id: number,
    patch: Parameters<typeof api.patchChapter>[1],
  ) => Promise<void>
  createDraft: () => Promise<boolean>
  syncDraft: () => Promise<void>
  reviewExercise: (id: number, state: 'validated' | 'rejected') => void
  validateAll: () => void
  publishDraft: (isPublic: boolean) => Promise<void>
}

const StoreContext = createContext<Store | null>(null)

export function StoreProvider({ children }: { children: ReactNode }) {
  const [s, setS] = useState<State>(initialState)
  const [deck, setDeck] = useState<ApiExercise[]>([])
  const [user, setUser] = useState<ApiUser | null>(null)
  const [categories, setCategories] = useState<ApiCategory[]>([])
  const [themes, setThemes] = useState<ApiTheme[]>([])
  const [myThemes, setMyThemes] = useState<ApiTheme[]>([])
  const [sharedExercises, setSharedExercises] = useState<ApiExercise[]>([])
  // Le programme de l'apprentissage dont la feuille d'auteur est
  // ouverte. Distinct de `s.knowledge`, qui appartient à l'écran de
  // création : ouvrir une fiche depuis la liste ne doit pas écraser une
  // création en cours.
  const [sheetKnowledge, setSheetKnowledge] = useState<ApiKnowledge | null>(null)
  const [sheetLoading, setSheetLoading] = useState(false)
  const [progression, setProgression] = useState<ApiProgress[]>([])
  const [rankRows, setRankRows] = useState<ApiRankRow[]>([])
  const [comments, setComments] = useState<ApiComment[]>([])
  const [draftExercises, setDraftExercises] = useState<ApiExercise[]>([])
  // Lue hors du rendu par la validation groupée, comme `liveDeck` l'est
  // par la boucle d'animation.
  const liveDrafts = useRef(draftExercises)
  liveDrafts.current = draftExercises
  const [ready, setReady] = useState(false)
  const [offline, setOffline] = useState(false)
  /** Le rang de la prochaine tentative quand le flux est vide. */
  const [attente, setAttente] = useState(0)

  const phaseStart = useRef<number>(performance.now())
  const ended = useRef(false)
  const answeredAt = useRef<number>(performance.now())
  const live = useRef(s)
  live.current = s
  const liveDeck = useRef(deck)
  liveDeck.current = deck
  const fetching = useRef(false)
  /**
   * Les abonnements ont changé pendant qu'on était ailleurs — le flux
   * chargé d'avance ne les reflète plus. Voir `toggleSubscribe` et
   * l'effet qui le consomme au retour sur le flux.
   */
  const deckStale = useRef(false)

  const set = useCallback<Store['set']>((patch) => {
    setS((prev) => ({ ...prev, ...(typeof patch === 'function' ? patch(prev) : patch) }))
  }, [])

  /**
   * Le renvoi vers le catalogue remplace l'adresse au lieu de l'empiler
   * (voir l'effet qui suit celui-ci). Sans ça, le Précédent ramenait au
   * flux, que le renvoi renvoyait aussitôt au catalogue : le bouton
   * n'avançait plus.
   */
  const replaceRoute = useRef(false)

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
    const replace = replaceRoute.current
    replaceRoute.current = false
    const next = routeOf(s.screen, s.phase)
    if (window.location.hash === next) return
    const url = window.location.pathname + window.location.search + next
    if (replace || (s.screen === 'exo' && s.phase !== 'q')) {
      window.history.replaceState(null, '', url)
    } else {
      window.history.pushState(null, '', url)
    }
  }, [s.screen, s.phase])

  /**
   * Sans aucun apprentissage suivi, le flux n'est pas un choix : il sert
   * « un peu de tout », et l'écran ne dit pas comment en sortir. On
   * emmène donc au catalogue, où l'on choisit.
   *
   * Trois gardes, chacune pour un cas qui cassait :
   *   · `themes` vide, c'est le catalogue pas encore chargé — sans quoi
   *     tout le monde partait au catalogue le temps d'une requête ;
   *   · un quiz ouvert par code se joue sans abonnement, le détourner
   *     serait fermer la porte par laquelle on vient d'entrer ;
   *   · un catalogue sans un seul thème n'a rien à faire choisir.
   */
  useEffect(() => {
    if (!ready || s.screen !== 'exo' || s.code) return
    if (themes.length === 0 || themes.some((x) => x.subscribed)) return
    replaceRoute.current = true
    set({ screen: 'picker', sheet: null, sentToPicker: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, s.screen, s.code, themes, set])

  /**
   * Pas d'exercice sans nom.
   *
   * Un exercice compte : il alimente le classement, il autorise un
   * commentaire, il nourrit la progression. Tout cela s'affiche sous un
   * nom, et une ligne « Joueur 412 » en tête du classement n'apprend
   * rien à personne. On demande donc de quoi se reconnaître avant la
   * première question — un pseudo, ou un compte, ou les deux.
   *
   * Le compte suffit sans pseudo : il porte déjà un e-mail, et une
   * identité vérifiée vaut mieux qu'une étiquette libre.
   *
   * La garde est ici, dans un effet sur l'écran, et non dans les mains
   * qui y mènent : on entre dans le flux par le rail, par la marque de
   * la barre, par un `Précédent`, par « retour aux exercices », par un
   * lien collé, par un rechargement. Poser la règle sur chacune, c'est
   * l'oublier sur la prochaine.
   *
   * Elle vient APRÈS le renvoi au catalogue pour gagner sur lui quand
   * les deux s'appliquent : on dit qui l'on est, puis on choisit ce
   * qu'on apprend, puis on apprend.
   */
  useEffect(() => {
    if (!ready || s.screen !== 'exo') return
    const named = Boolean(s.pseudo || user?.display_name)
    const registered = Boolean(user && !user.is_anonymous)
    if (named || registered) return
    replaceRoute.current = true
    set({ screen: 'pseudo', sheet: null })
  }, [ready, s.screen, s.pseudo, user, set])

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
        JSON.stringify({
          dark: s.dark,
          muted: s.muted,
          lang: s.lang,
          pseudo: s.pseudo,
        }),
      )
    } catch {
      /* stockage indisponible */
    }
  }, [s.dark, s.muted, s.lang, s.pseudo])

  // Le nom du quiz ouvert par un code, pour que le bandeau dise sur quoi
  // on est. Une requête, au montage seulement : le code ne change pas
  // pendant une session, on en sort, on n'en change pas.
  useEffect(() => {
    if (!s.code || s.codeTitle) return
    void api
      .themeByCode(s.code)
      .then((th) => set({ codeTitle: th.title }))
      .catch(() => set({ code: null, codeTitle: '' }))
  }, [s.code, s.codeTitle, set])

  // ----------------------------------------------------------------
  // Chargement initial
  // ----------------------------------------------------------------

  const loadMore = useCallback(async () => {
    if (fetching.current) return
    fetching.current = true
    try {
      const batch = await api.feed(5, live.current.code)
      let added = 0
      setDeck((prev) => {
        const seen = new Set(prev.map((e) => e.id))
        const fresh = batch.filter((e) => !seen.has(e.id))
        added = fresh.length
        return [...prev, ...fresh]
      })
      // La déduplication est juste pour un flux sans fin : elle évite de
      // reposer la même carte deux fois dans un long défilement. Sur un
      // quiz fermé par un code, elle finit par tout écarter — le serveur
      // ressert les mêmes questions parce qu'il n'en a pas d'autres — et
      // le deck cessait de grandir sans que rien ne le dise.
      if (live.current.code) set({ codeDone: added === 0 })
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
        // `allSettled` et pas `all` : le feed et la taxonomie ne
        // dépendent pas l'un de l'autre, et les lier faisait tomber les
        // deux ensemble. Un feed en panne a laissé les catégories à zéro
        // alors que `/categories` répondait — le sélecteur affichait une
        // colonne vide et « aucun apprentissage » sur un catalogue de 35.
        const [feed, cats] = await Promise.allSettled([
          api.feed(5, live.current.code),
          api.categories(),
        ])
        if (!alive) return
        if (feed.status === 'fulfilled') setDeck(feed.value)
        if (cats.status === 'fulfilled') setCategories(cats.value)
        // Hors ligne se juge sur le feed : c'est lui qui porte l'écran
        // principal. La taxonomie manquante dégrade le sélecteur, elle
        // n'interrompt pas la session.
        setOffline(feed.status === 'rejected')
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

  /**
   * Le flux est vide : on redemande, tout seul.
   *
   * Il n'y avait AUCUN chemin de retour. Le flux se recharge au
   * démarrage, au changement d'abonnements, et deux cartes avant la fin
   * — cette dernière condition demandant un deck non vide. Un deck vide
   * était donc définitif : une API qui repart, un apprentissage dont les
   * questions viennent d'être écrites, rien ne les faisait apparaître.
   * Il fallait recharger la page à la main, et sur desktop même le
   * bouton pour le faire manquait.
   *
   * Le délai grandit — cinq secondes, puis dix, jusqu'à trente : une
   * panne longue ne doit pas se payer en requêtes toutes les cinq
   * secondes pendant des heures. `loadMore` se garde lui-même des appels
   * qui se chevauchent, donc une écriture de trente secondes en cours
   * n'est jamais doublée.
   */
  useEffect(() => {
    if (deck.length > 0 && attente !== 0) setAttente(0)
  }, [deck.length, attente])

  useEffect(() => {
    if (!ready || s.screen !== 'exo' || deck.length > 0 || s.codeDone) return
    const delai = Math.min(30000, 5000 * (attente + 1))
    const id = window.setTimeout(() => {
      void loadMore().then(() => setAttente((n) => n + 1))
    }, delai)
    return () => window.clearTimeout(id)
  }, [ready, s.screen, s.codeDone, deck.length, attente, loadMore])

  /**
   * Le retour au flux après avoir touché aux abonnements.
   *
   * Le flux est chargé d'avance — cinq cartes, complétées deux avant la
   * fin. Prendre ou lâcher un apprentissage ne le touchait pas : on
   * revenait sur la carte qu'on avait laissée, servie par des
   * abonnements abandonnés depuis. « J'ai ajouté un thème » ne montrait
   * rien de neuf, et « je l'ai retiré » continuait de le servir.
   *
   * On repart donc de la première carte, et non de l'index laissé
   * derrière : après un changement d'abonnements, ce n'est plus le même
   * flux, et reprendre sa place dans celui d'avant n'a pas de sens.
   */
  useEffect(() => {
    if (!ready || s.screen !== 'exo' || !deckStale.current) return
    deckStale.current = false
    set({ i: 0, ...NO_ANSWER, prog: 0, phase: 'q' })
    setDeck([])
    void api
      .feed(5, live.current.code)
      .then(setDeck)
      .catch(() => setOffline(true))
  }, [ready, s.screen, set])

  const exo = deck[s.i] ? adapt(deck[s.i], s.lang) : null
  const liveExo = useRef(exo)
  liveExo.current = exo

  // ----------------------------------------------------------------
  // Machine de phases
  // ----------------------------------------------------------------

  const setPhase = useCallback(
    (phase: Phase) => {
      phaseStart.current = performance.now()
      ended.current = false
      set({ phase, prog: 0, step: 0 })
    },
    [set],
  )

  /**
   * Passer à l'étape suivante de l'explication.
   *
   * `depuis` est le rang d'où l'on part, et c'est un GARDE-FOU, pas une
   * commodité : deux sources font avancer l'écran — la voix qui finit
   * de lire une phrase, et le minuteur qui suit la vitesse de lecture.
   * La première qui arrive gagne ; l'autre se présente ensuite avec un
   * rang périmé et ne fait rien. Sans ça, une étape sautait deux fois.
   */
  const avancerEtape = useCallback(
    (depuis: number) => {
      const cur = live.current
      const etapes = liveExo.current?.steps ?? []
      if (cur.phase !== 'exp' || cur.step !== depuis) return
      if (depuis >= etapes.length - 1) return
      phaseStart.current = performance.now()
      set({ step: depuis + 1, prog: 0 })
    },
    [set],
  )

  /** Revenir sur une étape déjà lue, ou sauter en avant. */
  const allerEtape = useCallback(
    (rang: number) => {
      const etapes = liveExo.current?.steps ?? []
      if (!etapes.length) return
      phaseStart.current = performance.now()
      set({ step: Math.max(0, Math.min(etapes.length - 1, rang)), prog: 0 })
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

  /**
   * La fin d'une phase. Elle ne fait plus avancer par elle-même quand
   * `AUTO_ADVANCE` est faux : la barre se remplit, et on attend un
   * geste. C'est `advance` qui porte la transition, appelée par les
   * boutons — la lecture à voix haute n'est donc plus jamais coupée par
   * un minuteur qui ne l'écoutait pas.
   */
  const endPhase = useCallback(() => {
    if (ended.current) return
    ended.current = true
    if (!AUTO_ADVANCE) return
    const phase = live.current.phase
    if (phase === 'ok' || phase === 'ko') {
      setPhase('exp')
      play('exp', live.current.muted)
    } else if (phase === 'exp') {
      next()
    }
  }, [next, setPhase])

  /**
   * Passer à la suite, à la demande. Depuis la réussite ou l'erreur elle
   * ouvre l'explication ; depuis l'explication elle sert l'exercice
   * suivant. Le swipe vers le haut reste un raccourci vers l'exercice
   * suivant, à tout moment.
   */
  const advance = useCallback(() => {
    const phase = live.current.phase
    if (phase === 'ok' || phase === 'ko') {
      setPhase('exp')
      play('exp', live.current.muted)
    } else {
      next()
    }
  }, [next, setPhase])

  useEffect(() => {
    let raf = 0
    const tick = () => {
      raf = requestAnimationFrame(tick)
      const cur = live.current
      if (cur.screen !== 'exo') return
      // La durée d'une phase est celle de sa lecture, pas un forfait.
      // Les valeurs fixes de `DURATIONS` ont été calibrées sur des
      // questions de grammaire de cinquante caractères ; mesurées au
      // MP3, les questions d'informatique demandent jusqu'à 43 s là où
      // la barre en accordait 3. Elles ne servent plus qu'aux phases
      // sans texte — il n'en reste aucune depuis que la félicitation se
      // lit elle aussi. La barre y suit donc la voix, comme ailleurs,
      // et ne décide de rien : `AUTO_ADVANCE` étant faux, personne ne
      // quitte l'écran à la place du lecteur.
      const lu = readingMs(spokenText(liveExo.current, cur.phase, cur.step))
      const total = (lu || DURATIONS[cur.phase]) * PACE
      const p = Math.min(1, (performance.now() - phaseStart.current) / total)
      if (Math.abs(p - cur.prog) > 0.004 || (p === 1 && cur.prog !== 1)) set({ prog: p })
      if (p < 1) return
      // L'explication n'est pas finie tant qu'il lui reste une étape :
      // la barre repart, l'image change, et personne ne quitte l'écran.
      const etapes = liveExo.current?.steps ?? []
      if (cur.phase === 'exp' && cur.step < etapes.length - 1) {
        avancerEtape(cur.step)
        return
      }
      endPhase()
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [endPhase, set, avancerEtape])

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
    // Le flux a besoin des mêmes données que « mes apprentissages » :
    // la pastille de l'exercice dit « abonné » ou « s'abonner », et le
    // cadre desktop pose une colonne de suggestions à côté de la carte.
    // Sans ce chargement, la pastille affichait « s'abonner » même sur
    // un apprentissage suivi — `themes` était vide.
    // La connexion chiffre ce qu'un compte conserve — apprentissages
    // suivis, exercices réussis, progression locale. Sans ces deux
    // appels, la colonne annonçait « rien pour l'instant » à quelqu'un
    // qui vient de faire trente exercices.
    if (
      s.screen === 'settings' ||
      s.screen === 'themes' ||
      s.screen === 'exo' ||
      s.screen === 'auth'
    ) {
      void api.progression().then(setProgression).catch(() => undefined)
      void api.themes().then(setThemes).catch(() => undefined)
    }
    if (s.screen === 'rank') {
      // Les deux jeux de données sont chargés quel que soit l'onglet : la
      // planche desktop pose la progression ET le classement côte à côte,
      // et n'en charger qu'un laissait la moitié de l'écran vide.
      void api.progression().then(setProgression).catch(() => undefined)
      // La maquette pose un sélecteur de thème à côté du classement :
      // 0 = tous thèmes confondus, sinon le classement de ce thème.
      const call = s.rankTheme ? api.rankTheme(s.rankTheme) : api.rankGlobal()
      void call.then(setRankRows).catch(() => undefined)
      void api.themes().then(setThemes).catch(() => undefined)
    }
    if (s.screen === 'rankOne' && exo) {
      void api.rankTheme(exo.themeId).then(setRankRows).catch(() => undefined)
    }
    if (s.screen === 'picker' || s.screen === 'picker2' || s.screen === 'onb2' || s.screen === 'onb3') {
      void api.themes().then(setThemes).catch(() => undefined)
    }
    // `themes` est le catalogue public : filtrer dessus sur `is_owner`
    // rate les brouillons privés, qui n'y sont pas. L'onglet « Créés par
    // moi » lit donc la même liste que « Ce que je partage ».
    if (s.screen === 'shared' || s.screen === 'sharedOne' || s.screen === 'themes') {
      void api.themes(true).then(setMyThemes).catch(() => undefined)
    }
    if (s.screen === 'sharedOne' && s.sharedThemeId) {
      void api
        .themeExercises(s.sharedThemeId)
        .then(setSharedExercises)
        .catch(() => setSharedExercises([]))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, s.screen, s.tab, s.rankTheme, s.sharedThemeId])

  useEffect(() => {
    if (s.sheet === 'comments' && exo) {
      void api.comments(exo.id).then(setComments).catch(() => undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [s.sheet])

  // Le programme n'est chargé qu'à l'ouverture de la feuille, pas avec
  // la liste : une liste de vingt apprentissages créés ferait vingt
  // appels pour un panneau qu'on n'ouvrira peut-être jamais.
  useEffect(() => {
    if (s.sheet !== 'myTheme' || !s.sheetThemeId) return
    let alive = true
    setSheetLoading(true)
    setSheetKnowledge(null)
    void api
      .knowledge(s.sheetThemeId)
      .then((k) => alive && setSheetKnowledge(k))
      .catch(() => alive && setSheetKnowledge(null))
      .finally(() => alive && setSheetLoading(false))
    return () => {
      alive = false
    }
  }, [s.sheet, s.sheetThemeId])

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
    const target = themes.find((t) => t.id === themeId)
    const suivre = !target?.subscribed
    // La seule ligne cliquée, et c'est exact : l'API prend aussi la
    // descendance CACHÉE du chapitre, mais elle n'a pas de ligne ici. Le
    // catalogue s'arrête à l'étage 1 et l'abonnement ne coche jamais de
    // lui-même une ligne visible — voir `_caches` côté API.
    //
    // Il y avait une propagation ici, du temps où suivre « Optique »
    // cochait la racine « Lumière » : elle peignait une branche que
    // l'abonnement ne prend plus.
    setThemes((prev) =>
      prev.map((t) => (t.id === themeId ? { ...t, subscribed: suivre } : t)),
    )
    const call = suivre ? api.subscribe : api.unsubscribe
    void call(themeId)
      .then((t) => {
        setThemes((prev) => prev.map((x) => (x.id === t.id ? t : x)))

        // Le flux servi ne correspond plus aux abonnements. Deux
        // situations, deux réponses :
        //
        //   · on est SUR le flux — la pastille de la carte, la colonne
        //     de suggestions du desktop. On ne touche pas à ce qui est
        //     sous les yeux : on jette seulement ce qui n'a pas encore
        //     été vu, et le préchargement le remplace aussitôt avec les
        //     nouveaux thèmes ;
        //   · on est ailleurs — catalogue, « mes apprentissages ». Le
        //     flux se refera entièrement au retour.
        //
        // Après la réponse du serveur, pas avant : le rechargement part
        // aussitôt, et il redemanderait le flux d'avant si l'abonnement
        // n'y était pas encore enregistré.
        if (live.current.screen === 'exo') {
          setDeck((prev) => prev.slice(0, live.current.i + 1))
        } else {
          deckStale.current = true
        }
      })
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
        .then(() =>
          // Trois appels indépendants : chacun se pose pour son compte,
          // sinon le plus fragile emporte les deux autres.
          Promise.allSettled([
            api.feed(5, live.current.code),
            api.categories(),
            api.themes(),
          ]),
        )
        .then(([feed, cats, ths]) => {
          if (feed.status === 'fulfilled') setDeck(feed.value)
          if (cats.status === 'fulfilled') setCategories(cats.value)
          if (ths.status === 'fulfilled') setThemes(ths.value)
          setOffline(feed.status === 'rejected')
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

  /**
   * Pose le pseudo. Il part en base ET reste en local : le local sert à
   * l'afficher avant que le réseau réponde, la base à le retrouver
   * ailleurs — c'est déjà le contrat des autres réglages.
   */
  const setPseudo = useCallback(
    (name: string) => {
      const clean = name.trim().replace(/\s+/g, ' ')
      set({ pseudo: clean })
      if (clean.length >= 2) {
        void api.saveSettings({ display_name: clean }).catch(() => undefined)
      }
    },
    [set],
  )

  /**
   * L'entrée dans le flux. Elle demande le flux, rien de plus : c'est la
   * garde plus haut qui décide si on y arrive ou si on passe d'abord par
   * le pseudo. Elle la doublait, et deux endroits pour une seule règle,
   * c'est un des deux qui finit par diverger.
   */
  const enterFeed = useCallback(() => {
    set({ screen: 'exo', phase: 'q', sheet: null, ...NO_ANSWER })
  }, [set])

  /**
   * Quitter le quiz ouvert par un code.
   *
   * On nettoie l'adresse en même temps que l'état : sans ça, un
   * rechargement ramènerait le code et la sortie n'en serait pas une.
   */
  const leaveCode = useCallback(() => {
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href)
      url.searchParams.delete('code')
      window.history.replaceState(null, '', url.pathname + url.search + url.hash)
    }
    set({ code: null, codeTitle: '', i: 0, ...NO_ANSWER, prog: 0, phase: 'q' })
    setDeck([])
    void api
      .feed(5)
      .then(setDeck)
      .catch(() => setOffline(true))
  }, [set])

  /** Rejouer le quiz partagé depuis le début, les mêmes questions. */
  const restartCode = useCallback(() => {
    set({ codeDone: false, i: 0, ...NO_ANSWER, prog: 0, phase: 'q' })
    setDeck([])
    void api
      .feed(5, live.current.code)
      .then(setDeck)
      .catch(() => setOffline(true))
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
      const [feed, cats, ths] = await Promise.allSettled([
        api.feed(5, live.current.code),
        api.categories(),
        api.themes(),
      ])
      if (feed.status === 'fulfilled') setDeck(feed.value)
      if (cats.status === 'fulfilled') setCategories(cats.value)
      if (ths.status === 'fulfilled') setThemes(ths.value)
      setOffline(feed.status === 'rejected')
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
        if (live.current.afterAuth === 'create') {
          set({ screen: 'create', createStep: 1, afterAuth: null, genLoading: false })
        }
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

  /**
   * La création est fermée : réservée à l'administration le temps que
   * son pipeline rejoigne le catalogue reconstruit.
   *
   * On y va quand même, et l'écran dit pourquoi. Le détour par
   * l'inscription qui se trouvait ici n'a plus de sens — il faisait
   * créer un compte pour arriver sur une porte fermée, ce qui est pire
   * que la porte fermée.
   */
  const goCreate = useCallback(
    (step: number) =>
      set({ screen: 'create', createStep: step, sheet: null, genLoading: false }),
    [set],
  )

  const openMyTheme = useCallback(
    (themeId: number) => set({ sheet: 'myTheme', sheetThemeId: themeId }),
    [set],
  )

  const toastTimer = useRef<number>()
  const pollTimer = useRef<number>()

  /** Étape 1 : le dépôt crée le thème côté serveur, en privé. */
  /**
   * Étape 1 — le sujet part au modèle.
   *
   * L'appel est long : le modèle écrit la présentation ET le programme
   * d'un trait. On bascule sur l'écran d'attente pendant ce temps, et
   * tout est déjà en base au retour — l'écran suivant ne fait que relire.
   */
  const proposeKnowledge = useCallback(async () => {
    const subject = live.current.subject.trim()
    if (subject.length < 3) return false
    set({ thinking: true, genError: null })
    try {
      const k = await api.outline(subject, live.current.lang)
      set({
        knowledge: k,
        draftThemeId: k.theme_id,
        draftTitle: k.title,
        draftDescription: k.description ?? '',
        draftTags: k.tags,
        draftCategoryId: k.category_id,
        thinking: false,
      })
      return true
    } catch (err) {
      set({
        thinking: false,
        genError: err instanceof Error ? err.message : "La proposition a échoué.",
      })
      return false
    }
  }, [set])

  /**
   * Étape 3 — un prompt par chapitre, écrits en parallèle côté serveur.
   *
   * Le suivi relit la connaissance entière toutes les trois secondes.
   * Un chapitre est fini quand il a un type ou une erreur ; on s'arrête
   * quand plus aucun n'est en attente. Pas de compteur deviné : ce qui
   * s'affiche, ce sont des chapitres réellement écrits.
   */
  /**
   * Écrit un prompt par chapitre. Rend `true` si au moins un chapitre en
   * ressort exploitable.
   *
   * La promesse ne se résout qu'à la fin du suivi, pas à l'acceptation de
   * la demande : c'est ce qui permet d'enchaîner sur l'écriture des
   * exercices sans rendre la main à l'auteur entre les deux. Il ne
   * supervise plus une étape intermédiaire qui ne lui demandait rien.
   */
  const writePrompts = useCallback(
    async (force = false): Promise<boolean> => {
      const themeId = live.current.draftThemeId
      if (!themeId) return false
      set({ thinking: true, genError: null })
      try {
        set({ knowledge: await api.writePrompts(themeId, force) })
      } catch (err) {
        set({
          thinking: false,
          genError: err instanceof Error ? err.message : 'La rédaction a échoué.',
        })
        return false
      }

      return await new Promise<boolean>((resolve) => {
        const poll = async () => {
          try {
            const k = await api.knowledge(themeId)
            set({ knowledge: k })
            const vivants = k.chapters.filter((c) => c.status !== 'rejected')
            const attendus = vivants.filter((c) => !c.type_question && !c.error)
            if (attendus.length > 0) {
              pollTimer.current = window.setTimeout(() => void poll(), 3000)
              return
            }
            set({ thinking: false })
            resolve(vivants.some((c) => c.type_question))
          } catch {
            set({ thinking: false, genError: 'Le suivi de la rédaction a été interrompu.' })
            resolve(false)
          }
        }
        pollTimer.current = window.setTimeout(() => void poll(), 2000)
      })
    },
    [set],
  )

  const generateFromChapters = useCallback(async () => {
    const themeId = live.current.draftThemeId
    if (!themeId) return
    set({ screen: 'create', createStep: 3, genLoading: true, toast: false, genError: null })
    try {
      await api.generateFromChapters(themeId, live.current.genCount)
    } catch (err) {
      set({
        genLoading: false,
        genError: err instanceof Error ? err.message : 'La rédaction a échoué.',
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
  }, [set])

  /** Corriger, retenir ou écarter un chapitre relu. */
  const reviewChapter = useCallback(
    async (id: number, patch: Parameters<typeof api.patchChapter>[1]) => {
      try {
        const updated = await api.patchChapter(id, patch)
        set((p) =>
          p.knowledge
            ? {
                knowledge: {
                  ...p.knowledge,
                  chapters: p.knowledge.chapters.map((c) => (c.id === id ? updated : c)),
                },
              }
            : {},
        )
      } catch (err) {
        set({ genError: err instanceof Error ? err.message : 'Modification refusée.' })
      }
    },
    [set],
  )

  const createDraft = useCallback(async () => {
    const cur = live.current
    if (cur.draftThemeId) return true

    // La catégorie ne se choisit qu'à l'étape 2, mais le thème se crée
    // dès l'étape 1 : il faut donc une valeur d'attente. Ce ne peut pas
    // être `1` — les identifiants de catégorie ne commencent pas à 1 et
    // n'ont aucune raison de le faire, si bien que « Analyser »
    // répondait « Catégorie inconnue. » à tout le monde. On prend la
    // première catégorie réellement servie, celle-là même que l'étape 2
    // présélectionnera.
    const fallback = categories[0]?.id
    if (!cur.draftCategoryId && !fallback) {
      set({ genError: "Les catégories ne sont pas encore chargées. Réessaie dans un instant." })
      return false
    }

    try {
      const theme = await api.createTheme({
        title: cur.draftTitle.trim() || 'Nouveau thème',
        category_id: cur.draftCategoryId || (fallback as number),
        description: cur.draftDescription || null,
        source_markdown: cur.draftMarkdown || null,
        tags: cur.draftTags,
      })
      set({
        draftThemeId: theme.id,
        genError: null,
        // Garder la catégorie effectivement retenue, pour que l'étape 2
        // montre celle du thème créé et non un menu vide.
        draftCategoryId: cur.draftCategoryId || theme.category_id,
      })
      return true
    } catch (err) {
      set({ genError: err instanceof Error ? err.message : 'Création impossible.' })
      return false
    }
  }, [categories, set])

  /**
   * Étape 2 : reporter le classement sur le thème déjà créé.
   *
   * Le brouillon existe depuis l'étape 1, avec une catégorie d'attente.
   * Sans ce report, la catégorie, la description et les mots-clés
   * choisis ici ne quittaient jamais le navigateur : le
   * thème restait classé au hasard, et son auteur ne le voyait qu'une
   * fois publié.
   */
  const syncDraft = useCallback(async () => {
    const cur = live.current
    if (!cur.draftThemeId) return
    try {
      await api.updateTheme(cur.draftThemeId, {
        title: cur.draftTitle.trim() || undefined,
        category_id: cur.draftCategoryId || undefined,
        description: cur.draftDescription || null,
        tags: cur.draftTags,
      })
    } catch (err) {
      set({ genError: err instanceof Error ? err.message : 'Classement non enregistré.' })
    }
  }, [set])

  /**
   * Reprendre la relecture d'un apprentissage déjà généré.
   *
   * `draftExercises` n'était rempli que pendant la boucle de génération :
   * en revenant plus tard, la pile à relire était vide et « Modifier les
   * exercices » retombait sur l'étape 1, celle où l'on écrit un sujet.
   * Des questions écrites restaient donc en brouillon sans aucun moyen
   * de les valider — l'apprentissage s'affichait « 0 exercice » pour
   * toujours.
   *
   * On redemande la pile au serveur, qui la sert déjà, et on ouvre
   * directement l'étape de relecture quand il y a quelque chose à relire.
   */
  /**
   * Le geste unique de l'écran de proposition.
   *
   * Les questions se préparent puis les exercices s'écrivent, sans rendre
   * la main entre les deux. L'auteur voyait auparavant un écran de plus,
   * qui relistait les mêmes chapitres pour n'ajouter qu'un type de
   * question et un exemple — et qui n'affichait aucun bouton quand la
   * préparation avait été interrompue, laissant le brouillon sans issue.
   *
   * Relancer est sans danger : la préparation saute les chapitres qui ont
   * déjà leur prompt. C'est ce qui rend cet écran rattrapable.
   */
  const startWriting = useCallback(async () => {
    const k = live.current.knowledge
    const vivants = k ? k.chapters.filter((c) => c.status !== 'rejected') : []
    if (vivants.some((c) => !c.type_question)) {
      if (!(await writePrompts())) return
    }
    await generateFromChapters()
  }, [writePrompts, generateFromChapters])

  const resumeDraft = useCallback(
    async (themeId: number) => {
      set({ screen: 'create', draftThemeId: themeId, sheet: null, genLoading: false, genError: null })
      try {
        const drafts = await api.themeExercises(themeId, 'draft')
        setDraftExercises(drafts)
        set({ createStep: drafts.length > 0 ? 3 : 2, validated: 0 })
      } catch {
        set({ createStep: 2 })
      }
    },
    [set],
  )

  /**
   * Tout valider d'un coup.
   *
   * Le critique a déjà écarté ce qui ne tenait pas — six propositions sur
   * vingt à la dernière création. Ce qui reste a passé un contrôle ;
   * exiger un tap par exercice faisait payer à l'auteur une relecture
   * déjà faite. Elle reste offerte, elle n'est plus le péage.
   */
  const validateAll = useCallback(() => {
    const ids = liveDrafts.current.map((e) => e.id)
    if (ids.length === 0) return
    setDraftExercises([])
    set((p) => ({ validated: p.validated + ids.length }))
    for (const id of ids) {
      void api.patchExercise(id, { state: 'validated' }).catch(() => undefined)
    }
  }, [set])

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

  // Le bouton « Générer » de la maquette. Il passait par
  // `POST /themes/{id}/generate`, retirée avec la table `prompt`
  // (migration 018) : il n'existe plus qu'un seul chemin de rédaction,
  // celui des chapitres, et les types cochés à l'écran n'ont plus
  // d'effet — seul le QCM est produit.
  const generate = useCallback(() => {
    void generateFromChapters()
  }, [generateFromChapters])

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
      myThemes,
      sharedExercises,
      sheetKnowledge,
      sheetLoading,
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
      advance,
      avancerEtape,
      allerEtape,
      leaveCode,
      restartCode,
      goCreate,
      resumeDraft,
      setPseudo,
      enterFeed,
      openMyTheme,
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
      proposeKnowledge,
      writePrompts,
      generateFromChapters,
      startWriting,
      reviewChapter,
      createDraft,
      syncDraft,
      reviewExercise,
      validateAll,
      publishDraft,
    }),
    [
      s, exo, deck.length, ready, offline, user, categories, themes, myThemes,
      sharedExercises, progression,
      rankRows, comments, set, toggleFlag, hideFlag, answer, next, prev, go,
      advance, avancerEtape, allerEtape, leaveCode, restartCode, goCreate, resumeDraft, setPseudo, enterFeed, openMyTheme, sheetKnowledge, sheetLoading, generate, setLang, toggleDark, toggleMute, vote, card, subscribedIds,
      toggleSubscribe, sendComment, submitAuth, logout, draftExercises, createDraft,
      syncDraft, reviewExercise, publishDraft,
      proposeKnowledge, writePrompts, reviewChapter, generateFromChapters, startWriting, validateAll,
    ],
  )

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}

export function useStore(): Store {
  const store = useContext(StoreContext)
  if (!store) throw new Error('useStore doit être appelé dans un <StoreProvider>')
  return store
}
