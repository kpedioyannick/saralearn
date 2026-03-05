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
            ->addOption('dry-run', null, InputOption::VALUE_NONE, 'Affiche ce qui serait fait sans appeler Suno')
            ->addOption('video-id', null, InputOption::VALUE_OPTIONAL, 'Si renseigné, ne fait que récupérer le lien vidéo pour cet id Suno et s’arrête');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);

        $videoId = $input->getOption('video-id');
        if (is_string($videoId) && $videoId !== '') {
            return $this->handleVideoStatus($videoId, $io);
        }

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

        if ($dryRun) {
            $io->note('Mode dry-run : aucun appel HTTP à Suno.');
            foreach ($toProcess as $cm) {
                \assert($cm instanceof CourseMusic);
                $io->text(sprintf(
                    '  - id=%d, subchapter=%d, title="%s", prompt=%d caractères (sunoTaskId=%s, audioUrl=%s)',
                    $cm->getId(),
                    $cm->getSubchapter()?->getId() ?? 0,
                    (string) $cm->getTitle(),
                    mb_strlen((string) $cm->getPrompt()),
                    $cm->getSunoTaskId() ?? 'null',
                    $cm->getAudioUrl() ?? 'null',
                ));
            }
            return Command::SUCCESS;
        }

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
                $clipId = $generation['clip_ids'][0];

                $courseMusic->setSunoTaskId($taskId);
                $this->entityManager->flush();

                $io->text(sprintf('   task_id=%s, clip_id=%s', $taskId, $clipId));

                $this->waitForCompletion($courseMusic, $clipId, $io);
                $this->entityManager->flush();

                $io->success('OK : audioUrl mis à jour.');
                $success++;
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
                return;
            }

            if ($state === 'blocked' || $state === 'failed' || $state === 'error') {
                throw new \RuntimeException(sprintf('Suno clip status=%s', $state));
            }

            sleep(self::POLL_INTERVAL_SECONDS);
        }

        throw new \RuntimeException('Timeout attente Suno (clip non terminé).');
    }

    private function handleVideoStatus(string $videoId, SymfonyStyle $io): int
    {
        try {
            $status = $this->sunoStudioClient->getVideoStatus($videoId);
            $io->title(sprintf('Statut vidéo Suno %s', $videoId));
            $io->writeln(sprintf('status: %s', $status['status']));
            $io->writeln(sprintf('video_url: %s', $status['video_url'] ?? 'null'));

            return Command::SUCCESS;
        } catch (\Throwable $e) {
            $io->error(sprintf('Erreur lors de la récupération du statut vidéo : %s', $e->getMessage()));
            return Command::FAILURE;
        }
    }
}

