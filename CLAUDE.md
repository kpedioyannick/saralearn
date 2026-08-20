# SaraLearn — état et règles

App de QCM à feed vertical. FastAPI (`api/`) + React/TS (`src/`) + SQLite
(`data/sara.db`). Servie par Apache sur `learn.sara.education` ; `dist/` est la
racine, `/api` est mandaté vers `127.0.0.1:8010`, et `media/` est exposé sous
`/media`.

**L'API tourne sous pm2** : `pm2 restart sara-learn` après toute modification de
`api/`, sinon elle sert le code d'avant. Le front se reconstruit avec
`npm run build`, qui écrit dans `dist/` — donc en ligne immédiatement.

## Le vocabulaire, et c'est le piège numéro un

Trois mots désignent trois choses, et le client en emploie deux à contresens.

|  ce que dit le client  |  ce que c'est en base  |  combien  |
|---|---|---|
| catégorie | `theme` — un jour de la création | 11 |
| learning / apprentissage / « thème » dans les URL | `chapter` — un article | 2 187 |
| `ExerciseOut.theme_id` | un `chapter_id` | — |

L'API a longtemps eu une génération de retard sur la base : elle interrogeait
`exercise.theme_id`, `user_theme`, `category`, `theme.lang` — tous disparus.
Résultat, `/feed` rendait 500 et l'app restait sur « Getting your exercises
ready… » pour toujours. Réparé le 17/08/2026. **Ne renomme pas ces champs sans
reconstruire le front** : `dist/` est un bundle compilé, il ne suit pas.

## Où en est le contenu

```bash
python3 -c "import sqlite3;c=sqlite3.connect('data/sara.db');
print(c.execute(\"SELECT COUNT(*) FROM exercise WHERE state='validated'\").fetchone())"
```

Au 17/08/2026 : **51 exercices** répartis sur **6 chapitres**, sur 2 187. Les
2 180 autres ont leur source en base — 22 916 sections, 32 Mo de texte
Wikipédia — et aucune question.

**C'est voulu.** Le catalogue ne s'écrit pas d'avance : un chapitre s'écrit le
jour où quelqu'un l'ouvre. Écrire les 20 000 questions à l'avance coûterait des
heures d'appels pour un catalogue que personne n'a encore joué.

## L'écriture à la demande — le cœur du système

`api/topup.py` fabrique un lot de 10 questions à partir de l'article du
chapitre. Deux portes le déclenchent, et les deux comptent :

- **le bouton « suivre »** (`routers/themes.py`, `routers/progress.py`) — en
  tâche de fond, la réponse part en 15 ms ;
- **le feed** (`routers/feed.py`) — **en attendant la fin**, quand il ne reste
  rien d'inédit à servir. Une trentaine de secondes, derrière l'écran de
  préparation. C'est assumé : le client déployé n'a aucune façon de redemander
  le flux tout seul, donc lui répondre une liste vide, c'est le laisser sur
  l'écran d'attente pour de bon.

Mesuré : **23 s** pour écrire un lot, 4 413 jetons d'entrée et 3 093 de sortie,
soit **$0,0079** aux tarifs pleins. Le juge de `critic.py` ajoute 10 appels
courts. Le modèle est `deepseek-chat`, **alias qui pointe aujourd'hui sur
`deepseek-v4-flash`**.

Trois plafonds, tous dans `topup.py`, tous surchargeables par variable
d'environnement :

- `DAILY_CAP = 3` lots par chapitre et par jour ;
- `DAILY_CAP_GLOBAL = 60` lots par jour, tout le catalogue confondu — l'écran
  d'ajout a un bouton « suivre tout » qui peut abonner 146 apprentissages d'un
  clic ;
- `MAX_EN_VOL = 3` écritures menées de front.

Et un registre des écritures **en vol** par chapitre : le second appelant attend
le premier au lieu de payer le même lot deux fois. Sans lui, deux onglets
écrivaient le même chapitre en double — c'est comme ça que le thème 229 avait
récolté 50 doublons.

## La traduction

`api/traduction.py`, table `exercise_translation` (migration 024). L'anglais
reste la source ; un exercice n'existe qu'une fois, sous un seul identifiant.
C'est ce qui garde `attempt`, la progression et les classements comparables
d'une langue à l'autre — deux jeux d'exercices séparés auraient coupé chaque
classement en deux.

Le moteur est **`deep-translator`** (Google), gratuit, sans clé. Choix du
propriétaire, fait en connaissance de la limite : il traduit **chaque champ
isolément**, donc il ne voit ni la question quand il traduit une option, ni les
autres options. Deux conséquences mesurées :

- l'accord se perd — « Elle ralentit / Elle accélère / … / **Il** disparaît » ;
- le sens se perd — « the **metre** is defined as… » est devenu « le
  **compteur** est défini comme… ».

`verifier()` refuse ce qui est cassé dans sa FORME — options identiques, option
vide, énoncé sans « ? ». **Rien ne rattrape le sens.** Ce qui est refusé reste
en anglais.

**`translate_batch` n'est pas un lot** : c'est une boucle d'une requête HTTP par
morceau de texte — 15 par exercice, 135 pour un chapitre de neuf, d'où les
82 secondes. Et un seul `TooManyRequests` faisait remonter l'exception,
abandonner le chapitre entier et jeter les 130 traductions déjà obtenues. Le
17/08, trois chapitres suivis coup sur coup ont lancé trois boucles de front,
Google a coupé, et **35 exercices sont restés en anglais** — servis tels quels à
un lecteur français le 19/08. Réparé le 19/08/2026 :

- **un exercice à la fois**, écrit dès qu'il est prêt : un raté coûte un
  exercice, jamais le chapitre. Tout ou rien par exercice — une carte moitié
  française serait pire que l'anglais ;
- **on réessaie** (2 s, 5 s, 15 s) et **un seul appel à Google à la fois** pour
  tout le service (`_GOOGLE`). Ce qui fait couper, c'est le parallélisme ;
- **l'écriture emporte sa traduction** — `topup.ecrire_et_traduire`, jamais
  `topup` seul, et pour `LANGUES_CACHE` quelle que soit la langue de celui qui a
  déclenché l'écriture. Sept comptes anglophones sur dix remplissaient un
  catalogue que personne ne traduisait ;
- **le feed garantit les deux premières cartes qu'il rend**
  (`_garantir_les_premieres`, ~10 s chacune, dans la requête) et **écarte les
  autres si elles ne sont pas traduites** (`_seulement_lisibles`) — sauf si tout
  est anglais, auquel cas l'anglais passe : un écran d'attente sans sortie est
  pire.

Toujours **dans un fil** (`asyncio.to_thread`) : `translate` est un appel réseau
synchrone, appelé directement il gèle toute l'API.

Le retard s'attrape avec `python3 scripts/traduire_manquants.py` (`--dry-run`
d'abord).

**`ok_title` et `ko_title` ne passent plus par le traducteur** (`api/titres.py`,
19/08/2026). Ces deux champs font un ou deux mots : Google les prend seuls, sans
phrase autour, et rendait **« Droite ! » pour « Right! » sur trente-sept
cartes**, « Fermer » pour « Close », « Prudent » pour « Careful » — affichés ET
lus à voix haute par `lib/spoken.ts`. Ils sont désormais un **jeu fermé de cinq
formes de chaque côté**, que le modèle CHOISIT au lieu de rédiger, avec leur
équivalent français en table. Un titre RÉAGIT À LA TENTATIVE, il n'affirme rien
sur le contenu : « C'est l'inverse. » a été retiré pour ça — sur quatre options
il désignait presque la bonne case avant l'explication. Il a cédé la place à
« Le piège classique. », qui dit à l'élève qu'il a fait l'erreur que tout le
monde fait — le pendant exact de la consigne, qui veut que chaque mauvaise
option soit une croyance réelle. Laissés libres, ils avaient donné 70 formes pour
173 cartes — « Bouncer! », « Space kitchen » en titre de réussite — et des
titres qui rabaissent, « Wrong », « Nope », que la règle interdit pourtant.
Rattrapage de l'existant : `python3 scripts/normaliser_titres.py`, sans aucun
appel réseau. La voix suit celle du front (`src/data/content.ts`) : un point,
pas de point d'exclamation, aucune adresse directe — l'app hésite entre
tutoiement et vouvoiement.

`correct_index` n'est **jamais** traduit ni recopié : c'est une position dans le
tableau d'options, elle appartient à l'original.

## Les photos d'ambiance

`api/photos.py`, migrations 028 et 029. Une photo Unsplash par exercice, et
c'est **la SCÈNE, jamais le phénomène** : la route droite et vide, pas le
mirage. Une photo du mécanisme donnerait la réponse avant qu'on ait lu les
options ; une photo du décor rappelle la scène que la question demande de se
remémorer — ce que le format « intuition » exige justement de l'élève.

**Les mots de recherche viennent du modèle** (`image_query`), pas de l'énoncé.
Mesuré : envoyer la question telle quelle à une banque d'images rend des livres
du XIXᵉ numérisés — un fonds indexe du plein texte, une phrase longue accroche
des pages. Trois ou quatre noms communs rendent la bonne image du premier coup.

**Le filtre `revele()` est une liste fixe, et c'est un choix mesuré.** La règle
« un mot de la réponse ou de l'explication absent de l'énoncé » était plus
élégante et sans entretien : elle refusait **36 %** des requêtes, dont « prism
sunlight *white* wall ». Une explication décrit la scène qu'elle explique, donc
ses mots sont ceux du décor. La liste fixe `PHENOMENES`, exemptée des mots déjà
présents dans l'énoncé, refuse **2 %** — et les cinq sont de vrais noms de
phénomène. Requête refusée = pas de photo, ce qui est le cas normal.

**Trois banques en chaîne** (20/08/2026) : Unsplash, puis Pexels si elle est à
sec, puis Pixabay. La suivante prend le relais dès que la précédente ne rend
rien — quota, panne ou simple absence de résultat, les trois cas se ressemblent
de l'extérieur. Une banque sans clé est sautée ; le catalogue tourne avec zéro
comme avec trois. Le nom de la banque voyage en base (`image_source`, migration
031) parce que le front doit créditer la bonne.

|  | débit | ce qu'elle exige |
|---|---|---|
| Unsplash | 50/h en démo, 5 000 approuvée | lien direct vers leur CDN, crédit du photographe, appel à `download_location` |
| Pexels | 200/h, 20 000/mois | crédit du photographe et lien visible vers Pexels |
| Pixabay | 100 par **minute** | **interdit le lien direct permanent** |

Deux pièges. **Une photo Unsplash coûte deux requêtes** : `download_location`
est facturé au même compteur que la recherche — une ronde dimensionnée sur 45
s'est arrêtée à 27 cartes, 27 + 23 = 50. **Pixabay dit l'inverse d'Unsplash** :
*« permanent hotlinking … is not allowed … download them to your server
first »*, d'où `_rapatrier()` et une copie dans `media/photos/`. C'est le seul
cas où une photo est un fichier chez nous, et pourquoi la source ne se devine
pas depuis l'URL.

**Le compteur s'oublie après l'attente** (`oublier_le_quota`). Il ne se met à
jour qu'en lisant l'en-tête d'une réponse réelle : tombé à zéro, il dimensionne
une ronde de zéro carte, qui ne fait aucun appel, qui ne relit aucun en-tête. La
boucle a dormi quatorze heures là-dessus le 20/08, quota plein et 173 cartes en
attente.

Rattrapage : `scripts/illustrer_catalogue.py --mots` puis `--photos --boucle`.
Les deux phases sont séparées parce que les mots, une fois en base, ne se
repaient jamais.

**La photo arrive EN DERNIER, et deux garde-fous ferment la fenêtre**
(20/08/2026). L'ordre d'écriture est `topup` → traduction → photos : trois
minutes entre la première carte écrite et sa photo, parce qu'on peut lire une
carte sans image mais pas une carte en anglais quand on a demandé le français.
Un lecteur est tombé dans cet intervalle le jour même.

- **le feed relègue la carte nue** (`_PHOTO_ORDER`, `routers/feed.py`) — après
  la clé pédagogique et après la langue, jamais avant. Elle n'est pas écartée,
  contrairement au non-traduit : c'est le décor qui manque, pas la question,
  et une page vide serait pire ;
- **`sara-photos` veille sous pm2** — `illustrer_catalogue.py --photos
  --boucle`, qui ramasse ce que la chaîne d'écriture a manqué (réseau, banques
  à sec sur le moment, API relancée en plein travail). Sans lui, une carte
  ratée à l'écriture ne repassait JAMAIS : rien ne la relisait. Il dort dix
  minutes quand tout est illustré, une heure sur une vraie impasse — plus de
  quota, ou une ronde entière sans une seule photo posée.

## La règle éditoriale — elle décide de tout

**L'intuition, jamais l'accumulation.** C'est le but de l'app, et depuis le
19/08/2026 c'est écrit dans la consigne. Le test, appliqué à chaque question :
*quelqu'un qui n'a jamais lu l'article peut-il y arriver EN RÉFLÉCHISSANT ?* Si
le seul chemin est d'avoir retenu un mot, la question ne vaut rien ici.

Trois formes autorisées — **la scène** (« sur une route brûlante, on dirait une
flaque : qu'est-ce qu'on voit ? »), **la prédiction** (« si l'axe de la Terre
était droit, que deviendraient les saisons ? »), **la cause** (« pourquoi la
paille semble-t-elle cassée dans le verre ? »). Interdites : « What is X »,
« What does X mean », « Who discovered X », « Which X is the largest ». Et pas
de scène de laboratoire inventée quand le sujet n'a pas de scène : on retombe
alors sur la cause.

**Les trois mauvaises options sont le cœur de l'exercice.** Chacune est une
croyance que quelqu'un a vraiment, et l'une d'elles est l'erreur que tout le
monde fait. Tant qu'elles sont du vocabulaire sans rapport — *Gravity of Earth /
Magnetic fields / Wind speed* —, on élimine au flair et on n'apprend rien. Se
tromper doit montrer à l'élève son propre modèle ; le `feedback` dit où
l'intuition lâche.

**Le mot technique est la récompense, pas le péage.** Aucun jargon dans l'énoncé
ni dans les quatre libellés ; le terme apparaît dans `exp_text`, pour nommer ce
qu'on vient de comprendre.

**Ne jamais finir une explication sur un chiffre ou un superlatif** : la chute
spectaculaire écrase la réponse que la question posait. La dernière phrase
referme le mécanisme. Cette consigne, mise dans le prompt, divise le défaut par
deux — mesuré sur l'ancien catalogue.

Le juge tient la première règle (`critic._CRITERE_INTUITION`, réservé à
`matiere='connaissance'`), écrit étroit pour ne refuser que le cas franc.
Rendement mesuré sur « Microwave » : **10 rendus → 8 passent `validate` → 7
gardés**, contre 8 à 10 avec l'ancienne consigne. Deux perdus sur la borne dure
des 60 caractères d'un libellé, un sur un refus du juge.

**Les 179 exercices déjà en base sont de l'ancienne forme** — définitions, noms
propres, appariements de mots. Ils ne changeront pas tant qu'on ne les réécrira
pas.

## Mesurer ce qui est écrit — l'audit

`scripts/auditer_exercices.py` FAIT RÉPONDRE le modèle aux cartes, à froid :
la question, les quatre options, rien d'autre. Ni l'article, ni la clé, ni
l'explication. C'est autre chose que le juge de `critic.py`, qui relit avant
l'entrée ; ici on joue la carte comme un élève. Une carte qu'un lecteur
compétent rate est cassée, quelle qu'en soit la cause.

**Le chiffre qui décide est « réponse manquée », jamais « options
défendables ».** Première version de l'audit, la question posée était « liste
tout ce qu'on pourrait défendre » : 46 % de cartes signalées, dont *« une flaque
qui s'évapore »* pour le mirage et *« la galaxie a toujours 13 milliards
d'années »*. Le modèle sur-liste dès qu'on le laisse faire. Question resserrée —
*« ex aequo seulement si l'option est AUSSI juste que ton choix ; une option
seulement plausible n'y appartient pas ; la liste vide est le cas normal »* — le
chiffre tombe à 1 carte sur 165.

Relevé du 19/08/2026 sur les 165 réécrits : **7 % manquées en anglais, 10 % en
français**. C'est un plafond : sur les douze cartes anglaises, quatre étaient des
erreurs de l'auditeur (le mirage, Pluton, le halo, le poids au pôle) et non des
cartes fausses. Le vrai taux tourne autour de **5 %**.

Les défauts se groupent sur **les sujets à plusieurs causes vraies** — vallée en
U glaciaire *et* plaine alluviale, stocker l'eau *et* réduire sa perte. C'est la
limite de la consigne d'intuition : elle exige une seule option vraie, la
biologie et la géographie n'obéissent pas à ça.

Deux chapitres décrochaient franchement — **Bird flight** (4 ratées sur 7) et
**22° halo** (4 sur 8 en français) : réécrits, ils sont retombés à **0 sur 31 en
anglais, 1 en français**. Quatre cartes cassées ailleurs sont passées en `draft`
(236, 256, 285, 286).

Le français perd trois points sur l'anglais, et c'est le traducteur : *« Light
from the fish bends away from you »* est devenu *« La lumière du poisson
s'éloigne de vous »*. Laissé tel quel — le corriger voudrait dire traduire au
modèle.

## Écrire un chapitre à la main

Le chemin normal est l'écriture à la demande. À la main, il reste :

1. `db/creation/<thème>-<NN>-<chapitre>.json` — une **liste** de lots,
   `[{"chapter_id": N, "items": [...]}]`, exactement 10 items. La liste n'est
   pas décorative : `import_exercises.py` fait `for lot in lots`.
2. `python3 scripts/import_exercises.py --file <lot> --dry-run`
3. `python3 scripts/import_exercises.py --file <lot>`

```json
{"type_question": "qcm",
 "prompt": "…?", "body": null, "correct_index": 0,
 "options": [{"label": "…", "feedback": "…"}],
 "ok_title": "…", "ok_line": "…", "ko_title": "…", "ko_line": "…",
 "exp_title": "…", "exp_text": "…"}
```

`body` reste `null`. Seul `qcm` est produit. `exp_text` porte le fait **et son
mécanisme**, le `feedback` de chaque option dit **pourquoi** elle est fausse.

## Ce que `critic.py` refuse

Les bornes de longueur ont toutes été retirées. Il reste cinq refus, qui
attrapent des exercices cassés : `correct_index` hors bornes, deux options
identiques, une option vide, un énoncé de QCM sans « ? », un renvoi au support
(« according to the text ») — il n'y a aucun cours.

## Décidé, et à ne pas rouvrir sans raison

- **anglais comme source**, français en traduction cachée
- **publication directe**, sans passage par le juge pour le semis
- **10 questions par lot**, QCM uniquement
- **écriture à la demande**, pas de pré-remplissage du catalogue

## L'administration

Deux portes dans `routers/admin.py` : un compte avec `is_admin = 1`, ou
l'en-tête `X-Admin-Token` comparé à `SARA_ADMIN_TOKEN` (posé dans `.env`).

**Il n'y a aujourd'hui aucun compte admin en base.** Seule la porte du jeton
fonctionne, et l'écran d'admin du front sait s'en servir. Ça compte, parce que
le pouce en bas met un exercice en quarantaine tout seul (`state='draft'`) dès
que les votes négatifs l'emportent : sans admin, un exercice écarté ne peut plus
être relu. Pour donner le droit au compte du propriétaire :

```sql
UPDATE app_user SET is_admin = 1 WHERE email = 'yannick.kpedio@gmail.com';
```

## Faiblesses connues

**Les exercices sont écrits depuis l'article, mais sans relecture humaine.** La
source est en base et la consigne interdit d'en sortir — c'est ce qui rend la
chose acceptable. Les familles à risque restent les chiffres, les records et les
« comment reconnaître ».

**Personne n'a jamais joué.** Zéro ligne dans `attempt`. Le niveau, la longueur
des explications et le ton n'ont jamais été éprouvés sur un être humain.

**Ce qui reste cassé, hors du chemin du joueur** : `routers/knowledge.py` (500),
la création et la mise à jour de thème dans `routers/themes.py`, et
`routers/generate.py` — tous encore écrits sur `category` et `theme_tag`. Ils
sont derrière des portes fermées (403), donc invisibles.

## Deux règles de sécurité, apprises à la dure

**Jamais de migration par le client `sqlite3`.** Il poursuit après une erreur :
un `INSERT` raté n'empêche pas le `DROP TABLE` suivant de s'exécuter. Ce dépôt a
perdu 619 panneaux puis 886 exercices comme ça. Toujours
`python3 scripts/migrate.py <fichier>`, qui sauvegarde, s'arrête à la première
exception et restaure. **Pas de copie manuelle de la base** : le script s'en
charge.

**Pas de `git` sur ce dépôt.** L'arbre de travail non commité est plus récent que
le dernier commit.
