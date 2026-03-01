<?php

declare(strict_types=1);

namespace App\Command;

use App\Repository\CourseMusicRepository;
use App\Repository\SubchapterRepository;
use App\Service\Suno\CourseMusicGenerator;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:generate-course-music',
    description: 'Génère une musique (Suno) par sous-chapitre pour les cours qui n\'en ont pas encore.',
)]
final class GenerateCourseMusicCommand extends Command
{
    public function __construct(
        private readonly SubchapterRepository $subchapterRepository,
        private readonly CourseMusicRepository $courseMusicRepository,
        private readonly CourseMusicGenerator $courseMusicGenerator,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addOption('subchapter', null, InputOption::VALUE_OPTIONAL, 'ID ou slug d\'un seul sous-chapitre à traiter')
            ->addOption('dry-run', null, InputOption::VALUE_NONE, 'Afficher ce qui serait fait sans appeler Suno');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $subchapterOpt = $input->getOption('subchapter') !== null ? trim((string) $input->getOption('subchapter')) : null;
        $dryRun = (bool) $input->getOption('dry-run');

        if ($subchapterOpt !== null && $subchapterOpt !== '') {
            $subchapter = is_numeric($subchapterOpt)
                ? $this->subchapterRepository->find((int) $subchapterOpt)
                : $this->subchapterRepository->findOneBy(['slug' => $subchapterOpt]);
            if ($subchapter === null) {
                $io->error(sprintf('Sous-chapitre introuvable : %s', $subchapterOpt));
                return Command::FAILURE;
            }
            if (!$subchapter->isCourseType()) {
                $io->error('Seuls les sous-chapitres de type "Cours" sont traités.');
                return Command::FAILURE;
            }
            $subchapters = [$subchapter];
        } else {
            $subchapters = array_values(array_filter(
                $this->subchapterRepository->findBy([], ['id' => 'ASC']),
                static fn (\App\Entity\Subchapter $s) => $s->isCourseType(),
            ));
        }

        // Garder uniquement ceux qui ont un cours (course non vide) et pas encore de musique
        $withCourse = array_filter($subchapters, static function ($s) {
            $c = $s->getCourse();
            return $c !== null && is_array($c) && $c !== [];
        });
        $withMusicIds = $this->courseMusicRepository->getSubchapterIdsWithMusic($withCourse);
        $toProcess = array_values(array_filter($withCourse, static fn ($s) => !isset($withMusicIds[$s->getId()])));

        if ($toProcess === []) {
            $io->success('Aucun sous-chapitre à traiter (tous ont déjà une musique ou pas de cours).');
            return Command::SUCCESS;
        }

        $io->title(sprintf('Génération musique Suno : %d sous-chapitre(s)', count($toProcess)));
        if ($dryRun) {
            $io->note('Mode dry-run : aucun appel à Suno.');
            foreach ($toProcess as $s) {
                $io->text(sprintf('  - %s (id=%d)', $s->getTitle(), $s->getId()));
            }
            return Command::SUCCESS;
        }

        $ok = 0;
        foreach ($toProcess as $subchapter) {
            $io->text(sprintf('Suno : %s…', $subchapter->getTitle()));
            try {
                $this->courseMusicGenerator->generateForSubchapter($subchapter);
                $io->text(sprintf('  → OK'));
                $ok++;
            } catch (\Throwable $e) {
                $io->warning(sprintf('  → Erreur : %s', $e->getMessage()));
            }
        }

        $io->success(sprintf('Terminé. %d musique(s) générée(s).', $ok));
        return Command::SUCCESS;
    }
}
