<?php

declare(strict_types=1);

namespace App\Service\Prompt;

use App\Type\H5pType;

/**
 * Construit le prompt pour la génération de contenu IA (CDC).
 * Stratégies implémentées : Proposition 2 (chapitre × Bloom), Proposition 3 (sous-chapitre × Bloom).
 * Par défaut : Proposition 2 (chapter_bloom).
 */
final class PromptTemplateProvider
{
    public const STRATEGY_FULL_CHAPTER = 'full_chapter';
    /** Proposition 2 : un prompt par chapitre × un niveau Bloom (recommandé, défaut). */
    public const STRATEGY_CHAPTER_BLOOM = 'chapter_bloom';
    /** Proposition 3 : un prompt par sous-chapitre × un niveau Bloom. */
    public const STRATEGY_SUBCHAPTER_BLOOM = 'subchapter_bloom';

    /** Stratégie par défaut = Proposition 2 (chapitre × Bloom). */
    public const DEFAULT_STRATEGY = self::STRATEGY_CHAPTER_BLOOM;

    /**
     * Construit le prompt à envoyer à l'IA.
     *
     * @param string       $strategy  STRATEGY_FULL_CHAPTER | STRATEGY_CHAPTER_BLOOM | STRATEGY_SUBCHAPTER_BLOOM
     * @param array{matiere: string, niveau: string, noms_sous_chapitres: string, niveau_bloom?: string} $context
     */
    public function build(string $strategy, array $context): string
    {
        $matiere = $context['matiere'] ?? '';
        $niveau = $context['niveau'] ?? '';
        $nomsSousChapitres = $context['noms_sous_chapitres'] ?? '';
        $niveauBloom = $context['niveau_bloom'] ?? '';
        $idSousChapitre = $context['id_sous_chapitre'] ?? '';

        $replace = [
            '[MATIÈRE]' => $matiere,
            '[NIVEAU]' => $niveau,
            '[NOMS_SOUS_CHAPITRES]' => $nomsSousChapitres,
            '[NIVEAU_BLOOM]' => $niveauBloom,
            '[ID_SOUS_CHAPITRE]' => $idSousChapitre,
            '[TYPES_H5P_AUTORISES]' => $niveauBloom !== ''
                ? BloomH5pTypeMap::getH5pTypesAsString($niveauBloom)
                : '',
        ];

        $template = $this->getTemplate($strategy);
        return str_replace(array_keys($replace), array_values($replace), $template);
    }

    /**
     * Pour la stratégie chapitre × Bloom : construire le contexte pour un chapitre et un niveau Bloom.
     */
    public function buildForChapterAndBloom(
        string $matiere,
        string $niveauClasse,
        string $nomsSousChapitres,
        string $bloomLevel,
    ): string {
        return $this->build(self::STRATEGY_CHAPTER_BLOOM, [
            'matiere' => $matiere,
            'niveau' => $niveauClasse,
            'noms_sous_chapitres' => $nomsSousChapitres,
            'niveau_bloom' => $bloomLevel,
        ]);
    }

    /**
     * Pour la stratégie sous-chapitre × Bloom : un seul sous-chapitre, un niveau Bloom.
     */
    public function buildForSubchapterAndBloom(
        string $matiere,
        string $niveauClasse,
        string $titreSousChapitre,
        string $bloomLevel,
        ?int $idSousChapitre = null,
    ): string {
        return $this->build(self::STRATEGY_SUBCHAPTER_BLOOM, [
            'matiere' => $matiere,
            'niveau' => $niveauClasse,
            'noms_sous_chapitres' => $titreSousChapitre,
            'niveau_bloom' => $bloomLevel,
            'id_sous_chapitre' => $idSousChapitre !== null ? (string) $idSousChapitre : '',
        ]);
    }

    /**
     * Stratégie par défaut (Proposition 2). Utilisée quand le cron/commande ne précise pas la stratégie.
     */
    public function getDefaultStrategy(): string
    {
        return self::DEFAULT_STRATEGY;
    }

    /**
     * Construit le prompt avec la stratégie par défaut (Proposition 2).
     * Contexte requis : matiere, niveau, noms_sous_chapitres, niveau_bloom.
     */
    public function buildWithDefault(array $context): string
    {
        return $this->build(self::DEFAULT_STRATEGY, $context);
    }

    /**
     * Pour la stratégie tout le chapitre (tous les niveaux Bloom en un seul appel).
     */
    public function buildForFullChapter(
        string $matiere,
        string $niveauClasse,
        string $nomsSousChapitres,
    ): string {
        return $this->build(self::STRATEGY_FULL_CHAPTER, [
            'matiere' => $matiere,
            'niveau' => $niveauClasse,
            'noms_sous_chapitres' => $nomsSousChapitres,
        ]);
    }

    private function getTemplate(string $strategy): string
    {
        return match ($strategy) {
            self::STRATEGY_FULL_CHAPTER => $this->getFullChapterTemplate(),
            self::STRATEGY_CHAPTER_BLOOM => $this->getChapterBloomTemplate(),
            self::STRATEGY_SUBCHAPTER_BLOOM => $this->getSubchapterBloomTemplate(),
            default => throw new \InvalidArgumentException(sprintf('Stratégie inconnue : %s', $strategy)),
        };
    }

    private function getH5pFormatSpecification(): string
    {
        $lines = [
            '',
            'TYPES H5P AUTORISÉS ET LEUR STRUCTURE STRICTE (à respecter à la lettre) :',
            '',
        ];
        foreach (H5pType::cases() as $i => $type) {
            $inputs = $type->getExpectedInputs();
            $lines[] = sprintf(
                '%d. %s (%s) :',
                $i + 1,
                $type->value,
                $type->getLabel(),
            );
            $lines[] = '   level : ' . $type->getLevelsAsString();
            $lines[] = '   goal : ' . $inputs['goal'];
            $lines[] = '   systemMessage : ' . $inputs['systemMessage'];
            if (isset($inputs['instructions'])) {
                $lines[] = '   instructions : ' . $inputs['instructions'];
            }
            $lines[] = '   outputFormat : ' . json_encode($inputs['outputFormat'], \JSON_UNESCAPED_UNICODE | \JSON_PRETTY_PRINT);
            $lines[] = '';
        }
        $lines[] = 'Chaque exercice généré DOIT être un objet JSON conforme à l\'un de ces types. Les champs "explications" et "indices" sont des tableaux de chaînes obligatoires pour tous les types.';
        $lines[] = '';
        $lines[] = 'STRUCTURE OBLIGATOIRE de chaque exercice : { "type": "H5P.MultiChoice", "level": "débutant", "content": { ... } }. La clé "content" (et non "params") doit contenir les données spécifiques au type H5P (questions, answers, etc.).';

        return implode("\n", $lines);
    }

    private function getFullChapterTemplate(): string
    {
        return $this->getFullChapterTemplateIntro() . $this->getH5pFormatSpecification() . "\n\nGénère maintenant un JSON complet pour le domaine [MATIÈRE] au niveau [NIVEAU], portant sur les sous-chapitres suivants : [NOMS_SOUS_CHAPITRES]. Assure-toi que chaque module contienne bien 5 questions \"débutant\" et 5 \"intermédiaire\" par niveau Bloom.";
    }

    private function getFullChapterTemplateIntro(): string
    {
        return <<<'TEXT'
Tu es un expert en ingénierie pédagogique, spécialiste de la taxonomie de Bloom et de la création de contenus interactifs au format H5P. Ton objectif est de générer un fichier JSON contenant des modules d'apprentissage structurés pour un niveau scolaire précis.

LANGUE : L'intégralité du contenu généré (cours, questions, réponses, indices, explications) DOIT être rédigée en français.

STRUCTURE : Renvoie UNIQUEMENT un objet JSON valide avec la racine "subchapters" (tableau). Chaque sous-chapitre doit contenir : title, slug, level, et "bloom_levels" avec les 5 niveaux (remember, understand, apply, analyze, evaluate). Pour CHAQUE niveau Bloom : 2 sous-niveaux "débutant" et "intermédiaire", chacun avec 5 exercices. Types H5P par niveau : remember → MultiChoice, TrueFalse, Blanks, Flashcards, DragText ; understand → DragText, Summary, Dialogcards, Blanks ; apply → Blanks, DragText, Dialogcards, SortParagraphs, MultiChoice ; analyze → Blanks, MultiChoice, Essay, DragText, SingleChoiceSet ; evaluate → Essay, MarkTheWords, SortParagraphs, SingleChoiceSet, MultiChoice.

TEXT;
    }

    private function getChapterBloomTemplate(): string
    {
        return <<<'TEXT'
Tu es un expert en ingénierie pédagogique et en taxonomie de Bloom. Tu génères du contenu au format JSON pour un niveau scolaire précis.

LANGUE : Tout le contenu (cours, questions, réponses, indices, explications) DOIT être en français.

PÉRIMÈTRE DE CET APPEL :
- Domaine : [MATIÈRE]
- Niveau classe : [NIVEAU]
- Sous-chapitres concernés (format "id : titre", renvoyer l'id tel quel dans le JSON) : [NOMS_SOUS_CHAPITRES]
- Niveau de Bloom à générer UNIQUEMENT : [NIVEAU_BLOOM]
- Types H5P autorisés pour ce niveau : [TYPES_H5P_AUTORISES]

TEXT
            . $this->getH5pFormatSpecification()
            . <<<'TEXT'

Pour ce niveau Bloom uniquement, génère 2 sous-niveaux de difficulté : "débutant" (5 exercices) et "intermédiaire" (5 exercices). Chaque exercice DOIT avoir la structure { "type": "...", "level": "...", "content": { ... } } — les données H5P dans la clé "content" uniquement (pas "params").

Renvoie UNIQUEMENT un objet JSON valide avec la racine "subchapters". Chaque élément doit contenir id (l'entier fourni pour ce sous-chapitre), title (chaîne, maximum 1000 caractères), slug, level, et "bloom_levels" avec UNIQUEMENT la clé [NIVEAU_BLOOM] : "débutant": [ 5 exercices ], "intermédiaire": [ 5 exercices ].
TEXT;
    }

    private function getSubchapterBloomTemplate(): string
    {
        return <<<'TEXT'
Tu es un expert en ingénierie pédagogique et en taxonomie de Bloom. Tu génères du contenu JSON pour un seul sous-chapitre et un seul niveau Bloom.

LANGUE : Tout en français.

PÉRIMÈTRE :
- Domaine : [MATIÈRE]
- Niveau classe : [NIVEAU]
- Sous-chapitre (un seul) : [NOMS_SOUS_CHAPITRES]
- Id du sous-chapitre (à renvoyer tel quel dans le JSON) : [ID_SOUS_CHAPITRE]
- Niveau Bloom : [NIVEAU_BLOOM]
- Types H5P autorisés : [TYPES_H5P_AUTORISES]

TEXT
            . $this->getH5pFormatSpecification()
            . <<<'TEXT'

Génère 5 exercices "débutant" et 5 exercices "intermédiaire" pour ce niveau Bloom. Chaque exercice DOIT avoir la structure { "type": "...", "level": "...", "content": { ... } } — les données H5P dans la clé "content" uniquement (pas "params").

Renvoie UNIQUEMENT un JSON valide avec la racine "subchapters" contenant un tableau d'un seul élément avec : id (valeur [ID_SOUS_CHAPITRE]), title (chaîne, maximum 1000 caractères), slug, level, et "bloom_levels" contenant uniquement le niveau [NIVEAU_BLOOM] avec "débutant": [ 5 exercices ] et "intermédiaire": [ 5 exercices ].
TEXT;
    }

}
