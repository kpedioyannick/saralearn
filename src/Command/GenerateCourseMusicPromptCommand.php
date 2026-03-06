<?php

declare(strict_types=1);

namespace App\Command;

use App\Repository\SubchapterRepository;
use App\Service\Suno\CourseMusicPromptGenerator;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:generate-course-music-prompt',
    description: 'Génère le prompt (paroles slam) et le style pour la musique du cours via le provider curl, et sauvegarde dans CourseMusic (PROMPT.md).',
)]
final class GenerateCourseMusicPromptCommand extends Command
{
    public function __construct(
        private readonly SubchapterRepository $subchapterRepository,
        private readonly CourseMusicPromptGenerator $promptGenerator,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addOption('limit', null, InputOption::VALUE_OPTIONAL, 'Nombre max de sous-chapitres (sans CourseMusic), défaut 50', '50');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $limitOpt = $input->getOption('limit');
        $limit = (is_string($limitOpt) && $limitOpt !== '' && ctype_digit($limitOpt)) ? max(1, (int) $limitOpt) : 50;

        $toProcess = $this->subchapterRepository->findWithContextWithoutCourseMusicOrderById($limit);

        if ($toProcess === []) {
            $io->success('Aucun sous-chapitre à traiter (tous ont déjà une CourseMusic).');
            return Command::SUCCESS;
        }

        $io->title(sprintf('Génération prompt slam (style + relevance) : %d sous-chapitre(s)', count($toProcess)));

        $ok = 0;
        foreach ($toProcess as $subchapter) {
            $io->text(sprintf('Prompt : %s…', $subchapter->getTitle()));
            try {
                $this->promptGenerator->createOrUpdatePromptForSubchapter($subchapter);
                $io->text('  → OK');
                $ok++;
            } catch (\Throwable $e) {
                $io->warning(sprintf('  → Erreur : %s', $e->getMessage()));
            }
        }

        $io->success(sprintf('Terminé. %d prompt(s) créé(s) ou mis à jour.', $ok));
        return Command::SUCCESS;
    }
}
