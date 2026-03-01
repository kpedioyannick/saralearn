<?php

declare(strict_types=1);

namespace App\Controller;

use App\Entity\Chapter;
use App\Entity\Subchapter;
use App\Repository\ChapterRepository;
use App\Repository\SubchapterRepository;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

/**
 * Route pour afficher le cours avec Reveal.js.
 * GET /reveal/{type}/{id} avec type = chapter|subchapter et id = ID de l'entité.
 */
#[Route('/reveal')]
final class RevealController extends AbstractController
{
    public const TYPE_CHAPTER = 'chapter';
    public const TYPE_SUBCHAPTER = 'subchapter';

    public function __construct(
        private readonly ChapterRepository $chapterRepository,
        private readonly SubchapterRepository $subchapterRepository,
    ) {
    }

    #[Route('/{type}/{id}', name: 'app_reveal_show', requirements: ['type' => 'chapter|subchapter', 'id' => '\d+'], methods: ['GET'])]
    public function show(string $type, int $id): Response
    {
        $entity = $this->resolveEntity($type, $id);
        if ($entity === null) {
            throw $this->createNotFoundException(sprintf('Aucun %s trouvé pour l\'id %d.', $type, $id));
        }

        $course = $entity->getCourse();
        if (!is_array($course) || empty($course['slides'])) {
            return $this->render('reveal/empty.html.twig', [
                'title' => $entity instanceof Chapter ? $entity->getTitle() : $entity->getTitle(),
                'message' => 'Aucun cours Reveal.js généré pour cet élément. Exécutez app:generate-course-mindmap.',
            ]);
        }

        return $this->render('reveal/show.html.twig', [
            'title' => $course['title'] ?? ($entity instanceof Chapter ? $entity->getTitle() : $entity->getTitle()),
            'description' => $course['description'] ?? '',
            'slides' => $course['slides'],
        ]);
    }

    private function resolveEntity(string $type, int $id): Chapter|Subchapter|null
    {
        return match ($type) {
            self::TYPE_CHAPTER => $this->chapterRepository->find($id),
            self::TYPE_SUBCHAPTER => $this->subchapterRepository->find($id),
            default => null,
        };
    }
}
