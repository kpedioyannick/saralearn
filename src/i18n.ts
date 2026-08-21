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
  // Le bandeau du quiz ouvert par un code : il dit sur quoi on est
  // fermé, et donne la sortie. Sans lui, on ne comprend pas pourquoi
  // les autres apprentissages ont disparu.
  codeBanner: 'Quiz partagé',
  codeDoneTitle: 'Vous avez tout fait.',
  codeDoneLine:
    'Ce quiz partagé n’a rien de plus à vous proposer. Vous pouvez le refaire, ou revenir au flux complet.',
  codeRestart: 'Refaire ce quiz',
  codeLeave: 'Quitter',
  codeSearchHint: 'Ou colle un code de partage',
  codeNotFound: 'Aucun quiz ne porte ce code.',
  codeLabel: 'Code de partage',
  codeCopy: 'Copier',
  codeCopied: 'Copié',
  nextExercise: 'Exercice suivant',
  // La réussite et l'erreur n'avaient aucun bouton : elles passaient
  // seules à l'explication. Sans enchaînement automatique, il en faut un,
  // sinon on reste bloqué sur l'écran de félicitation.
  seeExplanation: "Voir l'explication",
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
  // Passé quelques secondes, « on prépare » ne suffit plus : l'attente
  // n'est pas un chargement mais une ÉCRITURE, et une demi-minute sans
  // explication se lit comme une panne.
  preparingLong: 'On écrit les questions de cet apprentissage. Une demi-minute environ.',
  serverDown: 'Le serveur ne répond pas.',
  serverDownHint: 'On réessaie tout seul. Tu peux aussi recharger.',
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
    'Choisis tes apprentissages, on te sert des exercices sans fin. Tu peux commencer tout de suite.',
  start: 'Commencer',
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
  noThemeFollowed: 'Aucun apprentissage suivi — on te sert un peu de tout.',
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
  languageSub: 'Change aussi les apprentissages proposés',
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
  themesLead: 'Ce que vous suivez, et où vous en êtes. Ajoutez ou retirez quand vous voulez.',
  menu: 'Menu',
  settingsLead: "Le son, l'apparence, la langue et ton compte. Rien d'autre.",
  signupLang: 'Langue des apprentissages',
  signupLangSub: 'Elle décide du catalogue qui te sera proposé. Modifiable dans les réglages.',
  myAccount: 'Mon compte',

  // Classement
  myStrengths: 'Mes forces',
  others: 'Les autres',
  strengthsIntro: 'De la mieux réussie à celle qui demande encore du travail.',
  noStrengthsYet: 'Fais quelques exercices : tes forces apparaîtront ici.',
  nobodyYet: "Personne n'a encore joué cette semaine.",
  thisWeek: 'Cette semaine',
  // Classement, planche 1m : deux colonnes, la progression par
  // apprentissage à gauche, le classement sur un apprentissage à droite.
  myProgress: 'Ma progression',
  rankLead: 'Votre progression et celle des autres',
  byTheme: 'Par apprentissage',
  rankOnLearning: 'Classement sur un apprentissage',
  yourStrength: 'Votre point fort',
  toResume: 'À reprendre',
  participants: (n: number) => `${n} participant${n > 1 ? 's' : ''}`,
  yourPlace: 'Ta place sur cet apprentissage',
  sharedNotFound: "Cette connaissance n'existe pas, ou elle n'est pas à vous.",
  exercisesPassed: 'exercices réussis',
  statToReview: 'à revoir',
  points: 'points',
  weeklyReset: "Le classement d'un apprentissage se remet à zéro chaque lundi.",
  you: 'Toi',

  // Feuille
  themeBlurb: (name: string) =>
    `Des exercices courts sur ${name.toLowerCase()}. Mélangés à vos autres apprentissages dans le flux.`,
  exercises: 'exercices',
  subscribers: 'abonnés',
  yourProgressHere: 'Ta progression ici',
  passed: 'réussis',
  subscribed: 'Abonné — se désabonner',
  subscribe: "S'abonner à cet apprentissage",
  seeThemeRanking: 'Voir le classement de cet apprentissage',
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
  newLearning: 'Nouvel apprentissage',
  // L'écran de création est fermé le temps que son pipeline soit remis
  // au niveau du catalogue reconstruit. On le dit plutôt que de laisser
  // quelqu'un écrire un sujet pour se faire refuser à la première
  // requête.
  createClosedTitle: "Réservé à l'administration",
  createClosedLine:
    "Déposer une connaissance n'est ouvert qu'aux administrateurs pour le moment. Le catalogue s'écrit tout seul : choisis un apprentissage, ses questions s'écrivent à l'ouverture.",
  createClosedBack: 'Retour aux exercices',
  markdownPlaceholder: '# Titre du cours\n\nUn accord majeur se compose de…',
  titlePlaceholder: 'Accords de guitare — bases',
  descriptionPlaceholder:
    'Les accords ouverts, leurs tierces, et les erreurs classiques de doigté.',
  dropWhatYouHave: 'Dépose ce que tu as.',
  pasteMarkdown: 'Colle ton cours en Markdown',
  pasteMarkdownSub:
    "C'est à partir de ce texte, et de lui seul, que les exercices seront écrits.",

  // Création par sujet — le parcours en cinq temps
  subjectHint:
    "Un sujet suffit. Je m'occupe du titre, du plan et des exercices.",
  subjectPlaceholder: 'les fonctions PHP',
  propose: 'Proposer un programme',
  thinkingHead: 'Je prépare ton programme.',
  thinkingLine: 'Quelques secondes : je cherche le plan, puis je le découpe.',
  yourKnowledge: 'Voici ta connaissance.',
  presentLead: 'Tout est pré-rempli. Corrige ce qui ne va pas, complète ce qui manque.',
  tagsDetected: 'Tags détectés',
  newCategoryNote: (label: string) =>
    `« ${label} » n'existait pas : je l'ai créée. Elle attend d'être retenue avant d'entrer au catalogue.`,
  programme: 'Programme',
  chapterCount: (n: number) => `${n} chapitre${n > 1 ? 's' : ''}`,
  writePromptsAction: 'Préparer les questions',
  // Le seul bouton de l'écran de proposition : il enchaîne la préparation
  // des questions et l'écriture des exercices. C'était deux boutons sur
  // deux écrans, dont l'un pouvait ne jamais s'afficher.
  writeExercises: 'Écrire les exercices',
  validateAll: 'Tout valider',
  validateOneByOne: 'Relire une par une',
  reviewedByCritic: "Un relecteur automatique a déjà écarté ce qui n'allait pas. Validez tout, ou relisez.",
  preparingHead: 'Je prépare les questions.',
  preparedCount: (done: number, total: number) =>
    `${done} chapitre${done > 1 ? 's' : ''} sur ${total}`,
  chaptersHead: 'Comment chaque chapitre sera interrogé.',
  exampleLabel: 'Exemple',
  noExample: 'Pas d’aperçu pour ce chapitre — les questions seront écrites quand même.',
  chapterFailed: 'La préparation a échoué pour ce chapitre.',
  retryChapter: 'Réessayer',
  askedAs: 'Interrogé en',
  typeQcm: 'choix multiple',
  typeComplete: 'texte à compléter',
  typeFindError: 'erreur à trouver',
  typeShortAnswer: 'réponse à écrire',
  typeCloze: 'texte à trous',

  title: 'Titre',
  description: 'Description',
  analyse: 'Analyser',
  proposed: 'Proposé — corrige librement',
  hereIsClassing: 'Voilà comment je le classe.',
  category: 'Catégorie',
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
  summary: 'Récapitulatif',
  validatedExercises: (n: number) =>
    `${n} exercice${n > 1 ? 's' : ''} validé${n > 1 ? 's' : ''}`,
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
  // Le titre de l'onglet et du partage. La description qui l'accompagne
  // n'a pas sa clé : c'est « SaraLearn — » suivi du slogan ci-dessus,
  // qui est déjà traduit et n'a pas à l'être deux fois.
  metaTitle: 'SaraLearn — apprendre sans fin',
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

  // Bandeau de lecture — planche 4c
  pauseReading: 'Mettre la lecture en pause',
  resumeReading: 'Reprendre la lecture',
  replayReading: 'Réécouter',

  // ----------------------------------------------------------------
  // Refonte « tour 1 »
  //
  // La planche parle d'« apprentissage » là où le code dit « thème ».
  // Le mot du code n'a pas bougé — c'est le nom d'une table — mais
  // c'est celui de la planche qui s'affiche.
  // ----------------------------------------------------------------
  follow: "s'abonner",
  followed: 'abonné',
  unfollow: 'Ne plus suivre',
  exercisesNav: 'Exercices',
  localAccount: 'Compte local',
  learnings: 'Apprentissages',
  myLearnings: 'Mes apprentissages',
  addLearnings: 'Ajouter des apprentissages',
  learningsCount: (n: number) => `${n} apprentissage${n > 1 ? 's' : ''}`,
  exercisesCount: (n: number) => `${n} exercice${n > 1 ? 's' : ''}`,
  // Forme brève des listes denses : en colonne étroite, « 118
  // exercices » passe à la ligne et casse la rangée.
  exercisesShort: (n: number) => `${n} ex.`,
  shareKnowledge: 'Partager une connaissance',
  shareKnowledgeLine: "Déposez un document, l'IA écrit les exercices, vous validez.",
  searchLearning: 'Chercher un apprentissage, une catégorie, un tag',
  followedTab: 'Suivis',
  suggestedTab: 'Suggérés',
  // Les deux onglets que la planche desktop ajoute : en pleine largeur
  // la liste tient, et distinguer « suivi » de « commencé » devient
  // utile — le téléphone garde ses deux onglets.
  startedTab: 'Commencés',
  createdByMeTab: 'Créés par moi',
  // Le troisième onglet du téléphone (planche 1f). Il classe par nombre
  // d'abonnés : c'est la seule mesure de popularité que la base tienne.
  popularTab: 'Populaires',
  themesMeta: (followed: number, total: number) =>
    `${followed} suivi${followed > 1 ? 's' : ''} · ${total} disponible${total > 1 ? 's' : ''}`,
  suggestions: 'Suggestions',
  // La planche 1f pose les suggestions SOUS la liste suivie, pas
  // seulement dans un onglet : un écran sans rien suivi doit quand même
  // proposer quelque chose.
  suggestedForYou: 'Suggéré pour vous',
  nearYourLearnings: 'proche de vos apprentissages',
  noPopular: 'Rien à classer pour le moment.',
  // La ligne d'auteur, sous « Créés par moi », et la feuille qu'elle ouvre.
  promptsCount: (n: number) => `${n} prompt${n > 1 ? 's' : ''}`,
  learnersCount: (n: number) =>
    n > 1 ? `${n} personnes l'ont fait` : `${n} personne l'a fait`,
  themeDetail: 'Détail de l’apprentissage',
  // Une seule porte, quel que soit l'état : `resumeDraft` sait où
  // reprendre — relecture s'il y a des brouillons, chapitres sinon.
  resumeCreation: 'Reprendre la création',
  promptsList: 'Les prompts',
  // Libellés courts des trois compteurs de la fiche : sous un grand
  // chiffre, un article ou un verbe conjugué se lit mal.
  promptsShort: 'prompts',
  learnersShort: 'ont pratiqué',
  noPromptYet: "Aucun prompt : cet apprentissage n'est pas passé par le programme.",
  promptNotWritten: "Prompt pas encore écrit.",
  showAll: 'Voir tout',
  showLess: 'Replier',
  chapterRejected: 'écarté',
  // Le libellé de la pastille d'abonnement, forme courte : « Suivi » au
  // repos, « Retirer » au survol — le bouton annonce son geste.
  followedShort: 'Suivi',
  followShort: 'Suivre',
  unfollowShort: 'Retirer',
  noThemeStarted: "Aucun apprentissage commencé — répondez à un exercice et il apparaîtra ici.",
  noThemeCreated: "Vous n'avez encore rien partagé.",
  startSharing: 'Commencer',
  nothingToSuggest: 'Vous suivez déjà tout ce que nous avons ici.',
  categories: 'Catégories',
  followAll: 'Tout suivre',
  addToFeed: 'Ajouter au flux',

  // « Ajouter des apprentissages » — barre d'outils et panneau de
  // sélection de la planche 1m.
  pickerMeta: (themes: number, cats: number) =>
    `${themes} apprentissage${themes > 1 ? 's' : ''} · ${cats} catégorie${cats > 1 ? 's' : ''}`,
  searchCatalogue: (n: number) => `Chercher parmi ${n} apprentissages`,
  sortPopular: 'Populaires',
  sortNew: 'Nouveaux',
  filters: 'Filtres',
  filterFollowedOnly: 'Seulement ceux que je suis',
  filterHideFollowed: 'Masquer ceux que je suis',
  searchResults: 'Résultats',
  selection: 'Sélection',
  clearSelection: 'Vider la sélection',
  moreOthers: (n: number) => `+ ${n} autre${n > 1 ? 's' : ''}`,
  feedEstimate: (n: number) =>
    `Environ ${n.toLocaleString('fr-FR')} exercice${n > 1 ? 's' : ''} ajouté${n > 1 ? 's' : ''} au flux.`,
  emptySelection: 'Rien de sélectionné pour le moment.',
  noMatch: 'Aucun apprentissage ne correspond.',

  // ----------------------------------------------------------------
  // Tour 2 — « Ajouter », refondu : la recherche d'abord, les rayons
  // ensuite. Mêmes libellés à l'ajout et à la première étape de
  // l'inscription : c'est le même écran.
  // ----------------------------------------------------------------
  addShort: 'Ajouter',
  // Montré seulement quand on n'a rien demandé : on a été emmené ici
  // faute d'abonnement. Dire pourquoi, puis quoi faire — un renvoi sans
  // explication se lit comme une panne.
  whyHereTitle: 'Vous ne suivez encore aucun apprentissage',
  whyHereLine:
    "C'est pour ça que vous arrivez ici. Sans abonnement, le flux vous sert un peu de tout, au hasard du catalogue. Touchez un apprentissage ci-dessous pour le suivre : vos exercices viendront alors de ce que vous avez choisi.",
  whatToLearn: 'Que voulez-vous apprendre ?',
  becauseYouFollow: (name: string) => `Parce que vous suivez ${name}`,
  // La planche écrivait « les plus suivis cette semaine ». Aucune
  // statistique n'est datée côté API : la mention temporelle serait
  // fausse, le classement ne l'est pas.
  mostFollowed: 'Les plus suivis',
  newlyAdded: 'Nouveaux',
  seeAll: 'Tout voir',
  byCategory: 'Par catégorie',
  addThis: 'Ajouter',
  addedThis: 'Ajouté',
  cancelSearch: 'Annuler',
  resultsIn: (n: number, cats: number) =>
    `${n} résultat${n > 1 ? 's' : ''} dans ${cats} catégorie${cats > 1 ? 's' : ''}`,
  inCategory: (label: string) => `Dans ${label}`,
  questionsCount: (n: number) => `${n} question${n > 1 ? 's' : ''}`,
  addedCount: (n: number) => `${n} ajouté${n > 1 ? 's' : ''}`,
  approxQuestions: (n: number) => `≈ ${n.toLocaleString('fr-FR')} questions`,
  finish: 'Terminer',
  emptyCatalogue: 'Le catalogue est vide pour le moment.',

  // Inscription refondue — planche 1e
  stepOf: (n: number, total: number) => `${n} / ${total}`,
  // La planche 1e passe au vouvoiement sur l'inscription refondue.
  // « Choisis ce qui t'intéresse » suivi de « Cherchez, ou piochez »
  // mélangeait les deux dans le même écran.
  whatInterestsYou: 'Qu’est-ce qui vous intéresse ?',
  searchOrPick: 'Cherchez, ou piochez dans les propositions.',
  refine: 'On affine',
  refineLead: 'Tout est coché. Retirez ce qui ne vous parle pas.',
  uncheckAll: 'Tout décocher',
  continueLabel: 'Continuer',

  // ----- ACCUEIL PUBLIC — planche 1j ---------------------------
  // « Présentation fidèle des fonctions · essayer ou se connecter ».
  // La page est longue et assumée : elle présente le produit à
  // quelqu'un qui n'est jamais entré, et rien de ce qu'elle annonce
  // n'est absent de l'app.
  // Le pseudo, demandé une fois à l'entrée. Ce n'est pas une connexion :
  // la session est déjà authentifiée, le pseudo ne sert qu'à mettre un
  // nom au classement et sous les commentaires.
  pseudoTitle: 'Comment vous appelle-t-on ?',
  pseudoLead:
    'Un pseudo suffit, sans email ni mot de passe. Il s’affiche au classement et sous vos commentaires, et se change quand vous voulez dans les réglages.',
  pseudoPlaceholder: 'Votre pseudo',
  pseudoSave: 'C’est noté',
  pseudoTooShort: 'Au moins deux caractères.',
  pseudoNoPassword:
    'Aucun mot de passe : votre session est déjà reconnue sur cet appareil.',
  pseudoWhereTitle: 'Où il s’affiche',
  pseudoWhereRank: 'À la place de « Joueur 179 », dans le classement de chaque apprentissage.',
  pseudoWhereComments: 'Sous vos commentaires, à la place d’« Anonyme ».',
  pseudoLocal:
    'Il vit sur cet appareil tant que vous n’avez pas de compte. Le jour où vous en créez un — pour partager une connaissance — il le suit.',
  pseudoCardTitle: 'Choisir mon pseudo',
  pseudoLabel: 'Pseudo',
  pseudoNone: 'Pas encore de pseudo',

  homeTry: 'Essayer',
  homeKicker: "Le quiz qui s'écrit à la demande",
  // Le titre disait « Apprenez. Créez. Partagez. » — trois verbes pour
  // trois fonctions dont deux sont fermées : « Créez » et « Partagez »
  // menaient à la création, dont les routes interrogent une table
  // `category` qui n'existe plus.
  //
  // Il nomme maintenant le SUJET plutôt que les gestes. Les onze thèmes
  // sont des articles sur la nature — la lumière, le ciel, la Terre, les
  // animaux, le corps humain — et c'est la seule chose qu'un visiteur
  // doit comprendre en une ligne.
  homeTitle: 'Apprenez sur le monde qui nous entoure',
  // Le héros dit ce qu'on y gagne, pas comment c'est fabriqué.
  // Il portait « chaque sujet s'écrit le jour où quelqu'un l'ouvre, à
  // partir de son article » : c'est vrai, c'est même le cœur du système,
  // mais c'est de la mécanique, et un visiteur n'a rien à en faire à la
  // première phrase. L'explication garde sa section, plus bas, où elle a
  // la place de se dérouler.
  homeLead:
    "La lumière, le ciel, la Terre, les animaux, le corps humain. Une question par écran, et on y apprend comment les choses marchent, pas seulement comment elles s'appellent.",
  homeStartLearning: 'Commencer à apprendre',

  // L'APERÇU EST UN VRAI EXERCICE DE LA BASE — le 58, chapitre
  // « Lumière du Soleil ». Il montrait un vrai/faux intitulé « Faux
  // amis · Anglais », et ni l'un ni l'autre n'existent : les 142
  // exercices validés sont tous des QCM, et le catalogue porte onze
  // thèmes sur le monde naturel, pas de l'anglais.
  //
  // Écrit en dur quand même : la page s'affiche avant toute session, il
  // n'y a pas de flux à interroger à ce moment-là. Mais recopié, pas
  // inventé — et choisi pour ce que la règle éditoriale demande, un
  // mécanisme plutôt qu'un record.
  previewTheme: 'Lumière du Soleil · Le Soleil et plus',
  previewType: 'QCM',
  previewQuestion: 'Pourquoi voit-on un ciel rouge au lever et au coucher du soleil ?',
  previewOptions: [
    'En raison de la diffusion de la lumière bleue',
    "En raison de l'absorption de la lumière rouge",
    'À cause du reflet de la Lune',
  ],

  // L'OBJECTIF DE L'APP, DIT AVANT SES FONCTIONS.
  // Les quatre intentions du fondateur, dans ses mots. Elles viennent
  // avant la boucle et avant la liste des fonctions parce qu'elles
  // disent POURQUOI on joue, quand tout le reste dit comment.
  //
  // Trois mots, sans glose. Chacun portait une ligne d'explication —
  // « aucune leçon à lire avant », « se tromper montre où le
  // raisonnement a lâché » — retirées : elles décrivaient la mécanique
  // de l'app, que les deux bandes suivantes détaillent déjà. Le mot nu
  // dit l'intention et laisse la page respirer.
  //
  // Pas de surtitre non plus : le titre annonce la liste et se termine
  // par deux points.
  homeAimsTitle: 'Ce que nous essayons de développer :',
  homeAims: ['La curiosité', "L'autonomie", "L'intuition", 'La résilience'],



  homeLoopEyebrow: "La boucle d'apprentissage",
  // Trois écrans, pas quatre. La réussite et l'erreur ne se suivent
  // jamais — `setPhase(good ? 'ok' : 'ko')` — ce sont les deux issues
  // du même moment. Les compter séparément décrivait un parcours qui
  // n'existe pas. La boucle est dans le titre, faute d'être un écran.
  homeLoopTitle: 'Trois écrans, et on recommence',
  homeLoop: [
    {
      title: 'La question',
      line: 'Une question par écran, quatre réponses au plus. Un tap suffit.',
    },
    {
      title: 'La correction',
      line: 'Juste ou faux, la bonne réponse s’affiche aussitôt. Rien n’est sanctionné : on situe votre choix, on ne le punit pas.',
    },
    {
      title: "L'explication",
      line: 'Le raisonnement, lu à voix haute si vous le souhaitez. Puis la question suivante arrive.',
    },
  ],

  // « Ce que la communauté rend possible » : il n'y a pas de communauté
  // qui produise quoi que ce soit — le catalogue est semé par script et
  // la création est fermée. Le titre dit maintenant ce que la section
  // fait vraiment, énumérer les fonctions de l'app.
  homeCommunityTitle: "Ce que l'app fait",
  homeCommunity: [
    {
      title: 'Choisir vos apprentissages',
      // « Rayons personnalisés » a disparu de l'écran : les trois rayons
      // éditoriaux — les plus suivis, les nouveaux, le voisinage de vos
      // choix — ont été retirés, aucun ne mesurait ce que son titre
      // annonçait. Reste la recherche et un rayon par catégorie.
      line: 'Une recherche sur tout le catalogue, puis un rayon par catégorie, rangé du sujet le plus large au plus précis. Ajout en un tap.',
    },
    {
      title: "Suivre un flux qui ne s'arrête pas",
      line: 'Les apprentissages suivis se mélangent, une question par écran, on passe au suivant en swipant vers le haut.',
    },
    {
      title: 'Écouter et lire',
      line: "Une voix lit la question, la correction et l'explication. Bandeau de lecture en haut de l'écran : pause, reprise, réécouter, ou coupé une fois pour toutes.",
    },
    {
      title: 'Voir où vous en êtes',
      line: 'Une barre de progression par apprentissage, un compteur de réussites et un compteur de questions à revoir, qui reviennent dans le flux.',
    },
    {
      title: 'Vous situer, si vous voulez',
      line: 'Un classement par apprentissage, sur 30 jours. Consultable, jamais imposé : l’onglet par défaut reste votre progression.',
    },
    {
      title: 'Réagir sur chaque question',
      // « Les auteurs voient ces retours et corrigent leurs questions » :
      // il n'y a pas d'auteur. Le catalogue est semé par script, aucun
      // chapitre n'a de propriétaire. Le pouce en bas fait autre chose,
      // et de plus intéressant : il met l'exercice en quarantaine tout
      // seul dès que les votes négatifs l'emportent.
      line: "J'aime, j'aime pas, commentaires. Une question que les pouces en bas emportent quitte le flux d'elle-même, en attente de relecture.",
    },
    // TROIS ENTRÉES SONT PARTIES D'ICI : « Partager une connaissance »,
    // « Écrire vos prompts », « Suivre vos partages ». Elles décrivaient
    // la création — dépôt de PDF, de photo, de mémo vocal, rédaction de
    // prompts, tableau de bord d'auteur. Ce chemin est fermé : ses routes
    // interrogent une table `category` qui n'existe plus, et elles
    // rendraient 500 derrière le 403 qui les garde.
    //
    // Ce qui ne peut pas être tenu ne s'écrit pas ici — c'est la règle
    // que la page s'était donnée, et c'est elle qui les retire.
    //
    // Une septième entrée les avait remplacées un moment, « Deux langues,
    // un seul classement ». Exacte, mais elle expliquait un choix
    // d'architecture — un exercice n'existe qu'une fois, sous un seul
    // identifiant, pour que les classements restent comparables. Ce n'est
    // pas une fonction qu'on utilise, c'est une raison qu'on a eue.
    // Retirée aussi. La liste ne garde que ce qui se fait à l'écran.
  ],

  // LA BANDE « D'OÙ VIENNENT LES QUESTIONS » A ÉTÉ RETIRÉE, avec ses
  // onze clés. Elle avait porté deux contenus : la création — fermée, ses
  // routes interrogent une table `category` supprimée — puis l'écriture à
  // la demande, l'extrait d'article et la question qui en sortait.
  //
  // Le second était exact, mais c'est de la fabrication : le visiteur
  // n'a pas à savoir d'où sortent les questions pour décider d'essayer.
  homeClosing: 'Une question. Sa réponse. Pourquoi.',
  homeClosingLine:
    'Aucun email demandé. Vous créerez un compte quand vous voudrez garder votre progression.',
  homeHow: 'Comment ça marche',

  // Ce que je partage
  whatIShare: 'Ce que je partage',
  whatIShareLead: 'Vos connaissances publiées, et ce qu’elles deviennent.',
  nothingShared: "Vous n'avez encore rien partagé.",
  usages: 'utilisations',
  pendingLabel: 'En relecture',
  publishIt: 'Publier',
  editExercises: 'Modifier les exercices',
  exercisesOf: 'Exercices',
  noExerciseYet: 'Aucun exercice pour le moment.',
  metricUnavailable: 'non mesuré',
  metricUnavailableLine:
    "Utilisations, j'aime et commentaires par connaissance ne sont pas encore remontés par l'API.",

  // Nous écrire
  contact: 'Contact',
  writeToUs: 'Nous écrire',
  help: 'Aide',
  contactHead: 'Écrivez-nous',
  contactLead:
    "Une erreur dans un exercice, une idée d'apprentissage, un souci de compte. On répond sous deux jours ouvrés.",
  contactLeadShort:
    'Une erreur dans un exercice, une idée, un souci de compte. Réponse sous deux jours ouvrés.',
  subject: 'Sujet',
  subjectReport: 'Signaler un exercice',
  subjectIdea: 'Proposer un apprentissage',
  subjectIdeaShort: 'Une idée',
  subjectTech: 'Problème technique',
  subjectTechShort: 'Technique',
  subjectOther: 'Autre',
  yourName: 'Nom',
  namePlaceholder: 'Comment vous appeler',
  message: 'Message',
  messagePlaceholder: "Dites-nous ce qui s'est passé…",
  charCount: (n: number, max: number) => `${n} / ${max.toLocaleString('fr-FR')}`,
  attach: "Joindre une capture d'écran",
  attachShort: 'Joindre une capture',
  attachHint: 'PNG, JPG · 5 Mo max',
  sendMessage: 'Envoyer le message',
  contactPrivacy: 'Vos réglages et votre progression ne sont pas transmis.',
  beforeWriting: "Avant d'écrire",
  beforeWritingLine:
    "Pour signaler une seule question, le bouton ⋯ sur l'exercice est plus rapide : il nous envoie directement l'exercice concerné.",
  faqTitle: 'Questions fréquentes',
  faqQ1: 'Puis-je utiliser SaraLearn sans compte ?',
  faqA1: "Oui. Le flux s'ouvre sans email et votre progression reste sur cet appareil. Le compte sert à la retrouver ailleurs.",
  faqQ2: 'Comment publier un apprentissage ?',
  faqA2: "Créez-le, relisez les exercices proposés, puis choisissez « rendre public » : il passe en relecture avant d'entrer au catalogue.",
  faqQ3: 'Qui écrit les exercices ?',
  faqA3: "Un modèle les rédige à partir du document déposé, et la personne qui a créé l'apprentissage valide chaque question avant publication.",
  faqQ4: 'Comment supprimer mes données ?',
  faqA4: "Écrivez-nous depuis cette page avec le sujet « Autre » : le compte et tout ce qui s'y rattache sont effacés sous huit jours.",
  byEmail: 'Par email',
  contactAddress: 'bonjour@saralearn.fr',
  replyDelay: 'Réponse sous deux jours ouvrés.',
  messageSent: 'Message envoyé',
  sentHead: "C'est parti",
  sentLine: (email: string) => `On vous répond à ${email} sous deux jours ouvrés.`,
  sentMailNote:
    "Votre logiciel de messagerie s'ouvre avec le message prêt à partir — il ne reste qu'à l'envoyer.",
  writeAnother: 'Écrire un autre message',

  // Connexion — ce que garde un compte
  whatYouKeep: 'Ce que vous gardez',
  keepThemes: (n: number) => `${n} apprentissage${n > 1 ? 's' : ''} suivi${n > 1 ? 's' : ''}`,
  keepThemesLine: (names: string) => names,
  keepPassed: (n: number) => `${n} exercice${n > 1 ? 's' : ''} réussi${n > 1 ? 's' : ''}`,
  keepPassedLine: (n: number) => `Et ${n} à revoir, qui reviendront dans le flux.`,
  keepCreated: (n: number) => `${n} apprentissage${n > 1 ? 's' : ''} créé${n > 1 ? 's' : ''}`,
  keepCreatedLine: 'Vos prompts et vos exercices validés.',
  localProgress: 'Progression locale',
  localProgressWarn: 'Sans compte, tout cela disparaît si vous changez de navigateur.',
  nothingKeptYet: "Rien pour l'instant — un exercice suffit pour commencer.",
  legalLine: 'Conditions · Confidentialité',

  // Génération
  genReady: (n: number) => `C'est prêt · ${n} exercices`,
  genReadyLine: "Vous pouvez fermer l'app pendant la génération, rien n'est perdu.",
  goToValidation: 'Passer à la validation',
  writingHead: "L'IA écrit vos exercices",
  writingSub:
    'Environ deux minutes. Les explications des mauvaises réponses sont rédigées en dernier.',
  writtenCount: (n: number) => `${n} exercice${n > 1 ? 's' : ''} écrit${n > 1 ? 's' : ''}`,
  keepPracticing: "Continuer à s'entraîner pendant ce temps",
}

/**
 * Le dictionnaire anglais est typé d'après le français : une clé
 * oubliée ou en trop est une erreur de compilation.
 */
export type Dict = typeof fr

const en: Dict = {
  swipeHint: 'Swipe to skip',
  codeBanner: 'Shared quiz',
  codeDoneTitle: 'You have done them all.',
  codeDoneLine:
    'This shared quiz has nothing more for you. You can run it again, or go back to the full flow.',
  codeRestart: 'Run it again',
  codeLeave: 'Leave',
  codeSearchHint: 'Or paste a share code',
  codeNotFound: 'No quiz carries this code.',
  codeLabel: 'Share code',
  codeCopy: 'Copy',
  codeCopied: 'Copied',
  nextExercise: 'Next exercise',
  seeExplanation: 'See the explanation',
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
  preparingLong: 'Writing the questions for this learning. About half a minute.',
  serverDown: 'The server is not responding.',
  serverDownHint: 'We keep trying on our own. You can also reload.',
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
  letsGo: 'Let’s go',
  themesCount: (n) => `${n} learning${n > 1 ? 's' : ''}`,
  skip: 'Skip',

  addThemes: 'Add topics',
  allThemes: 'All topics',
  themesOfChosen: 'Topics in the chosen categories',
  createOwn: 'Create my own topic',
  continue: 'Continue',
  subCategories: 'Subcategories',
  level2: 'Level 2 of 2',

  themes: 'Topics',
  noThemeFollowed: 'No learning followed — we serve a bit of everything.',
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
  languageSub: 'Also changes which learnings you get',
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
  menu: 'Menu',
  settingsLead: 'Sound, appearance, language and your account. Nothing else.',
  signupLang: 'Learning language',
  signupLangSub: 'It decides which catalogue you are offered. You can change it in settings.',
  myAccount: 'My account',

  myStrengths: 'My strengths',
  others: 'Others',
  strengthsIntro: 'From the best mastered to the one still needing work.',
  noStrengthsYet: 'Do a few exercises and your strengths will show up here.',
  nobodyYet: 'Nobody has played yet this week.',
  thisWeek: 'This week',
  myProgress: 'My progress',
  rankLead: 'Your progress, and everyone else’s',
  byTheme: 'By learning',
  rankOnLearning: 'Ranking on a learning',
  yourStrength: 'Your strong suit',
  toResume: 'Worth revisiting',
  participants: (n) => `${n} participant${n > 1 ? 's' : ''}`,
  yourPlace: 'Your place on this learning',
  sharedNotFound: 'That piece of knowledge does not exist, or is not yours.',
  exercisesPassed: 'exercises passed',
  statToReview: 'to review',
  points: 'points',
  weeklyReset: 'A learning ranking resets every Monday.',
  you: 'You',

  themeBlurb: (name) =>
    `Short exercises on ${name.toLowerCase()}. Mixed in with your other learnings.`,
  exercises: 'exercises',
  subscribers: 'subscribers',
  yourProgressHere: 'Your progress here',
  passed: 'passed',
  subscribed: 'Subscribed — unsubscribe',
  subscribe: 'Follow this learning',
  seeThemeRanking: 'See this learning’s ranking',
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
  newLearning: 'New learning',
  createClosedTitle: 'Admins only',
  createClosedLine:
    'Sharing a learning is open to administrators for now. The catalogue writes itself: pick a learning and its questions are written when you open it.',
  createClosedBack: 'Back to the exercises',
  markdownPlaceholder: '# Lesson title\n\nA major chord is made of…',
  titlePlaceholder: 'Guitar chords — the basics',
  descriptionPlaceholder: 'Open chords, their thirds, and the classic fingering mistakes.',
  dropWhatYouHave: 'Drop in what you have.',
  pasteMarkdown: 'Paste your lesson in Markdown',
  pasteMarkdownSub: 'The exercises will be written from this text, and this text alone.',

  subjectHint: 'A subject is enough. I will handle the title, the plan and the exercises.',
  subjectPlaceholder: 'PHP functions',
  propose: 'Draft a programme',
  thinkingHead: 'Preparing your programme.',
  thinkingLine: 'A few seconds: I look for the plan, then break it down.',
  yourKnowledge: 'Here is your knowledge.',
  presentLead: 'Everything is pre-filled. Fix what is wrong, add what is missing.',
  tagsDetected: 'Detected tags',
  newCategoryNote: (label: string) =>
    `“${label}” did not exist, so I created it. It stays out of the catalogue until you keep it.`,
  programme: 'Programme',
  chapterCount: (n: number) => `${n} chapter${n > 1 ? 's' : ''}`,
  writePromptsAction: 'Prepare the questions',
  writeExercises: 'Write the exercises',
  validateAll: 'Approve all',
  validateOneByOne: 'Review one by one',
  reviewedByCritic: 'An automatic reviewer already dropped what did not hold. Approve them all, or read through.',
  preparingHead: 'Preparing the questions.',
  preparedCount: (done: number, total: number) => `${done} of ${total} chapters`,
  chaptersHead: 'How each chapter will be tested.',
  exampleLabel: 'Example',
  noExample: 'No preview for this chapter — the questions will still be written.',
  chapterFailed: 'Preparation failed for this chapter.',
  retryChapter: 'Try again',
  askedAs: 'Tested as',
  typeQcm: 'multiple choice',
  typeComplete: 'fill the gap',
  typeFindError: 'spot the error',
  typeShortAnswer: 'write the answer',
  typeCloze: 'gapped text',
  title: 'Title',
  description: 'Description',
  analyse: 'Analyse',
  proposed: 'Suggested — correct freely',
  hereIsClassing: 'Here is how I would file it.',
  category: 'Category',
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
  summary: 'Summary',
  validatedExercises: (n: number) => `${n} validated exercise${n > 1 ? 's' : ''}`,
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
  metaTitle: 'SaraLearn — endless learning',
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

  pauseReading: 'Pause reading',
  resumeReading: 'Resume reading',
  replayReading: 'Play again',

  follow: 'follow',
  followed: 'following',
  unfollow: 'Unfollow',
  exercisesNav: 'Exercises',
  localAccount: 'Local account',
  learnings: 'Learnings',
  myLearnings: 'My learnings',
  addLearnings: 'Add learnings',
  learningsCount: (n) => `${n} learning${n > 1 ? 's' : ''}`,
  exercisesCount: (n) => `${n} exercise${n > 1 ? 's' : ''}`,
  exercisesShort: (n) => `${n} ex.`,
  shareKnowledge: 'Share what you know',
  shareKnowledgeLine: 'Drop in a document, the AI writes the exercises, you approve them.',
  searchLearning: 'Search a learning, a category, a tag',
  followedTab: 'Following',
  suggestedTab: 'Suggested',
  startedTab: 'Started',
  createdByMeTab: 'Created by me',
  popularTab: 'Popular',
  themesMeta: (followed, total) => `${followed} followed · ${total} available`,
  suggestions: 'Suggestions',
  suggestedForYou: 'Suggested for you',
  nearYourLearnings: 'close to your learnings',
  noPopular: 'Nothing to rank yet.',
  promptsCount: (n) => `${n} prompt${n > 1 ? 's' : ''}`,
  learnersCount: (n) => (n > 1 ? `${n} people did it` : `${n} person did it`),
  themeDetail: 'Learning detail',
  resumeCreation: 'Resume the creation',
  promptsList: 'The prompts',
  promptsShort: 'prompts',
  learnersShort: 'practised',
  noPromptYet: "No prompt — this learning didn't go through the programme.",
  promptNotWritten: 'Prompt not written yet.',
  showAll: 'Show all',
  showLess: 'Collapse',
  chapterRejected: 'discarded',
  followedShort: 'Following',
  followShort: 'Follow',
  unfollowShort: 'Remove',
  noThemeStarted: 'Nothing started yet — answer an exercise and it shows up here.',
  noThemeCreated: "You haven't shared anything yet.",
  startSharing: 'Get started',
  nothingToSuggest: 'You already follow everything we have here.',
  categories: 'Categories',
  followAll: 'Follow all',
  addToFeed: 'Add to the flow',

  pickerMeta: (themes, cats) =>
    `${themes} learning${themes > 1 ? 's' : ''} · ${cats} categor${cats > 1 ? 'ies' : 'y'}`,
  searchCatalogue: (n) => `Search across ${n} learnings`,
  sortPopular: 'Popular',
  sortNew: 'New',
  filters: 'Filters',
  filterFollowedOnly: 'Only the ones I follow',
  filterHideFollowed: 'Hide the ones I follow',
  searchResults: 'Results',
  selection: 'Selection',
  clearSelection: 'Clear the selection',
  moreOthers: (n) => `+ ${n} more`,
  feedEstimate: (n) =>
    `About ${n.toLocaleString('en-GB')} exercise${n > 1 ? 's' : ''} added to the flow.`,
  emptySelection: 'Nothing selected yet.',
  noMatch: 'No learning matches.',

  addShort: 'Add',
  whyHereTitle: 'You are not following any learning yet',
  whyHereLine:
    'That is why you landed here. With no subscription the feed serves you a bit of everything, at random. Tap a learning below to follow it: your exercises will then come from what you picked.',
  whatToLearn: 'What do you want to learn?',
  becauseYouFollow: (name) => `Because you follow ${name}`,
  mostFollowed: 'Most followed',
  newlyAdded: 'New',
  seeAll: 'See all',
  byCategory: 'By category',
  addThis: 'Add',
  addedThis: 'Added',
  cancelSearch: 'Cancel',
  resultsIn: (n, cats) =>
    `${n} result${n > 1 ? 's' : ''} in ${cats} categor${cats > 1 ? 'ies' : 'y'}`,
  inCategory: (label) => `In ${label}`,
  questionsCount: (n) => `${n} question${n > 1 ? 's' : ''}`,
  addedCount: (n) => `${n} added`,
  approxQuestions: (n) => `≈ ${n.toLocaleString('en-GB')} questions`,
  finish: 'Done',
  emptyCatalogue: 'The catalogue is empty for now.',

  stepOf: (n, total) => `${n} / ${total}`,
  whatInterestsYou: 'What are you interested in?',
  searchOrPick: 'Search, or pick from the suggestions.',
  refine: 'Fine-tune',
  refineLead: 'Everything is ticked. Untick what does not speak to you.',
  uncheckAll: 'Untick all',
  continueLabel: 'Continue',

  pseudoTitle: 'What should we call you?',
  pseudoLead:
    'A nickname is enough — no email, no password. It shows on the leaderboard and under your comments, and you can change it any time in the settings.',
  pseudoPlaceholder: 'Your nickname',
  pseudoSave: 'Got it',
  pseudoTooShort: 'At least two characters.',
  pseudoNoPassword: 'No password: this device is already recognised.',
  pseudoWhereTitle: 'Where it shows',
  pseudoWhereRank: 'Instead of “Player 179”, on every learning’s leaderboard.',
  pseudoWhereComments: 'Under your comments, instead of “Anonymous”.',
  pseudoLocal:
    'It lives on this device until you have an account. The day you create one — to share what you know — it follows you.',
  pseudoCardTitle: 'Choose my nickname',
  pseudoLabel: 'Nickname',
  pseudoNone: 'No nickname yet',

  homeTry: 'Try it',
  homeKicker: 'Quizzes written on demand',
  homeTitle: 'Learn about the world around us',
  homeLead:
    'Light, the sky, the Earth, animals, the human body. One question per screen, and you learn how things work, not just what they are called.',
  homeStartLearning: 'Start learning',

  // Exercise 58, from the database — chapter “Sunlight”. See the French
  // block for why the old true/false preview had to go.
  previewTheme: 'Sunlight · The Sun and more',
  previewType: 'Multiple choice',
  previewQuestion: 'Why do we see a red sky at sunrise and sunset?',
  previewOptions: [
    'Due to scattering of blue light',
    'Due to absorption of red light',
    'Due to the Moon’s reflection',
  ],

  homeAimsTitle: 'What we are trying to develop:',
  homeAims: ['Curiosity', 'Autonomy', 'Intuition', 'Resilience'],

  homeLoopEyebrow: 'The learning loop',
  homeLoopTitle: 'Three screens, then it starts over',
  homeLoop: [
    {
      title: 'The question',
      line: 'One question per screen, four answers at most. One tap is enough.',
    },
    {
      title: 'The correction',
      line: 'Right or wrong, the answer appears at once. Nothing is penalised: your choice is shown in context, not marked wrong.',
    },
    {
      title: 'The explanation',
      line: 'The reasoning, read aloud if you want it. Then the next question arrives.',
    },
  ],

  homeCommunityTitle: 'What the app does',
  homeCommunity: [
    {
      title: 'Choose your learnings',
      line: 'One search across the whole catalogue, then one row per category, ordered from the broadest topic to the narrowest. Added with a tap.',
    },
    {
      title: 'Follow a flow that never stops',
      line: 'Everything you follow gets mixed in, one question per screen, swipe up for the next.',
    },
    {
      title: 'Listen and read',
      line: 'A voice reads the question, the correction and the explanation. Playback bar at the top of the screen: pause, resume, replay, or off for good.',
    },
    {
      title: 'See where you stand',
      line: 'A progress bar per learning, a counter of wins and a counter of questions to revisit, which come back in the flow.',
    },
    {
      title: 'See how you compare, if you want to',
      line: 'A leaderboard per learning, over 30 days. Available, never imposed: the default tab stays your own progress.',
    },
    {
      title: 'React on every question',
      line: 'Like, dislike, comments. A question the dislikes carry off leaves the flow on its own, pending review.',
    },
  ],

  homeClosing: 'One question. Its answer. Why.',
  homeClosingLine:
    'No email required. Create an account whenever you want to keep your progress.',
  homeHow: 'How it works',

  whatIShare: 'What I share',
  whatIShareLead: 'What you published, and what became of it.',
  nothingShared: 'You have not shared anything yet.',
  usages: 'uses',
  pendingLabel: 'In review',
  publishIt: 'Publish',
  editExercises: 'Edit the exercises',
  exercisesOf: 'Exercises',
  noExerciseYet: 'No exercise yet.',
  metricUnavailable: 'not measured',
  metricUnavailableLine:
    'Plays, likes and comments per shared learning are not reported by the API yet.',

  contact: 'Contact',
  writeToUs: 'Write to us',
  help: 'Help',
  contactHead: 'Write to us',
  contactLead:
    'A mistake in an exercise, an idea for a learning, an account problem. We answer within two working days.',
  contactLeadShort:
    'A mistake in an exercise, an idea, an account problem. Answer within two working days.',
  subject: 'Subject',
  subjectReport: 'Report an exercise',
  subjectIdea: 'Suggest a learning',
  subjectIdeaShort: 'An idea',
  subjectTech: 'Technical problem',
  subjectTechShort: 'Technical',
  subjectOther: 'Other',
  yourName: 'Name',
  namePlaceholder: 'What to call you',
  message: 'Message',
  messagePlaceholder: 'Tell us what happened…',
  charCount: (n, max) => `${n} / ${max.toLocaleString('en-GB')}`,
  attach: 'Attach a screenshot',
  attachShort: 'Attach a screenshot',
  attachHint: 'PNG, JPG · 5 MB max',
  sendMessage: 'Send the message',
  contactPrivacy: 'Your settings and your progress are not sent along.',
  beforeWriting: 'Before you write',
  beforeWritingLine:
    'To report a single question, the ⋯ button on the exercise is quicker: it sends us that exercise directly.',
  faqTitle: 'Frequent questions',
  faqQ1: 'Can I use SaraLearn without an account?',
  faqA1: 'Yes. The flow opens without an email and your progress stays on this device. An account is what lets you find it elsewhere.',
  faqQ2: 'How do I publish a learning?',
  faqA2: 'Create it, review the proposed exercises, then choose “make public”: it goes through review before entering the catalogue.',
  faqQ3: 'Who writes the exercises?',
  faqA3: 'A model drafts them from the document you drop in, and whoever created the learning approves every question before publication.',
  faqQ4: 'How do I delete my data?',
  faqA4: 'Write to us from this page with the “Other” subject: the account and everything attached to it are erased within eight days.',
  byEmail: 'By email',
  contactAddress: 'bonjour@saralearn.fr',
  replyDelay: 'Answer within two working days.',
  messageSent: 'Message sent',
  sentHead: 'On its way',
  sentLine: (email) => `We will answer you at ${email} within two working days.`,
  sentMailNote: 'Your mail app opens with the message ready — all that is left is to send it.',
  writeAnother: 'Write another message',

  whatYouKeep: 'What you keep',
  keepThemes: (n) => `${n} learning${n > 1 ? 's' : ''} followed`,
  keepThemesLine: (names) => names,
  keepPassed: (n) => `${n} exercise${n > 1 ? 's' : ''} passed`,
  keepPassedLine: (n) => `And ${n} to revisit, which will come back in the flow.`,
  keepCreated: (n) => `${n} learning${n > 1 ? 's' : ''} created`,
  keepCreatedLine: 'Your prompts and your approved exercises.',
  localProgress: 'Local progress',
  localProgressWarn: 'Without an account, all of this disappears if you change browser.',
  nothingKeptYet: 'Nothing yet — one exercise is enough to start.',
  legalLine: 'Terms · Privacy',

  genReady: (n) => `Ready · ${n} exercises`,
  genReadyLine: 'You can close the app while it writes, nothing is lost.',
  goToValidation: 'Move on to the review',
  writingHead: 'The AI is writing your exercises',
  writingSub: 'About two minutes. Explanations for wrong answers are written last.',
  writtenCount: (n) => `${n} exercise${n > 1 ? 's' : ''} written`,
  keepPracticing: 'Keep practising meanwhile',
}

const DICTS: Record<Lang, Dict> = { fr, en }

export function dict(lang: Lang): Dict {
  return DICTS[lang] ?? en
}

/**
 * Langue de départ : l'anglais, pour tout le monde.
 *
 * On ne lit plus `navigator.language`. Deviner d'après le navigateur
 * servait un catalogue français à qui n'avait rien demandé — et la
 * langue ne change pas que des libellés ici, elle change les
 * apprentissages proposés (voir `theme.lang`). Un seul point de départ,
 * et le choix se fait à la main : `LangSwitch` est visible dans le
 * cadre de l'app, pas au fond des réglages.
 *
 * Ce départ ne vaut qu'à la première visite : un choix déjà fait est
 * relu depuis les préférences, et la langue du compte prime ensuite.
 */
export function defaultLang(): Lang {
  return 'en'
}
