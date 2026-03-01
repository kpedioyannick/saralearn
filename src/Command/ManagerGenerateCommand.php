<?php

declare(strict_types=1);

namespace App\Command;

use App\Entity\Subchapter;
use App\Repository\ModuleRepository;
use App\Repository\PathRepository;
use App\Repository\SubchapterRepository;
use App\Service\InteractiveBook\PathTypePresets;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\ArrayInput;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:manager:generate',
    description: 'Manager : détermine quoi générer (cours, modules, livres) en interrogeant la base, puis lance les commandes par sous-chapitre / preset pour éviter les réponses IA tronquées.',
)]
final class ManagerGenerateCommand extends Command
{
    /** Niveaux Bloom traités par le Manager pour l’instant (remember, understand, apply uniquement). */
    private const BLOOM_LEVELS = ['remember', 'understand', 'apply'];

    public function __construct(
        private readonly SubchapterRepository $subchapterRepository,
        private readonly ModuleRepository $moduleRepository,
        private readonly PathRepository $pathRepository,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this->addOption('dry-run', null, InputOption::VALUE_NONE, 'Ne pas persister (transmis aux commandes appelées)');
        $this->addOption('batch-size', 'b', InputOption::VALUE_REQUIRED, 'Nombre d\'éléments par phase par round (cours, puis modules, puis livres)', '20');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $dryRun = (bool) $input->getOption('dry-run');

        $allSubchapters = array_filter(
            $this->subchapterRepository->findBy([], ['id' => 'ASC']),
            static fn (Subchapter $s) => $s->isCourseType(),
        );
        $subchaptersWithContext = $this->withContext(array_values($allSubchapters));
        if ($subchaptersWithContext === []) {
            $io->warning('Aucun sous-chapitre trouvé (ou aucun avec chapitre/matière/classe).');
            return Command::SUCCESS;
        }

        $batchSize = max(1, (int) $input->getOption('batch-size'));
        $io->title(sprintf('Manager : %d sous-chapitre(s) — lots de %d (cours / modules / livres) par round', count($subchaptersWithContext), $batchSize));

        $baseArgs = [
            '--no-interaction' => true,
            '--filter' => 'subchapter',
        ];
        if ($dryRun) {
            $baseArgs['--dry-run'] = true;
        }
        $argsWithProvider = $baseArgs + ['--provider' => 'deepseek'];
        $exit = Command::SUCCESS;

        $needCourse = $this->subchaptersWithoutCourse($subchaptersWithContext);
        $needModules = $this->subchaptersWithMissingBloomLevels($subchaptersWithContext);
        $needBooks = $this->subchapterPresetsWithoutPath($subchaptersWithContext);
        $totalCourse = count($needCourse);
        $totalModules = count($needModules);
        $totalBooks = count($needBooks);
        $io->text(sprintf('À générer : %d cours, %d modules (sous-chapitres), %d livres.', $totalCourse, $totalModules, $totalBooks));

        $round = 0;
        $offsetCourse = 0;
        $offsetModules = 0;
        $offsetBooks = 0;

        while ($offsetCourse < $totalCourse || $offsetModules < $totalModules || $offsetBooks < $totalBooks) {
            $round++;
            $batchCourse = array_slice($needCourse, $offsetCourse, $batchSize);
            $batchModules = array_slice($needModules, $offsetModules, $batchSize);
            $batchBooks = array_slice($needBooks, $offsetBooks, $batchSize);

            if ($batchCourse === [] && $batchModules === [] && $batchBooks === []) {
                break;
            }

            $io->section(sprintf('Round %d — %d cours, %d modules, %d livres', $round, count($batchCourse), count($batchModules), count($batchBooks)));

            foreach ($batchCourse as $item) {
                $code = $this->runCommand($output, 'app:generate-course-mindmap', $argsWithProvider + [
                    '--classroom' => $item['classroom'],
                    '--subject' => $item['subject'],
                    '--subchapter' => (string) $item['subchapter']->getId(),
                ]);
                if ($code !== Command::SUCCESS) {
                    $exit = $code;
                }
            }
            $offsetCourse += count($batchCourse);

            foreach ($batchModules as $item) {
                $code = $this->runCommand($output, 'app:h5p:generate-modules', $argsWithProvider + [
                    '--classroom' => $item['classroom'],
                    '--subject' => $item['subject'],
                    '--subchapter' => (string) $item['subchapter']->getId(),
                    '--bloom-types' => implode(',', $item['missing_bloom_levels']),
                ]);
                if ($code !== Command::SUCCESS) {
                    $exit = $code;
                }
            }
            $offsetModules += count($batchModules);

            foreach ($batchBooks as $item) {
                $code = $this->runCommand($output, 'app:h5p:generate-interactive-books', $baseArgs + [
                    '--classroom' => $item['classroom'],
                    '--subject' => $item['subject'],
                    '--subchapter' => (string) $item['subchapter']->getId(),
                    '--preset' => $item['preset_key'],
                ]);
                if ($code !== Command::SUCCESS) {
                    $exit = $code;
                }
            }
            $offsetBooks += count($batchBooks);
        }

        $io->success('Manager terminé.');
        return $exit;
    }

    /**
     * Garde uniquement les sous-chapitres ayant chapitre → subject → classroom, avec identifiants pour les commandes.
     *
     * @param list<Subchapter> $subchapters
     * @return list<array{classroom: string, subject: string, subchapter: Subchapter}>
     */
    private function withContext(array $subchapters): array
    {
        $result = [];
        foreach ($subchapters as $subchapter) {
            $chapter = $subchapter->getChapter();
            if ($chapter === null) {
                continue;
            }
            $subject = $chapter->getSubject();
            if ($subject === null) {
                continue;
            }
            $classroom = $subject->getClassroom();
            if ($classroom === null) {
                continue;
            }
            $result[] = [
                'classroom' => $classroom->getSlug() ?? (string) $classroom->getId(),
                'subject' => $subject->getSlug() ?? (string) $subject->getId(),
                'subchapter' => $subchapter,
            ];
        }
        return $result;
    }

    /**
     * Sous-chapitres qui n'ont pas encore de cours (course null ou vide).
     *
     * @param list<array{classroom: string, subject: string, subchapter: Subchapter}> $items
     * @return list<array{classroom: string, subject: string, subchapter: Subchapter}>
     */
    private function subchaptersWithoutCourse(array $items): array
    {
        $out = [];
        foreach ($items as $item) {
            $course = $item['subchapter']->getCourse();
            if ($course === null || !is_array($course) || $course === []) {
                $out[] = $item;
            }
        }
        return $out;
    }

    /**
     * Sous-chapitres avec au moins un niveau Bloom sans aucun module ; chaque entrée contient la liste des niveaux manquants.
     *
     * @param list<array{classroom: string, subject: string, subchapter: Subchapter}> $items
     * @return list<array{classroom: string, subject: string, subchapter: Subchapter, missing_bloom_levels: list<string>}>
     */
    private function subchaptersWithMissingBloomLevels(array $items): array
    {
        $out = [];
        foreach ($items as $item) {
            $subchapter = $item['subchapter'];
            $missing = [];
            foreach (self::BLOOM_LEVELS as $level) {
                $existing = $this->moduleRepository->findBySubchapterAndBloomLevel($subchapter->getId(), $level);
                if ($existing === []) {
                    $missing[] = $level;
                }
            }
            if ($missing !== []) {
                $out[] = $item + ['missing_bloom_levels' => $missing];
            }
        }
        return $out;
    }

    /**
     * Combinaisons (sous-chapitre, preset) pour lesquelles il n'existe pas encore de Path.
     *
     * @param list<array{classroom: string, subject: string, subchapter: Subchapter}> $items
     * @return list<array{classroom: string, subject: string, subchapter: Subchapter, preset_key: string}>
     */
    private function subchapterPresetsWithoutPath(array $items): array
    {
        $out = [];
        $presets = PathTypePresets::presetsForManager(); // remember+understand, understand+apply uniquement
        foreach ($items as $item) {
            $subchapter = $item['subchapter'];
            foreach ($presets as $types) {
                if ($this->pathRepository->findOneBySubchapterAndTypes($subchapter, $types) === null) {
                    $out[] = $item + ['preset_key' => PathTypePresets::key($types)];
                }
            }
        }
        return $out;
    }

    private function runCommand(OutputInterface $output, string $commandName, array $args): int
    {
        $app = $this->getApplication();
        if ($app === null) {
            return Command::FAILURE;
        }
        $command = $app->find($commandName);
        $cmdInput = new ArrayInput($args);
        $cmdInput->setInteractive(false);
        return $command->run($cmdInput, $output);
    }
}
