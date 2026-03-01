<?php

declare(strict_types=1);

namespace App\Service\ContentGenerator;

interface ContentGeneratorInterface
{
    /**
     * Génère du contenu à partir du prompt et retourne la réponse en texte.
     *
     * @throws \App\Service\ContentGenerator\Exception\ContentGeneratorException en cas d'erreur (réseau, API, timeout)
     */
    public function generate(string $prompt): string;
}
