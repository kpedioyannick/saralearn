<?php

declare(strict_types=1);

namespace App\Controller\Api;

use App\Entity\Module;
use App\Repository\SubchapterRepository;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

/**
 * API pour gérer les modules H5P "experts" (ou "avancés") en fonction des priorités.
 */
#[Route('/api/expert-modules')]
final class ExpertModuleApiController extends AbstractController
{
    public function __construct(
        private readonly SubchapterRepository $subchapterRepository,
        private readonly EntityManagerInterface $entityManager
    ) {
    }

    /**
     * Retourne les sous-chapitres candidats pour avoir des modules "expert".
     * Classes = high, Matières != low, sans module expert.
     * Body : { "number": 10 }
     */
    #[Route('/candidates', name: 'api_expert_modules_candidates', methods: ['POST'])]
    public function getCandidates(Request $request): JsonResponse
    {
        $body = json_decode((string) $request->getContent(), true);
        $number = isset($body['number']) && is_numeric($body['number']) ? max(1, min(500, (int) $body['number'])) : 50;

        $subchapters = $this->subchapterRepository->findPriorityCandidatesForExpertModules($number);
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
     * Sauvegarde un ou plusieurs modules H5P (de difficulté 'expert') pour un sous-chapitre.
     * Body : { "subchapterId": 123, "modules": [ { "title": "M1", "bloomLevel": "analyze", "h5pType": "H5P.MultiChoice", "content": "..." } ] }
     */
    #[Route('/save', name: 'api_expert_modules_save', methods: ['POST'])]
    public function saveExpertModules(Request $request): JsonResponse
    {
        $body = json_decode((string) $request->getContent(), true);
        if (!is_array($body)) {
            return $this->json(['error' => 'Body JSON invalide.'], Response::HTTP_BAD_REQUEST);
        }

        $subchapterId = $body['subchapterId'] ?? null;
        if ($subchapterId === null || !is_numeric($subchapterId)) {
            return $this->json(['error' => 'subchapterId requis.'], Response::HTTP_BAD_REQUEST);
        }

        $subchapter = $this->subchapterRepository->find((int) $subchapterId);
        if ($subchapter === null) {
            return $this->json(['error' => 'Sous-chapitre introuvable.'], Response::HTTP_NOT_FOUND);
        }

        $modulesData = $body['modules'] ?? [];
        if (!is_array($modulesData)) {
            return $this->json(['error' => 'La clé modules doit être un tableau.'], Response::HTTP_BAD_REQUEST);
        }

        $chapter = $subchapter->getChapter();
        $createdCount = 0;

        foreach ($modulesData as $m) {
            if (!isset($m['content'], $m['h5pType'], $m['bloomLevel'], $m['title'])) {
                continue; // Skip invalid module definitions
            }

            $module = new Module();
            $module->setSubchapter($subchapter);
            $module->setChapter($chapter);
            $module->setTitle($m['title']);
            $module->setBloomLevel($m['bloomLevel']);
            $module->setDifficulty('expert'); // Forced to expert
            $module->setH5pType($m['h5pType']);
            
            // Content can be an array in JSON payload or a stringized JSON
            $content = is_array($m['content']) ? json_encode($m['content']) : $m['content'];
            $module->setContent($content);

            $this->entityManager->persist($module);
            $createdCount++;
        }

        $this->entityManager->flush();

        return $this->json(['success' => true, 'createdCount' => $createdCount], Response::HTTP_CREATED);
    }
}
