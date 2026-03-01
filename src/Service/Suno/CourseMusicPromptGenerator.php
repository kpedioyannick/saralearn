<?php

declare(strict_types=1);

namespace App\Service\Suno;

use App\Entity\CourseMusic;
use App\Entity\Subchapter;
use App\Repository\CourseMusicRepository;
use App\Service\ContentGenerator\ContentGeneratorService;
use Doctrine\ORM\EntityManagerInterface;

/**
 * Génère le prompt (max 400 caractères) pour la musique du cours via le provider curl,
 * en extrayant les éléments essentiels du cours à mettre en chanson.
 */
final class CourseMusicPromptGenerator
{
    private const MAX_PROMPT_LENGTH = 400;

    public function __construct(
        private readonly ContentGeneratorService $contentGeneratorService,
        private readonly CourseMusicRepository $courseMusicRepository,
        private readonly EntityManagerInterface $entityManager,
    ) {
    }

    /**
     * Extrait le contenu essentiel du cours (titre + texte des slides) pour l’envoyer à l’IA.
     */
    public function extractCourseContentForPrompt(Subchapter $subchapter): string
    {
        $course = $subchapter->getCourse();
        if ($course === null || !is_array($course)) {
            return $subchapter->getTitle() ?? '';
        }

        $parts = [];
        $title = $course['title'] ?? $subchapter->getTitle() ?? '';
        if ($title !== '') {
            $parts[] = 'Titre : ' . $title;
        }
        $slides = $course['slides'] ?? [];
        if (is_array($slides)) {
            foreach ($slides as $slide) {
                $text = $slide['texte_audio'] ?? $slide['text_to_audio'] ?? $slide['slide'] ?? '';
                if (is_string($text) && trim($text) !== '') {
                    $parts[] = trim($text);
                }
            }
        }
        return implode("\n\n", $parts);
    }

    /**
     * Génère un prompt (max 400 caractères) pour Suno via le provider curl :
     * les éléments essentiels du cours à traduire en chanson.
     *
     * @throws \RuntimeException
     */
    public function generatePromptForSubchapter(Subchapter $subchapter): string
    {
        $courseContent = $this->extractCourseContentForPrompt($subchapter);
        if ($courseContent === '') {
            $fallback = $subchapter->getTitle() ?? 'Educational lesson';
            return mb_substr('Calm instrumental background music for a lesson about: ' . $fallback, 0, self::MAX_PROMPT_LENGTH);
        }

        $instruction = <<<PROMPT
Tu es un expert en création de contenu pour la musique éducative.

Contenu du cours (sous-chapitre) :
---
{$courseContent}
---

Rédige UN SEUL prompt en anglais, de 400 caractères maximum, qui décrit une chanson instrumentale de fond pour ce cours. Le prompt doit contenir les éléments essentiels que le cours doit faire passer en musique : thème, notions clés, ambiance. Style : instrumental, calme, pédagogique. Pas de paroles.

Réponds UNIQUEMENT par le prompt, sans explication, sans guillemets superflus.
PROMPT;

        $raw = $this->contentGeneratorService->generateViaCurl($instruction);
        $data = json_decode($raw, true);
        if (is_array($data) && isset($data['content'])) {
            $prompt = (string) $data['content'];
        } else {
            $prompt = trim(preg_replace('/^["\']|["\']$/u', '', trim($raw)));
        }

        return mb_substr($prompt, 0, self::MAX_PROMPT_LENGTH);
    }

    /**
     * Génère le prompt via curl et crée ou met à jour CourseMusic (champ prompt uniquement, pas d’appel Suno).
     */
    public function createOrUpdatePromptForSubchapter(Subchapter $subchapter): CourseMusic
    {
        $prompt = $this->generatePromptForSubchapter($subchapter);

        $courseMusic = $this->courseMusicRepository->findOneBySubchapter($subchapter)
            ?? new CourseMusic();
        $courseMusic->setSubchapter($subchapter);
        $courseMusic->setPrompt($prompt);
        $courseMusic->setTitle(mb_substr($subchapter->getTitle() ?? 'Course music', 0, 255));
        if (!$this->entityManager->contains($courseMusic)) {
            $this->entityManager->persist($courseMusic);
            $subchapter->addCourseMusic($courseMusic);
        }
        $this->entityManager->flush();

        return $courseMusic;
    }
}
