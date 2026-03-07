<?php

declare(strict_types=1);

namespace App\Type;

/**
 * Types H5P autorisés pour la génération de contenu.
 * Pour chaque type : levels possibles et format JSON attendu.
 */
enum H5pType: string
{
    case MultiChoice = 'H5P.MultiChoice';
    case TrueFalse = 'H5P.TrueFalse';
    case Blanks = 'H5P.Blanks';
    case Flashcards = 'H5P.Flashcards';
    case DragText = 'H5P.DragText';
    case Summary = 'H5P.Summary';
    case SingleChoiceSet = 'H5P.SingleChoiceSet';
    case MarkTheWords = 'H5P.MarkTheWords';
    case Essay = 'H5P.Essay';
    case InteractiveBook = 'H5P.InteractiveBook';

    /** Niveaux de difficulté communs à tous les types. */
    private const LEVELS = ['débutant', 'intermédiaire', 'avancé', 'expert'];

    public function getLabel(): string
    {
        return match ($this) {
            self::MultiChoice => 'QCM',
            self::TrueFalse => 'Vrai ou Faux',
            self::Blanks => 'Texte à trous',
            self::Flashcards => 'Cartes mémoires',
            self::DragText => 'Glisser-déposer de mots',
            self::Summary => 'Résumé interactif',
            self::SingleChoiceSet => 'Choix unique multiple',
            self::MarkTheWords => 'Marquer les mots',
            self::Essay => 'Rédaction structurée',
            self::InteractiveBook => 'Livre interactif',
        };
    }

    /** @return list<string> */
    public function getLevels(): array
    {
        return self::LEVELS;
    }

    public function getLevelsAsString(): string
    {
        return implode(' ou ', self::LEVELS);
    }

    /**
     * Entrées attendues pour la génération IA : objectif, instructions, message système et format de sortie.
     *
     * @return array{goal: string, instructions?: string, systemMessage: string, outputFormat: array<int, mixed>}
     */
    public function getExpectedInputs(): array
    {
        return match ($this) {
            self::Blanks => [
                'goal' => 'Exercices à trous pour valider la compréhension et la mémorisation',
                'instructions' => "Mettez les réponses entre *astérisques*.\nUtilisez / pour les réponses alternatives.\nAjoutez des indices après : si nécessaire.",
                'systemMessage' => "Génère uniquement des exercices à trous. Les mots à deviner doivent être encadrés par des astérisques (*mot*).",
                'outputFormat' => [[
                    'instruction' => "Consigne claire et précise pour guider l'élève",
                    'text' => ['text', 'texte_avec_mots_entourés_par_astérisques'],
                    'explications' => ['string'],
                    'indices' => ['string'],
                ]],
            ],
            self::MultiChoice => [
                'goal' => 'Question à choix multiples',
                'systemMessage' => 'Crée des QCM avec une bonne réponse et des distracteurs.',
                'outputFormat' => [[
                    'question' => 'La question peut contenir des tags HTML',
                    'answers' => [
                        [
                            'text' => 'string',
                            'correct' => 'boolean',
                            'tipsAndFeedback' => [
                                'chosenFeedback' => 'Le texte peut contenir des tags HTML',
                            ],
                        ],
                    ],
                    'explications' => ['string'],
                    'indices' => ['string'],
                ]],
            ],
            self::DragText => [
                'goal' => 'Glisser-déposer de mots',
                'instructions' => "Mettez les mots à déplacer entre *astérisques*. Ajoutez des indices après : si nécessaire.",
                'systemMessage' => "Crée un exercice où il faut placer les réponses aux bons endroits ; les mots à déplacer sont entre *astérisques*.",
                'outputFormat' => [[
                    'taskDescription' => 'Consigne instruction',
                    'textField' => 'texte_avec_mots_entourés_par_astérisques',
                    'explications' => ['string'],
                    'indices' => ['string'],
                ]],
            ],
            self::MarkTheWords => [
                'goal' => 'Marquage de mots',
                'systemMessage' => "Crée un texte avec les éléments à identifier entre astérisques (*). 'taskDescription' et 'textField' peuvent contenir des tags HTML.",
                'outputFormat' => [[
                    'taskDescription' => 'Consigne ou instruction, peut contenir des tags HTML.',
                    'textField' => 'texte_avec_mots_entourés_par_astérisques',
                    'explications' => ['string'],
                    'indices' => ['string'],
                ]],
            ],
            self::TrueFalse => [
                'goal' => 'Question vrai/faux',
                'systemMessage' => 'Crée des affirmations vrai/faux pour valider la compréhension.',
                'outputFormat' => [[
                    'question' => 'Le texte peut contenir des tags HTML',
                    'correct' => 'boolean',
                    'explications' => ['string'],
                    'indices' => ['string'],
                ]],
            ],
            self::Essay => [
                'goal' => 'Rédaction avec mots-clés à détecter',
                'systemMessage' => 'Crée des questions ouvertes avec consigne, réponse type et mots-clés attendus.',
                'outputFormat' => [[
                    'taskDescription' => 'La consigne ou question à laquelle l\'utilisateur doit répondre.',
                    'solution' => ['sample' => 'Proposition de réponse idéale attendue.'],
                    'keywords' => [['keyword' => 'string', 'options' => ['points' => 'int', 'occurrences' => 'int']]],
                    'explications' => ['string'],
                    'indices' => ['string'],
                ]],
            ],
            self::Summary => [
                'goal' => 'Créer des listes de phrases où la première phrase de chaque liste est la bonne réponse',
                'systemMessage' => 'Crée des listes de phrases où la première phrase de chaque liste est la bonne réponse.',
                'outputFormat' => [[
                    'intro' => 'Texte d\'introduction (optionnel).',
                    'summaries' => [
                        [
                            'summary' => ['affirmation_correcte', 'affirmation_fausse', 'affirmation_fausse'],
                            'explications' => ['string'],
                            'indices' => ['string'],
                        ],
                    ],
                ]],
            ],
            self::Flashcards => [
                'goal' => 'Cartes mémoire avec question/réponse',
                'systemMessage' => 'Crée des cartes question/réponse avec explications et indices.',
                'outputFormat' => [[
                    'cards' => [
                        [
                            'text' => 'string',
                            'answer' => 'string',
                            'explications' => ['string'],
                            'indices' => ['string'],
                        ],
                    ],
                ]],
            ],
            self::SingleChoiceSet => [
                'goal' => 'Série de questions à choix unique',
                'systemMessage' => 'Crée des séries de questions à choix unique ; la première réponse de chaque liste est la bonne.',
                'outputFormat' => [[
                    'choices' => [
                        [
                            'question' => 'Le texte peut contenir des tags HTML',
                            'answers' => ['bonne_réponse', 'mauvaise_réponse', 'mauvaise_réponse'],
                            'explications' => ['string'],
                            'indices' => ['string'],
                        ],
                    ],
                ]],
            ],
            self::InteractiveBook => [
                'goal' => 'Créer un livre interactif avec des chapitres et des éléments variés',
                'systemMessage' => 'Crée un livre interactif structuré avec des chapitres contenant différents types de contenu. Chaque chapitre peut contenir des éléments interactifs variés. Retourne uniquement un tableau JSON.',
                'outputFormat' => [[
                    'showCoverPage' => 'boolean',
                    'bookCover' => [
                        'coverDescription' => 'string (HTML)',
                    ],
                    'chapters' => [
                        [
                            'library' => 'H5P.Column 1.18',
                            'type' => 'H5P.Column',
                            'params' => [
                                'content' => [
                                    ['library' => self::MultiChoice->value, 'type' => self::MultiChoice->value, 'params' => self::MultiChoice->getExpectedInputs()['outputFormat'][0]],
                                    ['library' => self::DragText->value, 'type' => self::DragText->value, 'params' => self::DragText->getExpectedInputs()['outputFormat'][0]],
                                    ['library' => self::Blanks->value, 'type' => self::Blanks->value, 'params' => self::Blanks->getExpectedInputs()['outputFormat'][0]],
                                    ['library' => self::MarkTheWords->value, 'type' => self::MarkTheWords->value, 'params' => self::MarkTheWords->getExpectedInputs()['outputFormat'][0]],
                                    ['library' => self::SingleChoiceSet->value, 'type' => self::SingleChoiceSet->value, 'params' => self::SingleChoiceSet->getExpectedInputs()['outputFormat'][0]],
                                    ['library' => self::Flashcards->value, 'type' => self::Flashcards->value, 'params' => self::Flashcards->getExpectedInputs()['outputFormat'][0]],
                                    ['library' => self::Summary->value, 'type' => self::Summary->value, 'params' => self::Summary->getExpectedInputs()['outputFormat'][0]],
                                    ['library' => self::Essay->value, 'type' => self::Essay->value, 'params' => self::Essay->getExpectedInputs()['outputFormat'][0]],
                                ],
                            ],
                        ],
                    ],
                    'behaviour' => [
                        'baseColor' => 'string (hex color)',
                        'defaultTableOfContents' => 'boolean',
                        'progressIndicators' => 'boolean',
                        'progressAuto' => 'boolean',
                        'displaySummary' => 'boolean',
                        'enableRetry' => 'boolean',
                    ],
                ]],
            ],
        };
    }
}
