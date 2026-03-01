# Commande Manager – Spécification technique

## Objectif et problème

Avec des projets comme **Dipsyc**, les réponses de l’IA sont si volumineuses qu’**on ne reçoit qu’une partie** de la réponse (troncature, limites d’API). Il faut donc **découper** le travail en petits morceaux.

Le **rôle du Manager** : il **sait quoi lancer** en interrogeant la base. Il ne reçoit **pas d’options** (sauf `--dry-run`) : il détermine lui-même quels sous-chapitres n’ont pas de cours, quels (sous-chapitre × Bloom) n’ont pas de modules, quels (sous-chapitre × preset) n’ont pas de livre. Puis il appelle les commandes **uniquement pour ce qui manque**, et **par sous-chapitre / par preset** pour éviter les réponses tronquées.

---

## 1. Principe : le Manager n’a pas d’options, il décide tout

- Le Manager **n’a pas d’option** (sauf `--dry-run` éventuel). Il ne reçoit pas `--classroom`, `--subject`, `--filter`, etc.
- Il **charge tous les sous-chapitres** (ou ceux ayant un chapitre → matière → classe valide), puis interroge la base pour savoir :
  - **Cours** : quels sous-chapitres n’ont **pas encore de cours** (`course` null ou vide) → il ne lance la commande cours que pour ceux-là.
  - **Modules** : pour chaque sous-chapitre, quels **niveaux Bloom** n’ont **aucun module** → il ne lance la commande modules que pour les (sous-chapitre, liste de Bloom manquants), avec `--bloom-types=...` pour ne générer que les niveaux manquants.
  - **Livres** : quelles combinaisons (sous-chapitre, preset) n’ont **pas encore de Path** → il ne lance la commande livres que pour celles-là.
- Il **découpe** : chaque appel enfant cible **un sous-chapitre** (et pour les livres **un preset**), pour limiter la taille des réponses IA.

---

## 2. Ce que le Manager calcule (côté Manager)

| Besoin | Critère « déjà fait » | Ce que le Manager lance |
|--------|------------------------|--------------------------|
| **Cours** | `Subchapter::getCourse()` non null et non vide | Un appel par sous-chapitre **sans cours** : `app:generate-course-mindmap --classroom=... --subject=... --filter=subchapter --subchapter=<id>` |
| **Modules** | Pour chaque (sous-chapitre, niveau Bloom) : au moins un `Module` en base | Un appel par sous-chapitre ayant **au moins un Bloom manquant** : `app:h5p:generate-modules ... --subchapter=<id> --bloom-types=remember,apply` (ex. uniquement les niveaux qui n’ont pas encore de module) |
| **Livres** | Un `Path` existe pour (sous-chapitre, types du preset) | Un appel par (sous-chapitre, preset) **sans Path** : `app:h5p:generate-interactive-books ... --subchapter=<id> --preset=remember,understand` |

Les identifiants `classroom` et `subject` sont déduits pour chaque sous-chapitre via `subchapter → chapter → subject → classroom` (slug ou id).

---

## 3. Ordre d’exécution

1. **Phase 1** : génération des **cours** pour tous les sous-chapitres qui n’en ont pas.
2. **Phase 2** : génération des **modules** pour chaque sous-chapitre qui a au moins un niveau Bloom sans module (un appel par sous-chapitre avec `--bloom-types` = niveaux manquants).
3. **Phase 3** : génération des **livres interactifs** pour chaque (sous-chapitre, preset) sans Path.

Chaque commande est lancée en **non-interactif** (`--no-interaction`).

---

## 4. Implémentation

| Élément | Détail |
|--------|--------|
| **Nom** | `app:manager:generate` |
| **Options** | Aucune (ou uniquement `--dry-run` transmis aux commandes). |
| **Repositories** | `SubchapterRepository` (tous les sous-chapitres), `ModuleRepository` (existence modules par sous-chapitre × Bloom), `PathRepository` (existence Path par sous-chapitre × types). |
| **Résolution contexte** | Pour chaque sous-chapitre : `chapter → subject → classroom` pour construire `--classroom` et `--subject` passés aux commandes. |

---

## 5. Résumé

- **Problème** : réponses IA trop longues → troncature.
- **Rôle du Manager** : **savoir quoi lancer** en interrogeant la base (sous-chapitres sans cours, Bloom sans modules, presets sans Path), puis **découper** les appels (sous-chapitre par sous-chapitre, preset par preset).
- Le Manager **n’a pas d’options** : il décide tout depuis les données (c’est bien le côté « manager »).

---

## 6. Musique par cours (Suno API)

L’**API Suno** permet de générer de la musique à partir d’un texte (prompt) : style, ambiance, instrumental ou avec voix. Elle peut servir à créer **une musique par cours** (sous-chapitre), par exemple une courte piste de fond ou un jingle pour le Reveal.js.

- **Doc** : [Suno API – Quick Start](https://docs.sunoapi.org/suno-api/quickstart)
- **Workflow** : `POST /api/v1/generate` avec `prompt`, `model` (ex. `V4_5ALL`), `instrumental` → retourne un `taskId` ; puis `GET /api/v1/generate/record-info?taskId=...` jusqu’à `status === 'SUCCESS'` ; la réponse contient `response.data[].audio_url` (MP3).

### Ce qu’il faut en termes de service et d’entité

| Composant | Rôle |
|-----------|------|
| **Entité `CourseMusic`** | Lier un sous-chapitre à une piste générée : `subchapter` (ManyToOne vers `Subchapter`), `sunoTaskId` (string), `audioUrl` (string, URL du MP3), `prompt` (texte envoyé à Suno), `title`, `duration` (secondes), `createdAt`. Une entrée par sous-chapitre (ou une par « version » si on veut garder l’historique). |
| **Service `SunoApiClient`** | Appels HTTP à Suno : `generate(array $params): string` (retourne `taskId`), `getRecordInfo(string $taskId): array` (status + `response.data`). Clé API dans `.env` : `SUNO_API_KEY`, base URL `https://api.sunoapi.org`. |
| **Service `CourseMusicGenerator`** | Construit le prompt à partir du sous-chapitre (titre, matière, niveau classe), appelle `SunoApiClient::generate`, poll `getRecordInfo` jusqu’à SUCCESS, récupère `audio_url`, crée ou met à jour une entité `CourseMusic` et l’associe au `Subchapter`. Peut proposer un style par défaut (ex. instrumental, calme, « background education »). |
| **Commande `app:generate-course-music`** | Pour les sous-chapitres qui ont déjà un cours mais pas de `CourseMusic` (ou par `--subchapter=id`). Appelle `CourseMusicGenerator` par sous-chapitre. Optionnel : le Manager peut ajouter une phase « musique » après les cours. |
| **Intégration front** | Dans le cours Reveal.js : utiliser `CourseMusic.audioUrl` (ou `Subchapter` → première `CourseMusic`) comme piste audio de fond (balise `<audio>` ou config Reveal). |

Résumé : **oui, l’API Suno peut nous aider** ; il faut une entité pour stocker la piste (ex. `CourseMusic`), un client API (Suno), un service de génération qui bâtit le prompt et enregistre le résultat, et une commande (éventuellement pilotée par le Manager) pour lancer la génération par sous-chapitre.
