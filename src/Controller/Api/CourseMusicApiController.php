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
 * API Course Music — sous-chapitres sans prompt et enregistrement CourseMusic.
 *
 * Toutes les routes attendent un body JSON et renvoient du JSON.
 * Content-Type : application/json.
 *
 * ---
 *
 * POST /api/subchapters/list
 * Retourne les sous-chapitres qui n'ont pas encore de CourseMusic (candidats pour remplir un prompt).
 *
 * Request body (JSON) :
 *   - number (int, optionnel) : nombre de sous-chapitres à retourner (1–500, défaut 50).
 *
 * Response 200 :
 *   { "items": [ { "id", "subchapterTitle", "chapterTitle", "classroom", "subject" }, ... ] }
 *
 * Exemple : POST /api/subchapters/list  { "number": 10 }
 *
 * ---
 *
 * POST /api/course-music
 * Crée ou met à jour une CourseMusic. Tous les champs de l'entité (sauf id, subchapter, createdAt) sont éditables via le body.
 *
 * Request body (JSON) :
 *   - subchapterId (int, requis) : ID du sous-chapitre.
 *   - title (string, optionnel)
 *   - prompt (string, optionnel)
 *   - style (string, optionnel)
 *   - relevance (string, optionnel)
 *   - sunoTaskId (string, optionnel)
 *   - audioUrl (string, optionnel)
 *   - videoUrl (string, optionnel)
 *   - coverUrl (string, optionnel) : URL de la cover image Suno.
 *   - duration (float, optionnel) : durée en secondes.
 *
 * Response 201 : { "id": <id de la CourseMusic> }
 * Response 400 : { "error": "..." }  (body invalide ou subchapterId manquant)
 * Response 404 : { "error": "Sous-chapitre introuvable." }
 *
 * Exemple : POST /api/course-music  { "subchapterId": 42, "title": "Intro", "prompt": "...", "style": "pop", "relevance": "high", "audioUrl": "https://...", "duration": 120.5 }
 *
 * ---
 *
 * GET /api/course-music/status
 * Statut : nombre total de sous-chapitres et nombre de sous-chapitres avec prompt (aucune liste).
 *
 * Response 200 : { "totalSubchapters": 123, "subchaptersWithPromptCount": 45 }
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
     * Liste de sous-chapitres sans CourseMusic.
     *
     * Body : { "number": 10 }. Réponse : { "items": [ { id, subchapterTitle, chapterTitle, classroom, subject }, ... ] }
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
     * Crée ou met à jour une CourseMusic.
     *
     * Body : subchapterId (requis), title, prompt, style, relevance, sunoTaskId, audioUrl, videoUrl, coverUrl, duration (optionnels). 201 : { "id" }. 400/404 : { "error" }.
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
        if (array_key_exists('relevance', $body)) {
            $courseMusic->setRelevance(is_string($body['relevance']) ? $body['relevance'] : null);
        }
        if (array_key_exists('sunoTaskId', $body)) {
            $courseMusic->setSunoTaskId(is_string($body['sunoTaskId']) ? $body['sunoTaskId'] : null);
        }
        if (array_key_exists('audioUrl', $body)) {
            $courseMusic->setAudioUrl(is_string($body['audioUrl']) ? $body['audioUrl'] : null);
        }
        if (array_key_exists('videoUrl', $body)) {
            $courseMusic->setVideoUrl(is_string($body['videoUrl']) ? $body['videoUrl'] : null);
        }
        if (array_key_exists('coverUrl', $body)) {
            $courseMusic->setCoverUrl(is_string($body['coverUrl']) ? $body['coverUrl'] : null);
        }
        if (array_key_exists('duration', $body)) {
            $courseMusic->setDuration(is_numeric($body['duration']) ? (float) $body['duration'] : null);
        }

        $this->entityManager->flush();

        return $this->json(['id' => $courseMusic->getId()], Response::HTTP_CREATED);
    }

    /**
     * Statut : uniquement les totaux (totalSubchapters, subchaptersWithPromptCount).
     */
    #[Route('/course-music/status', name: 'api_course_music_status', methods: ['GET'])]
    public function status(): JsonResponse
    {
        return $this->json([
            'totalSubchapters' => $this->subchapterRepository->countWithContext(),
            'subchaptersWithPromptCount' => $this->subchapterRepository->countWithContextWithPrompt(),
        ]);
    }
}
