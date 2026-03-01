<?php

declare(strict_types=1);

namespace App\Service\InteractiveBook;

/**
 * Map H5P type (Module.h5pType) to library string with version for content.json.
 * Basé sur les préloadedDependencies du livre interactif existant.
 */
final class H5pLibraryVersionMap
{
    /** @var array<string, string> */
    private const MAP = [
        'H5P.MultiChoice' => 'H5P.MultiChoice 1.16',
        'H5P.TrueFalse' => 'H5P.TrueFalse 1.8',
        'H5P.Blanks' => 'H5P.Blanks 1.14',
        'H5P.Flashcards' => 'H5P.Dialogcards 1.9',
        'H5P.DragText' => 'H5P.DragText 1.10',
        'H5P.Summary' => 'H5P.Summary 1.10',
        'H5P.SingleChoiceSet' => 'H5P.SingleChoiceSet 1.11',
        'H5P.MarkTheWords' => 'H5P.MarkTheWords 1.11',
        'H5P.Essay' => 'H5P.Essay 1.5',
    ];

    private const COLUMN_LIBRARY = 'H5P.Column 1.18';
    private const DEFAULT_LIBRARY = 'H5P.Blanks 1.14';

    public static function getLibrary(string $h5pType): string
    {
        return self::MAP[$h5pType] ?? self::DEFAULT_LIBRARY;
    }

    public static function getColumnLibrary(): string
    {
        return self::COLUMN_LIBRARY;
    }
}
