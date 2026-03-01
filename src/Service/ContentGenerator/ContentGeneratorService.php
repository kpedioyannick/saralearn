<?php

declare(strict_types=1);

namespace App\Service\ContentGenerator;

use App\Service\ContentGenerator\Exception\ContentGeneratorException;

/**
 * Service exposant les 3 méthodes de génération de contenu (CDC)
 * et une méthode par défaut selon CONTENT_GENERATOR_DEFAULT.
 */
final class ContentGeneratorService
{
    public const PROVIDER_OPENAI = 'openai';
    public const PROVIDER_DEEPSEEK = 'deepseek';
    public const PROVIDER_CURL = 'curl';

    /** @var array<string, ContentGeneratorInterface> */
    private array $generators;

    public function __construct(
        OpenAiContentGenerator $openAiGenerator,
        DeepSeekContentGenerator $deepSeekGenerator,
        CurlContentGenerator $curlGenerator,
        #[\Symfony\Component\DependencyInjection\Attribute\Autowire(param: 'content_generator_default')]
        private readonly string $defaultProvider,
    ) {
        $this->generators = [
            self::PROVIDER_OPENAI => $openAiGenerator,
            self::PROVIDER_DEEPSEEK => $deepSeekGenerator,
            self::PROVIDER_CURL => $curlGenerator,
        ];
    }

    public function generateViaOpenAI(string $prompt): string
    {
        return $this->generators[self::PROVIDER_OPENAI]->generate($prompt);
    }

    public function generateViaDeepSeek(string $prompt): string
    {
        return $this->generators[self::PROVIDER_DEEPSEEK]->generate($prompt);
    }

    public function generateViaCurl(string $prompt): string
    {
        return $this->generators[self::PROVIDER_CURL]->generate($prompt);
    }

    /**
     * Génère via le provider par défaut (CONTENT_GENERATOR_DEFAULT).
     */
    public function generate(string $prompt): string
    {
        $provider = strtolower($this->defaultProvider);
        if (!isset($this->generators[$provider])) {
            throw new ContentGeneratorException(sprintf(
                'CONTENT_GENERATOR_DEFAULT "%s" is invalid. Use: openai, deepseek, curl.',
                $this->defaultProvider,
            ));
        }

        return $this->generators[$provider]->generate($prompt);
    }

    public function getDefaultProvider(): string
    {
        return $this->defaultProvider;
    }
}
