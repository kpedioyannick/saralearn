# Entités Doctrine, import et crons – Spécification détaillée

**Référence :** [analyse-technique-cdc.md](analyse-technique-cdc.md)  
**Données source :** CDC/school_data.json  

---

## 1. Entités Doctrine

### 1.1 Country (optionnel)

| Champ   | Type   | Contraintes |
|---------|--------|-------------|
| id      | int    | PK, auto |
| code    | string | unique, length 2 (ex. `fr`) |

- Utilisation : filtre à l’import et éventuellement sur les parcours. **country = fr** par défaut.

### 1.2 Classroom (classe)

| Champ   | Type   | Contraintes |
|---------|--------|-------------|
| id      | int    | PK, auto |
| name    | string | ex. CM2, 3eme |
| slug    | string | dérivé de name (lowercase, tirets) |
| cycle   | string | ex. Primaire, Collège, Lycée (clé du JSON `levels`) |

- **Unicité :** (cycle + slug).
- **Relations :** OneToMany → Subject.
- C'est le **niveau** utilisé pour les modules H5P et le prompt IA (ex. niveau CM2).

### 1.3 Subject (matière)

| Champ     | Type   | Contraintes |
|-----------|--------|-------------|
| id        | int    | PK, auto |
| name      | string | ex. FRANÇAIS |
| slug      | string | importé du JSON |
| classroom | ManyToOne → Classroom |

- **Unicité :** unique (Classroom + slug).
- **Relations :** OneToMany → Chapter.

### 1.4 Chapter (chapitre)

| Champ   | Type   | Contraintes |
|---------|--------|-------------|
| id      | int    | PK, auto |
| title   | string | ex. Lecture et comprehension de l'ecrit |
| slug    | string | importé du JSON |
| subject | ManyToOne → Subject |

- **Unicité :** unique (Subject + slug).
- **Relations :** OneToMany → Subchapter.

### 1.5 Subchapter (sous-chapitre)

| Champ         | Type    | Contraintes |
|---------------|---------|-------------|
| id            | int     | PK, auto |
| title         | string  | |
| slug          | string  | |
| href          | string  | URL source (nullable) |
| type          | string  | ex. Cours, Quiz |
| questionCount | int     | nullable |
| chapter       | ManyToOne → Chapter |

- **Unicité :** unique (Chapter + slug).
- **Relations :** OneToMany → Module.

### 1.6 Module (module H5P généré)

| Champ              | Type    | Contraintes |
|--------------------|---------|-------------|
| id                 | int     | PK, auto |
| subchapter         | ManyToOne → Subchapter |
| classroom          | ManyToOne → Classroom | niveau (classe) pour lequel le module est généré |
| taxonomyBloomLevel | string  | remember, understand, apply, analyze, evaluate |
| taxonomyBloomOrder | smallint | 1–5 |
| difficulty         | string  | débutant, intermédiaire |
| h5pType            | string  | ex. H5P.MultiChoice |
| contentPath        | string  | chemin relatif du JSON sous `h5p/server/content/modules/` |
| exerciseIndex      | smallint | index de l’exercice dans la case (0–4) |
| createdAt          | datetime | |

- **Unicité (recommandée) :** (Subchapter + Classroom + taxonomyBloomLevel + difficulty + exerciseIndex) pour éviter doublons à la re-génération.
- Permet d’agréger tous les modules d’un chapitre pour une classe donnée (parcours Interactive Book).

### 1.7 H5pInteractiveBook (parcours)

| Champ       | Type   | Contraintes |
|-------------|--------|-------------|
| id          | int    | PK, auto |
| chapter     | ManyToOne → Chapter |
| subject     | ManyToOne → Subject (redondant mais pratique) |
| classroom   | ManyToOne → Classroom |
| title       | string | ex. dérivé du chapitre + matière + classe |
| slug        | string | pour URL / nom de fichier |
| outputPath  | string | chemin relatif du JSON sous `h5p/server/content/books/` |
| createdAt   | datetime | |

- **Unicité :** unique (Chapter + Classroom). Un seul parcours par (chapitre × matière × classe).
- **Contenu :** le JSON du livre est généré à partir des H5pModule dont Subchapter appartient au Chapter, pour ce Classroom.

### 1.8 H5pInteractiveBookChapter (optionnel, pour ordre des pages)

Si on veut persister l’ordre des pages (colonnes) en base :

| Champ   | Type   | Contraintes |
|---------|--------|-------------|
| id      | int    | PK, auto |
| book    | ManyToOne → H5pInteractiveBook |
| position | int   | ordre de la page |
| h5pModule | ManyToOne → H5pModule (ou référence au contenu Column) |

- Sinon : l’ordre est entièrement dérivé à la génération du JSON (par ordre des sous-chapitres puis des modules).

---

## 2. Commande d’import : `app:import:school-data`

### 2.1 Signature proposée

```bash
php bin/console app:import:school-data [--country=fr] [--file=CDC/school_data.json] [--dry-run]
```

| Option     | Description | Défaut |
|------------|-------------|--------|
| --country  | Code pays (pour filtre / lien Country) | fr |
| --file     | Chemin vers le JSON | CDC/school_data.json |
| --dry-run  | Ne pas écrire en base, seulement afficher les opérations | false |

### 2.2 Algorithme

1. Charger le JSON ; lire `levels` (clés = cycle : Primaire, Collège, Lycée).
2. Pour chaque clé `cycle` de `levels` et chaque élément du tableau (objet avec `name`, `subjects`) :
   - Trouver ou créer **Classroom** (cycle + slug) ; slug = normaliser(name).
3. Pour chaque `subject` dans `classroom.subjects` :
   - Trouver ou créer **Subject** (classroom + slug).
4. Pour chaque `chapter` dans `subject.chapters` :
   - Trouver ou créer **Chapter** (subject + slug).
5. Pour chaque `subchapter` dans `chapter.subchapters` :
   - Trouver ou créer **Subchapter** (chapter + slug) ; remplir title, href, type, questionCount si présent.
6. Flush et statistiques (X classrooms, Y subjects, Z chapters, …).

### 2.3 Upsert

- **Trouver ou créer :** par les clés d'unicité (Classroom : cycle + slug ; Subject : Classroom + slug ; Chapter : Subject + slug ; Subchapter : Chapter + slug).
- Si l’entité existe : mettre à jour les champs (title, href, type, etc.) sans dupliquer.
- Pas de suppression des entités existantes dans cette commande (import additif/update).

### 2.4 Fichier cible

- Par défaut : `CDC/school_data.json` (depuis la racine du projet).
- Créer les répertoires `content/modules` et `content/books` sous `h5p/server` si besoin (optionnel dans cette commande ; les crons H5P peuvent les créer).

---

## 3. Crons (commandes Symfony)

### 3.1 Import (déjà décrit)

- **Commande :** `app:import:school-data`
- **Planification :** une fois par jour ou après mise à jour du fichier (ex. cron système `0 2 * * *`).

### 3.2 Génération des modules H5P : `app:h5p:generate-modules`

**Commande :**  
`php bin/console app:h5p:generate-modules [--country=fr] [--limit=] [--classroom=] [--provider=]`

- **Logique :**
  1. Récupérer les Subchapter (filtrés par country si besoin, optionnellement par classroom).
  2. Pour chaque Subchapter (éventuellement limité par `--limit`) :
     - Déduire Subject → Classroom (une matière est liée à une classe).
     - Construire le prompt CDC : matière, **niveau = Classroom.name**, liste des sous-chapitres du même chapitre (ou ce sous-chapitre seul selon le CDC).
     - Appeler le service IA (provider = `CONTENT_GENERATOR_DEFAULT` ou `--provider`).
     - Parser la réponse JSON (`subchapters` → `bloom_levels` → débutant/intermédiaire → exercices).
     - Pour chaque exercice : valider le schéma H5P, écrire le fichier JSON dans `h5p/server/content/modules/` (nom : `{subchapter_slug}_{bloom}_{difficulty}_{index}.json`), créer/mettre à jour **H5pModule** (subchapter, classroom, bloomLevel, difficulty, h5pType, contentPath, exerciseIndex).
  3. Verrou optionnel (lock file ou flag en base) pour éviter exécutions concurrentes.

**Dépendances :** Service IA (OpenAI / DeepSeek / Curl), entités Subchapter, Classroom, H5pModule.

### 3.3 Génération des parcours Interactive Book : `app:h5p:generate-interactive-books`

**Commande :**  
`php bin/console app:h5p:generate-interactive-books [--country=fr] [--chapter=] [--classroom=]`

- **Logique :**
  1. Énumérer les triplets (Chapter, Subject, Classroom) pour lesquels au moins un H5pModule existe pour ce chapitre et cette classe (via les Subchapter du chapitre).
  2. Pour chaque triplet (optionnellement filtré par `--chapter` ou `--classroom`) :
     - Récupérer les H5pModule dont le Subchapter appartient au Chapter et dont Classroom correspond, ordonnés (ex. par subchapter puis bloom puis difficulty puis index).
     - Construire le JSON **H5P.InteractiveBook** : `chapters` = liste de pages ; chaque page = contenu **H5P.Column** contenant les références ou le contenu embarqué des modules.
     - Écrire le fichier dans `h5p/server/content/books/` : nom `{chapter_slug}_{subject_slug}_{classroom_slug}.json`.
     - Créer ou mettre à jour **H5pInteractiveBook** (chapter, subject, classroom, outputPath).
  3. Verrou optionnel.

**Dépendances :** H5pModule, Chapter, Subject, Classroom, structure H5P.InteractiveBook / H5P.Column.

### 3.4 Ordre d’exécution recommandé

1. `app:import:school-data` (au moins une fois, puis périodique si le JSON évolue).
2. `app:h5p:generate-modules` (génère les modules par sous-chapitre).
3. `app:h5p:generate-interactive-books` (agrège les modules par chapitre × matière × classe).

---

## 4. Récapitulatif des chemins et variables d’environnement

| Élément | Valeur |
|--------|--------|
| Modules H5P | `h5p/server/content/modules/` |
| Interactive Books | `h5p/server/content/books/` |
| Nom module | `{subchapter_slug}_{bloom}_{difficulty}_{index}.json` |
| Nom book | `{chapter_slug}_{subject_slug}_{classroom_slug}.json` |
| Provider IA | `CONTENT_GENERATOR_DEFAULT` (curl / openai / deepseek) |
| URL service curl | `CURL_CONTENT_URL` |
| Clés API | `OPENAI_API_KEY`, `DEEPSEEK_API_KEY` (ou équivalent) |

---

*Document dérivé de l’analyse technique CDC. À utiliser pour l’implémentation des entités, de l’import et des crons.*
