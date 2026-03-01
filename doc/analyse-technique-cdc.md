# Analyse technique – Cahier des charges SaraLearn

**Référence :** CDC/Features.md  
**Données source :** CDC/school_data.json (programme scolaire France, ~26k lignes)  
**Dernière mise à jour :** 2025-02-27  

---

## 1. Synthèse du besoin

| Bloc | Description |
|------|-------------|
| **Données** | Importer le programme scolaire FR (`school_data.json`) et le persister via les entités Subject, Classroom, Chapter, Subchapter. **Country = fr par défaut.** |
| **Modules H5P** | Générer des modules H5P par sous-chapitre, alignés sur la taxonomie de Bloom (5 niveaux : remember → evaluate), avec 2 difficultés (débutant / intermédiaire), 5 exercices par combinaison, via un cron. |
| **Parcours H5P** | Un parcours = **un chapitre + une matière + une classe** ; Interactive Book composé des modules générés pour ce chapitre ; fichiers JSON dans `h5p/server`. |
| **IA** | Un service exposant 3 méthodes publiques pour générer du contenu à partir d’un prompt : OpenAI, DeepSeek, et un appel HTTP (curl) vers un service externe. |

---

## 2. Modèle de données proposé

### 2.1 Structure du fichier source

`school_data.json` est organisé ainsi :

- **Racine :** `levels` (pas de clé `country` dans le fichier ; à traiter côté import ou métier).
- **Niveaux :** `Primaire`, `Collège`, `Lycée`.
- Pour chaque niveau : liste d’objets **classe** avec `name` (ex. CM2, 3eme) et `subjects`.
- Chaque **subject** : `name`, `slug`, `chapters`.
- Chaque **chapter** : `title`, `slug`, `subchapters`.
- Chaque **subchapter** : `title`, `slug`, `href`, `type` (Cours / Quiz), optionnellement `question_count`.

### 2.2 Entités et relations

```
Country (optionnel)
  └── code: string (ex. 'fr')

Classroom (classe)
  - name: string (CM2, 3eme, etc.)
  - slug: string (dérivé ou importé)
  - cycle: string (Primaire | Collège | Lycée, clé du JSON levels)
  └── subjects: OneToMany → Subject

Subject (matière)
  - name: string
  - slug: string
  - classroom: ManyToOne → Classroom
  └── chapters: OneToMany → Chapter

Chapter (chapitre)
  - title: string
  - slug: string
  - subject: ManyToOne → Subject
  └── subchapters: OneToMany → Subchapter

Subchapter (sous-chapitre)
  - title: string
  - slug: string
  - href: string (URL source)
  - type: string (Cours | Quiz)
  - questionCount: int|null
  - chapter: ManyToOne → Chapter
  └── modules: OneToMany → Module (voir ci-dessous)
```

Pour les **modules H5P** et les **parcours** :

```
Module (module généré par sous-chapitre)
  - subchapter: ManyToOne → Subchapter
  - title: string
  - chapter: ManyToOne → Chapter
  - bloomLevel: string (niveau Bloom : remember, understand, apply, analyze, evaluate)
  - difficulty: string (débutant, intermédiaire)
  - h5pType: string (ex. H5P.MultiChoice)
  - content: text (contenu JSON H5P)
  - path: ManyToOne → Path (optionnel, si le module est inclus dans un parcours)
  - createdAt: datetime

Path (parcours ; category = H5pInteractiveBook)
  - category: string (= H5pInteractiveBook)
  - chapter: ManyToOne → Chapter
  - subchapter: ManyToOne → Subchapter (optionnel)
  - title: string
  - modules: OneToMany → Module (ordre des modules du parcours)
  - type: string (type de parcours)
  - outputPath: string (chemin du fichier .json généré sous h5p/server)
  - createdAt: datetime
```

Remarque : le CDC demande **Subject, Classroom, Chapter, Subchapter**. Pas d'entité Level : le cycle (Primaire / Collège / Lycée) est porté par un champ **cycle** sur Classroom ; **country = fr** par défaut (champ ou filtre à l’import).

---

## 3. Taxonomie de Bloom (CDC)

**5 niveaux utilisés** (sans « create ») :

| Ordre | Niveau   | Clé       | Types H5P autorisés (CDC) |
|-------|----------|-----------|----------------------------|
| 1     | Mémoriser | remember  | MultiChoice, TrueFalse, Blanks, Flashcards, DragText |
| 2     | Comprendre | understand | DragText, Summary, Dialogcards, Blanks |
| 3     | Appliquer | apply    | Blanks, DragText, Dialogcards, SortParagraphs, MultiChoice |
| 4     | Analyser  | analyze  | Blanks, MultiChoice, Essay, DragText, SingleChoiceSet |
| 5     | Évaluer   | evaluate | Essay, MarkTheWords, SortParagraphs, SingleChoiceSet, MultiChoice |

Pour **chaque niveau** : 2 sous-niveaux de difficulté — **« débutant »** et **« intermédiaire »** — avec **5 exercices** chacun (donc 10 exercices par niveau Bloom, 50 par sous-chapitre).

**Méta-données obligatoires** sur chaque exercice : `explications` (tableau de strings) et `indices` (tableau de strings).

---

## 4. Structure de la réponse IA (JSON)

L’IA doit renvoyer **uniquement** un JSON valide, racine **`subchapters`** (tableau). Langue : **français**.

Pour chaque élément du tableau :

| Champ | Description |
|-------|-------------|
| `title` | Titre du sous-chapitre |
| `slug` | Titre formaté URL (minuscules, sans accents, espaces → tirets) |
| `level` | Niveau classe (ex. CM2) |
| `course` | Résumé synthétique du cours |
| `mindmap` | Carte mentale PlantUML (`@startmindmap` … `@endmindmap`) |
| `bloom_levels` | Objet avec clés `remember`, `understand`, `apply`, `analyze`, `evaluate` |

Structure de **`bloom_levels`** :

```json
{
  "remember": { "débutant": [ 5 exercices ], "intermédiaire": [ 5 exercices ] },
  "understand": { "débutant": [ ... ], "intermédiaire": [ ... ] },
  ...
}
```

Chaque exercice : propriété **`level`** = `"débutant"` ou `"intermédiaire"` + **`type`** (ex. `H5P.MultiChoice`) + **`content`** selon le type (voir CDC pour les schémas stricts).

**Template de prompt (CDC) :**  
« Génère un JSON pour le domaine **[MATIÈRE]** au niveau **[NIVEAU]**, portant sur les sous-chapitres suivants : **[NOMS DES SOUS-CHAPITRES]**. » (+ instructions complètes du CDC en contexte.)

---

## 5. Types H5P et structures (référence CDC)

Types à supporter dans le pipeline (définition stricte dans Features.md) :

- **H5P.MultiChoice** — QCM (questions, answers, explications, indices)
- **H5P.TrueFalse** — Vrai/Faux
- **H5P.Blanks** — Texte à trous (*mot*)
- **H5P.Flashcards** — Cartes mémoires (text, answer, explications, indices)
- **H5P.DragText** — Glisser-déposer de mots
- **H5P.Summary** — Résumé interactif (intro, summaries)
- **H5P.SingleChoiceSet** — Choix unique (choices avec question, answers)
- **H5P.MarkTheWords** — Marquer les mots (textField avec *mot*)
- **H5P.Essay** — Rédaction (taskDescription, solution.sample, keywords, explications, indices)

Autres types mentionnés dans la répartition Bloom : **H5P.Dialogcards**, **H5P.SortParagraphs** (à valider selon les libs disponibles dans `h5p/server`).

---

## 6. H5P – Modules et Interactive Book

### 6.1 Modules H5P par sous-chapitre (cron)

- **Déclenchement :** cron.
- **Logique :** pour chaque Subchapter (country = fr), construire le prompt avec matière, niveau (classe), noms des sous-chapitres ; appeler le **service IA** ; parser la réponse JSON (`subchapters` → `bloom_levels` → exercices) ; valider et convertir chaque exercice au format H5P attendu par le serveur ; persister les modules (lien Subchapter + niveau Bloom + difficulté + référence contenu H5P).
- **Persistance :** entité(s) type `H5pModule` avec Subchapter, `bloomLevel` (remember / understand / apply / analyze / evaluate), `difficulty` (débutant / intermédiaire), type H5P, référence au contenu (id ou chemin fichier).
- **Fichiers :** à stocker dans ou à référencer depuis `h5p/server` (convention à définir).

### 6.2 Parcours Interactive Book (cron)

- **Périmètre (CDC) :** **Un parcours = un chapitre + une matière + une classe**, composé des **modules** générés pour ce chapitre.
- **Déclenchement :** cron (après génération des modules).
- **Format cible :** `H5P.InteractiveBook` ; `chapters` = pages ; chaque page = contenu type **H5P.Column**, contenant les références ou le JSON des modules concernés.
- **Sortie :** fichiers JSON dans `/var/php/saralearn/h5p/server` (sous-dossier et nommage à définir).

---

## 7. Service de génération de contenu (IA)

Trois méthodes publiques, une par source :

| Méthode (proposée) | Source   | Rôle |
|--------------------|----------|------|
| `generateViaOpenAI(string $prompt): string`   | API OpenAI | Génère une réponse à partir de `$prompt`. |
| `generateViaDeepSeek(string $prompt): string` | API DeepSeek | Idem. |
| `generateViaCurl(string $prompt): string`     | Service externe | POST vers `http://57.129.6.99:8001/content` avec `['prompt' => $prompt]`, timeout 300 s. |

**Implémentation suggérée :**

- Une interface `ContentGeneratorInterface` avec une méthode `generate(string $prompt): string`.
- Trois implémentations (OpenAI, DeepSeek, Curl) injectées dans un **service unique** qui expose les 3 méthodes publiques du CDC (chaque méthode délègue au bon provider).
- Configuration : clés API et URL du service curl dans `.env` (aucune clé en dur).
- Gestion des erreurs (timeout, HTTP, API) et éventuels retries à définir.

---

## 8. Crons

| Cron | Rôle | Dépendances |
|------|------|-------------|
| Import (une fois ou périodique) | Lire `school_data.json`, créer/mettre à jour Classroom, Subject, Chapter, Subchapter ; **country = fr** par défaut. | - |
| Génération modules H5P | Par sous-chapitre : prompt (matière, niveau, sous-chapitres) → IA → JSON `subchapters` → 5 niveaux Bloom × 2 difficultés × 5 exercices → conversion H5P, persistance `H5pModule`, fichiers. | Service IA, entités Subchapter / H5pModule. |
| Génération parcours Interactive Book | Par **chapitre** (× matière × classe) : agréger les modules du chapitre, produire un Interactive Book, écrire le JSON dans `h5p/server`. | H5pModule, Chapter, Subject, Classroom. |

Fréquences et verrous (éviter exécutions concurrentes) à définir en opération.

---

## 9. Décisions sur les points ouverts

| Point | Décision |
|-------|----------|
| **Unicité** | Subject : unique (Classroom + slug). Chapter : unique (Subject + slug). Subchapter : unique (Chapter + slug). Import en mode upsert sur ces clés. |
| **Level** | Pas d'entité Level ; champ **cycle** (Primaire / Collège / Lycée) sur Classroom. Niveau H5P / Bloom = **Classroom** (classe, ex. CM2). |
| **Emplacement fichiers** | Modules : `h5p/server/content/modules/`. Books : `h5p/server/content/books/`. Nommage : module `{subchapter_slug}_{bloom}_{difficulty}_{index}.json`, book `{chapter_slug}_{subject_slug}_{classroom_slug}.json`. |
| **Provider IA** | `CONTENT_GENERATOR_DEFAULT` dans `.env` (curl / openai / deepseek). URL curl : `CURL_CONTENT_URL`. |
| **H5P** | Dialogcards présent (1.9). SortParagraphs absent — à installer ou remplacer dans la répartition Bloom. |

---

## 10. Recommandations techniques

- **Import :** Commande Symfony `app:import:school-data` lisant `CDC/school_data.json`, avec option `--country=fr` et mode dry-run.
- **Crons :** Commandes Symfony (`app:h5p:generate-modules`, `app:h5p:generate-interactive-books`) appelables par le planificateur (cron système ou scheduler Symfony).
- **H5P :** S’appuyer sur la structure sémantique de `H5P.InteractiveBook` (chapters = pages, chaque page = H5P.Column) pour générer le JSON ; valider un échantillon dans le serveur H5P existant.
- **Config :** Variables d’environnement pour `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `DEEPSEEK_CONTENT_URL` (ou équivalent), et `CURL_CONTENT_URL` (ex. `http://57.129.6.99:8001/content`), timeout éventuellement configurable.
- **Tests :** Tests unitaires sur le service IA (mocks HTTP), et tests d’intégration sur l’import (fichier de test réduit).

---

## 11. Prochaines étapes proposées

1. Créer les entités Classroom, Subject, Chapter, Subchapter (champ cycle sur Classroom ; country = fr par défaut).
2. Implémenter l’import `school_data.json` (commande `app:import:school-data`).
3. Mettre en place le service IA (3 méthodes : OpenAI, DeepSeek, Curl) et le template de prompt CDC.
4. Définir les entités H5pModule (subchapter, bloomLevel, difficulty, type H5P, contenu) et H5pInteractiveBook (chapter, subject, classroom, modules).
5. Cron génération modules : prompt → IA → parse JSON `subchapters` → conversion H5P → persistance + fichiers.
6. Cron génération parcours : 1 Interactive Book par (Chapter × Subject × Classroom), sortie dans `h5p/server`.

**Spécification détaillée :** voir [entites-import-crons.md](entites-import-crons.md) (entités Doctrine, commande d'import, crons).

---

*Document aligné avec CDC/Features.md (version étendue).*
