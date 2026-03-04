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
 * Crée ou met à jour une CourseMusic pour un sous-chapitre (title, prompt, style).
 *
 * Request body (JSON) :
 *   - subchapterId (int, requis) : ID du sous-chapitre.
 *   - title (string, optionnel) : titre de la musique / cours.
 *   - prompt (string, optionnel) : prompt pour la génération (ex. Suno).
 *   - style (string, optionnel) : style musical.
 *
 * Response 201 : { "id": <id de la CourseMusic> }
 * Response 400 : { "error": "..." }  (body invalide ou subchapterId manquant)
 * Response 404 : { "error": "Sous-chapitre introuvable." }
 *
 * Exemple : POST /api/course-music  { "subchapterId": 42, "title": "Intro", "prompt": "...", "style": "pop" }
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
     * Body : subchapterId (requis), title, prompt, style (optionnels). 201 : { "id" }. 400/404 : { "error" }.
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
