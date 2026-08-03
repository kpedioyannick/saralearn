/**
 * Français et anglais.
 *
 * Deux plans distincts, à ne pas confondre :
 *   · l'INTERFACE est traduite — ce fichier ;
 *   · un THÈME est écrit dans une langue, il n'est jamais traduit.
 *     Changer de langue change le catalogue servi, pas seulement les
 *     libellés (voir `theme.lang` côté base).
 *
 * Le dictionnaire anglais est typé d'après le français : oublier une
 * clé est une erreur de compilation, pas un trou découvert en
 * production.
 */

export type Lang = 'fr' | 'en'

const fr = {
  // Exercice
  swipeHint: 'Swipe pour passer',
  nextExercise: 'Exercice suivant',
  yourAnswer: 'Ta réponse',
  rightAnswer: 'La bonne réponse',
  // Produire une réponse plutôt que la reconnaître
  shortAnswerHint: 'Ta réponse…',
  oneWordOnly: 'Un seul mot',
  validateAnswer: 'Valider ma réponse',
  blankOf: (n: number, total: number) => `Trou ${n} sur ${total}`,
  explanation: 'Explication',
  remember: 'À retenir',
  streakOne: (n: number) => `${n} réussites aujourd'hui`,
  streakMany: (n: number) => `${n} bonnes réponses d'affilée`,
  preparing: 'On prépare tes exercices…',
  serverDown: 'Le serveur ne répond pas.',
  serverDownHint: "Vérifie que l'API tourne, puis recharge.",
  retry: 'Réessayer',

  // Rail
  voteUp: "J'aime",
  voteDown: "Je n'aime pas",
  voteUndo: 'Retirer mon vote',
  comments: 'Commentaires',
  ranking: 'Classement',
  settings: 'Réglages',

  // Types de question
  qcm: 'QCM',
  true_false: 'Vrai / Faux',
  complete: 'Complète',
  find_error: "Trouve l'erreur",
  reorder: "Remets dans l'ordre",
  short_answer: 'Réponse courte',
  cloze: 'Texte à trous',

  // Onboarding
  tagline: 'Un exercice. Un tap. Le suivant.',
  welcomeLine:
    'Choisis tes thèmes, on te sert des exercices sans fin. Tu peux commencer tout de suite.',
  start: 'Commencer',
  noAccountNeeded: "Pas d'email, pas de mot de passe.",
  step2: 'Étape 2 sur 3',
  step3: 'Étape 3 sur 3',
  pickInterests: "Choisis ce qui t'intéresse.",
  uncheckWhatever: 'Décoche ce qui ne te dit rien.',
  defaultAll: 'Sans choix, on te sert un peu de tout.',
  subThemes: (n: number) => `${n} sous-thèmes`,
  continueWith: (n: number) => `Continuer · ${n} choisi${n > 1 ? 's' : ''}`,
  letsGo: 'C’est parti',
  themesCount: (n: number) => `${n} thème${n > 1 ? 's' : ''}`,
  skip: 'Passer',

  // Thèmes
  addThemes: 'Ajouter des thèmes',
  allThemes: 'Tous les thèmes',
  themesOfChosen: 'Thèmes des catégories choisies',
  createOwn: 'Créer mon propre thème',
  continue: 'Continuer',
  subCategories: 'Sous-catégories',
  level2: 'Niveau 2 sur 2',

  // Réglages
  themes: 'Thèmes',
  noThemeFollowed: 'Aucun thème suivi — on te sert un peu de tout.',
  add: 'Ajouter',
  progression: 'Progression',
  nothingStarted: "Rien de commencé. Réponds à un exercice et ça s'affichera ici.",
  audio: 'Audio',
  feedbackSounds: 'Sons de retour',
  feedbackSoundsSub: 'Félicitation, erreur, explication',
  darkMode: 'Mode sombre',
  darkOn: 'Activé — fond sombre chaud',
  darkOff: 'Désactivé — papier crème',
  language: 'Langue',
  languageSub: 'Change aussi les thèmes proposés',
  account: 'Compte',
  playingAnonymously:
    'Tu joues sans compte. Crée-en un pour garder ta progression sur tous tes appareils.',
  signedInAs: 'Connecté avec',
  signedInSub: 'Ta progression te suit sur tous tes appareils.',
  createAccount: 'Créer un compte',
  signIn: 'Se connecter',
  signOut: 'Se déconnecter',
  signOutSub: "Tu repasseras en session libre. Rien n'est perdu : tout est gardé sur ton compte.",
  myThemes: 'Mes thèmes',
  themesLead: 'Ce que tu suis, et où tu en es. Ajoute ou retire quand tu veux.',
  addThemesLead: "Filtre par catégorie, puis choisis. Rien n'est définitif.",
  menu: 'Menu',
  settingsLead: "Le son, l'apparence, la langue et ton compte. Rien d'autre.",
  signupLang: 'Langue des thèmes',
  signupLangSub: 'Elle décide du catalogue qui te sera proposé. Modifiable dans les réglages.',
  myAccount: 'Mon compte',

  // Classement
  myStrengths: 'Mes forces',
  others: 'Les autres',
  strengthsIntro: 'De la mieux réussie à celle qui demande encore du travail.',
  noStrengthsYet: 'Fais quelques exercices : tes forces apparaîtront ici.',
  nobodyYet: "Personne n'a encore joué cette semaine.",
  thisWeek: 'Cette semaine',
  yourPlace: 'Ta place sur ce thème',
  points: 'points',
  weeklyReset: "Le classement d'un thème se remet à zéro chaque lundi.",
  you: 'Toi',

  // Feuille
  themeBlurb: (name: string) =>
    `Des exercices courts sur ${name.toLowerCase()}. Mélangés à tes autres thèmes dans le flux.`,
  exercises: 'exercices',
  subscribers: 'abonnés',
  yourProgressHere: 'Ta progression ici',
  passed: 'réussis',
  subscribed: 'Abonné — se désabonner',
  subscribe: "S'abonner à ce thème",
  seeThemeRanking: 'Voir le classement de ce thème',
  noComments: "Personne n'a encore réagi. À toi.",
  addComment: 'Ajouter un commentaire',
  send: 'Envoyer',
  followAlso: 'À suivre aussi',
  subscribeShort: "S'abonner",

  // Compte
  keepProgress: 'Garde ta progression.',
  keepProgressLine:
    'Tes exercices faits et tes thèmes te suivront sur tous tes appareils.',
  welcomeBack: 'Content de te revoir.',
  welcomeBackLine: 'Retrouve tes thèmes et ta progression là où tu les avais laissés.',
  email: 'Email',
  password: 'Mot de passe',
  passwordHint: '8 caractères minimum',
  mergeSignup: 'Ce que tu as déjà fait sans compte est conservé et rattaché à ce compte.',
  mergeLogin: 'Ta session actuelle sera fusionnée avec ton compte.',
  createMyAccount: 'Créer mon compte',
  haveAccount: "J'ai déjà un compte",
  noAccount: "Je n'ai pas encore de compte",
  continueWithout: 'Continuer sans compte',
  oneMoment: 'Un instant…',

  // Création
  newTheme: 'Nouveau thème',
  dropWhatYouHave: 'Dépose ce que tu as.',
  pasteMarkdown: 'Colle ton cours en Markdown',
  pasteMarkdownSub:
    "C'est à partir de ce texte, et de lui seul, que les exercices seront écrits.",
  title: 'Titre',
  description: 'Description',
  analyse: 'Analyser',
  proposed: 'Proposé — corrige librement',
  hereIsClassing: 'Voilà comment je le classe.',
  category: 'Catégorie',
  subCategory: 'Sous-catégorie',
  none: '— aucune —',
  tags: 'Tags',
  addTagHint: 'Ajouter un tag, puis Entrée',
  whichTypes: "Quels types d'exercices ?",
  recommended: 'Conseillé',
  howMany: "Nombre d'exercices",
  estimate: (a: number, b: number) => `Environ ${a} à ${b} minutes de rédaction.`,
  generateAction: 'Générer',
  writing: 'Je rédige tes exercices.',
  writingLine:
    'Ça prend une minute ou deux. Tu peux fermer l’app, je te préviens quand c’est prêt.',
  writingProgress: (n: number) => `Rédaction en cours — ${n} exercices demandés`,
  toReview: 'À valider',
  validatedCount: (v: number, p: number) =>
    `${v} validé${v > 1 ? 's' : ''} · ${p} en attente`,
  allReviewed: 'Tout est relu.',
  nothingToReview: 'Rien à relire.',
  willJoinFeed: (n: number) =>
    `${n} exercice${n > 1 ? 's' : ''} rejoindront ton flux.`,
  launchFromPrevious: "Lance une génération depuis l'étape précédente.",
  explanationToReview: 'Explication à relire',
  validate: 'Valider',
  discard: 'Écarter',
  regenerate: 'Régénérer',
  privatePublish: 'Privé · publier',
  ready: "C'est prêt.",
  toReviewCount: (n: number) => `${n} exercices à relire`,

  // Publication
  publication: 'Publication',
  privateLabel: 'Privé',
  byDefault: 'Par défaut',
  privateLine: 'Seul toi vois ce thème et ses exercices.',
  publicLabel: 'Public',
  publicLine:
    "Tout le monde peut s'y abonner. Une relecture est faite avant la mise en ligne.",
  canSwitchLater: 'Tu peux passer de privé à public plus tard, depuis les réglages du thème.',
  askPublication: 'Demander la publication',
  savePrivate: 'Enregistrer en privé',
  sentForReview: 'Envoyé en relecture.',
  savedPrivate: 'Enregistré en privé.',
  sentForReviewLine:
    "Je te préviens dès que le thème est visible par les autres. En attendant, il est déjà dans ton flux.",
  savedPrivateLine:
    'Le thème est dans ton flux, visible de toi seul. Tu pourras le rendre public depuis ses réglages.',
  backToExercises: 'Retour aux exercices',

  // À propos — vision et mission
  about: 'À propos',
  slogan: "Rendre l'apprentissage simple, accessible et infini.",
  visionTitle: 'Notre vision',
  visionLead:
    'Permettre à chacun d\'apprendre tout ce qu\'il souhaite, quand il le souhaite et à son propre rythme.',
  visionBody:
    'Que vous souhaitiez apprendre à coder, comprendre les mathématiques, découvrir l\'histoire, améliorer votre culture générale ou explorer un nouveau domaine, SaraLearn vous offre une expérience d\'apprentissage simple, accessible et basée sur la découverte continue.',
  missionTitle: 'Notre mission',
  missionLead: 'Rendre l\'apprentissage simple, accessible et infini.',
  missionBody:
    'SaraLearn veut transformer la manière dont nous apprenons en rendant la connaissance plus accessible à tous. Pas besoin de passer des heures à chercher quoi apprendre. Pas besoin de suivre un parcours compliqué. Il suffit de commencer.',
  missionBeat: 'Une question. Une réponse. Une nouvelle connaissance.',
  missionThen: 'Puis une autre. Et encore une autre.',
  missionBoth: 'Sur SaraLearn, tout le monde peut apprendre et tout le monde peut transmettre.',
  missionClose: 'Apprendre n\'a pas de limites.',
  creditsTitle: 'Crédits des illustrations',
  creditsIntro:
    'Les pictogrammes de panneaux proviennent de sources publiques. Certains sont diffusés sous licence CC BY-SA, qui impose de citer leurs auteurs.',
  creditsSigns: (n: number) => `${n} panneau${n > 1 ? 'x' : ''}`,

  // Divers
  admin: 'Administration',
  back: 'Retour',
  close: 'Fermer',
  soundOn: 'Son activé',
  soundOff: 'Son coupé',
  prevExercise: 'Exercice précédent',
}

/**
 * Le dictionnaire anglais est typé d'après le français : une clé
 * oubliée ou en trop est une erreur de compilation.
 */
export type Dict = typeof fr

const en: Dict = {
  swipeHint: 'Swipe to skip',
  nextExercise: 'Next exercise',
  yourAnswer: 'Your answer',
  rightAnswer: 'The right answer',
  shortAnswerHint: 'Your answer…',
  oneWordOnly: 'One word only',
  validateAnswer: 'Submit my answer',
  blankOf: (n, total) => `Blank ${n} of ${total}`,
  explanation: 'Explanation',
  remember: 'Worth remembering',
  streakOne: (n) => `${n} correct today`,
  streakMany: (n) => `${n} in a row`,
  preparing: 'Getting your exercises ready…',
  serverDown: 'The server is not responding.',
  serverDownHint: 'Check that the API is running, then reload.',
  retry: 'Try again',

  voteUp: 'Like',
  voteDown: 'Dislike',
  voteUndo: 'Remove my vote',
  comments: 'Comments',
  ranking: 'Ranking',
  settings: 'Settings',

  qcm: 'Multiple choice',
  true_false: 'True / False',
  complete: 'Fill in',
  find_error: 'Spot the error',
  reorder: 'Put in order',
  short_answer: 'Short answer',
  cloze: 'Fill the blanks',

  tagline: 'One exercise. One tap. The next.',
  welcomeLine:
    'Pick your topics and we will keep the exercises coming. You can start right away.',
  start: 'Start',
  noAccountNeeded: 'No email, no password.',
  step2: 'Step 2 of 3',
  step3: 'Step 3 of 3',
  pickInterests: 'Pick what interests you.',
  uncheckWhatever: 'Uncheck anything that leaves you cold.',
  defaultAll: 'Pick nothing and we will serve a bit of everything.',
  subThemes: (n) => `${n} topics`,
  continueWith: (n) => `Continue · ${n} selected`,
  letsGo: 'Let’s go',
  themesCount: (n) => `${n} topic${n > 1 ? 's' : ''}`,
  skip: 'Skip',

  addThemes: 'Add topics',
  allThemes: 'All topics',
  themesOfChosen: 'Topics in the chosen categories',
  createOwn: 'Create my own topic',
  continue: 'Continue',
  subCategories: 'Subcategories',
  level2: 'Level 2 of 2',

  themes: 'Topics',
  noThemeFollowed: 'No topic followed — we serve a bit of everything.',
  add: 'Add',
  progression: 'Progress',
  nothingStarted: 'Nothing started yet. Answer an exercise and it will show up here.',
  audio: 'Audio',
  feedbackSounds: 'Feedback sounds',
  feedbackSoundsSub: 'Praise, miss, explanation',
  darkMode: 'Dark mode',
  darkOn: 'On — warm dark ground',
  darkOff: 'Off — cream paper',
  language: 'Language',
  languageSub: 'Also changes which topics you get',
  account: 'Account',
  playingAnonymously:
    'You are playing without an account. Create one to keep your progress across devices.',
  signedInAs: 'Signed in as',
  signedInSub: 'Your progress follows you across devices.',
  createAccount: 'Create an account',
  signIn: 'Sign in',
  signOut: 'Sign out',
  signOutSub: 'You will go back to a free session. Nothing is lost — it all stays on your account.',
  myThemes: 'My themes',
  themesLead: 'What you follow, and where you stand. Add or drop any time.',
  addThemesLead: 'Filter by category, then pick. Nothing is final.',
  menu: 'Menu',
  settingsLead: 'Sound, appearance, language and your account. Nothing else.',
  signupLang: 'Theme language',
  signupLangSub: 'It decides which catalogue you are offered. You can change it in settings.',
  myAccount: 'My account',

  myStrengths: 'My strengths',
  others: 'Others',
  strengthsIntro: 'From the best mastered to the one still needing work.',
  noStrengthsYet: 'Do a few exercises and your strengths will show up here.',
  nobodyYet: 'Nobody has played yet this week.',
  thisWeek: 'This week',
  yourPlace: 'Your place on this topic',
  points: 'points',
  weeklyReset: 'A topic ranking resets every Monday.',
  you: 'You',

  themeBlurb: (name) =>
    `Short exercises on ${name.toLowerCase()}. Mixed into your other topics in the feed.`,
  exercises: 'exercises',
  subscribers: 'subscribers',
  yourProgressHere: 'Your progress here',
  passed: 'passed',
  subscribed: 'Subscribed — unsubscribe',
  subscribe: 'Subscribe to this topic',
  seeThemeRanking: 'See this topic’s ranking',
  noComments: 'Nobody has reacted yet. Your turn.',
  addComment: 'Add a comment',
  send: 'Send',
  followAlso: 'Worth following too',
  subscribeShort: 'Subscribe',

  keepProgress: 'Keep your progress.',
  keepProgressLine: 'Your exercises and topics will follow you across devices.',
  welcomeBack: 'Good to see you again.',
  welcomeBackLine: 'Pick your topics and progress back up where you left them.',
  email: 'Email',
  password: 'Password',
  passwordHint: '8 characters minimum',
  mergeSignup: 'What you did without an account is kept and attached to this one.',
  mergeLogin: 'Your current session will be merged into your account.',
  createMyAccount: 'Create my account',
  haveAccount: 'I already have an account',
  noAccount: 'I do not have an account yet',
  continueWithout: 'Continue without an account',
  oneMoment: 'One moment…',

  newTheme: 'New topic',
  dropWhatYouHave: 'Drop in what you have.',
  pasteMarkdown: 'Paste your lesson in Markdown',
  pasteMarkdownSub: 'The exercises will be written from this text, and this text alone.',
  title: 'Title',
  description: 'Description',
  analyse: 'Analyse',
  proposed: 'Suggested — correct freely',
  hereIsClassing: 'Here is how I would file it.',
  category: 'Category',
  subCategory: 'Subcategory',
  none: '— none —',
  tags: 'Tags',
  addTagHint: 'Add a tag, then Enter',
  whichTypes: 'Which kinds of exercise?',
  recommended: 'Recommended',
  howMany: 'How many exercises',
  estimate: (a, b) => `About ${a} to ${b} minutes of writing.`,
  generateAction: 'Generate',
  writing: 'Writing your exercises.',
  writingLine:
    'It takes a minute or two. You can close the app — I will let you know when it is ready.',
  writingProgress: (n) => `Writing — ${n} exercises requested`,
  toReview: 'To review',
  validatedCount: (v, p) => `${v} approved · ${p} waiting`,
  allReviewed: 'All reviewed.',
  nothingToReview: 'Nothing to review.',
  willJoinFeed: (n) => `${n} exercise${n > 1 ? 's' : ''} will join your feed.`,
  launchFromPrevious: 'Start a generation from the previous step.',
  explanationToReview: 'Explanation to check',
  validate: 'Approve',
  discard: 'Discard',
  regenerate: 'Regenerate',
  privatePublish: 'Private · publish',
  ready: 'Ready.',
  toReviewCount: (n) => `${n} exercises to review`,

  publication: 'Publishing',
  privateLabel: 'Private',
  byDefault: 'Default',
  privateLine: 'Only you see this topic and its exercises.',
  publicLabel: 'Public',
  publicLine: 'Anyone can subscribe. It gets a read-through before going live.',
  canSwitchLater: 'You can switch from private to public later, from the topic settings.',
  askPublication: 'Request publishing',
  savePrivate: 'Save as private',
  sentForReview: 'Sent for review.',
  savedPrivate: 'Saved as private.',
  sentForReviewLine:
    'I will let you know as soon as the topic is visible to others. In the meantime it is already in your feed.',
  savedPrivateLine:
    'The topic is in your feed, visible to you alone. You can make it public from its settings.',
  backToExercises: 'Back to exercises',

  about: 'About',
  slogan: 'Making learning simple, open and endless.',
  visionTitle: 'Our vision',
  visionLead:
    'Let anyone learn whatever they want, whenever they want, at their own pace.',
  visionBody:
    'Whether you want to learn to code, get to grips with maths, discover history, broaden your general knowledge or explore a new field, SaraLearn offers a learning experience that is simple, open, and built on continuous discovery.',
  missionTitle: 'Our mission',
  missionLead: 'Making learning simple, open and endless.',
  missionBody:
    'SaraLearn sets out to change the way we learn, by putting knowledge within everyone\'s reach. No hours spent working out what to learn. No complicated path to follow. Just start.',
  missionBeat: 'A question. An answer. Something new.',
  missionThen: 'Then another. And another.',
  missionBoth: 'On SaraLearn, everyone can learn and everyone can teach.',
  missionClose: 'Learning has no limits.',
  creditsTitle: 'Illustration credits',
  creditsIntro:
    'Sign pictograms come from public sources. Some are released under CC BY-SA, which requires crediting their authors.',
  creditsSigns: (n) => `${n} sign${n > 1 ? 's' : ''}`,

  admin: 'Administration',
  back: 'Back',
  close: 'Close',
  soundOn: 'Sound on',
  soundOff: 'Sound off',
  prevExercise: 'Previous exercise',
}

const DICTS: Record<Lang, Dict> = { fr, en }

export function dict(lang: Lang): Dict {
  return DICTS[lang] ?? fr
}

/** Langue de départ : celle du navigateur si on la sert, français sinon. */
export function detectLang(): Lang {
  if (typeof navigator === 'undefined') return 'fr'
  return navigator.language.toLowerCase().startsWith('en') ? 'en' : 'fr'
}
