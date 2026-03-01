<?php

declare(strict_types=1);

namespace App\Service\Suno;

use App\Entity\CourseMusic;
use App\Entity\Subchapter;
use App\Repository\CourseMusicRepository;
use Doctrine\ORM\EntityManagerInterface;

/**
 * Génère une piste musicale pour un sous-chapitre via Suno et persiste CourseMusic.
 */
final class CourseMusicGenerator
{
    private const POLL_INTERVAL_SECONDS = 20;
    private const MAX_WAIT_SECONDS = 600; // 10 min

    public function __construct(
        private readonly SunoApiClient $sunoClient,
        private readonly CourseMusicRepository $courseMusicRepository,
        private readonly EntityManagerInterface $entityManager,
    ) {
    }

    /**
     * Construit le style musical Suno (tags) à partir du sous-chapitre.
     */
    public function buildStyleForSubchapter(Subchapter $subchapter, bool $isInstrumental = false): string
    {
        $title = $subchapter->getTitle() ?? 'Cours';
        $chapter = $subchapter->getChapter();
        $subject = $chapter?->getSubject()?->getName() ?? '';

        if ($isInstrumental) {
            $parts = [
                'Calm background music',
                'instrumental only',
                'no vocals',
                'relaxing atmosphere',
            ];
        } else {
            $parts = [
                'Catchy educational song',
                'clear vocals',
                'upbeat rhythm',
                'melodic',
            ];
        }

        if ($subject !== '') {
            $parts[] = mb_substr($subject, 0, 30);
        }
        if ($title !== '') {
            $parts[] = mb_substr('theme: ' . $title, 0, 50);
        }

        return mb_substr(implode(', ', $parts), 0, 120);
    }

    /**
     * Extrait le texte des slides du cours pour en faire les paroles de la chanson.
     */
    private function extractLyrics(Subchapter $subchapter): string
    {
        $course = $subchapter->getCourse();
        if ($course === null || !is_array($course)) {
            return '';
        }

        $slides = $course['slides'] ?? [];
        if (!is_array($slides)) {
            return '';
        }

        $lyrics = [];
        foreach ($slides as $slide) {
            $text = $slide['texte_audio'] ?? $slide['text_to_audio'] ?? '';
            if ($text !== '') {
                $lyrics[] = trim((string) $text);
            }
        }
        return implode("\n\n", $lyrics);
    }

    /**
     * Génère la musique pour le sous-chapitre, attend la fin, crée ou met à jour CourseMusic.
     *
     * @throws \RuntimeException
     */
    public function generateForSubchapter(Subchapter $subchapter): CourseMusic
    {
        $lyrics = $this->extractLyrics($subchapter);
        $isInstrumental = $lyrics === '';
        
        $style = $this->buildStyleForSubchapter($subchapter, $isInstrumental);
        $title = mb_substr($subchapter->getTitle() ?? 'Course music', 0, 80);
        
        // Suno customMode: "prompt" is lyrics, "style" is musical genre/tags
        $prompt = $isInstrumental ? $style : mb_substr($lyrics, 0, 3000);

        $params = [
            'prompt' => $prompt,
            'instrumental' => $isInstrumental,
            'model' => 'V4_5ALL',
            'customMode' => !$isInstrumental,
            'title' => $title,
        ];
        if (!$isInstrumental) {
            $params['style'] = $style;
        }

        $taskId = $this->sunoClient->generate($params);

        $courseMusic = $this->courseMusicRepository->findOneBySubchapter($subchapter)
            ?? new CourseMusic();
        $courseMusic->setSubchapter($subchapter);
        $courseMusic->setSunoTaskId($taskId);
        $courseMusic->setPrompt(mb_substr($prompt, 0, 2000)); // Limiter la longueur persistée pour éviter l'erreur Doctrine si string trop long
        $courseMusic->setTitle($title);
        if (!$this->entityManager->contains($courseMusic)) {
            $this->entityManager->persist($courseMusic);
            $subchapter->addCourseMusic($courseMusic);
        }
        $this->entityManager->flush();

        $this->waitForCompletion($taskId, $courseMusic);
        $this->entityManager->flush();

        return $courseMusic;
    }

    private function waitForCompletion(string $taskId, CourseMusic $courseMusic): void
    {
        $deadline = time() + self::MAX_WAIT_SECONDS;
        while (time() < $deadline) {
            $info = $this->sunoClient->getRecordInfo($taskId);
            $status = $info['status'];

            if ($status === 'SUCCESS') {
                $data = $info['response']['sunoData'] ?? $info['response']['data'] ?? [];
                $first = $data[0] ?? null;
                if ($first !== null) {
                    $audioUrl = $first['audioUrl'] ?? $first['sourceAudioUrl'] ?? $first['audio_url'] ?? null;
                    $courseMusic->setAudioUrl($audioUrl);
                    $courseMusic->setTitle($first['title'] ?? $courseMusic->getTitle());
                    $courseMusic->setDuration(isset($first['duration']) ? (float) $first['duration'] : null);
                }
                return;
            }

            if ($status === 'FAILED' || $status === 'ERROR') {
                throw new \RuntimeException(sprintf('Suno generation failed: %s', $status));
            }

            sleep(self::POLL_INTERVAL_SECONDS);
        }

        throw new \RuntimeException('Suno generation timeout');
    }
}
