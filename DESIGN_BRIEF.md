# SaraLearn — brief design

Inventaire complet des écrans, de leur contenu et de leurs fonctions, destiné à
servir de base à une nouvelle proposition de design.

---

## 1. Ce qu'est le produit

Une app d'apprentissage par **feed vertical d'exercices**. On ouvre l'app et on
tombe directement sur une question — pas sur un tableau de bord, pas sur un
catalogue. On swipe vers le haut pour l'exercice suivant, comme un fil social.

L'apprenant **s'abonne à des thèmes** (« Vocabulaire anglais », « Mythologie
grecque »…) ; le feed est alimenté par ces abonnements. N'importe qui peut
**créer un thème** en déposant du Markdown : l'IA génère les exercices, l'auteur
les relit un par un, puis publie en privé ou soumet à relecture.

L'app est **jouable sans compte**. Le compte sert à conserver la progression.

Deux langues : français et anglais. Un thème est écrit dans une langue et n'est
jamais traduit — changer de langue change le catalogue servi.

### Le ton, non négociable

- **Jamais de rouge, jamais de croix.** Une erreur s'affiche en ambre de reprise,
  avec la bonne réponse en vert calme et une ligne en italique qui dédramatise.
  Ce parti pris traverse toute l'app, jusqu'au pouce-bas du rail.
- **Les pourcentages n'apparaissent que sur la progression et le classement.**
  Jamais pendant un exercice.
- **Un écran, un contenu.** Le feed ne scrolle pas ; seule la page « À propos »
  est une exception assumée.
- Un papier crème et une action verte. Typo display serif, UI sans-serif.

---

## 2. Les deux cadres

L'app n'est pas « un design mobile étiré ». Ce sont deux mises en scène
distinctes du même contenu, qui basculent à **1024 px**.

### Mobile (< 1024 px)

```
┌─────────────────────────┐
│ [Wordmark]        [⋯]   │  mobile-bar (logo + menu 3 points)
├─────────────────────────┤
│ ▓▓▓▓▓░░░░░░░░░░░░░░░░░  │  loader de progression
│ [● Thème ›]      TYPE   │  exo-head
│                         │
│      contenu de          │  exo-body — se déplace au drag
│      la phase            │
│                         │  ┌──┐ rail vertical droit
│                         │  │✓ │ 44px de cible
│  ─────────────────────  │  │↺ │
│   zone de réponse        │  │👍│
│                         │  │👎│
└─────────────────────────┘  │💬│
                             │🏆│
                             │⚙ │
                             └──┘
```

Le **rail** vertical à droite : réussites (vert), échecs (ambre), pouce haut,
pouce bas, commentaires, classement, réglages. Les deux premiers sont des
compteurs qui se lisent — pas des boutons. Les cinq autres sont de vraies cibles
de 44 px. Sept éléments, c'est le maximum tenable.

Les pages autres que le feed ont une `nav-head` (flèche retour + titre) et une
`footer-bar` collée en bas avec l'action principale.

### Desktop (≥ 1024 px)

```
┌──────────────────────────────────────────────────────────┐
│ [Wordmark]  Mes thèmes  Classement  Réglages  À propos    │
│                          🔊 Son  👤 Compte  ⚙            │  topbar
├──────────────────────────────────────────────────────────┤
│  ┌──┐         ┌────────────────────────┐          ┌───┐  │
│  │✓ │         │ ▓▓▓▓░░░░░░░░░░░░░░░░░  │          │ ▲ │  │
│  │↺ │         │ [● Thème]      TYPE     │          │ ▼ │  │
│  │👍│         │                        │          └───┘  │
│  │👎│         │   contenu de la phase   │   desk-nav      │
│  │💬│         │                        │                 │
│  │🏆│         │  ────────────────────  │                 │
│  └──┘         │   zone de réponse       │                 │
│  rail         └────────────────────────┘                 │
│  gauche          desk-card (carte centrale)              │
└──────────────────────────────────────────────────────────┘
```

Le rail passe **à gauche**, la carte d'exercice est centrée dans un cadre
vertical, et deux flèches à droite doublent la molette et les touches.

Les autres écrans prennent **toute la largeur** (`desk-column is-wide`) et
adoptent des mises en page à deux colonnes propres au desktop — détaillées écran
par écran ci-dessous.

### Les superpositions

| Élément | Mobile | Desktop |
|---|---|---|
| **Sheet** (thème / commentaires) | feuille du bas, avec poignée | panneau latéral 440 px |
| **Menu** de navigation | pop-over sous les 3 points | inutile, liens en clair |
| **Toast** | bandeau bas | bandeau bas |

---

## 3. Les écrans, un par un

### 3.1 `#welcome` — Porte d'entrée

Une affiche, pas un formulaire. Wordmark, une accroche en gros display serif, une
ligne de corps, un bouton « Commencer », et sous lui la mention « aucun compte
nécessaire ». En desktop, la maquette pose délibérément la promesse à gauche et
laisse une colonne vide de 380 px à droite — c'est ce déséquilibre qui donne à
l'écran son air d'affiche.

### 3.2 `#categories` — Choix des catégories (étape 2/3)

Eyebrow « Étape 2 », titre « Choisis ce qui t'intéresse », puis une grille de
tuiles (3 colonnes en desktop, 2 en mobile). Chaque tuile : une pastille de
couleur, le nom de la catégorie, et dessous le nombre de sous-thèmes. Sélection
multiple — la tuile cochée passe en vert pâle avec une coche en coin.

Deux actions en pied : « Continuer avec N » et « Passer ».

Ce choix ne fait que **filtrer l'écran suivant** ; il n'engage à rien.

### 3.3 `#subcategories` — Choix des thèmes (étape 3/3)

Titre « Décoche ce que tu veux », lead « tout est coché par défaut ». Une liste
verticale de lignes : case à cocher, nom du thème, catégorie en dessous. Filtrée
par les catégories de l'étape précédente.

Pied : « C'est parti · N thèmes ». Mène directement au feed.

### 3.4 `#exercise` — Le feed (l'écran principal)

C'est **le** écran de l'app. Il porte quatre phases successives, dans la même
carte, avec des transitions animées (`anim-fade-up`).

#### Phase `q` — Question

Illustration optionnelle **avant** la question (sur « que signifie ce panneau ? »,
c'est l'image qui porte l'information ; la question se fait alors plus discrète
pour que les deux tiennent sans scroll). Puis l'énoncé en display serif, puis un
corps de texte optionnel dans un bloc encadré.

La zone de réponse dépend du type :

| Type | Interaction |
|---|---|
| **QCM** (défaut) | 3–4 boutons d'option empilés |
| **short_answer** | un champ texte + bouton d'envoi ; la réponse est acceptée après normalisation (accents, casse) |
| **cloze** | texte à trous : les trous se remplissent **dans le texte lui-même**, les candidats sont dans le pied. Chaque trou porte SES candidats — jamais de banque commune |

Un indice de swipe (flèche + « glisse pour la suite ») apparaît en pied.

#### Phase `ok` — Réussite

Célébration dorée centrée : un anneau qui s'échappe en boucle, un disque or, une
coche qui se trace au trait. Titre en très gros display, une ligne de corps, puis
une pastille de série (« 3 d'affilée »).

#### Phase `ko` — Erreur

**Aucune croix, aucun rouge.** Un disque ambre avec une icône « refaire », le
titre à côté. Puis deux blocs côte à côte en desktop, empilés en mobile :

- « Ta réponse » — fond creusé, texte gris
- « La bonne réponse » — fond vert pâle, bordure et texte vert

Enfin une ligne en **italique serif** qui dédramatise.

#### Phase `exp` — Explication

Une ampoule dorée + eyebrow « Explication », un titre display, un paragraphe de
corps, puis un bloc « À retenir » encadré. Un bouton « Exercice suivant » avec
une flèche qui fait un léger va-et-vient.

#### États d'attente

- **Chargement** : deux barres shimmer + « on prépare… »
- **Serveur injoignable** : icône d'alerte, message, bouton « Réessayer »

### 3.5 `#themes` — Mes thèmes

Deux sections. En haut, mes abonnements sous forme de **chips** avec une pastille
de couleur et un petit bouton « − » pour se désabonner, plus un chip d'ajout
bordé de vert qui mène au choix de thèmes. Un état vide si rien n'est suivi.

En bas, **la progression** : une grille de jauges (côte à côte, pour qu'elles se
comparent d'un coup d'œil), chacune avec le nom du thème, le pourcentage, et une
barre qui passe à l'or au-delà de 80 %.

### 3.6 `#add-themes` — Ajouter des thèmes (niveau 1)

Titre + lead « Filtre par catégorie, puis choisis. Rien n'est définitif. »

Une grille de tuiles de catégories (3 colonnes de 160 px en desktop) qui sert de
**filtre local**, puis en dessous la liste des thèmes en chips cliquables — l'état
« abonné » se lit au fond vert pâle.

En pied de la liste, un bouton « Créer le mien » qui ouvre le flux de création.

> **Point à trancher dans le nouveau design** : aujourd'hui, tant qu'aucune
> catégorie n'est cochée, la liste affiche **tous** les thèmes sous l'intitulé
> « Tous les thèmes ». C'est redondant avec l'écran suivant, qui affiche lui aussi
> la liste complète. La direction souhaitée est que **le filtre gère seul** ce qui
> s'affiche.

### 3.7 `#all-themes` — Choix des thèmes (niveau 2)

Une grille de tuiles 4 colonnes : pastille de couleur, titre du thème, catégorie
en petit, coche en coin si abonné. Pied : « C'est parti · N thèmes ».

### 3.8 `#leaderboard` — Classement

Un sélecteur segmenté à deux positions.

**« Mes forces »** — une intro en italique serif, puis une grille de cartes : un
badge de rang, le nom du thème, « 12/40 · 30 % », et une jauge.

**« Les autres »** — une mise en page à deux colonnes : à gauche un sélecteur
vertical de thèmes (« Tous les thèmes » + mes abonnements avec leur pastille), à
droite le classement du thème choisi. Chaque ligne : rang, avatar à initiale,
nom, points. **Ma ligne est surlignée** en vert pâle avec bordure verte, et le nom
est remplacé par « Toi ».

Lead permanent : « remis à zéro chaque semaine ».

### 3.9 `#leaderboard-theme` — Classement d'un thème

Deux colonnes (340 px + reste). À gauche, une grande carte verte : mon rang en
chiffre énorme avec son suffixe (« 3ᵉ »), « Ta place », mes points et ma
progression sur ce thème. À droite, « Cette semaine » et la liste complète.

### 3.10 `#create` — Création d'un thème (4 étapes)

Un en-tête permanent : flèche retour, « Nouveau thème », et **quatre traits de
progression** à droite qui se remplissent en vert.

**Étape 1 — Dépôt.** Une grande zone en pointillés avec trois pastilles d'icônes
colorées (fichier bleu, texte violet, micro rose), un titre « Colle ton
Markdown », et un textarea. Puis deux champs : titre et description. Bouton
« Analyser » avec une icône étincelle, désactivé tant que le Markdown fait moins
de 40 caractères.

**Étape 2 — Classement.** Un badge « Proposé » avec étincelle, puis le titre
« Voici son classement ». Deux menus déroulants (catégorie, sous-catégorie) et une
zone de tags : chaque tag est un chip avec un « − », et un champ en dessous pour
en ajouter à la volée avec Entrée.

**Étape 3 — Types et volume.** Une liste de cinq types d'exercices, chacun une
ligne cochable avec nom, description, et un badge or « Recommandé » sur le QCM :

| Type | Description |
|---|---|
| QCM | 3 ou 4 options, une correcte |
| Trouve l'erreur | Une production fausse à localiser |
| Vrai / Faux | Une affirmation à trancher |
| Complète | Un élément manquant à retrouver |
| Remets dans l'ordre | Des éléments à réordonner |

Puis une carte avec un curseur (5 à 40, par pas de 5), le nombre affiché en gros
display, et une estimation de durée. Bouton « Générer ».

**État de génération.** Un écran plein : « On rédige… », une ligne de corps, trois
barres shimmer, et un compteur de progression.

**Étape 4 — Relecture.** En tête, « À relire » et « 3/12 validés ». Puis **une
carte à la fois** : pastille ambre + type, l'énoncé en display, le corps, les
options avec la bonne réponse surlignée en vert et cochée, et enfin un bloc ambre
« Explication à relire ».

En pied : un gros bouton vert « Valider » et un bouton carré « corbeille » pour
rejeter. En dessous, « Régénérer » à gauche et un petit bouton cadenas
« Publication privée » à droite.

### 3.11 `#publish` — Publication

Deux colonnes (1fr + 380 px). À gauche, deux grandes cartes de choix mutuellement
exclusives :

- **Privé** — icône cadenas, badge « par défaut »
- **Public** — icône globe, précise que ça passe par une relecture

Sous elles, un bloc creusé en italique : « tu pourras changer plus tard ».

À droite, un récapitulatif : titre du thème, « N exercices validés », et les tags
en chips.

**État de succès** : un disque or avec une grande coche, un titre selon le cas
(« Envoyé en relecture » ou « Enregistré en privé »), une ligne d'explication, et
un bouton de retour au feed.

### 3.12 `#sign-in` — Compte

Deux colonnes en desktop : la **promesse à gauche** en gros (« Garde ta
progression »), avec une ligne cochée en vert qui explique que la progression
anonyme sera fusionnée ; le **formulaire dans une carte à droite**.

Le formulaire bascule entre connexion et inscription sur le même écran : email,
mot de passe (8 caractères minimum), et — **à l'inscription seulement** — un
sélecteur segmenté Français / English, parce que la langue fixe le catalogue.

Les erreurs s'affichent dans un bloc dédié qui dit ce qui s'est passé et comment
le régler. En pied : bascule connexion/inscription, et « continuer sans compte ».

### 3.13 `#settings` — Réglages

Mobile : une liste verticale de sections. Desktop : les **mêmes sections en cartes
sur deux colonnes**, sous un vrai titre de page.

| Section | Contenu |
|---|---|
| Thèmes | une ligne qui mène à « Mes thèmes », avec le compte d'abonnements |
| À propos | une ligne qui mène à la page vision/mission |
| Audio | interrupteur « sons de retour », interrupteur « mode sombre » |
| Langue | segmenté Français / English + note explicative |
| **Compte** | traverse toute la grille — connecté : email + « Se déconnecter » ; sinon : « Créer un compte » + « Se connecter » |

Le compte est en pleine largeur parce que c'est la décision la moins fréquente et
la plus conséquente de la page.

### 3.14 `#about` — Vision et mission

**Le seul écran qui scrolle**, et c'est assumé. Il se lit comme une page imprimée :
un wordmark en grand et un slogan en italique serif, puis vision et mission **en
vis-à-vis sur deux colonnes**, puis un « battement » en pleine largeur — trois
temps de plus en plus courts — et enfin une clôture. La mesure de ligne reste
bornée même sur écran large.

### 3.15 `#admin` — File de relecture

Un calque hors du parcours normal, ouvert par l'URL et fermé en effaçant le
fragment. Protégé par un jeton de service qui meurt avec l'onglet.

Un sélecteur segmenté à trois positions :

- **Thèmes** — les thèmes en attente de publication publique, avec leur auteur,
  leur nombre d'exercices, et deux actions accepter / refuser
- **Exercices** — ceux que le vote a mis en quarantaine, avec le détail des
  pouces et le pourcentage de rejet
- **Avis** — les commentaires remontés, lus ou non, avec l'exercice concerné

Chaque entrée est une carte. Un état « accès refusé » avec champ de jeton, un
état d'erreur avec bouton de réessai, un état vide en italique.

---

## 4. Les composants transverses

| Composant | Rôle |
|---|---|
| **Wordmark** | la marque, cliquable, ramène au feed |
| **Loader** | barre de progression fine en haut de la carte d'exercice |
| **NavHead** | flèche retour + titre + sous-titre optionnel (mobile) |
| **Meter** | jauge de progression, or au-delà de 80 %, vert sinon |
| **Toggle** | interrupteur, vert quand actif |
| **Checkbox** | case carrée arrondie avec coche |
| **TileCheck** | coche en coin de tuile sélectionnée |
| **Dot** | pastille de couleur d'un thème |
| **Avatar** | disque coloré à initiale |
| **Chip** | pilule cliquable ou statique, état actif en vert pâle |
| **Segmented** | sélecteur à 2 ou 3 positions |
| **Toast** | notification basse |
| **Sheet / Panel** | feuille basse (mobile) ou panneau 440 px (desktop) |
| **Rail** | colonne d'actions du feed |

### Le Sheet, en détail

Deux contenus dans le même contenant.

**Panneau thème** : pastille + nom en display, un blurb, deux statistiques côte à
côte (exercices, abonnés), une carte creusée « Ta progression ici » avec la jauge,
puis un bouton d'abonnement qui change de couleur selon l'état et un lien vers le
classement du thème.

**Panneau commentaires** : la liste (avatar, nom, texte), un état vide en italique,
et en bas une barre de saisie avec bouton d'envoi.

---

## 5. Le système actuel

Les jetons viennent déjà d'un design system (« Réviz »), retaillés à ce que l'app
utilise. Le nouveau design peut les remplacer entièrement — l'app peint
**exclusivement** à travers les variables `--sc-*`, ce qui rend un changement de
peau complet possible sans toucher à la mise en page.

### Typographies

- **Display** : Newsreader (serif) — titres, questions, chiffres importants
- **UI** : Manrope (sans-serif) — tout le reste
- Un style **serif italique** dédié aux lignes qui dédramatisent ou introduisent

### Palette claire (le monde « papier »)

| Rôle | Valeur |
|---|---|
| Fond | `#faf7f0` crème |
| Surface | `#ffffff` |
| Surface creusée | `#f6f2ea` |
| Texte / secondaire / tertiaire | `#1a1814` / `#3f3a33` / `#6e665b` |
| Filet | `#e5decf` |
| **Action** | `#0a5c2c` vert profond |
| Action pâle | `#e6f4ec` |
| Marque | `#20814a` (le vert du logo, distinct de l'action) |

### Palette sombre

Fond `#14120f`, surface `#1e1b17`, texte `#f5f1e8`, action `#74c494` — la même
teinte éclaircie pour tenir le contraste, jamais une autre couleur.

### Accents

Or (`#c8932e`) pour la célébration et la maîtrise. Ambre (`#d88a0e`) pour la
reprise et l'erreur. Vert semantic (`#2f9352`) pour la bonne réponse. Bleu,
violet, rose, ambre pour distinguer les thèmes entre eux.

### Rayons, ombres, mouvement

Rayons 10 / 14 / 20 / 28 px et pilule. Quatre niveaux d'ombre plus une ombre
creusée. Deux courbes d'accélération (une sortie douce, un ressort) et trois
durées (140 / 220 / 360 ms). Toutes les animations se coupent sous
`prefers-reduced-motion`.

---

## 6. Ce qu'on attend de la nouvelle proposition

1. **Le feed d'abord.** C'est 90 % du temps passé dans l'app. Les quatre phases
   (question, réussite, erreur, explication) sont les écrans qui comptent le plus.
2. **Les deux cadres.** Mobile et desktop ne sont pas la même mise en scène ; il
   faut les deux.
3. **Le ton non punitif tenu jusqu'au bout.** Si la proposition introduit du rouge
   ou une croix sur l'erreur, elle rate le sujet.
4. **Clair et sombre.** Les deux mondes, pas un thème sombre bricolé après coup.
5. **Un système de jetons** substituable aux `--sc-*` actuels.
