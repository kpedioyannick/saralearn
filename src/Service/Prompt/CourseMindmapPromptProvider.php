<?php

declare(strict_types=1);

namespace App\Service\Prompt;

/**
 * Prompt pour la génération de cours Reveal.js + mindmap (CDC).
 * Utilise le template documenté dans CDC/Features.md.
 */
final class CourseMindmapPromptProvider
{
    /**
     * Construit le prompt pour générer un cours Reveal.js (sans mindmap).
     * Réponse attendue : { "course": { "title", "description", "slides": [...] } }
     */
    public function buildForCourseRevealAndMindmap(string $chapitre, string $niveauClasse): string
    {
        $replace = [
            '[CHAPITRE À INDIQUER]' => $chapitre,
            '[CLASSE À INDIQUER, ex: CP, CE1, 6ème, Seconde...]' => $niveauClasse,
        ];
        return str_replace(array_keys($replace), array_values($replace), $this->getRevealJsTemplate());
        // Mindmap désactivé : ne plus demander à l'IA de générer la clé "mindmap"
        // . "\n\n" . $this->getMindmapInstruction();
    }

    private function getRevealJsTemplate(): string
    {
        return <<<'TEXT'
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
6. **Structure pédagogique etsurtout doit etre progressif et doit etre court et concis ** :
   -Introduction / titre
   - Définitions et vocabulaire
   - Méthodes
   - Exemples
   - Exercice rapide
   -  Correction et conclusion
7. **Texte audio** : Rédige un commentaire clair, adapté au niveau indiqué, qui explique ce qui est affiché sans le lire mot à mot
8. **Accessibilité** : Utilise des couleurs contrastées et des balises simples

Le cours doit être :
- Progressif (du simple au complexe)
- Visuel (couleurs, emojis, mise en évidence)
- Interactif (animations fragment)
- Adapté à la classe , au chapitre
- Les slides seront visibles sur un petit écran : donc 
les slides ne doivent pas etre trop longs pas de gros titre, pas de grose taille et de police

Renvoie UN SEUL objet JSON avec la clé "course" (objet avec title, description, slides). Génère maintenant le JSON complet.
TEXT;
    }

    /** Instruction mindmap désactivée (génération et sauvegarde non utilisées). */
    // private function getMindmapInstruction(): string
    // {
    //     return <<<'TEXT'
    // En plus du cours Reveal.js ci-dessus, ajoute une clé "mindmap" à la racine du JSON avec :
    // { "content": "code PlantUML (@startmindmap ... @endmindmap)", "text_to_audio": "texte pour synthèse vocale décrivant la mind map" }
    //
    // ATTENTION: Le code PlantUML dans "content" doit être écrit sur une seule ligne. Utilise le littéral \n (un antislash suivi d'un n) pour marquer les retours à la ligne, ne mets JAMAIS de vrais retours à la ligne dans la chaîne JSON.
    //
    // Renvoie UN SEUL objet JSON avec les clés "course" (objet avec title, description, slides) et "mindmap" (objet avec content, text_to_audio).
    // TEXT;
    // }
}
