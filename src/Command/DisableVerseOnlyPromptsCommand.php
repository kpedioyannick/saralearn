<?php

declare(strict_types=1);

namespace App\Command;

use App\Repository\CourseMusicRepository;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:course-music:disable-verse-only',
    description: 'Désactive les CourseMusic dont le prompt commence par [Verse] (sans texte avant).',
)]
final class DisableVerseOnlyPromptsCommand extends Command
{
    private const PREFIX = '[Verse]';

    public function __construct(
        private readonly CourseMusicRepository $courseMusicRepository,
        private readonly EntityManagerInterface $entityManager,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this->addOption('dry-run', null, InputOption::VALUE_NONE, 'Afficher les entrées concernées sans modifier la base');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $dryRun = (bool) $input->getOption('dry-run');

        $items = $this->courseMusicRepository->findWherePromptStartsWith(self::PREFIX);

        if ($items === []) {
            $io->success('Aucun CourseMusic dont le prompt commence par "[Verse]".');
            return Command::SUCCESS;
        }

        $io->section(sprintf('CourseMusic dont le prompt commence par "%s" : %d', self::PREFIX, count($items)));

        if ($dryRun) {
            $rows = [];
            foreach ($items as $cm) {
                $sub = $cm->getSubchapter();
                $ch = $sub?->getChapter();
                $subject = $ch?->getSubject();
                $classroom = $subject?->getClassroom();
                $rows[] = [
                    $cm->getId(),
                    $classroom?->getName() ?? '—',
                    $subject?->getName() ?? '—',
                    (mb_strlen($p = $cm->getPrompt() ?? '') > 60 ? mb_substr($p, 0, 60) . '…' : $p),
                ];
            }
            $io->table(['ID', 'Classe', 'Matière', 'Début du prompt'], $rows);
            $io->note('Mode dry-run : aucune modification. Relancez sans --dry-run pour désactiver.');
            return Command::SUCCESS;
        }

        foreach ($items as $cm) {
            $cm->setActive('disabled');
        }
        $this->entityManager->flush();

        $io->success(sprintf('%d CourseMusic désactivé(s) (active = disabled).', count($items)));
        return Command::SUCCESS;
    }
}
