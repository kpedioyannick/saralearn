# Analyse technique – Création des livres interactifs H5P

**Contexte :** Le serveur H5P affiche les livres interactifs à partir des dossiers sous `h5p/server/content/`. Chaque livre = un dossier nommé par l’**ID du livre**, contenant **content.json** et **h5p.json**. Les modules déjà générés (table `module`) doivent être regroupés par niveau de Bloom pour **composer** ces livres.

---

## 1. Objectif

- **Composer des livres interactifs** à partir des **modules** générés (commande `app:h5p:generate-modules`).
- Un livre = un **parcours** par **niveau Bloom** (remember, understand, apply, analyze, evaluate).
- Pour chaque livre : créer le dossier `h5p/server/content/{id}/` et les deux fichiers **content.json** et **h5p.json**, puis remplir **content.json** en allant **récupérer les modules** concernés en base.

---

## 2. Rôle du serveur et structure des dossiers

- **Répertoire de base :** `h5p/server/content/`
- **Nom du dossier = ID du livre** (ex. `interactive-book-1` ou l’ID numérique du `Path`).
- **Fichiers requis dans ce dossier :**
  - **content.json** : structure du livre (couverture, chapitres = colonnes, contenus H5P, comportement). **Spécifique à chaque livre** (données issues des modules).
  - **h5p.json** : métadonnées du paquet H5P (titre, langue, `mainLibrary`, dépendances). **Identique pour tous les livres interactifs** (template commun).

La structure **content.json** doit être **alignée** avec celle définie dans **H5pType::InteractiveBook** (getExpectedInputs) et cohérente avec l’exemple réel `h5p/server/content/interactive-book-1/content.json`.

---

## 3. Modèle de données (rappel)

### 3.1 Module (table `module`)

| Champ        | Rôle |
|-------------|------|
| id          | Identifiant unique |
| subchapter  | Sous-chapitre concerné |
| chapter     | Chapitre (dénormalisé) |
| bloomLevel  | remember, understand, apply, analyze, evaluate |
| difficulty  | débutant, intermédiaire |
| h5pType     | Ex. H5P.MultiChoice, H5P.DragText, H5P.Essay |
| content     | **JSON** : paramètres du contenu H5P (params + library + metadata + subContentId) |
| path        | Optionnel : lien vers le Path (livre) auquel le module est rattaché |

### 3.2 Path (table `learning_path`)

| Champ      | Rôle |
|-----------|------|
| id        | **ID du livre** → nom du dossier `h5p/server/content/{id}/` |
| category  | Ex. `H5pInteractiveBook` |
| chapter   | Chapitre du parcours |
| subchapter| Optionnel : sous-chapitre cible |
| title     | Titre du livre |
| types     | **Niveau(x) Bloom** (tableau JSON) : ex. `["remember"]` ou `["remember", "understand", "apply"]`. Les modules rattachés ont leur `bloomLevel` parmi ces types. |
| outputPath| Chemin de sortie (ex. `h5p/server/content/{id}`) |
| modules   | Collection des Module rattachés à ce livre |

Les modules sont générés **par sous-chapitre × niveau Bloom** (ou chapitre × Bloom). Pour composer un livre, on **récupère les modules** (par chapitre/sous-chapitre et par niveau Bloom) et on les attache à un **Path** dont l’**id** sert de nom au dossier du livre.

---

## 4. Structure des fichiers à générer

### 4.1 content.json (spécifique à chaque livre)

Structure cible (alignée H5pType et exemple réel) :

```json
{
  "showCoverPage": false,
  "bookCover": {
    "coverDescription": "<p>…</p>",
    "coverMedium": { "params": {} }
  },
  "chapters": [
    {
      "params": {
        "content": [
          {
            "content": {
              "params": { /* params du module (Module.content décodé) */ },
              "library": "H5P.MultiChoice 1.16",
              "metadata": { "contentType": "…", "license": "U", "title": "…", … },
              "subContentId": "uuid"
            },
            "useSeparator": "auto"
          }
        ]
      },
      "library": "H5P.Column 1.18",
      "subContentId": "uuid",
      "metadata": { "contentType": "Page", "license": "U", "title": "…", … }
    }
  ],
  "behaviour": {
    "baseColor": "#1768c4",
    "defaultTableOfContents": true,
    "progressIndicators": true,
    "progressAuto": true,
    "displaySummary": true,
    "enableRetry": true
  },
  "read": "Read",
  "displayTOC": "…",
  …
}
```

- **chapters** : un chapitre = **une colonne** (H5P.Column). Chaque élément de **params.content** = un contenu H5P (un **module** : son `content` en base contient déjà ou doit être transformé en `{ params, library, metadata, subContentId }`).
- **Vérification :** comparer avec `h5p/server/content/interactive-book-1/content.json` et avec **H5pType::InteractiveBook** (getExpectedInputs) pour garder la même forme (library avec version, metadata, subContentId, useSeparator, etc.).

### 4.2 h5p.json (identique pour tous les livres interactifs)

- **mainLibrary** : `H5P.InteractiveBook`
- **title** : peut être dérivé du Path (ex. titre du livre ou `interactive-book-{id}`).
- **preloadedDependencies** : liste des librairies H5P nécessaires (Essay, DragText, TrueFalse, Column, MultiChoice, etc.) – **template fixe** basé sur `h5p/server/content/interactive-book-1/h5p.json`.

Un **template unique** h5p.json pour tous les livres interactifs suffit ; seuls le **title** (et éventuellement la langue) peuvent varier.

---

## 5. Stratégie de composition (implémentée)

- **Livre = Path lié à un sous-chapitre**, avec **types** = combinaison de niveaux Bloom.
- **3 types de livres** par sous-chapitre (presets) :
  1. **remember + understand** → Path avec `types = ["remember", "understand"]`
  2. **understand + apply**   → Path avec `types = ["understand", "apply"]`
  3. **apply + analyze**      → Path avec `types = ["apply", "analyze"]`

Pour chaque sous-chapitre, la commande `app:h5p:generate-interactive-books` crée ou récupère 3 Paths (un par preset), récupère les **modules** existants en base (subchapter + bloomLevel dans path.types), puis génère le dossier `h5p/server/content/{pathId}/` avec **content.json** et **h5p.json**. Chaque module = une « page » (une colonne) du livre.

---

## 6. Processus à mettre en œuvre (à chaque lancement)

Lorsqu’on lance la génération des livres interactifs (commande ou cron) :

1. **Déterminer les “livres” à créer**  
   Ex. : pour chaque (Chapter, bloomLevel) ou (Subchapter, bloomLevel), selon la stratégie retenue.

2. **Pour chaque livre :**
   - **Créer ou récupérer un Path** (category = H5pInteractiveBook, chapter/subchapter, title, type = bloomLevel).
   - **ID du livre = Path::id** (ou slug dérivé) → nom du dossier : `h5p/server/content/{id}/`.

3. **Créer le dossier**  
   `h5p/server/content/{id}/` (si nécessaire).

4. **Récupérer les modules**  
   Requête : modules du chapitre (ou sous-chapitre) concerné, avec `bloomLevel = X`, ordonnés (ex. par subchapter, puis par id). Optionnel : lier les modules au Path (setPath + flush).

5. **Construire content.json :**
   - **bookCover** : titre / description dérivés du Path ou du chapitre.
   - **chapters** : pour chaque “colonne” (ex. un sous-chapitre ou un groupe de modules), créer un objet chapitre :
     - `library` : `H5P.Column 1.18`
     - `params.content` : tableau d’objets `{ content: { params, library, metadata, subContentId }, useSeparator: "auto" }`.
     - Chaque élément = un Module : décoder `Module::content` (JSON), l’envelopper dans la structure attendue (params, library avec version, metadata, subContentId UUID).
   - **behaviour** : valeurs par défaut (comme dans l’exemple ou H5pType).
   - Chaînes de traduction (read, displayTOC, etc.) : reprise de l’exemple ou template.

6. **Écrire content.json**  
   Fichier `h5p/server/content/{id}/content.json` (JSON valide, encodage UTF-8).

7. **Écrire h5p.json**  
   Fichier `h5p/server/content/{id}/h5p.json` à partir du **template commun** (identique pour tous), en personnalisant éventuellement le titre avec le Path/chapitre/Bloom.

8. **Mettre à jour Path**  
   Ex. `outputPath` = `h5p/server/content/{id}` et persister.

---

## 7. Commande et cron (implémenté)

- **Commande :** `php bin/console app:h5p:generate-interactive-books`
  - **--subchapter=ID|slug** : traiter un seul sous-chapitre
  - **--limit=N** : limiter le nombre de sous-chapitres
  - **--dry-run** : ne pas créer les Paths ni écrire les fichiers

Pour chaque sous-chapitre (ou ceux filtrés), la commande crée ou réutilise 3 Paths (presets remember+understand, understand+apply, apply+analyze), récupère les modules en base pour ce sous-chapitre et ces niveaux Bloom, puis écrit `h5p/server/content/{pathId}/content.json` et `h5p.json`. Les modules sont déjà en base (générés par `app:h5p:generate-modules`).

**Cron :** planifier cette commande après la génération des modules (ex. quotidien ou après import) pour régénérer les livres interactifs.

## 8. Tâches de développement à prévoir

| # | Tâche | Détail |
|---|--------|--------|
| 1 | **Template h5p.json** | Fichier ou constante (PHP/JSON) avec la structure complète (mainLibrary, preloadedDependencies, etc.) basée sur `interactive-book-1/h5p.json`. |
| 2 | **Mapping Module → contenu chapitre** | Décoder `Module::content` et le formater en `{ params, library (avec version), metadata, subContentId }` comme dans l’exemple content.json. Gérer les versions des librairies (1.16, 1.18, etc.) si besoin. |
| 3 | **Stratégie chapitre vs sous-chapitre** | Décider : un livre = (Chapter + bloomLevel) ou (Subchapter + bloomLevel). Adapter les requêtes Module et la construction des colonnes. |
| 4 | **Commande ou service** | Ex. `app:h5p:generate-interactive-books` (options : --classroom, --chapter, --bloom-level, --dry-run) qui pour chaque livre : crée le Path si besoin, crée le dossier, récupère les modules, construit content.json, écrit content.json et h5p.json, met à jour Path. |
| 5 | **Alignement H5pType** | Vérifier que la structure générée pour content.json respecte bien **H5pType::InteractiveBook** (getExpectedInputs) et l’exemple réel pour éviter les erreurs d’affichage côté serveur H5P. |
| 6 | **Tests** | Créer un livre de test (un sous-chapitre avec modules, lancer la commande) et vérifier l’affichage dans le serveur H5P. |

---

## 9. Résumé

- **Dossier livre** = `h5p/server/content/{id}/` avec **id** = ID du Path (livre).
- **Deux fichiers** : **content.json** (données du livre, construites à partir des **modules** récupérés) et **h5p.json** (template **identique** pour tous, avec titre éventuellement personnalisé).
- **Composition** : récupérer les modules (par chapitre/sous-chapitre et par **niveau Bloom**), puis construire **chapters** (colonnes) où chaque contenu = un module dont le champ `content` est converti au format attendu par le livre interactif.
- **À chaque lancement** : pour chaque “livre” (par ex. par niveau Bloom), créer le dossier, les deux fichiers et mettre à jour le Path.

Cette analyse servira de base pour implémenter la commande (ou le service) de génération des livres interactifs et le mapping Module → content.json.
