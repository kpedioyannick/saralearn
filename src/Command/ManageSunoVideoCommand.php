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
    name: 'app:manage-suno-video',
    description: 'Trouve les CourseMusic avec sunoClipId mais sans videoUrl, appelle getVideoStatus pour chacune et met à jour videoUrl.',
)]
final class ManageSunoVideoCommand extends Command
{
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
            ->addOption('limit', null, InputOption::VALUE_OPTIONAL, 'Nombre maximum de CourseMusic à traiter', '500')
            ->addOption('dry-run', null, InputOption::VALUE_NONE, 'Affiche la liste sans appeler getVideoStatus');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);

        $limit = $input->getOption('limit');
        $limitValue = (is_string($limit) && $limit !== '' && ctype_digit($limit)) ? max(1, (int) $limit) : 500;
        $dryRun = (bool) $input->getOption('dry-run');

        $toProcess = $this->courseMusicRepository->findWithClipIdWithoutVideo($limitValue);

        if ($toProcess === []) {
            $io->success('Aucune CourseMusic à traiter (toutes ont déjà une videoUrl ou pas de sunoClipId).');
            return Command::SUCCESS;
        }

        $io->title(sprintf('Suno video (getVideoStatus) : %d CourseMusic avec clip sans video', count($toProcess)));

        if ($dryRun) {
            $io->note('Mode dry-run : aucun appel à getVideoStatus.');
            foreach ($toProcess as $cm) {
                \assert($cm instanceof CourseMusic);
                $io->text(sprintf(
                    '  - id=%d, sunoClipId=%s',
                    $cm->getId(),
                    $cm->getSunoClipId() ?? '',
                ));
            }
            return Command::SUCCESS;
        }

        $ok = 0;
        foreach ($toProcess as $courseMusic) {
            \assert($courseMusic instanceof CourseMusic);
            $clipId = $courseMusic->getSunoClipId();
            if ($clipId === null || $clipId === '') {
                continue;
            }

            $io->section(sprintf('CourseMusic #%d → getVideoStatus(%s)', $courseMusic->getId(), $clipId));

            try {
                $status = $this->sunoStudioClient->getVideoStatus($clipId);
                $state = $status['status'] ?? 'unknown';
                $videoUrl = $status['video_url'] ?? null;

                $io->text(sprintf('   status: %s', $state));
                $io->text(sprintf('   video_url: %s', $videoUrl ?? 'null'));

                if ($state === 'complete' && $videoUrl !== null && $videoUrl !== '') {
                    $courseMusic->setVideoUrl($videoUrl);
                    $this->entityManager->flush();
                    $io->success(sprintf('   videoUrl enregistré : %s', $videoUrl));
                    $ok++;
                } else {
                    $io->text('   getVideoStatus sans URL → essai getClipStatus (feed v3)');
                    $clipStatus = $this->sunoStudioClient->getClipStatus($clipId);
                    $videoUrl = $clipStatus['video_url'] ?? null;
                    if ($videoUrl !== null && $videoUrl !== '') {
                        $courseMusic->setVideoUrl($videoUrl);
                        $this->entityManager->flush();
                        $io->success(sprintf('   videoUrl enregistré : %s', $videoUrl));
                        $ok++;
                    }
                }
            } catch (\Throwable $e) {
                $io->warning(sprintf('   getVideoStatus: %s', $e->getMessage()));
                $io->text('   → essai getClipStatus (feed v3)');
                try {
                    $clipStatus = $this->sunoStudioClient->getClipStatus($clipId);
                    $videoUrl = $clipStatus['video_url'] ?? null;
                    if ($videoUrl !== null && $videoUrl !== '') {
                        $courseMusic->setVideoUrl($videoUrl);
                        $this->entityManager->flush();
                        $io->success(sprintf('   videoUrl enregistré (feed v3) : %s', $videoUrl));
                        $ok++;
                    } else {
                        $io->text(sprintf('   feed v3 video_url: %s', $videoUrl ?? 'null'));
                    }
                } catch (\Throwable $e2) {
                    $io->error(sprintf('   %s', $e2->getMessage()));
                }
            }
        }

        $io->success(sprintf('Terminé. %d videoUrl mis à jour.', $ok));
        return Command::SUCCESS;
    }
}
