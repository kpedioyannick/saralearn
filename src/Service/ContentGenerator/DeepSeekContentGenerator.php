<?php

declare(strict_types=1);

namespace App\Service\ContentGenerator;

use App\Service\ContentGenerator\Exception\ContentGeneratorException;
use Symfony\Contracts\HttpClient\HttpClientInterface;

final class DeepSeekContentGenerator implements ContentGeneratorInterface
{
    private const DEFAULT_MODEL = 'deepseek-chat';
    private const ENDPOINT = 'https://api.deepseek.com/chat/completions';

    public function __construct(
        private readonly HttpClientInterface $httpClient,
        #[\Symfony\Component\DependencyInjection\Attribute\Autowire(param: 'deepseek_api_key')]
        private readonly string $apiKey,
        #[\Symfony\Component\DependencyInjection\Attribute\Autowire(param: 'deepseek_model')]
        private readonly string $model,
    ) {
    }

    public function generate(string $prompt): string
    {
        if ($this->apiKey === '') {
            throw new ContentGeneratorException('DEEPSEEK_API_KEY is not set.');
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
                        ['role' => 'system', 'content' => 'You are a helpful assistant. Always output valid JSON.'],
                        ['role' => 'user', 'content' => $prompt],
                    ],
                    'max_tokens' => 8000,
                    'response_format' => ['type' => 'json_object'],
                    'stream' => false,
                ],
                'timeout' => 300,
            ]);

            $data = $response->toArray();
            $content = $data['choices'][0]['message']['content'] ?? null;

            if (!\is_string($content)) {
                throw new ContentGeneratorException('DeepSeek response missing choices[0].message.content');
            }

            return $content;
        } catch (\Symfony\Contracts\HttpClient\Exception\ExceptionInterface $e) {
            throw new ContentGeneratorException('DeepSeek request failed: ' . $e->getMessage(), 0, $e);
        }
    }
}
