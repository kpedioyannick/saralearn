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
    private const BLOOM_LEVELS = ['remember', 'understand', 'apply', 'analyze', 'evaluate'];

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

        $io->title(sprintf('Manager : %d sous-chapitre(s) — ne lance que ce qui manque', count($subchaptersWithContext)));

        $baseArgs = [
            '--no-interaction' => true,
            '--filter' => 'subchapter',
        ];
        if ($dryRun) {
            $baseArgs['--dry-run'] = true;
        }
        $exit = Command::SUCCESS;

        // Phase 1 : cours — uniquement les sous-chapitres sans cours
        $needCourse = $this->subchaptersWithoutCourse($subchaptersWithContext);
        $io->section(sprintf('Phase 1 : Cours (Reveal.js + mindmap) — %d à générer', count($needCourse)));
        foreach ($needCourse as $item) {
            $code = $this->runCommand($output, 'app:generate-course-mindmap', $baseArgs + [
                '--classroom' => $item['classroom'],
                '--subject' => $item['subject'],
                '--subchapter' => (string) $item['subchapter']->getId(),
            ]);
            if ($code !== Command::SUCCESS) {
                $exit = $code;
            }
        }

        // Phase 2 : modules — par sous-chapitre, uniquement les niveaux Bloom qui n'ont pas encore de module
        $needModules = $this->subchaptersWithMissingBloomLevels($subchaptersWithContext);
        $io->section(sprintf('Phase 2 : Modules H5P — %d sous-chapitre(s) avec niveaux Bloom manquants', count($needModules)));
        foreach ($needModules as $item) {
            $code = $this->runCommand($output, 'app:h5p:generate-modules', $baseArgs + [
                '--classroom' => $item['classroom'],
                '--subject' => $item['subject'],
                '--subchapter' => (string) $item['subchapter']->getId(),
                '--bloom-types' => implode(',', $item['missing_bloom_levels']),
            ]);
            if ($code !== Command::SUCCESS) {
                $exit = $code;
            }
        }

        // Phase 3 : livres interactifs — uniquement (sous-chapitre, preset) sans Path
        $needBooks = $this->subchapterPresetsWithoutPath($subchaptersWithContext);
        $io->section(sprintf('Phase 3 : Livres interactifs — %d combinaison(s) à générer', count($needBooks)));
        foreach ($needBooks as $item) {
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
        $presets = PathTypePresets::all();
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
