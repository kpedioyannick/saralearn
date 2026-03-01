<?php

declare(strict_types=1);

namespace App\Service\ContentGenerator;

use App\Service\ContentGenerator\Exception\ContentGeneratorException;
use Symfony\Contracts\HttpClient\HttpClientInterface;

final class CurlContentGenerator implements ContentGeneratorInterface
{
    private const DEFAULT_TIMEOUT = 300;

    public function __construct(
        private readonly HttpClientInterface $httpClient,
        #[\Symfony\Component\DependencyInjection\Attribute\Autowire(param: 'curl_content_url')]
        private readonly string $url,
        #[\Symfony\Component\DependencyInjection\Attribute\Autowire(param: 'curl_content_timeout')]
        private readonly int $timeout,
    ) {
    }

    public function generate(string $prompt): string
    {
        if ($this->url === '') {
            throw new ContentGeneratorException('CURL_CONTENT_URL is not set.');
        }

        try {
            $response = $this->httpClient->request('POST', $this->url, [
                'headers' => [
                    'Content-Type' => 'application/json',
                ],
                'json' => [
                    'prompt' => $prompt,
                ],
                'timeout' => $this->timeout,
            ]);

            return $response->getContent();
        } catch (\Symfony\Contracts\HttpClient\Exception\ExceptionInterface $e) {
            throw new ContentGeneratorException('Curl content service request failed: ' . $e->getMessage(), 0, $e);
        }
    }
}
