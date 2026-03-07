<?php

namespace App\Controller;

use App\Entity\Chapter;
use App\Repository\ClassroomRepository;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

class FrontController extends AbstractController
{
    #[Route('/', name: 'app_home')]
    public function index(Request $request, ClassroomRepository $classroomRepository): Response
    {
        // 1. Fetch all classrooms for the horizontal selection row
        $classrooms = $classroomRepository->findAll();
        
        // 2. Determine selected classroom
        $classSlug = $request->query->get('class');
        $currentClassroom = null;
        
        if ($classSlug) {
            $currentClassroom = $classroomRepository->findOneBy(['slug' => $classSlug]);
        }
        
        // Default to first class if none selected or found
        if (!$currentClassroom && count($classrooms) > 0) {
            $currentClassroom = $classrooms[0];
        }

        // 3. Render the OnePage view
        return $this->render('front/index.html.twig', [
            'classrooms' => $classrooms,
            'currentClassroom' => $currentClassroom,
        ]);
    }

    #[Route('/api/chapter/{id}/playlist', name: 'api_chapter_playlist', methods: ['GET'])]
    public function chapterPlaylist(Chapter $chapter): JsonResponse
    {
        $playlist = [];
        
        foreach ($chapter->getSubchapters() as $subchapter) {
            $audioUrl = null;
            $duration = 0;
            
            // Get first course music if available
            $courseMusic = $subchapter->getCourseMusics()->first();
            if ($courseMusic) {
                $audioUrl = $courseMusic->getAudioUrl();
                $duration = $courseMusic->getDuration() ?? 0;
            }

            // Get first module if available
            $moduleId = null;
            $module = $subchapter->getModules()->first();
            if ($module) {
                $moduleId = $module->getId();
            }

            $playlist[] = [
                'id' => $subchapter->getId(),
                'title' => $subchapter->getTitle(),
                'audioUrl' => $audioUrl,
                'duration' => $duration,
                'moduleId' => $moduleId,
            ];
        }

        return $this->json([
            'chapterId' => $chapter->getId(),
            'chapterTitle' => $chapter->getTitle(),
            'chapterSubject' => $chapter->getSubject() ? $chapter->getSubject()->getName() : '',
            'tracks' => $playlist,
        ]);
    }
}
