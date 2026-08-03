# Analyse technique — App d'exercices (feed vertical)

## 1. Le vrai cœur du problème

Ce n'est pas une app de quiz. C'est **un feed TikTok dont les cartes sont générées par les réponses de l'utilisateur**.

Deux mécaniques portent 80 % de la complexité :

1. **Le deck dynamique** — répondre à un exercice *insère* 2 cartes juste après lui.
2. **Le loader qui bloque le swipe** — le geste n'est pas libre, il est sous condition.

Tout le reste (écrans, audio, progression) est du CRUD classique.

### Le deck

```
deck = [ex1, ex2, ex3, ...]          // au départ : que des exercices préchargés
                ↓ réponse sur ex1
deck = [ex1, résultat(ex1), explication(ex1), ex2, ex3, ...]
```

Une carte typée :

```ts
type Card =
  | { kind: 'exercise';    id: string; ... }
  | { kind: 'success';     exerciseId: string }
  | { kind: 'error';       exerciseId: string; chosen: number }
  | { kind: 'explanation'; exerciseId: string }
```

Un seul composant `<Deck>` mappe `kind → écran`. Ne surtout pas coder 4 écrans qui se poussent l'un l'autre : c'est une liste, pas un routeur.

### Le gate du loader

```ts
const canSwipe = loaderDone[currentIndex]   // seule condition
```

Durées : exercice 3 s · félicitation 2 s · erreur 6 s · explication 8 s.

⚠️ **Décision structurante** : ce loader n'est *pas* un indicateur de chargement réseau, c'est un **minuteur de lecture imposée**. À nommer comme tel en interne pour éviter que quelqu'un le branche sur un `fetch` plus tard.

**Conséquence technique** : on ne peut **pas** utiliser `scroll-snap` CSS. Bloquer un scroll natif en cours de geste = saccade garantie sur iOS. Il faut un geste contrôlé.

> **Stack geste** : `@use-gesture/react` (drag) + `framer-motion` (translate + spring).
> Seules 3 cartes montées dans le DOM (précédente / courante / suivante), `translate3d` uniquement, jamais de `top/height` animé.

---

## 2. Stack recommandée

| Couche | Choix | Pourquoi |
|---|---|---|
| Front | React 18 + TypeScript + Vite | réutilise l'écosystème existant |
| Style | Tailwind + `dark:` | mode sombre gratuit, tokens centralisés |
| Geste/anim | `@use-gesture/react` + `framer-motion` | contrôle total du gate |
| Célébration | `canvas-confetti` (~5 ko) | pas de Lottie/JSON lourd pour ça |
| État | Zustand | deck + compteurs + réglages, sans boilerplate |
| Persistance locale | `localStorage` (réglages, mute) + IndexedDB (queue offline) | |
| Back | FastAPI + SQLite | déjà maîtrisé, suffisant jusqu'à ~10 k users |
| Audio | fichiers **pré-générés** (mp3 64 kbps mono) servis en statique | voir §4 |
| Packaging | **PWA d'abord**, Capacitor ensuite | voir ci-dessous |

### PWA d'abord, natif ensuite

| | PWA seule | + Capacitor |
|---|---|---|
| Délai | immédiat | +1 semaine |
| Stores | ❌ | ✅ |
| Mode silencieux | comportement Safari par défaut | contrôlé (`AVAudioSession` en `ambient`) |
| Haptique au tap réponse | ❌ iOS | ✅ |

**Recommandation** : livrer le prototype et la V1 en PWA. Le wrapper Capacitor est un ajout de fin de parcours, pas une réécriture — même code.

---

## 3. Modèle de données

```sql
categories(id, label)
subcategories(id, category_id, label)

exercises(
  id, subcategory_id,
  question, options_json,      -- 3 ou 4 réponses
  correct_index,
  explanation_text,
  audio_error_url,             -- pré-généré
  audio_explanation_url        -- pré-généré
)

users(id, ...)
attempts(id, user_id, exercise_id, chosen_index, is_correct, created_at)
likes(user_id, exercise_id)
comments(id, user_id, exercise_id, body, created_at)   -- lu par l'admin
user_subcategories(user_id, subcategory_id)            -- écran Paramètres
```

**Compteurs réussites/échecs et progression sont dérivés de `attempts`.** Pas de table de compteurs — elle désynchronise toujours.

Progression d'une sous-catégorie :

```
% = exercices distincts réussis au moins une fois / total exercices de la sous-catégorie
```

⚠️ À valider : un exercice raté puis réussi compte-t-il ? (Recommandation : oui — c'est un app d'apprentissage, pas un examen.)

### API

```
GET  /feed?n=5              → prochains exercices (sous-cat. abonnées, anti-répétition)
POST /attempts              → enregistre, renvoie {correct}
POST /likes/{exercise_id}   → toggle
POST /comments              → envoi admin
GET  /progression           → [{subcategory, percent}]
GET|PUT /settings           → sous-catégories choisies, audio on/off
```

**Choix assumé** : `/feed` renvoie `correct_index` et l'explication **avec** l'exercice. Le feedback est alors instantané (0 ms) et fonctionne hors ligne ; `POST /attempts` part en arrière-plan, en fire-and-forget avec retry.
Le coût : un utilisateur curieux peut lire la réponse dans le DevTools. Sur une app d'apprentissage sans note ni classement, c'est un non-problème — et l'alternative (aller-retour serveur à chaque tap) casse la fluidité, qui est *le* produit ici.

### Sélection des exercices

Simple, et suffisant :

1. filtrer sur les sous-catégories abonnées ;
2. exclure les 20 derniers vus ;
3. pondérer vers les sous-catégories à faible progression ;
4. tirage aléatoire.

Pas d'algo adaptatif en V1.

---

## 4. Audio — le point le plus piégeux

### Autoplay : contrainte bloquante

iOS et Android **interdisent** de jouer un son sans geste utilisateur préalable.

Heureusement le parcours nous sauve : **le premier audio arrive juste après un tap** (tap sur une réponse → félicitation). Il faut simplement débloquer le contexte audio sur ce tout premier tap :

```ts
// au 1er tap de la session, quel qu'il soit
audioEl.play().then(() => audioEl.pause())   // unlock
```

Sans ça, le premier son de la session est muet — bug classique, invisible en dev sur desktop.

### Pré-génération, pas de TTS à la volée

| | TTS runtime | Fichiers pré-générés |
|---|---|---|
| Latence | 300–2000 ms | 0 |
| Hors ligne | ❌ | ✅ |
| Coût | par écoute | une fois |

**Décision : tout pré-générer** par un script batch au moment de la création du contenu.

Volume :

- **Félicitation** : ~8 clips génériques ("Bravo !", "Excellent !") + 1 son de célébration. Tirage aléatoire. **Pas de génération par exercice.**
- **Erreur** : 1 audio par exercice (il faut énoncer la bonne réponse).
- **Explication** : 1 audio par exercice.

Soit ~2 fichiers × ~25 s par exercice ≈ **400 ko**. 1 000 exercices ≈ **400 Mo** de statique. Trivial à servir.

### Mode silencieux

- PWA / Safari iOS : `<audio>` respecte l'interrupteur silencieux nativement. Rien à faire.
- Capacitor : forcer la catégorie `ambient` (sinon iOS joue par-dessus le mode silencieux — perçu comme un bug).

### Préchargement

Précharger l'audio de la carte **n+1** uniquement. Au-delà, on gaspille de la data mobile pour des cartes que l'utilisateur peut ne jamais atteindre.

---

## 5. Contraintes de layout (390 × 844)

Le rail gauche à 6 éléments et les boutons de réponse pleine largeur en bas **se disputent la place**.

```
┌──────────────────────────┐
│ ▓▓▓▓▓▓░░░░░░░░  loader   │  ~4 px + safe-area top
├──────────────────────────┤
│                          │
│      QUESTION            │  zone flexible
│                          │
│ ┌──┐                     │
│ │🏆│ 12                  │
│ │✕ │ 3                   │  rail : 44×44 min,
│ │♥ │ 48                  │  gap 8-12 px
│ │💬│                     │  → 6×44 + 5×10 = 314 px
│ │📊│                     │  centré verticalement
│ │⚙ │                     │
│ └──┘                     │
│                          │
│  [ Réponse A          ]  │  ~56 px chacun
│  [ Réponse B          ]  │  × 4 + gaps = ~260 px
│  [ Réponse C          ]  │
│  [ Réponse D          ]  │
└──────────────────────────┘  + safe-area bottom (34 px)
```

Budget vertical serré : 844 − 60 (statut/safe) − 34 (home indicator) − 260 (réponses) = **~490 px** pour question + rail. Le rail à 314 px doit être **centré dans cette zone**, pas collé au bas.

Points de vigilance :

- Les réponses pleine largeur passent **sous** le rail → prévoir un `padding-left` sur les boutons, ou remonter le rail. À trancher au design.
- Question longue : `clamp()` sur la taille de police + `line-clamp`. **Jamais de scroll** (règle du cahier des charges) → il faut donc une **limite de caractères à l'écriture du contenu** (~180 car. question, ~60 car. par réponse, ~400 car. explication). C'est une contrainte éditoriale, pas technique : à graver dans l'outil d'admin.
- `100vh` est cassé sur mobile → utiliser `100dvh` + `env(safe-area-inset-*)`.

---

## 6. Points à trancher avant de coder

| # | Question | Recommandation |
|---|---|---|
| 1 | Après une réponse, transition auto vers félicitation/erreur, ou swipe ? | **Auto** (le tap *est* le geste). Puis swipe pour la suite. |
| 2 | Félicitation → explication : auto quand le loader finit, ou swipe ? | **Swipe**. Sinon le loader ne sert plus de gate, il devient un simple timer. |
| 3 | Peut-on swiper vers le haut (revenir en arrière) ? | **Oui**, historique consultable, mais pas de re-réponse. |
| 4 | Un exercice sauté sans réponse revient-il plus tard ? | **Oui**, remis en pool. Il n'a pas été traité. |
| 5 | Compte / anonyme ? | **Anonyme + device_id** en V1. Compte = friction sur un onboarding qui doit ouvrir direct sur un exercice. |
| 6 | Le loader se réinitialise-t-il si on revient sur une carte déjà vue ? | **Non**, déjà validé → swipe libre. |
| 7 | Un exercice raté puis réussi compte dans la progression ? | **Oui** (§3). |
| 8 | Projet autonome ou module de SaraLearn ? | Impacte la réutilisation du backend — à confirmer. |

---

## 7. Risques

| Risque | Gravité | Mitigation |
|---|---|---|
| Premier son muet (autoplay iOS) | 🔴 | unlock au 1er tap, testé sur device réel |
| Saccades du swipe | 🔴 | 3 cartes max en DOM, `translate3d`, pas de scroll natif |
| Loader perçu comme "l'app rame" | 🟠 | animation fluide + micro-copie ; tester la perception |
| Rail 6 icônes illisible en 390 px | 🟠 | maquette à taille réelle **avant** l'intégration |
| Contenu trop long → scroll interdit | 🟠 | limites de caractères imposées côté admin |
| Volume d'audio à produire | 🟡 | générique pour la félicitation, batch pour le reste |

---

## 8. Chemin de livraison

**Prototype cliquable (livrable 3)** — 3 exercices en dur, aucun backend :
deck + geste + gate du loader + 4 types d'écran + 1 bonne réponse et 1 erreur. C'est là que se valide le *feeling*, et le feeling est le produit. Rien d'autre ne doit entrer dans cette étape.

Ensuite : kit de composants → backend + contenu → écrans progression/paramètres → audio → PWA → Capacitor.

**Ordre non négociable** : le geste et le gate en premier. Si le swipe n'est pas agréable, le reste ne sert à rien.
