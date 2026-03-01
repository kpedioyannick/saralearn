<?php

declare(strict_types=1);

namespace App\Service\Suno;

use Symfony\Contracts\HttpClient\HttpClientInterface;

/**
 * Client pour l'API Suno (génération de musique).
 * @see https://docs.sunoapi.org/suno-api/quickstart
 */
final class SunoApiClient
{
    private const BASE_URL = 'https://api.sunoapi.org/api/v1';

    public function __construct(
        private readonly HttpClientInterface $httpClient,
        private readonly string $apiKey,
    ) {
    }

    /**
     * Lance une génération de musique.
     *
     * @param array{prompt: string, instrumental?: bool, model?: string, customMode?: bool, style?: string, title?: string} $params
     * @return string taskId
     * @throws \RuntimeException
     */
    public function generate(array $params): string
    {
        $payload = [
            'prompt' => $params['prompt'],
            'customMode' => $params['customMode'] ?? false,
            'instrumental' => $params['instrumental'] ?? true,
            'model' => $params['model'] ?? 'V4_5ALL',
            'callBackUrl' => 'https://example.com/api/suno/webhook',
        ];
        if (!empty($params['style'])) {
            $payload['style'] = $params['style'];
        }
        if (!empty($params['title'])) {
            $payload['title'] = $params['title'];
        }

        $response = $this->httpClient->request('POST', self::BASE_URL . '/generate', [
            'headers' => [
                'Authorization' => 'Bearer ' . $this->apiKey,
                'Content-Type' => 'application/json',
            ],
            'json' => $payload,
            'timeout' => 30,
        ]);

        $data = $response->toArray();
        if (($data['code'] ?? 0) !== 200) {
            throw new \RuntimeException(sprintf('Suno API error: %s', $data['msg'] ?? 'Unknown error'));
        }
        $taskId = $data['data']['taskId'] ?? null;
        if ($taskId === null || $taskId === '') {
            throw new \RuntimeException('Suno API: no taskId in response');
        }
        return (string) $taskId;
    }

    /**
     * Récupère le statut et le résultat d'une tâche.
     *
     * @return array{status: string, response?: array{data: list<array{id?: string, audio_url?: string, title?: string, duration?: float}>}}
     */
    public function getRecordInfo(string $taskId): array
    {
        $response = $this->httpClient->request('GET', self::BASE_URL . '/generate/record-info', [
            'headers' => [
                'Authorization' => 'Bearer ' . $this->apiKey,
            ],
            'query' => ['taskId' => $taskId],
            'timeout' => 15,
        ]);

        $data = $response->toArray();
        if (($data['code'] ?? 0) !== 200) {
            throw new \RuntimeException(sprintf('Suno API record-info error: %s', $data['msg'] ?? 'Unknown error'));
        }
        return [
            'status' => $data['data']['status'] ?? 'UNKNOWN',
            'response' => $data['data']['response'] ?? null,
        ];
    }
}
