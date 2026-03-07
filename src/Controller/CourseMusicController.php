<?php

declare(strict_types=1);

namespace App\Controller;

use App\Repository\CourseMusicRepository;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

#[Route('/course-music')]
final class CourseMusicController extends AbstractController
{
    public function __construct(
        private readonly CourseMusicRepository $courseMusicRepository,
        private readonly EntityManagerInterface $entityManager,
    ) {
    }

    #[Route('', name: 'app_course_music_list', methods: ['GET'])]
    public function list(Request $request): Response
    {
        $activeFilter = $request->query->get('active');
        if ($activeFilter !== null && $activeFilter !== 'active' && $activeFilter !== 'disabled') {
            $activeFilter = null;
        }

        $items = $this->courseMusicRepository->findAllOrdered($activeFilter);

        return $this->render('course_music/list.html.twig', [
            'course_musics' => $items,
            'active_filter' => $activeFilter,
        ]);
    }

    #[Route('/{id}/edit', name: 'app_course_music_edit', requirements: ['id' => '\d+'], methods: ['POST'])]
    public function edit(int $id, Request $request): Response
    {
        $courseMusic = $this->courseMusicRepository->find($id);
        if ($courseMusic === null) {
            $this->addFlash('error', 'CourseMusic introuvable.');
            return $this->redirectToRoute('app_course_music_list');
        }

        $prompt = $request->request->get('prompt');
        $style = $request->request->get('style');
        $active = $request->request->get('active');

        if ($prompt !== null) {
            $courseMusic->setPrompt(is_string($prompt) ? $prompt : null);
        }
        if ($style !== null) {
            $courseMusic->setStyle(is_string($style) ? $style : null);
        }
        if ($active !== null) {
            $v = is_string($active) ? trim($active) : '';
            $courseMusic->setActive($v === 'active' || $v === 'disabled' ? $v : null);
        }

        $this->entityManager->flush();
        $this->addFlash('success', sprintf('CourseMusic #%d mis à jour.', $id));

        $filter = $request->request->get('filter');
        $params = ($filter === 'active' || $filter === 'disabled') ? ['active' => $filter] : [];

        return $this->redirectToRoute('app_course_music_list', $params);
    }
}
