<?php

declare(strict_types=1);

namespace App\Service\Prompt;

/**
 * Répartition des types H5P par niveau de la taxonomie de Bloom (CDC).
 */
final class BloomH5pTypeMap
{
    public const BLOOM_REMEMBER = 'remember';
    public const BLOOM_UNDERSTAND = 'understand';
    public const BLOOM_APPLY = 'apply';
    public const BLOOM_ANALYZE = 'analyze';
    public const BLOOM_EVALUATE = 'evaluate';

    /** @var array<string, list<string>> */
    private const MAP = [
        self::BLOOM_REMEMBER => [
            'H5P.MultiChoice',
            'H5P.TrueFalse',
            'H5P.Blanks',
            'H5P.Flashcards',
            'H5P.DragText',
        ],
        self::BLOOM_UNDERSTAND => [
            'H5P.DragText',
            'H5P.Summary',
            'H5P.Dialogcards',
            'H5P.Blanks',
        ],
        self::BLOOM_APPLY => [
            'H5P.Blanks',
            'H5P.DragText',
            'H5P.Dialogcards',
            'H5P.SortParagraphs',
            'H5P.MultiChoice',
        ],
        self::BLOOM_ANALYZE => [
            'H5P.Blanks',
            'H5P.MultiChoice',
            'H5P.Essay',
            'H5P.DragText',
            'H5P.SingleChoiceSet',
        ],
        self::BLOOM_EVALUATE => [
            'H5P.Essay',
            'H5P.MarkTheWords',
            'H5P.SortParagraphs',
            'H5P.SingleChoiceSet',
            'H5P.MultiChoice',
        ],
    ];

    /** @return list<string> */
    public static function getH5pTypesForBloomLevel(string $bloomLevel): array
    {
        return self::MAP[$bloomLevel] ?? [];
    }

    /** @return list<string> */
    public static function getAllBloomLevels(): array
    {
        return [
            self::BLOOM_REMEMBER,
            self::BLOOM_UNDERSTAND,
            self::BLOOM_APPLY,
            self::BLOOM_ANALYZE,
            self::BLOOM_EVALUATE,
        ];
    }

    public static function getH5pTypesAsString(string $bloomLevel): string
    {
        return implode(', ', self::getH5pTypesForBloomLevel($bloomLevel));
    }
}
