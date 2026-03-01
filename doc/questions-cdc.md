# Questions ouvertes – CDC SaraLearn

Liste des points à trancher pour finaliser l’implémentation. Voir le détail dans [analyse-technique-cdc.md](analyse-technique-cdc.md).

---

### Données & modèle

- **Country :** CDC confirme **country = fr par défaut** (champ ou filtre à l’import).
- **Unicité :** Subject (Classroom + slug), Chapter (Subject + slug), Subchapter (Chapter + slug) — upsert à l'import.
- **Level :** Pas d'entité Level ; champ **cycle** (Primaire / Collège / Lycée) sur Classroom. Niveau H5P/Bloom = **Classroom** (classe).

### Modules H5P & Bloom (répondu par le CDC)

- **Structure :** 5 niveaux Bloom (remember, understand, apply, analyze, evaluate) ; 2 difficultés (débutant, intermédiaire) ; 5 exercices par case. Réponse IA = JSON racine `subchapters` avec `course`, `mindmap` PlantUML, `bloom_levels`.
- **Types H5P :** MultiChoice, TrueFalse, Blanks, Flashcards, DragText, Summary, SingleChoiceSet, MarkTheWords, Essay (+ Dialogcards, SortParagraphs dans la répartition par niveau).
- **Prompt :** Template CDC avec [MATIÈRE], [NIVEAU], [NOMS DES SOUS-CHAPITRES].

### Parcours Interactive Book (répondu par le CDC)

- **Périmètre :** Un parcours = **un chapitre + une matière + une classe**, composé des modules générés pour ce chapitre.

### Décisions / réponses partielles

- **Unicité :** Subject unique par (Classroom + slug) ; Chapter unique par (Subject + slug) ; Subchapter unique par (Chapter + slug). Upsert à l’import (création ou mise à jour selon ces clés).
- **Level :** Pas d'entité Level ; champ **cycle** sur Classroom (Primaire / Collège / Lycée). Niveau H5P / Bloom = **classe** (Classroom).
- **Emplacement des fichiers :**  
  - Modules : `h5p/server/content/modules/` (sous-dossiers optionnels par subchapter ou flat avec slug).  
  - Interactive Books : `h5p/server/content/books/`.  
  - Nommage proposé : module `{subchapter_slug}_{bloom}_{difficulty}_{index}.json`, book `{chapter_slug}_{subject_slug}_{classroom_slug}.json`.
- **Provider IA par défaut :** Variable d’environnement `CONTENT_GENERATOR_DEFAULT=curl` (ou `openai` / `deepseek`) pour le cron ; URL du service curl dans `.env` (ex. `CURL_CONTENT_URL`).
- **H5P.Dialogcards / H5P.SortParagraphs :** **Dialogcards** présent (`H5P.Dialogcards-1.9`). **SortParagraphs** absent dans `h5p/server/libraries` — à ajouter (installation H5P) ou à remplacer dans la répartition Bloom par un type déjà présent (ex. DragQuestion, Summary).
