<?php

declare(strict_types=1);

namespace App\Service\InteractiveBook;

/**
 * Combinaisons de niveaux Bloom pour les livres interactifs (par sous-chapitre).
 * Chaque preset = un Path avec types = tableau de Bloom.
 */
final class PathTypePresets
{
    /** Remember + Understand */
    public const PRESET_REMEMBER_UNDERSTAND = ['remember', 'understand'];

    /** Understand + Apply */
    public const PRESET_UNDERSTAND_APPLY = ['understand', 'apply'];

    /** Apply + Analyze */
    public const PRESET_APPLY_ANALYZE = ['apply', 'analyze'];

    /** Analyze + Evaluate */
    public const PRESET_ANALYZE_EVALUATE = ['analyze', 'evaluate'];

    /**
     * Tous les presets (4 livres par sous-chapitre).
     *
     * @return list<list<string>>
     */
    public static function all(): array
    {
        return [
            self::PRESET_REMEMBER_UNDERSTAND,
            self::PRESET_UNDERSTAND_APPLY,
            self::PRESET_APPLY_ANALYZE,
            self::PRESET_ANALYZE_EVALUATE,
        ];
    }

    /**
     * Presets utilisés par le Manager pour l’instant : remember, understand et apply uniquement
     * (remember+understand, understand+apply). Exclut apply+analyze et analyze+evaluate.
     *
     * @return list<list<string>>
     */
    public static function presetsForManager(): array
    {
        return [
            self::PRESET_REMEMBER_UNDERSTAND,
            self::PRESET_UNDERSTAND_APPLY,
        ];
    }

    /**
     * Retourne le preset dont les types correspondent à la clé (ex. "remember,understand").
     * Utilisé par le Manager pour appeler la commande livres preset par preset.
     *
     * @return list<string>|null
     */
    public static function getByKey(string $key): ?array
    {
        $normalized = strtolower(str_replace(' ', '', $key));
        foreach (self::all() as $types) {
            if (implode(',', $types) === $normalized) {
                return $types;
            }
        }
        return null;
    }

    /**
     * Clé pour un preset (ex. "remember,understand").
     */
    public static function key(array $types): string
    {
        return implode(',', $types);
    }

    /**
     * Libellé court pour un preset (pour titre du Path).
     */
    public static function label(array $types): string
    {
        return implode(' + ', $types);
    }
}
