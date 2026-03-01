<?php

declare(strict_types=1);

namespace App\Service\ContentGenerator;

use App\Service\ContentGenerator\Exception\ContentGeneratorException;
use Symfony\Contracts\HttpClient\HttpClientInterface;

final class OpenAiContentGenerator implements ContentGeneratorInterface
{
    private const DEFAULT_MODEL = 'gpt-4o-mini';
    private const ENDPOINT = 'https://api.openai.com/v1/chat/completions';

    public function __construct(
        private readonly HttpClientInterface $httpClient,
        #[\Symfony\Component\DependencyInjection\Attribute\Autowire(param: 'openai_api_key')]
        private readonly string $apiKey,
        #[\Symfony\Component\DependencyInjection\Attribute\Autowire(param: 'openai_model')]
        private readonly string $model,
    ) {
    }

    public function generate(string $prompt): string
    {
        if ($this->apiKey === '') {
            throw new ContentGeneratorException('OPENAI_API_KEY is not set.');
        }

        try {
            $response = $this->httpClient->request('POST', self::ENDPOINT, [
                'headers' => [
                    'Authorization' => 'Bearer ' . $this->apiKey,
                    'Content-Type' => 'application/json',
                ],
                'json' => [
                    'model' => $this->model,
                    'messages' => [
                        ['role' => 'user', 'content' => $prompt],
                    ],
                ],
                'timeout' => 120,
            ]);

            $data = $response->toArray();
            $content = $data['choices'][0]['message']['content'] ?? null;

            if (!\is_string($content)) {
                throw new ContentGeneratorException('OpenAI response missing choices[0].message.content');
            }

            return $content;
        } catch (\Symfony\Contracts\HttpClient\Exception\ExceptionInterface $e) {
            throw new ContentGeneratorException('OpenAI request failed: ' . $e->getMessage(), 0, $e);
        }
    }
}
