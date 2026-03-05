<?php

declare(strict_types=1);

namespace App\Service\Suno;

use Symfony\Contracts\HttpClient\HttpClientInterface;

/**
 * Client HTTP pour l'API "studio" de Suno (site officiel).
 *
 * Les valeurs concrètes (Bearer, browser token, device id) sont fournies
 * via les variables d'environnement afin d'éviter de les committer.
 */
final class SunoStudioClient
{
    private const BASE_URL = 'https://studio-api.prod.suno.com';

    public function __construct(
        private readonly HttpClientInterface $httpClient,
        private readonly string $bearerToken,
        private readonly ?string $browserToken = null,
        private readonly ?string $deviceId = null,
    ) {
    }

    /**
     * Appelle l'API de génération de musique.
     *
     * @return array{task_id: string, clip_ids: list<string>}
     */
    public function createSong(string $prompt, ?string $style = null, ?string $title = null): array
    {
        $payload = [
            'token' => null,
            'generation_type' => 'TEXT',
            'title' => $title ?? '',
            'tags' => $style ?? '',
            'negative_tags' => '',
            'mv' => 'chirp-crow',
            'prompt' => $prompt,
            'make_instrumental' => false,
            'user_uploaded_images_b64' => null,
            'metadata' => [
                'web_client_pathname' => '/create',
                'is_max_mode' => false,
                'is_mumble' => false,
                'create_mode' => 'custom',
                'disable_volume_normalization' => false,
            ],
            'override_fields' => [],
            'cover_clip_id' => null,
            'cover_start_s' => null,
            'cover_end_s' => null,
            'persona_id' => null,
            'artist_clip_id' => null,
            'artist_start_s' => null,
            'artist_end_s' => null,
            'continue_clip_id' => null,
            'continued_aligned_prompt' => null,
            'continue_at' => null,
        ];

        $headers = $this->buildHeaders(true);

        $response = $this->httpClient->request('POST', self::BASE_URL . '/api/generate/v2-web/', [
            'headers' => $headers,
            'json' => $payload,
            'timeout' => 30,
        ]);

        $data = $response->toArray(false);
        if (!isset($data['id'], $data['clips']) || !is_array($data['clips']) || $data['clips'] === []) {
            throw new \RuntimeException('Réponse inattendue de Suno (generate v2-web).');
        }

        $clipIds = [];
        foreach ($data['clips'] as $clip) {
            if (!empty($clip['id']) && is_string($clip['id'])) {
                $clipIds[] = $clip['id'];
            }
        }
        if ($clipIds === []) {
            throw new \RuntimeException('Aucun clip id retourné par Suno.');
        }

        return [
            'task_id' => (string) $data['id'],
            'clip_ids' => $clipIds,
        ];
    }

    /**
     * Récupère le statut d'un clip audio (et l'URL audio finale si complete).
     *
     * @return array{status: string, audio_url: ?string, duration: ?float}
     */
    public function getClipStatus(string $clipId): array
    {
        $headers = $this->buildHeaders(false);

        $payload = [
            'filters' => [
                'ids' => [
                    'presence' => 'True',
                    'clipIds' => [$clipId],
                ],
            ],
            'limit' => 1,
        ];

        $response = $this->httpClient->request('POST', self::BASE_URL . '/api/feed/v3', [
            'headers' => $headers,
            'json' => $payload,
            'timeout' => 20,
        ]);

        $data = $response->toArray(false);
        $clips = $data['clips'] ?? [];
        if (!is_array($clips) || $clips === []) {
            return [
                'status' => 'unknown',
                'audio_url' => null,
                'duration' => null,
            ];
        }

        $clip = $clips[0];
        $status = (string) ($clip['status'] ?? 'unknown');
        $audioUrl = isset($clip['audio_url']) && is_string($clip['audio_url']) ? $clip['audio_url'] : null;
        $duration = null;
        if (isset($clip['metadata']['duration'])) {
            $duration = (float) $clip['metadata']['duration'];
        }

        return [
            'status' => $status,
            'audio_url' => $audioUrl,
            'duration' => $duration,
        ];
    }

    /**
     * Récupère le statut d'une génération vidéo Suno.
     *
     * @return array{status: string, video_url: ?string}
     */
    public function getVideoStatus(string $videoId): array
    {
        $headers = $this->buildHeaders(false);

        $response = $this->httpClient->request(
            'GET',
            self::BASE_URL . '/api/video/generate/' . urlencode($videoId) . '/status/',
            [
                'headers' => $headers,
                'timeout' => 20,
            ],
        );

        $data = $response->toArray(false);

        return [
            'status' => (string) ($data['status'] ?? 'unknown'),
            'video_url' => isset($data['video_url']) && is_string($data['video_url']) ? $data['video_url'] : null,
        ];
    }

    /**
     * Construit les en-têtes HTTP communs.
     *
     * @return array<string, string>
     */
    private function buildHeaders(bool $withContentType): array
    {
        $headers = [
            'Accept' => '*/*',
            'Authorization' => 'Bearer ' . $this->bearerToken,
        ];

        if ($withContentType) {
            $headers['Content-Type'] = 'application/json';
        }
        if ($this->browserToken !== null && $this->browserToken !== '') {
            $headers['browser-token'] = $this->browserToken;
        }
        if ($this->deviceId !== null && $this->deviceId !== '') {
            $headers['device-id'] = $this->deviceId;
        }

        return $headers;
    }
}

