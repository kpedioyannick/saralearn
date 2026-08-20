# Sara — app d'exercices

Flux vertical d'exercices sans fin. Implémentation de la maquette
`App exercices.dc.html` (projet Claude Design `7c5da877`), qui s'appuie sur les tokens
du **Réviz Design System**.

```bash
# API
sqlite3 data/sara.db < db/schema.sql
sqlite3 data/sara.db < db/seed_prompts.sql
sqlite3 data/sara.db < db/seed_prompts_en.sql
sqlite3 data/sara.db < db/migrations/002_langues.sql
sqlite3 data/sara.db < db/seed_demo.sql
sqlite3 data/sara.db < db/seed_demo_en.sql
python3 -m uvicorn api.main:app --port 8010     # /docs pour l'OpenAPI

# Front
npm install
npm run dev        # http://localhost:5174
npm run build      # tsc + vite build + garde-fou de déploiement
npm run typecheck
```

## Le parcours

```
EXERCICE ──répond──> FÉLICITATION ou ERREUR ──> EXPLICATION ──> EXERCICE SUIVANT
    │                                                                  ▲
    └──────────────── swipe / molette / ↑ ↓ sans répondre ─────────────┘
```

Trois entrées équivalentes pour changer d'exercice : **swipe vertical**, **molette**,
**flèches ↑ ↓**. Le geste est entièrement contrôlé (`src/lib/useDeckGestures.ts`) —
pas de `scroll-snap`, qui saccade sur iOS dès qu'on veut interrompre un scroll natif.

## Décisions du design

La maquette tranche plusieurs points laissés ouverts par le cahier des charges initial
(voir `ANALYSE_TECH.md`). **Le design fait foi.**

| Point | Analyse initiale | Retenu |
|---|---|---|
| Loader | bloque le swipe | **ne bloque pas** — il donne le rythme et enchaîne seul |
| Rail | à gauche | **à droite** |
| Après réponse | à trancher | **enchaînement automatique** vers félicitation/erreur, puis explication |
| Audio | fichiers TTS pré-générés | **WebAudio synthétisé** — zéro latence, zéro octet |

Rythme : exercice 3 s · félicitation 2 s · erreur 6 s · explication 8 s.
Ces trois réglages se changent dans `src/config.ts` — dont `BLOCKING_LOADER`, qui
rétablit le gate d'origine.

## Ce que le code garantit

- **Un écran, pas de scroll** sur l'exercice. Vérifié à 390 × 844.
- **Le rail ne recouvre jamais une réponse** — la question a 70 px de marge à droite,
  les boutons font 298 px de large.
- **Erreur non punitive** : aucune croix, aucun rouge. Ambre de reprise, bonne réponse
  en vert calme, ligne en italique.
- **Aucun pourcentage pendant les exercices.** Ils ne vivent que dans Réglages ›
  Progression et dans le Classement.
- **Jamais la répartition des réponses** option par option — ça donnerait la solution.
- **Cibles tactiles de 44 px** : le rail les respecte nativement ; les pastilles de
  retrait de 22 px voient leur zone étendue par `.hit-44` sans changer de visuel.

## Audio

Trois signatures synthétisées (`src/lib/audio.ts`), jamais sur l'écran exercice :

| Écran | Son |
|---|---|
| Félicitation | quinte montante (659 → 988 Hz) |
| Erreur | tierce descendante douce (392 → 311 Hz) |
| Explication | note tenue (523 Hz) |

iOS et Android refusent tout son sans geste préalable. `unlock()` est appelée au tout
premier `pointerdown` de la session — **sans ça le premier son est muet, et ça ne se
reproduit pas sur desktop**. L'état coupé/activé est mémorisé en `localStorage`.

## Structure

```
src/
  config.ts               réglages hérités de la maquette
  data/content.ts         exercices, catégories, classement — remplacé par /feed en prod
  lib/audio.ts            moteur WebAudio + unlock
  lib/useDeckGestures.ts  pointeur, molette, clavier
  lib/useIsDesktop.ts     bascule à 1024 px
  state/store.tsx         machine de phases, loader rAF, compteurs, préférences
  components/             Icon, Rail, OptionButton, PhaseBlocks, Sheet, Toast, ui
  screens/                Exercise, Onboarding, Picker, Settings, Rank, Create,
                          Publish, Auth, DesktopFrame
  styles/tokens.css       tokens Réviz + thèmes runtime --sc-*
  styles/app.css          composants, keyframes, prefers-reduced-motion
```

Toute la peinture passe par les variables `--sc-*`. Un composant ne référence une
couleur en dur que pour les pastilles de thème (données) et les couleurs sémantiques,
qui sont déclinées pour les deux fonds.

## Index des écrans

Le fragment d'URL ouvre n'importe quel écran — utile pour la revue design :

```
#exercise  #exercise/ok  #exercise/ko  #exercise/exp
#welcome  #categories  #subcategories  #add-themes  #all-themes
#settings  #themes  #leaderboard  #leaderboard-theme
#create  #publish  #sign-in  #about  #admin
```

Ce sont les **routes**, définies dans `ROUTES` (`src/state/store.tsx`), et non les
identifiants internes d'écran (`exo`, `rank`, `auth`) : `#exo` n'ouvre rien et l'URL
est réécrite en silence.

`#admin` demande le jeton d'administration (voir *Configuration*).

## Base de données

SQLite pour l'instant (`data/sara.db`), MySQL plus tard — le même modèle est porté
dans `db/*.mysql.sql`, à reprendre le jour où on bascule.

```bash
sqlite3 data/sara.db < db/schema.sql        # 13 tables, 3 vues, 2 triggers
sqlite3 data/sara.db < db/seed_prompts.sql  # 20 gabarits (5 types × 4 Bloom)
sqlite3 data/sara.db < db/seed_demo.sql     # le contenu de src/data/content.ts
```

```
category ──> theme ─< theme_tag >─ tag
               │  (source_markdown, visibility)
               └─< exercise_prompt >── prompt
                        │              (type_question × type_bloom, versionné)
                        └─< exercise
```

Côté usage : `app_user`, `user_theme`, `attempt`, `exercise_like`, `exercise_comment`.

Trois partis pris :

- **Aucune table de compteurs.** Réussites, échecs et progression se dérivent
  d'`attempt`. Une table de compteurs finit toujours désynchronisée.
- **`exercise_prompt` garde le texte exact envoyé au modèle**, pour remonter d'un
  exercice douteux au prompt qui l'a écrit. Les gabarits sont versionnés : les
  améliorer n'efface pas cette trace.
- **Les limites de longueur sont des contraintes SQL**, pas des règles d'interface :
  question 240 caractères, explication 600. « Un écran, pas de scroll » se tient à
  l'écriture.

Barème du classement, dans `v_theme_week_rank` : une bonne réponse vaut 10, une
tentative vaut 2, un exercice passé au swipe ne rapporte rien. Remise à zéro le lundi.
**C'est une hypothèse** — la maquette affiche des points sans dire d'où ils sortent.

## API

FastAPI + SQLite, aucune dépendance ajoutée à la machine (jetons signés HMAC avec la
bibliothèque standard plutôt qu'une bibliothèque JWT, contrainte email plutôt que
`email-validator`).

| Domaine | Points d'entrée |
|---|---|
| Compte | `POST /auth/anonymous` · `/auth/signup` · `/auth/login` · `GET /auth/me` |
| Flux | `GET /feed` · `POST /attempts` |
| Réactions | `POST\|DELETE /exercises/{id}/like` · `GET\|POST /exercises/{id}/comments` |
| Thèmes | `GET\|POST /themes` · `GET\|PATCH\|DELETE /themes/{id}` · `/publish` · `/subscribe` |
| Génération | `POST /themes/{id}/generate` · `GET /themes/{id}/generation` · `PATCH /exercises/{id}` |
| Progression | `GET /progression` · `/rank/global` · `/rank/theme/{id}` · `GET\|PUT /settings` |

**L'app ouvre sans compte.** `POST /auth/anonymous` lie une session à un identifiant
d'appareil. Créer un compte ensuite attache l'email à la **même ligne** — rien à
déplacer. Se connecter à un compte existant depuis une session anonyme déplace
tentatives, j'aime, commentaires et abonnements, puis supprime l'anonyme.

**Le feed renvoie `correct_index`.** Choix assumé : le retour est instantané et
fonctionne hors ligne, la tentative part en arrière-plan. Le coût est qu'un curieux
lit la réponse dans le DevTools — sans enjeu sur une app d'apprentissage sans note.

**La génération est asynchrone.** Un lancement crée une ligne `exercise_prompt` par
couple (type × Bloom), avec le texte exact envoyé au modèle. Les exercices arrivent en
`draft` : rien n'entre au feed sans relecture. Le service LLM se configure par
`SARA_LLM_URL` (défaut : le proxy local sur 8003).

## Créer une connaissance

L'auteur écrit un sujet — « les fonctions PHP », « l'imparfait de l'indicatif ». Rien
d'autre : ni titre, ni catégorie, ni cours. Deux appels au modèle en tirent le reste.

```
sujet ──> POST /knowledge/outline
          titre · description · catégorie · 3 à 5 chapitres · tags
             │  l'auteur corrige et valide
             └> POST /knowledge/{id}/prompts
                un prompt, un type de question et un exemple PAR CHAPITRE
                   │  l'auteur relit et valide
                   └> POST /knowledge/{id}/generate
                      les exercices, en draft, comme avant
```

| Table | Rôle |
|---|---|
| `theme` | la connaissance |
| `chapter` | son programme — `generated_prompt`, `type_question`, `example` |
| `exercise_prompt` | un lancement, citant `chapter_id` **ou** `prompt_id`, jamais les deux |

**Le programme appartient à la connaissance, pas à la taxonomie.** « Déclarer une
fonction » n'a de sens que dans « Les fonctions en PHP », là où une catégorie doit
servir cent thèmes. Un programme de trois à cinq chapitres ne tient pas dans un niveau
de classement.

**Un seul niveau de classement.** `sub_category` a été retirée (migration 013) : une
seule sous-catégorie a jamais existé, « Auto » sous « Permis de conduire », et l'écran
de création ne l'a jamais proposée — 93 des 106 thèmes n'en portaient aucune. Un
deuxième niveau qu'aucun chemin ne remplit n'est pas une taxonomie, c'est une colonne.

**Le modèle crée les catégories, mais reconnaît avant de créer.** Il reçoit les
catégories existantes et doit dire si l'une convient ; un dernier filet compare le nom
proposé aux libellés en place. Sans ça, « Programmation », « Développement » et
« Code » cohabitent au bout d'un mois sans que personne ne l'ait décidé — et une
taxonomie qui se dédouble ne se recolle pas. Une catégorie créée naît en `draft` et
n'entre au catalogue qu'une fois retenue : sinon chaque essai abandonné en laisse une.

**Le prompt d'un chapitre est composé, pas recopié.** Le modèle n'écrit que les
consignes pédagogiques ; le contrat de sortie — quatre options pour un QCM, `exp_text`
obligatoire, libellés sous 60 caractères — est écrit dans `api/chapters.py` et scellé
par-dessus. Un modèle à qui on demande d'inventer ce contrat le réinvente à chaque
appel, et les exercices sont écartés en silence à l'insertion.

**`cloze` est exclu du choix du modèle.** `llm.validate` ne conserve que le libellé de
chaque option et laisse tomber `blank` et `correct` : un texte à trous produit par
cette voie perd le lien entre ses candidats et ses trous. Les neuf en base viennent des
scripts, qui passent par `api/critic.py`. À rouvrir quand `validate` saura les lire.

**Tout s'écrit en base au fil de l'eau, en brouillon** — thème `private`, chapitres et
catégorie `draft`. Une création interrompue se reprend par `GET /knowledge/{id}`, et on
garde la trace de ce que le modèle a proposé même quand l'auteur le corrige.

Les deux chemins coexistent : `POST /themes/{id}/generate` part toujours des 42
gabarits versionnés et du Markdown déposé. Le dépôt de documents a seulement disparu de
l'écran, pas de l'API.

### Ce qui reste à surveiller

Le modèle penche vers `short_answer` et rate son exemple une fois sur deux quand il le
choisit — l'aperçu est alors écarté, le chapitre non. Trois tours de consigne ont été
nécessaires pour arriver là : le premier abusait de `short_answer`, le deuxième l'a
supprimé jusque sur « conjuguer les verbes du 1er groupe », où écrire la forme est
justement l'exercice. L'auteur voit le type et peut le changer avant de valider.

Et surtout : **il n'y a plus de source vérifiable.** Le modèle écrit sur ce qu'il sait.
Acceptable sur les fonctions PHP, discutable sur « Permis de conduire », où le pipeline
des panneaux — lui adossé à une ligne de `sign` — reste le seul à garantir ce qu'il
affirme. Rien ne distingue les deux dans l'interface.

## Français et anglais

Deux plans distincts, à ne pas confondre :

- **L'interface est traduite** — `src/i18n.ts`. Le dictionnaire anglais est typé
  d'après le français : une clé oubliée est une erreur de compilation.
- **Un thème est écrit dans une langue**, il n'est jamais traduit. `theme.lang` et
  `prompt.lang` : on ne sert pas un exercice français à quelqu'un qui lit l'app en
  anglais, et on ne demande pas un exercice français avec des consignes anglaises.

Changer de langue change donc **le catalogue servi**, pas seulement les libellés. Si
aucun thème suivi n'existe dans la nouvelle langue, le feed retombe sur le catalogue
public de cette langue — sinon basculer viderait l'écran.

La taxonomie, elle, est traduite (`category.label_en`). Colonne plutôt que table de
traductions : deux langues annoncées, et une jointure de moins sur le chemin du feed.
À revoir si une troisième arrive.

## Types de questions

Le catalogue des designers (projet Claude Design `7c5da877`) en définit **quatorze** ;
cinq sont autorisés en base, **cinq** sont servis :

| Type | Geste | En base |
|---|---|---|
| `qcm` | taper une option parmi quatre | 628 |
| `find_error` | désigner le fragment fautif | 130 |
| `complete` | choisir la forme qui remplit le trou | 128 |
| `short_answer` | **écrire** la réponse | 9 |
| `cloze` | remplir plusieurs trous, un à un | 9 |

Les trois premiers demandent tous le même geste : *reconnaître* la bonne réponse parmi
des propositions. Les deux derniers demandent de **produire** — c'est l'écart entre
reconnaître « allées » et savoir l'écrire.

**`short_answer`** — `options` ne contient pas des choix mais les **graphies acceptées**,
`correct_index` désignant la forme canonique (celle qu'on affiche en correction). La
comparaison passe par la normalisation de la maquette : minuscules, accents retirés,
ponctuation remplacée par des espaces. Elle **ne retire pas les articles** : « l'aorte »
devient « l aorte », d'où la nécessité de lister les variantes. Une seule graphie
acceptée est refusée par `api/critic.py` — un élève écrira le pronom ou l'article.

**`cloze`** — `body` porte le texte, chaque trou marqué par `…` (U+2026). Toutes les
options vivent dans la même liste et portent `blank` (l'indice du trou) et `correct`.
`correct_index` ne veut rien dire pour ce type. Règle du designer, appliquée par le
critique : **chaque trou a ses propres candidats**, jamais une banque commune — sinon
l'élève élimine par recoupement au lieu de savoir.

## Migrations

```bash
python3 scripts/migrate.py db/migrations/007_saisie_libre_et_trous.sql
```

**Ne joue jamais une migration avec `sqlite3 base < fichier`.** Le client en ligne de
commande *poursuit après une erreur* : sur une migration qui reconstruit une table, une
instruction fautive n'empêche pas le `DROP TABLE` suivant de s'exécuter. C'est arrivé
deux fois ici — 619 panneaux, puis 886 exercices.

`scripts/migrate.py` sauvegarde, joue le script avec `executescript` (qui s'arrête à la
première erreur), vérifie l'intégrité et les clés étrangères, et **restaure
automatiquement** en cas d'échec.

Deux pièges rencontrés en reconstruisant `exercise` :
- les **vues** qui lisent la table doivent être supprimées puis recréées dans la même
  transaction, sinon le `RENAME` bute sur elles ;
- les **clés étrangères ne sont pas actives par défaut** dans SQLite. Il faut
  `PRAGMA foreign_keys = ON` à chaque connexion — sans lui, supprimer des exercices
  laisse des tentatives et des votes orphelins, que la migration suivante refusera.

## Sauvegardes

La base porte **tout le contenu** : exercices, thèmes, comptes, votes. Le dépôt git ne
la contient pas — elle change à chaque réponse d'élève et contient des données
personnelles. Elle n'a donc qu'une seule protection : ces sauvegardes.

```bash
python3 scripts/sauvegarde.py                      # ponctuelle
python3 scripts/sauvegarde.py --vers /media/disque --garder 30
systemctl list-timers sara-sauvegarde              # la quotidienne
```

Un timer systemd la déclenche **chaque nuit à 3 h 20**, garde les **14 dernières** et
supprime le reste. `Persistent=true` rattrape la sauvegarde si la machine était éteinte.

**Ne sauvegarde jamais avec `cp sara.db ailleurs`.** SQLite est en mode WAL : les
écritures récentes vivent dans `sara.db-wal` et pas encore dans le fichier principal.
Copier l'un sans l'autre produit une base tronquée, et on ne s'en aperçoit qu'au moment
de restaurer. `scripts/sauvegarde.py` passe par `Connection.backup()`, qui prend un
instantané cohérent pendant que l'API continue d'écrire — puis **relit la copie** et
vérifie son intégrité avant de la conserver. Une sauvegarde qu'on n'a jamais ouverte
n'est pas une sauvegarde, c'est un espoir.

### Restaurer

```bash
pm2 stop sara-learn
gunzip -c /var/backups/saralearn/sara-AAAAMMJJ-HHMMSS.db.gz > data/sara.db
sqlite3 data/sara.db "PRAGMA integrity_check;"
pm2 start sara-learn
```

### La limite à connaître

`/var/backups/saralearn` est **sur la même machine que la base**. Ça protège d'une
fausse manœuvre — une suppression, une migration ratée — pas d'une panne de disque ni
de la perte du serveur. Une copie hors machine reste à mettre en place : elle demande
une destination et des identifiants.

## Configuration

Toute la configuration de l'API vit dans **`.env`**, à la racine. C'est
`api/config.py` qui le lit au démarrage, pas le superviseur : le fichier vaut donc
aussi bien sous pm2 que pour un lancement à la main. Format `CLE=valeur`, une par
ligne, sans `export` — les guillemets autour de la valeur sont retirés à la
lecture.

Une variable déjà présente dans l'environnement **n'est jamais remplacée** par
`.env`. Utile pour surcharger le temps d'un essai ; sournois quand un process a
été lancé avec des valeurs qui ne sont plus celles du fichier, puisqu'il tourne
alors sur une configuration que plus rien ne documente.

| Variable | Rôle |
|---|---|
| `SARA_DB` | Chemin de la base SQLite |
| `SARA_CORS` | Origines autorisées — développement seulement |
| `SARA_ADMIN_TOKEN` | Ouvre l'écran `#admin` |

```bash
cp .env.example .env
openssl rand -hex 32          # une valeur pour SARA_ADMIN_TOKEN
chmod 600 .env                # il contient un secret
pm2 restart sara-learn
```

`SARA_SECRET` n'est volontairement pas dans `.env` : à défaut, la signature des
jetons vient de `data/.secret`, écrit une fois puis relu. Redémarrer l'API ne
déconnecte donc personne — poser la variable, si.

`.env` est en `600` et listé dans `.gitignore`. **Ne le recopie jamais dans un vhost
Apache** : c'est ainsi qu'une clé OpenAI s'est retrouvée en clair dans
`sites-available`, puis dans les sauvegardes système. `.env.example` donne la liste des
variables sans aucune valeur réelle.

### Le jeton d'administration

`SARA_ADMIN_TOKEN` est une **clé d'amorçage**, pas un compte. Elle existe parce que
`app_user.is_admin` figure au schéma depuis le début mais qu'aucun compte ne la porte :
sans jeton, personne ne peut ouvrir `#admin`, et promouvoir le premier administrateur
demanderait un accès direct à la base.

Elle **n'identifie personne** — l'écran affiche « ouvert par le jeton de service » et
aucune action n'est mise au compte de qui que ce soit. Dès qu'un compte réel porte
`is_admin = 1`, vider la variable ferme cette porte :

```sql
UPDATE app_user SET is_admin = 1 WHERE email = 'ton@email';
```

Le jeton est comparé en `hmac.compare_digest` sur les octets, et une variable absente
ou vide ferme l'accès plutôt que de l'ouvrir. Côté navigateur il vit en
`sessionStorage` : il meurt avec l'onglet.

## Mesure d'audience

**Il n'y en a pas.** Google Tag Manager (conteneur `GTM-P2PR5ZNF`) a été posé dans
`index.html` le 7 août 2026, puis **retiré le 10 août 2026** à la demande du
propriétaire du projet. Le dépôt ne charge plus aucun script de mesure, ne pose
aucun cookie de mesure, et n'ouvre aucune connexion vers un tiers au chargement.

Ce que ça solde au passage : la dette du bandeau de consentement, qui n'a plus
d'objet — sans traceur, rien à faire consentir. Elle est retirée de `TODO.md`.

Le conteneur et la propriété GA4 (`G-PQR5WJ1Z34`) existent toujours côté Google ;
seul leur appel a disparu du code. Les rebrancher un jour ne demande que de
remettre les deux extraits dans `index.html` — mais alors le bandeau redevient dû
**avant** le script, pas après.

## Déploiement

En ligne sur **https://learn.sara.education** — le front, et l'API sous `/api`.

| Élément | Où |
|---|---|
| Front (bundle statique) | `/var/www/saralearn/dist`, servi par Apache |
| API | pm2 `sara-learn` → `start.sh`, uvicorn sur `127.0.0.1:8010` |
| Vhosts | `/etc/apache2/sites-available/040-learn.sara.education*.conf` |
| Configuration | `/var/www/saralearn/.env` (voir *Configuration*) |
| Adresse de l'API dans le bundle | `.env.production` → `VITE_API_URL=/api` |
| Certificat | Let's Encrypt, déjà en place pour ce domaine |

```bash
# Déployer une nouvelle version du front
npm run build

# Redémarrer l'API
pm2 restart sara-learn
pm2 logs sara-learn
```

`npm run build` suffit : `.env.production` fixe `VITE_API_URL=/api`, et
`scripts/check_build.mjs` refuse tout bundle contenant une adresse de boucle locale.

**`npm run build` publie.** `dist/` est la racine servie par Apache : il n'y a pas
d'étape entre construire et mettre en ligne, et la commande emporte tout ce qui
traîne sur le disque, commité ou non. Avant de la lancer, comparer ce qu'elle
produirait à ce qui est déjà servi — une construction vers un dossier de travail
(`npx vite build --outDir /tmp/…`) donne les mêmes empreintes de fichiers quand
rien n'a changé.

### La supervision de l'API

`pm2` gère les vingt-deux services de cette machine ; l'API de SaraLearn en fait
partie depuis le 7 août 2026.

```bash
pm2 start /var/www/saralearn/start.sh --name sara-learn
pm2 save          # sans ça, rien ne revient au redémarrage
```

**`pm2 save` n'est pas une formalité.** pm2 rejoue au démarrage la liste
enregistrée dans `~/.pm2/dump.pm2`, pas les process en cours. Ajouter un service
sans l'enregistrer donne une supervision qui marche jusqu'au premier redémarrage,
puis plus rien — et le fichier trouvé ici datait de deux mois.

`start.sh` ne pose aucune variable d'environnement : `api/config.py` lit `.env`
lui-même. Les secrets ne sont donc ni dans ce script, ni visibles dans la table
des process.

**Un seul superviseur à la fois.** Une unité `sara-exos-api.service` visait le
même port ; laissée activée, elle bouclait sur un échec toutes les quelques
secondes depuis qu'un lancement à la main lui avait pris le 8010, et se serait
disputé le port avec pm2 au redémarrage suivant. Elle est désactivée
(`systemctl disable --now`), l'unité reste sur disque. Pour revenir à systemd, il
faut faire l'inverse des deux côtés : `pm2 delete sara-learn && pm2 save`, puis
réactiver l'unité.

Vérifier que la supervision fait son travail, plutôt que de le supposer :

```bash
kill -9 $(pm2 pid sara-learn)      # doit revenir en une seconde
curl -s -o /dev/null -w '%{http_code}\n' https://learn.sara.education/api/health
```

Cette vérification existe parce que la panne était **silencieuse au moment où on la
crée**. Le code a pour valeur par défaut `http://127.0.0.1:8010` : juste en
développement, mortel en ligne, où cette adresse désigne la machine du visiteur. Un
bundle construit sans `VITE_API_URL` se déployait sans une erreur et affichait « le
serveur ne répond pas » à tout le monde. Elle sort maintenant dans le terminal, avant
d'atteindre `dist/`.

L'API **n'écoute que sur la boucle locale** : Apache est le seul chemin d'entrée.
`--root-path /api` lui indique où elle est montée, pour que `/api/docs` et les URLs
générées soient justes. Le front étant servi depuis la même origine, aucune requête
inter-origine n'a lieu en production — les entrées CORS ne servent qu'au développement.

Le `ProxyPass` est déclaré **avant** le `DocumentRoot` : dans l'autre ordre, le
`FallbackResource` du SPA avalerait les requêtes `/api`. Les bundles portent un hash et
sont mis en cache un an ; `index.html` ne l'est jamais, sinon un déploiement resterait
invisible.

## Contenu réglementaire (permis de conduire)

`country` sur `theme` et `app_user` — **nullable, NULL = universel**. Pays ≠ langue : le
Québec lit le français et suit un autre code. Sur du réglementaire, pas de repli : à
défaut de contenu dans le pays de l'utilisateur, on n'affiche rien plutôt que des règles
étrangères.

**La garantie image ↔ question repose sur un renversement du pipeline.** On ne génère pas
une question pour lui chercher ensuite une image : on part d'une ligne de `sign`, et
`exercise.sign_id` pointe dessus par clé étrangère. Aucune étape où quelqu'un — humain ou
modèle — choisit une image, donc rien à se tromper.

```bash
python3 scripts/import_signs.py --country US            # catalogue FHWA complet
python3 scripts/import_signs.py --country FR --codes A1a,B14
```

| Source | Confiance | État à l'import |
|---|---|---|
| FHWA (US) | le nom du fichier dans l'archive porte le code **et** le libellé → auto-vérifiant | `verified` |
| Wikimedia (FR) | convention exacte `France road sign <code>.svg`, communautaire | `imported` |

**Un exercice visuel ne peut s'adosser qu'à un panneau `verified`.** Les français exigent
une relecture humaine : jamais de recherche approchante, qui remonte un panneau algérien
ou un écusson d'autoroute pour « A9 ».

Les SVG français sont en **CC BY-SA** : l'attribution est obligatoire. Elle est stockée en
base et servie par `GET /api/credits`, pas maintenue à la main dans le front.

## Reste à faire

- **Le barème du classement est une hypothèse** : 10 points par bonne réponse, 2 par
  tentative, 0 si l'exercice est passé au swipe. La maquette affiche des points sans
  dire d'où ils sortent. Une ligne à changer dans `v_theme_week_rank`.
- **Le dépôt de fichier et l'enregistrement audio** de l'écran de création sont des
  intentions visuelles : seul le Markdown collé est réellement exploité.
- **La relecture des thèmes `pending`** n'a pas d'interface admin.
- **Deux unités systemd à trancher.** `saralearn-api.service` pointait vers l'ancien
  backend chatSara disparu et bouclait sur un échec depuis 420 000 redémarrages ;
  `sara-exos-api.service` visait le port de l'API avant le passage à pm2. Les deux
  sont désactivées et inertes, les fichiers restent sur disque. À supprimer une fois
  qu'on est sûr de ne pas revenir à systemd.
- `api.sara.education` ne proxifie plus vers le port 8001 disparu : il répond
  désormais en 308 vers `learn.sara.education/api/`. Reste à savoir si ce domaine
  a encore des appelants, ou s'il peut disparaître.
- **Les tests vivent hors du dépôt.** Les 79 assertions de bout en bout sont dans le
  scratchpad de session : à déplacer dans le dépôt avant qu'elles disparaissent.

`SHOW_MOCK_STATUS_BAR` dans `src/config.ts` dessine la fausse barre d'état de la
maquette (9:41, réseau, batterie). **À passer à `false` avant de livrer sur un
appareil réel** — sinon l'app affiche une heure fausse sous la vraie barre de l'OS.
