<?php

declare(strict_types=1);

namespace App\Controller\Api;

use App\Entity\CourseMusic;
use App\Repository\CourseMusicRepository;
use App\Repository\SubchapterRepository;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

/**
 * API 1 : POST /api/subchapters/list — retourne des sous-chapitres sans CourseMusic (sans prompt enregistré).
 * API 2 : POST /api/course-music — enregistre ou met à jour une CourseMusic.
 */
#[Route('/api')]
final class CourseMusicApiController extends AbstractController
{
    public function __construct(
        private readonly SubchapterRepository $subchapterRepository,
        private readonly CourseMusicRepository $courseMusicRepository,
        private readonly EntityManagerInterface $entityManager,
    ) {
    }

    /**
     * Liste de sous-chapitres qui n'ont pas encore de CourseMusic (pas de prompt enregistré).
     * POST body : { "number": 10 } (nombre de résultats à retourner).
     */
    #[Route('/subchapters/list', name: 'api_subchapters_list', methods: ['POST'])]
    public function subchaptersList(Request $request): JsonResponse
    {
        $body = json_decode((string) $request->getContent(), true);
        $number = isset($body['number']) && is_numeric($body['number']) ? max(1, min(500, (int) $body['number'])) : 50;

        $subchapters = $this->subchapterRepository->findWithContextWithoutCourseMusicOrderById($number);
        $items = [];
        foreach ($subchapters as $s) {
            $chapter = $s->getChapter();
            $subject = $chapter?->getSubject();
            $classroom = $subject?->getClassroom();
            $items[] = [
                'id' => $s->getId(),
                'subchapterTitle' => $s->getTitle(),
                'chapterTitle' => $chapter?->getTitle(),
                'classroom' => $classroom?->getName(),
                'subject' => $subject?->getName(),
            ];
        }

        return $this->json(['items' => $items]);
    }

    /**
     * Enregistre ou met à jour une CourseMusic. Body : subchapterId, title, prompt, style.
     * Si une CourseMusic existe déjà pour ce sous-chapitre, elle est mise à jour.
     */
    #[Route('/course-music', name: 'api_course_music_save', methods: ['POST'])]
    public function saveCourseMusic(Request $request): JsonResponse
    {
        $body = json_decode((string) $request->getContent(), true);
        if (!is_array($body)) {
            return $this->json(['error' => 'Body JSON invalide.'], Response::HTTP_BAD_REQUEST);
        }

        $subchapterId = $body['subchapterId'] ?? null;
        if ($subchapterId === null || !is_numeric($subchapterId)) {
            return $this->json(['error' => 'subchapterId requis (entier).'], Response::HTTP_BAD_REQUEST);
        }

        $subchapter = $this->subchapterRepository->find((int) $subchapterId);
        if ($subchapter === null) {
            return $this->json(['error' => 'Sous-chapitre introuvable.'], Response::HTTP_NOT_FOUND);
        }

        $courseMusic = $this->courseMusicRepository->findOneBySubchapter($subchapter);
        if ($courseMusic === null) {
            $courseMusic = new CourseMusic();
            $courseMusic->setSubchapter($subchapter);
            $this->entityManager->persist($courseMusic);
        }

        if (array_key_exists('title', $body)) {
            $courseMusic->setTitle(is_string($body['title']) ? $body['title'] : null);
        }
        if (array_key_exists('prompt', $body)) {
            $courseMusic->setPrompt(is_string($body['prompt']) ? $body['prompt'] : null);
        }
        if (array_key_exists('style', $body)) {
            $courseMusic->setStyle(is_string($body['style']) ? $body['style'] : null);
        }

        $this->entityManager->flush();

        return $this->json(['id' => $courseMusic->getId()], Response::HTTP_CREATED);
    }
}
