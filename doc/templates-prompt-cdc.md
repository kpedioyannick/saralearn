# Propositions de templates de prompt – Génération de modules H5P (CDC)

Le prompt envoyé à l’IA doit produire un JSON conforme au CDC (racine `subchapters`, `bloom_levels`, exercices avec `explications` et `indices`).

**Implémenté :** **Proposition 2** (chapitre × niveau Bloom) et **Proposition 3** (sous-chapitre × niveau Bloom). **Par défaut : Proposition 2.**

---

## Rappel des placeholders

| Placeholder | Rôle | Exemple |
|-------------|------|--------|
| `[MATIÈRE]` | Domaine / matière | FRANÇAIS, Mathématiques |
| `[NIVEAU]` | Classe (niveau scolaire) | CM2, 3eme |
| `[NOMS_SOUS_CHAPITRES]` | Liste des sous‑chapitres du chapitre | Titre 1, Titre 2, … |
| `[NIVEAU_BLOOM]` | Niveau de la taxonomie de Bloom (optionnel) | remember, understand, apply, analyze, evaluate |
| `[TYPES_H5P_AUTORISES]` | Types H5P autorisés pour ce niveau Bloom | H5P.MultiChoice, H5P.TrueFalse, … |

---

## Proposition 1 : Un prompt par chapitre (tous les niveaux Bloom)

- **Périmètre** : 1 appel = 1 chapitre entier → JSON complet (5 niveaux Bloom × 2 difficultés × 5 exercices par sous‑chapitre).
- **Avantage** : Moins d’appels API, cohérence globale du chapitre.
- **Inconvénient** : Réponse très longue, risque de coupure ou d’erreur.

**Template :**
```
Génère un fichier JSON pour le domaine [MATIÈRE] au niveau [NIVEAU], portant sur les sous-chapitres suivants : [NOMS_SOUS_CHAPITRES].
[Règles CDC complètes : structure subchapters, bloom_levels, 5 questions débutant + 5 intermédiaire par niveau Bloom, types H5P par niveau, explications et indices obligatoires.]
Renvoie UNIQUEMENT un objet JSON valide avec la racine "subchapters". Langue : français.
```

---

## Proposition 2 : Un prompt par chapitre × un niveau Bloom (recommandé)

- **Périmètre** : 1 appel = 1 chapitre + **1 niveau Bloom** (ex. `remember`).  
  La réponse ne contient que les exercices pour ce niveau Bloom (débutant + intermédiaire) pour tous les sous‑chapitres du chapitre.
- **Avantage** : Réponses de taille maîtrisée, adapté au cron « par chapitre et par type Bloom ».
- **Inconvénient** : 5 appels par chapitre (un par niveau Bloom).

**Template :**
```
Tu es un expert en ingénierie pédagogique et en taxonomie de Bloom. Tu génères du contenu au format JSON pour un niveau scolaire précis.

LANGUE : Tout le contenu (cours, questions, réponses, indices, explications) DOIT être en français.

PÉRIMÈTRE DE CET APPEL :
- Domaine : [MATIÈRE]
- Niveau classe : [NIVEAU]
- Sous-chapitres concernés : [NOMS_SOUS_CHAPITRES]
- Niveau de Bloom à générer UNIQUEMENT : [NIVEAU_BLOOM]
- Types H5P autorisés pour ce niveau : [TYPES_H5P_AUTORISES]

Pour ce niveau Bloom uniquement, génère 2 sous-niveaux de difficulté : "débutant" (5 exercices) et "intermédiaire" (5 exercices).
Chaque exercice DOIT contenir "explications" (tableau de strings) et "indices" (tableau de strings). Structure stricte selon le type H5P (voir CDC).

Renvoie UNIQUEMENT un objet JSON valide avec la racine "subchapters". Chaque élément du tableau doit contenir au minimum :
- title, slug, level, course, mindmap (PlantUML), et "bloom_levels" avec UNIQUEMENT la clé "[NIVEAU_BLOOM]" remplie, au format :
  "[NIVEAU_BLOOM]": { "débutant": [ 5 exercices ], "intermédiaire": [ 5 exercices ] }.
```

*(Le service remplacera `[NIVEAU_BLOOM]` dans la consigne par la valeur réelle, ex. `remember`.)*

---

## Proposition 3 : Un prompt par sous‑chapitre × un niveau Bloom

- **Périmètre** : 1 appel = **1 sous‑chapitre** + 1 niveau Bloom.  
  Réponse = 5 exercices débutant + 5 intermédiaire pour ce seul sous‑chapitre et ce niveau Bloom.
- **Avantage** : Réponses très courtes, idéal pour limiter les timeouts.
- **Inconvénient** : Beaucoup d’appels (nb_sous_chapitres × 5).

**Template :**
```
Tu es un expert en ingénierie pédagogique et en taxonomie de Bloom. Tu génères du contenu JSON pour un seul sous-chapitre et un seul niveau Bloom.

LANGUE : Tout en français.

PÉRIMÈTRE :
- Domaine : [MATIÈRE]
- Niveau classe : [NIVEAU]
- Sous-chapitre (un seul) : [NOMS_SOUS_CHAPITRES]
- Niveau Bloom : [NIVEAU_BLOOM]
- Types H5P autorisés : [TYPES_H5P_AUTORISES]

Génère 5 exercices "débutant" et 5 exercices "intermédiaire" pour ce niveau Bloom. Chaque exercice avec "explications" et "indices" obligatoires.

Renvoie UNIQUEMENT un JSON valide avec la racine "subchapters" contenant un tableau d'un seul élément : { "title", "slug", "level", "course", "mindmap", "bloom_levels": { "[NIVEAU_BLOOM]": { "débutant": [ 5 exercices ], "intermédiaire": [ 5 exercices ] } } }.
```

---

## Choix par défaut et utilisation

- **Stratégie par défaut** : **Proposition 2** (un prompt par chapitre × niveau Bloom) pour un bon compromis taille / nombre d’appels.
- Le service `PromptTemplateProvider` : `getDefaultStrategy()`, `buildWithDefault($context)`, `buildForChapterAndBloom()` (Prop. 2), `buildForSubchapterAndBloom()` (Prop. 3). Permet de choisir la stratégie (`full_chapter`, `chapter_bloom`, `subchapter_bloom`) et remplit les placeholders à partir du contexte (Chapter, Classroom, liste de Subchapter, niveau Bloom, types H5P).

Voir `src/Service/Prompt/PromptTemplateProvider.php` pour l’implémentation.
