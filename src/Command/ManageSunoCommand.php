<?php

declare(strict_types=1);

namespace App\Command;

use App\Entity\CourseMusic;
use App\Repository\CourseMusicRepository;
use App\Service\Suno\SunoStudioClient;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:manage-suno',
    description: 'Appelle l’API Suno (studio) pour les CourseMusic avec prompt mais sans audio, puis met à jour la BDD.',
)]
final class ManageSunoCommand extends Command
{
    private const POLL_INTERVAL_SECONDS = 15;
    private const MAX_WAIT_SECONDS = 600;

    public function __construct(
        private readonly CourseMusicRepository $courseMusicRepository,
        private readonly SunoStudioClient $sunoStudioClient,
        private readonly EntityManagerInterface $entityManager,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addOption('limit', null, InputOption::VALUE_OPTIONAL, 'Nombre maximum de CourseMusic à traiter', null)
            ->addOption('dry-run', null, InputOption::VALUE_NONE, 'Affiche ce qui serait fait sans appeler Suno');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);


        $dryRun = (bool) $input->getOption('dry-run');
        $limit = $input->getOption('limit');
        $limitValue = null;
        if ($limit !== null && $limit !== '') {
            $limitValue = max(1, (int) $limit);
        }

        $toProcess = $this->courseMusicRepository->findNeedingSunoGeneration();
        if ($limitValue !== null) {
            $toProcess = \array_slice($toProcess, 0, $limitValue);
        }

        if ($toProcess === []) {
            $io->success('Aucune CourseMusic à traiter (toutes ont déjà un sunoTaskId et une audioUrl).');
            return Command::SUCCESS;
        }

        $io->title(sprintf('Gestion Suno (studio) : %d CourseMusic à traiter', count($toProcess)));



        $success = 0;
        foreach ($toProcess as $courseMusic) {
            \assert($courseMusic instanceof CourseMusic);
            $io->section(sprintf(
                'CourseMusic #%d (subchapter=%d)',
                $courseMusic->getId(),
                $courseMusic->getSubchapter()?->getId() ?? 0,
            ));

            $prompt = (string) $courseMusic->getPrompt();
            $style = $courseMusic->getStyle();
            $title = $courseMusic->getTitle();

            try {
                $io->text('→ Appel Suno generate (v2-web)…');
                $generation = $this->sunoStudioClient->createSong($prompt, $style, $title);
                $taskId = $generation['task_id'];
                $clipIds = $generation['clip_ids'];
                if ($clipIds === []) {
                    throw new \RuntimeException('Aucun clip retourné par Suno.');
                }

                $io->text(sprintf('   task_id=%s, %d clip(s): %s', $taskId, count($clipIds), implode(', ', $clipIds)));

                foreach ($clipIds as $index => $clipId) {
                    $cm = $index === 0
                        ? $courseMusic
                        : $this->createCourseMusicForClip($courseMusic, $taskId, $clipId, $prompt, $title, $style);
                    $cm->setSunoTaskId($taskId);
                    $cm->setSunoClipId($clipId);
                    $this->entityManager->flush();
                    $io->text(sprintf('   Clip %d/%d (%s)…', $index + 1, count($clipIds), $clipId));
                    $this->waitForCompletion($cm, $clipId, $io);
                    $success++;
                }
                $this->entityManager->flush();
                $io->success(sprintf('OK : %d CourseMusic (audioUrl/cover/video) mises à jour.', count($clipIds)));
            } catch (\Throwable $e) {
                $io->error(sprintf('Erreur Suno pour CourseMusic #%d : %s', $courseMusic->getId(), $e->getMessage()));
            }
        }

        $io->success(sprintf('Terminé. %d CourseMusic mises à jour.', $success));

        return Command::SUCCESS;
    }

    private function waitForCompletion(CourseMusic $courseMusic, string $clipId, SymfonyStyle $io): void
    {
        $deadline = time() + self::MAX_WAIT_SECONDS;

        while (time() < $deadline) {
            $status = $this->sunoStudioClient->getClipStatus($clipId);
            $state = $status['status'];
            $audioUrl = $status['audio_url'];
            $duration = $status['duration'];

            $io->text(sprintf('   Statut clip=%s', $state));

            if ($state === 'complete') {
                $courseMusic->setAudioUrl($audioUrl);
                if ($duration !== null) {
                    $courseMusic->setDuration($duration);
                }
                $coverUrl = $status['cover_url'] ?? null;
                if ($coverUrl !== null && $coverUrl !== '') {
                    $courseMusic->setCoverUrl($coverUrl);
                }
                $this->handleVideoStatus($clipId, $courseMusic, $io);
                return;
            }

            if ($state === 'blocked' || $state === 'failed' || $state === 'error') {
                throw new \RuntimeException(sprintf('Suno clip status=%s', $state));
            }

            sleep(self::POLL_INTERVAL_SECONDS);
        }

        throw new \RuntimeException('Timeout attente Suno (clip non terminé).');
    }

    /**
     * Crée une nouvelle CourseMusic pour un clip additionnel (même subchapter, task_id, prompt/title/style).
     */
    private function createCourseMusicForClip(CourseMusic $template, string $taskId, string $clipId, string $prompt, ?string $title, ?string $style): CourseMusic
    {
        $subchapter = $template->getSubchapter();
        if ($subchapter === null) {
            throw new \RuntimeException('Subchapter manquant sur la CourseMusic source.');
        }
        $newCm = new CourseMusic();
        $newCm->setSubchapter($subchapter);
        $newCm->setPrompt($prompt);
        $newCm->setTitle($title);
        $newCm->setStyle($style);
        $newCm->setSunoTaskId($taskId);
        $newCm->setSunoClipId($clipId);
        if ($template->getRelevance() !== null) {
            $newCm->setRelevance($template->getRelevance());
        }
        $subchapter->addCourseMusic($newCm);
        $this->entityManager->persist($newCm);
        return $newCm;
    }

    private function handleVideoStatus(string $videoId, CourseMusic $courseMusic, SymfonyStyle $io): void
    {
        try {
            $status = $this->sunoStudioClient->getVideoStatus($videoId);
            if (($status['status'] ?? '') === 'complete') {
                $url = $status['video_url'] ?? null;
                if ($url !== null && $url !== '') {
                    $courseMusic->setVideoUrl($url);
                }
            }
        } catch (\Throwable $e) {
            $io->warning(sprintf('   getVideoStatus: %s', $e->getMessage()));
        }
    }
}

