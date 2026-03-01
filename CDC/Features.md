Cron pour les chapitres et sous-chapitres
========================================

Options (obligatoires ensemble pour le cron)
---------------------------------------------
- **classroom** : ID ou slug de la classe (obligatoire)
- **subject**   : ID ou slug de la matière (obligatoire)
- **filter**    : `chapter` ou `subchapter` — détermine ce qui est chargé puis traité

Comportement
------------
- **GenerateH5pModulesCommand**  
  - `--filter=chapter`   : charge les chapitres de la matière, traite chaque chapitre (× niveaux Bloom).  
  - `--filter=subchapter` : charge tous les sous-chapitres de la matière, traite chaque sous-chapitre × Bloom.

- **GenerateInteractiveBooksCommand**  
  - `--filter=chapter`   : charge les chapitres puis les sous-chapitres de chaque chapitre ; génère les livres (3 Paths par sous-chapitre).  
  - `--filter=subchapter` : charge la liste plate des sous-chapitres de la matière ; génère les livres pour chaque sous-chapitre.

Exemples
--------
  php bin/console app:h5p:generate-modules --classroom=cm2 --subject=maths --filter=subchapter
  php bin/console app:h5p:generate-interactive-books --classroom=cm2 --subject=maths --filter=subchapter

Tester avec DeepSeek (option --provider=deepseek)
-------------------------------------------------
  php bin/console app:h5p:generate-modules --classroom=cm2 --subject=maths --filter=subchapter --provider=deepseek --limit=1
  php bin/console app:h5p:generate-modules --classroom=cm2 --subject=maths --filter=chapter --provider=deepseek --limit=1 --dry-run

Entités Chapter et Subchapter : course et mindmap
-------------------------------------------------
- **course** : JSON (format Reveal.js) `{ "title": "...", "description": "...", "slides": [{ "id", "slide", "texte_audio" }] }` — généré par **app:generate-course-mindmap**
- **mindmap** : JSON objet `{ "content": "code PlantUML", "text_to_audio": "texte pour synthèse vocale" }`

La commande **app:generate-course-mindmap** génère et persiste ces champs via le prompt Reveal.js documenté ci-dessous.





Génération cours + mindmap (commande dédiée)
--------------------------------------------
La commande **app:generate-course-mindmap** génère les cours Reveal.js et mindmaps pour les chapitres/sous-chapitres. Elle utilise le prompt documenté dans CDC/Features.md (Reveal.js + PlantUML).

**GenerateH5pModulesCommand** ne génère plus que les exercices H5P (modules). Les cours et mindmaps sont gérés par **app:generate-course-mindmap**.

Options (identiques aux autres commandes) : --classroom, --subject, --filter (chapter|subchapter), --chapter, --subchapter, --limit, --provider, --dry-run.

Exemples :
  php bin/console app:generate-course-mindmap --classroom=cm2 --subject=maths --filter=chapter --provider=deepseek --limit=2
  php bin/console app:generate-course-mindmap --classroom=cm2 --subject=maths --filter=subchapter --limit=1 --dry-run



Tu es un professeur expert en pédagogie et en création de contenu éducatif interactif.

Génère un cours complet au format JSON pour Reveal.js sur le thème suivant :
- **Chapitre** : [CHAPITRE À INDIQUER]
- **Niveau** : [CLASSE À INDIQUER, ex: CP, CE1, 6ème, Seconde...]

Le JSON doit suivre EXACTEMENT cette structure :
{
  "title": "Titre du cours",
  "description": "Brève description",
  "slides": [
    {
      "id": 1,
      "slide": "<section data-background-color='[COULEUR]'>[CONTENU HTML avec animations]</section>",
      "texte_audio": "[Texte narratif à dire]"
    }
  ]
}

RÈGLES STRICTES À RESPECTER :

2. **Animations** : Utilise class="fragment" 
3. **data-line-numbers** : Pour chaque bloc <pre><code>, ajoute data-line-numbers avec des étapes (ex: '1|2|3|4-5')
4. **Couleurs de fond** : Alterne les data-background-color (aquamarine, #ff9999, #99ccff, rgb(70,70,255), #ffcc99, etc.)
6. **Structure pédagogique** :
   - Slide 1 : Introduction / titre
   - Slides 2-4 : Définitions et vocabulaire
   - Slides 5-8 : Méthodes et techniques
   - Slides 9-11 : Propriétés ou règles importantes
   - Slides 12-13 : Astuces / exemples
   - Slide 14 : Exercices
   - Slide 15 : Corrections
   - Slide 16 : Résumé / conclusion
7. **Texte audio** : Rédige un commentaire clair, adapté au niveau indiqué, qui explique ce qui est affiché sans le lire mot à mot
8. **Accessibilité** : Utilise des couleurs contrastées et des balises simples

Le cours doit être :
- Progressif (du simple au complexe)
- Visuel (couleurs, emojis, mise en évidence)
- Interactif (animations fragment)
- Adapté à la classe , au chapitre

Génère maintenant le JSON complet.

GenerateH5pModulesCommand : option --bloom-types
-------------------------------------------------
- **--bloom-types** : niveaux Bloom à traiter, séparés par des virgules. Par défaut : tous (remember, understand, apply, analyze, evaluate).
- Exemple : `--bloom-types=remember,understand` pour ne générer que ces deux niveaux.

Liste des commandes (modules et cours)
--------------------------------------

| Commande | Rôle | Options principales |
|----------|------|---------------------|
| **app:h5p:generate-modules** | Génère les **modules H5P** (exercices par niveau Bloom) | --classroom, --subject, --filter (chapter\|subchapter), --bloom-types (ex: remember,understand), --limit, --provider, --strategy, --dry-run |
| **app:generate-course-mindmap** | Génère les **cours Reveal.js** et **mindmaps** pour chapitres/sous-chapitres | --classroom, --subject, --filter (chapter\|subchapter), --chapter, --subchapter, --limit, --provider, --dry-run |
| **app:h5p:generate-interactive-books** | Génère les **livres interactifs H5P** (3 Paths par sous-chapitre) à partir des modules en base | --classroom, --subject, --filter (chapter\|subchapter), --subchapter, --limit, --dry-run |
| **app:import:school-data** | Import des données scolaires (classes, matières, chapitres, sous-chapitres) | — |

Ordre typique : 1) **app:import:school-data** → 2) **app:generate-course-mindmap** → 3) **app:h5p:generate-modules** → 4) **app:h5p:generate-interactive-books**.

Route Reveal.js (afficher le cours)
-----------------------------------
- **URL** : `GET /reveal/{type}/{id}` avec `type` = `chapter` ou `subchapter`, `id` = ID de l'entité (nombre).
- **Nom de route** : `app_reveal_show`.
- **Contrôleur** : `App\Controller\RevealController::show`.
- Affiche le cours (champ `course` au format Reveal.js) avec [Reveal.js](https://revealjs.com/) (CDN 5.0.0). Si aucun cours n'est présent, une page « Aucun cours généré » s'affiche avec un message invitant à lancer `app:generate-course-mindmap`.


Une commande Manager qui va gérer la création des modules , des cours , des books 
Les régles : 
Lancer une commande sans atteindre la réponse 
Regle des cours : Par classe , par subject et par chaoitre et pour tous les sous chapitres dont les cours ne sont pas créer 
Règle des modules : Par classe , par subject et par chaoitre et pour tous les sous chapitres et pour les taxonomy deux par deux =>  s'assurer que le bloom n'a pas dejaà etter créer 
Régle des interactiveBook :  Par classe , par subject et par chaoitre et pour tous les sous chapitres : pour un sous chapitre : 
1 interactivebook avec les modules de types  remenber et undertand
1 interactivebook avec les modules de types undertand et apply 
1 interactivebook avec les modules de types apply et anlyse
1 interactivebook avec les modules de types analyse et evaluate
Attention le manager peut etre coupé et lancer à tout moment mais doit recrer les elements deja crer 



1. Git Pusher sur le serveur 
2. Lancer les commandes 
3. Vérifier les crédits 