# TODO — SaraLearn

Le carnet de tâches du projet. Vous écrivez ici, je lis d'ici.

## Comment s'en servir

**Ce fichier ne déclenche rien.** Y écrire une tâche, c'est la noter, pas
me demander de la faire. Je n'ouvre le code que quand vous me dites d'y
aller — « fais la tâche X », « attaque le TODO », etc.

- Vous pouvez écrire vos demandes directement sous **À faire**, ou me les
  dicter : dans ce cas je les note ici, telles quelles, sans rien faire
  d'autre.
- Une phrase suffit. Si une tâche est ambiguë au moment de la traiter,
  je poserai la question à ce moment-là — pas maintenant.
- Quand une tâche est terminée, elle passe sous **Fait**, avec la date et
  les fichiers touchés.
- Ce que je ne peux pas faire seul (clé à poser, service à redémarrer)
  part sous **Chez vous** — c'est votre main qu'il faut.

Conventions utiles quand vous voulez cadrer :

| Marque | Sens |
|---|---|
| `!` en tête de ligne | à traiter en premier |
| `?` en tête de ligne | à discuter avant d'écrire du code |
| `(mobile)` / `(desktop)` | le cadre concerné, si un seul l'est |

---

## À faire

<!-- Écrivez vos tâches ici, sur le modèle des lignes ci-dessous. -->
<!-- Exemples : « - [ ] ! Le classement se recharge à chaque swipe » -->
<!--            « - [ ] ? Un écran tout-voir par catégorie, ou la recherche suffit ? » -->

**Ordre décidé le 7 août 2026** pour les chantiers produit : le pipeline
IA, puis les exercices illimités, puis la vidéo TikTok, puis l'écran des
catégories avant l'exercice, puis la détection de langue. Le commit du
travail en cours passe en dernier, après tout le reste.

- [ ] Avant d'accéder à l'écran exercice, si l'utilisateur n'est pas
      connecté, lui afficher l'écran des choix des catégories.
      À noter au moment de le faire : l'écran de catégories a été retiré
      de l'inscription par la planche 1e (tour 2) — il faudra décider
      lequel des deux gagne.

- [x] ~~En base : découper la sous-catégorie unique de la catégorie
      « Permis de conduire » en plusieurs sous-catégories.~~
      **Tranché dans l'autre sens le 11 août 2026 : la sous-catégorie est
      retirée** (migration 013). Elle n'avait qu'une ligne, `auto` (id 9),
      et surtout l'écran de création ne l'a JAMAIS proposée —
      `draftSubCategoryId` naissait à `null` et rien ne l'écrivait. Un
      niveau que rien ne remplit ne se découpe pas, il se retire.
      Reste à faire : appliquer la migration sur la base de production
      (`python3 scripts/migrate.py db/migrations/013_retrait_de_la_sous_categorie.sql`),
      redémarrer l'API et rebâtir le front.

- [ ] Défaut trouvé chez `sara-video`, laissé en l'état : les
      sous-titres n'analysent pas le SRT — `splitSubtitleChunks` découpe
      la chaîne brute en paquets de six mots, horodatages compris, et on
      lit « 3 00:00:25,000 --> 00:00:45,000 Au présent, » à l'écran. Ça
      touche les vidéos d'anythingllm, pas les nôtres, qui n'affichent
      plus de sous-titres. Le correctif était écrit puis annulé : c'est
      un service partagé, la décision n'est pas la mienne.

- [ ] Redéfinir la fonctionnalité qui permet d'avoir des exercices
      illimités.
      Où ça vit aujourd'hui : `api/routers/feed.py` (tirage sur les
      exercices validés, fenêtre anti-répétition `SARA_FEED_RECENT`,
      20 par défaut) et le deck de `src/state/store.tsx`.

- [ ] Détection de la langue — navigateur, IP, ou autre.
      Ce qui existe déjà : `detectLang()` lit la langue du navigateur au
      premier lancement (`src/i18n.ts`, appelé par `readPrefs()` dans
      `src/state/store.tsx`), puis le choix serveur prend le relais.
      Changer de langue change le catalogue servi, pas seulement les
      libellés — une mauvaise détection ne fait pas qu'afficher le mauvais
      mot, elle sert le mauvais catalogue.

---

### Risques — constatés le 6 août 2026

- [ ] ! Committer le travail en cours. 45 entrées en attente dans ce
      dépôt et le dernier commit est une sauvegarde de base : les tours 4
      et 2, la refonte de l'inscription et le portage de la voix
      n'existent que sur le disque. Même constat côté `sara-student`
      (8 fichiers modifiés, dont `lib/classe/tutorApi.js`).

- [ ] ! Séparer construire et publier. `dist/` est la racine servie par
      Apache : `npm run build` met en ligne, sans étape intermédiaire.
      C'est ce qui a fait partir en production des builds qui n'étaient
      que des vérifications de compilation.

- [ ] Poser un quota sur `POST /tts`. Le tuteur en a un
      (`TUTOR_DAILY_MESSAGES`) ; la route de SaraLearn n'en a pas. Le
      cache disque protège des textes répétés, pas d'un visiteur qui fait
      défiler le feed — et une session anonyme s'obtient en un POST.
      À regarder avant de poser la clé Google.

- [ ] Élaguer le cache TTS (`data/tts-cache`). Il grossit sans limite,
      rien ne le purge.

---

### Écarts produit — constatés le 6 août 2026

- [ ] Onze apprentissages « Harmonie à la guitare » à zéro exercice, mal
      classés sous `permis` (ids 192 à 202). À reclasser ou à supprimer.
      Leur origine est identifiée : `tests/test_api.py` crée ce thème à
      chaque passage et ne le reprend jamais — chaque exécution en laisse
      un de plus, avec un propriétaire neuf. Les corriger sans corriger
      le test ne ferait que retarder les suivants.

- [ ] Rendre `tests/test_layout.mjs` autonome. Il vise le port 4178, que
      `SARA_CORS` n'autorise pas, et attend qu'on ait lancé le serveur
      soi-même. Au premier essai de la session il a répondu « 42 réussis »
      **sur un site qui n'est pas celui-ci** — il devrait refuser de
      tourner plutôt que de passer au vert à vide.

- [ ] Dater les apprentissages. Sans colonne de création, « Nouveaux » ne
      peut que s'ordonner sur l'id, et « les plus suivis cette semaine »
      reste indicible — c'est ce qui a fait retirer la mention temporelle
      de la planche 2c.

- [ ] Signaler au designer l'écran manquant de la planche 4c : le 3ᵉ
      téléphone est un doublon exact du 1ᵉʳ, l'état « audio coupé » est
      décrit dans le texte mais jamais dessiné. Implémenté d'après le
      texte en attendant.

---

## Chez vous

Le portage de la voix est terminé. `GOOGLE_TTS_API_KEY` a été reprise du
`.env` d'AnythingLLM le 7 août, sur votre accord, guillemets retirés ;
`.env` est en 600. `POST /api/tts` répond 200 et rend du MP3 : le site
parle avec la voix Google, plus avec celle du navigateur.

À décider quand vous voudrez :

- [ ] Nettoyer les traces de mes tests — trois comptes anonymes dans
      `data/sara.db` (`tts-test-000000`, `voice-test-0001`, `nokey-0001`)
      et deux lignes de quota `user_id 999999` dans
      `/var/www/sara-tutor/data/tutor.db`. La suppression m'a été refusée
      par les permissions ; dites-moi si vous voulez que je la refasse.

---

## Fait

<!-- Je remplis cette section. Le plus récent en haut. -->

### 7 août 2026 — Les six écrans de la maquette, en français et en anglais

```bash
python3 scripts/video_tiktok.py --categorie conjugaison-fr --lang fr --nb 2
python3 scripts/video_tiktok.py --categorie grammar-en    --lang en --nb 2
```

Les écrans ne sont plus reproduits d'après des captures : ils viennent
de la **maquette Claude Design**, section « Six écrans pour une vidéo
TikTok », blocs `5a` à `5f`. La maquette est déjà tracée en 1080 × 1920,
donc les tailles sont recopiées telles quelles.

| | |
|---|---|
| 5a | accroche — sujet, règle du jeu, « ta réponse en commentaire » |
| 5b | la question — bandeau audio de l'app, barre d'avancement |
| 5c | la réponse — **même mise en page**, seuls les cadres changent |
| 5d | l'explication — trois étapes numérotées |
| 5e | le score du public — vert plein cadre, le pourcentage en grand |
| 5f | l'appel — promesse produit et adresse |

**Trois écarts avec ce que j'avais fait avant**, tous voulus par la
maquette. L'écran de réponse n'est plus une félicitation plein vert :
c'est la question, immobile, dont les cadres changent d'état — rien ne
bouge, l'œil compare. Le rouge entre dans la charte, sur l'option piège
seulement. Et la fermeture n'affiche plus de classement : c'était la
bonne décision, le palmarès réel n'aurait montré que des comptes de
test nommés « Smoke ». La question que je vous posais est donc réglée
par la maquette elle-même.

**Le rythme suit la voix.** La maquette donne des durées — 1,5 s pour
l'accroche, 5 s pour la question, 4 à 5 s pour l'explication ; ce sont
des planchers. Chaque texte est synthétisé d'abord, mesuré à l'`ffprobe`,
et l'écran dure au moins le temps qu'on met à le lire. Avec des durées
figées, un énoncé long se faisait couper au milieu d'un mot.

**L'écran 5e ne part pas aujourd'hui.** Il demande de vraies réponses en
base ; il y en a 268 en tout, quatre au maximum sur un même exercice. Un
pourcentage calculé là-dessus serait un chiffre inventé avec une
décimale. Le seuil est à 30 réponses (`--seuil-stats`) et l'écran
s'allumera seul quand le trafic sera là — rien à rebrancher. C'est aussi
lui qui désigne l'option piège de 5c : sans données, aucun cadre ne
passe au rouge.

**Les fontes manquaient.** `Space Grotesk`, `DM Sans` et `DM Mono`
étaient nommées dans la scène mais absentes de la machine : le rendu
retombait sur la sans-serif du système et la maquette n'était pas
reconnaissable. Elles sont installées dans
`/usr/local/share/fonts/saralearn`.

`--lang fr|en` choisit la langue des exercices **et** de la voix. Le
filtre porte sur le thème et non sur la catégorie — `permis` existe dans
les deux langues sous le même slug. Tout le texte fixe vit dans un seul
dictionnaire `TEXTES` en tête de script ; les scènes Remotion ne
contiennent plus une seule chaîne en dur.

**Le fond de la maquette a été corrigé.** Elle pose un papier à #FBFAF7
sous des cadres blancs : cinq niveaux d'écart, et un trait à 13 %
d'opacité pour les séparer. Sur un écran, à 31 %, ça tient. En vidéo
non — h264 lisse un trait clair d'un pixel, et les cadres de réponse
disparaissaient dans le fond. Le papier revient donc vers le #f7f5ef de
`tokens.css`, celui de l'app, et les traits montent à .24 et .16. Les
cadres se détachent alors par le fond ET par le trait.

**Rendez en `--hd`.** Sans lui, la vidéo sort en 540 × 960 et non en
1080 × 1920 : tout est divisé par deux, y compris les traits.

**Toute retouche des scènes demande un `pm2 restart sara-video`.** Le
service construit son bundle Remotion une fois, au démarrage. Sans
redémarrage, le rendu suivant utilise l'ancien code sans rien signaler —
j'ai perdu un rendu là-dessus.

Rendus vérifiés en 1080 × 1920, son mesuré sur les deux :

- <https://sara.education/sara-video/videos/1786121377916-scpbyy.mp4> — fr, 45 s
- <https://sara.education/sara-video/videos/1786121497288-batajk.mp4> — en, 52 s

### 7 août 2026 — La commande vidéo TikTok

> Les écrans et le minutage décrits ici ont été remplacés le même jour
> par ceux de la maquette (entrée du dessus). Ce qui suit reste vrai du
> pont vers `sara-video` et de la voix.

```bash
python3 scripts/video_tiktok.py --categorie conjugaison-fr --nb 2
```

Rejoue les écrans de l'app en 1080×1920. Ouverture 3 s, puis par
exercice : question 20 s, réponse 5 s, explication 20 s ; fermeture 8 s
sur le classement et l'invitation. Deux exercices, 101 s.

**La voix est celle du site**, pas celle du service vidéo. Le script
appelle `POST /api/tts` de SaraLearn, assemble les trois temps de parole
en une piste aux bons instants, la dépose dans `media/tts-video/` — déjà
servi par Apache — et la passe au service en `audioSrc`. Une seule voix
pour le site et les vidéos, un seul cache, une seule clé Google. C'est
`--voix sara`, le défaut ; `piper`, `elevenlabs` et `none` restent
possibles.

Le design ne vient pas de mémoire. Les trois écrans ont été **capturés
sur learn.sara.education** avec le Chromium de Playwright, en vue
téléphone, et reproduits d'après l'image — d'où des écarts qu'on
n'aurait pas devinés : le fond est voilé de vert en haut, les options
n'ont pas de bordure, le libellé de type est en DM Mono espacé, et
surtout l'écran de réponse est **plein vert** avec disque et coche, pas
la question avec la bonne option surlignée. Les couleurs sortent de
`tokens.css`.

Trois choses retirées à la demande : le cadre du service (bandeau,
pastilles, pied « COURS »), les sous-titres incrustés — l'app n'en a
pas ; le SRT continue de partir, c'est lui qui porte le texte lu par
Piper — et le rail de boutons, inutile là où l'on ne touche rien.

Le contenu est cadré dans la bande sûre du milieu, avec 300 px libres
en bas : sur TikTok, la légende, le pseudo et la colonne de boutons
couvrent cette zone. Ce qui descend là-dessous n'est pas lu.

Aucun moteur de rendu écrit : le script est un pont entre la base et
`sara-video`, déjà en place. Ce qui a été ajouté chez lui est une scène,
`src/remotion/SaraExerciseScene.jsx`, et un type de slide
`sara-exercise` dans la validation. Les types existants ne sont pas
touchés.

**Attention : `/var/www/saralearn-video` a donc trois fichiers modifiés
et non commités**, en plus de ce dépôt-ci. La sauvegarde des versions
d'avant est dans le scratchpad de session, qui ne survivra pas.

- `scripts/video_tiktok.py` (nouveau)
- chez `saralearn-video` : `src/remotion/SaraExerciseScene.jsx`
  (nouveau), `src/remotion/PedagogicalVideo.jsx`, `server.js`

### 7 août 2026 — Le pipeline IA, refondu

L'auteur écrit un sujet, rien d'autre. Deux appels au modèle en tirent
la présentation puis le programme, chapitre par chapitre. En ligne et
essayé en production : « les bases du solfège » a rendu cinq chapitres
et créé la catégorie « Musique » en brouillon.

Migration 008 : table `chapter`, `category.status`, et `exercise_prompt`
reconstruite pour que `prompt_id` puisse être nul. Les 465 liens
exercice → prompt ont été comptés avant et après : aucun perdu.

Trois défauts trouvés en testant, tous corrigés :

- le suivi de génération était aveugle aux chapitres — jointure fermée
  sur `prompt`, un lancement sans gabarit disparaissait du compte ;
- la relance des prompts réécrivait tout, y compris ce que l'auteur
  venait de corriger à la main ;
- mon garde-fou sur `short_answer` tuait des chapitres entiers pour un
  aperçu mal formé — huit sur dix perdus au premier essai.

Deux choses écartées, et documentées dans le README plutôt que tues :
`cloze` reste hors du choix du modèle tant que `llm.validate` jette
`blank` et `correct` ; et le contenu n'a plus de source vérifiable, ce
qui est sans conséquence sur les fonctions PHP mais discutable sur le
permis de conduire.

- `api/outline.py`, `api/chapters.py`, `api/routers/knowledge.py`,
  `db/migrations/008_chapitres.sql` (nouveaux)
- `api/llm.py`, `api/schemas.py`, `api/main.py`,
  `api/routers/generate.py`, `src/lib/api.ts`, `src/state/store.tsx`,
  `src/screens/Create.tsx`, `src/i18n.ts`, `src/styles/app.css`,
  `README.md`

L'ancien chemin n'est pas débranché : `POST /themes/{id}/generate` part
toujours des 42 gabarits. Seul le dépôt de Markdown a quitté l'écran.

### 7 août 2026 — L'API passe sous pm2

`pm2 start start.sh --name sara-learn`, puis `pm2 save`. Vérifié pour de
bon : tuée en `kill -9`, l'API est revenue en une seconde.

La note de risque se trompait sur un point. Une unité systemd existait,
`sara-exos-api.service`, **activée** — et en boucle d'échec depuis que le
lancement à la main du 5 août lui avait pris le port 8010. Elle serait
entrée en conflit avec pm2 au redémarrage suivant. Désactivée par
`systemctl disable --now`, le fichier reste sur disque.

Au passage, le redémarrage a mis en production le code Python du disque :
`POST /api/tts` répond enfin (401 au lieu de 404). Vérifié avant la
bascule que `.env` portait les mêmes valeurs que le process en cours, et
que `SARA_SECRET` n'était défini nulle part — la signature des jetons
vient de `data/.secret`, donc personne n'a été déconnecté.

- `start.sh` (nouveau), `README.md`

Reste ouvert : les modifications Python n'étaient pas commitées quand
elles sont parties en ligne. C'est exactement ce que la tâche « committer
le travail en cours » doit empêcher.

### 10 août 2026 — Google Tag Manager retiré

Le conteneur `GTM-P2PR5ZNF` est sorti d'`index.html` : le script du
`head` et le relais `noscript` du `body`. Plus aucun script de mesure,
plus aucun cookie de mesure, plus aucune connexion tierce au
chargement — vérifié dans `dist/index.html` après construction.

La tâche « poser le bandeau de consentement », ouverte en tête d'**À
faire** depuis le 7 août, est retirée : sans traceur, elle n'a plus
d'objet. Si la mesure revient un jour, le bandeau redevient dû **avant**
le script, pas après.

- `index.html`, `README.md`

### 7 août 2026 — Google Tag Manager posé

Conteneur `GTM-P2PR5ZNF` : le script en tête de `head`, le relais
`noscript` en ouverture de `body`. Vérifié en construisant vers un
dossier de travail — pas vers `dist/`, qui est en ligne — le tag
survit à la minification.

La propriété GA4 est `G-PQR5WJ1Z34`. Elle ne figure pas dans le code
et n'a pas à y figurer : elle se pose dans la balise Google du
conteneur, côté interface GTM. Les autres identifiants du compte
(`autocorrecteur`, `syxotur`) sont d'autres sites — ne pas les
brancher ici, GA4 ne sait pas retrier des données mélangées.

Sans consentement, à votre demande. Le bandeau reste à faire, il est
remonté en tête d'**À faire**. *(Caduc : le conteneur a été retiré le
10 août 2026, voir l'entrée du dessus.)*

- `index.html`

En ligne le 7 août 2026. La construction ne portait que ce tag : les
empreintes JS et CSS produites étaient identiques à celles déjà
servies, donc le travail en cours sur le disque n'est pas parti avec.
Conteneur en version 2, balise « Balise Google Sara » sur
*Initialization – All Pages*. Vérifié depuis l'extérieur : le site
sert le conteneur, et le conteneur publié contient bien
`G-PQR5WJ1Z34`.
