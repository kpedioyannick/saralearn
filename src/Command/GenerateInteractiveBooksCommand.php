<?php

declare(strict_types=1);

namespace App\Command;

use App\Entity\Path;
use App\Entity\Subject;
use App\Entity\Subchapter;
use App\Repository\ClassroomRepository;
use App\Repository\ModuleRepository;
use App\Repository\PathRepository;
use App\Repository\SubchapterRepository;
use App\Repository\SubjectRepository;
use App\Service\InteractiveBook\InteractiveBookFileGenerator;
use App\Service\InteractiveBook\PathTypePresets;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:h5p:generate-interactive-books',
    description: 'Génère les livres interactifs H5P par sous-chapitre (4 Paths par sous-chapitre : remember+understand, understand+apply, apply+analyze, analyze+evaluate).',
)]
final class GenerateInteractiveBooksCommand extends Command
{
    public const FILTER_CHAPTER = 'chapter';
    public const FILTER_SUBCHAPTER = 'subchapter';

    public function __construct(
        private readonly SubchapterRepository $subchapterRepository,
        private readonly PathRepository $pathRepository,
        private readonly ModuleRepository $moduleRepository,
        private readonly ClassroomRepository $classroomRepository,
        private readonly SubjectRepository $subjectRepository,
        private readonly EntityManagerInterface $entityManager,
        private readonly InteractiveBookFileGenerator $fileGenerator,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addOption('classroom', null, InputOption::VALUE_OPTIONAL, 'Obligatoire pour le cron : ID ou slug de classe')
            ->addOption('subject', null, InputOption::VALUE_OPTIONAL, 'Obligatoire pour le cron : ID ou slug de matière')
            ->addOption('filter', null, InputOption::VALUE_OPTIONAL, 'Obligatoire pour le cron : chapter ou subchapter (charge les chapitres ou les sous-chapitres)')
            ->addOption('subchapter', null, InputOption::VALUE_OPTIONAL, 'ID ou slug du sous-chapitre (traiter un seul sous-chapitre)')
            ->addOption('preset', null, InputOption::VALUE_OPTIONAL, 'Un seul preset à traiter (ex. remember,understand ou analyze,evaluate). Défaut : tous.')
            ->addOption('limit', null, InputOption::VALUE_OPTIONAL, 'Limiter le nombre de sous-chapitres à traiter')
            ->addOption('dry-run', null, InputOption::VALUE_NONE, 'Ne pas créer les Paths ni écrire les fichiers');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $classroomOpt = $input->getOption('classroom');
        $subjectOpt = $input->getOption('subject');
        $filterOpt = $input->getOption('filter') !== null ? trim((string) $input->getOption('filter')) : null;
        $subchapterId = $input->getOption('subchapter');
        $presetOpt = $input->getOption('preset') !== null ? trim((string) $input->getOption('preset')) : null;
        $limit = $input->getOption('limit') !== null ? (int) $input->getOption('limit') : null;
        $dryRun = (bool) $input->getOption('dry-run');

        $presetsToUse = $this->resolvePresets($presetOpt, $io);
        if ($presetsToUse === null) {
            return Command::FAILURE;
        }

        if ($classroomOpt !== null && $classroomOpt !== '' || $subjectOpt !== null && $subjectOpt !== '') {
            if ($classroomOpt === null || $classroomOpt === '' || $subjectOpt === null || $subjectOpt === '') {
                $io->error('Pour le cron, indiquez --classroom, --subject et --filter (chapter|subchapter) ensemble.');
                return Command::FAILURE;
            }
            $filter = strtolower($filterOpt ?? '');
            if ($filter !== self::FILTER_CHAPTER && $filter !== self::FILTER_SUBCHAPTER) {
                $io->error('Option --filter doit être "chapter" ou "subchapter".');
                return Command::FAILURE;
            }
            $classroom = $this->classroomRepository->resolveOne($classroomOpt);
            if ($classroom === null) {
                $io->error(sprintf('Classe introuvable : %s', $classroomOpt));
                return Command::FAILURE;
            }
            $subject = $this->subjectRepository->findOneByClassroomAndSubject($classroom, $subjectOpt);
            if ($subject === null) {
                $io->error(sprintf('Matière introuvable pour la classe : %s', $subjectOpt));
                return Command::FAILURE;
            }
            $subchapters = $filter === self::FILTER_CHAPTER
                ? $this->resolveSubchaptersFromChapters($subject, $limit)
                : $this->resolveSubchaptersFromSubject($subject, $limit);
        } else {
            $subchapters = $this->resolveSubchapters($subchapterId, $limit);
        }

        if ($subchapters === []) {
            $io->warning('Aucun sous-chapitre trouvé.');
            return Command::SUCCESS;
        }

        $pathsCreated = 0;
        $filesWritten = 0;

        foreach ($subchapters as $subchapter) {
            $chapter = $subchapter->getChapter();
            if ($chapter === null) {
                continue;
            }
            foreach ($presetsToUse as $types) {
                $path = $this->pathRepository->findOneBySubchapterAndTypes($subchapter, $types);
                if ($path === null && !$dryRun) {
                    $path = $this->createPath($subchapter, $chapter, $types);
                    $this->entityManager->persist($path);
                    $this->entityManager->flush();
                    $pathsCreated++;
                }
                if ($path === null) {
                    continue;
                }

                $modules = $this->moduleRepository->findBySubchapterAndBloomLevels(
                    $subchapter->getId(),
                    $path->getBloomLevels(),
                );
                if ($modules === []) {
                    $io->text(sprintf('  [skip] %s / %s : aucun module.', $subchapter->getTitle(), PathTypePresets::label($types)));
                    continue;
                }

                if (!$dryRun) {
                    $contentJson = $this->fileGenerator->buildContentJson($path, $modules);
                    $title = sprintf('%s - %s', $subchapter->getTitle(), PathTypePresets::label($types));
                    $h5pJson = $this->fileGenerator->buildH5pJson($title);
                    $this->fileGenerator->writeToDirectory($path, $contentJson, $h5pJson);
                    $outputPath = $this->fileGenerator->getDirectoryForPath($path);
                    $path->setOutputPath($outputPath);
                    $filesWritten++;
                }
            }
        }

        if (!$dryRun) {
            $this->entityManager->flush();
        }

        $io->success([
            $dryRun ? '[DRY-RUN] Aucune écriture.' : 'Génération terminée.',
            sprintf('Sous-chapitres traités : %d', count($subchapters)),
            sprintf('Paths créés : %d', $pathsCreated),
            sprintf('Fichiers écrits : %d', $dryRun ? 0 : $filesWritten),
        ]);

        return Command::SUCCESS;
    }

    /**
     * @return list<list<string>>|null null en cas d'erreur (preset invalide)
     */
    private function resolvePresets(?string $presetOpt, SymfonyStyle $io): ?array
    {
        if ($presetOpt === null || $presetOpt === '') {
            return PathTypePresets::all();
        }
        $preset = PathTypePresets::getByKey($presetOpt);
        if ($preset === null) {
            $valid = array_map(static fn (array $t) => PathTypePresets::key($t), PathTypePresets::all());
            $io->error(sprintf('Preset invalide "%s". Valeurs acceptées : %s', $presetOpt, implode(', ', $valid)));
            return null;
        }
        return [$preset];
    }

    /**
     * @return list<Subchapter>
     */
    private function resolveSubchapters(?string $subchapterId, ?int $limit): array
    {
        if ($subchapterId !== null && $subchapterId !== '') {
            $sub = is_numeric($subchapterId)
                ? $this->subchapterRepository->find((int) $subchapterId)
                : $this->subchapterRepository->findOneBy(['slug' => $subchapterId]);
            if ($sub === null || !$sub->isCourseType()) {
                return [];
            }
            return [$sub];
        }
        $all = array_values(array_filter(
            $this->subchapterRepository->findBy([], ['id' => 'ASC'], $limit),
            static fn (Subchapter $s) => $s->isCourseType(),
        ));
        return $all;
    }

    /**
     * filter=chapter : charge les chapitres de la matière, puis les sous-chapitres de chaque chapitre.
     * @return list<Subchapter>
     */
    private function resolveSubchaptersFromChapters(Subject $subject, ?int $limit): array
    {
        $list = [];
        foreach ($subject->getChapters() as $chapter) {
            foreach ($chapter->getSubchapters() as $subchapter) {
                if (!$subchapter->isCourseType()) {
                    continue;
                }
                $list[] = $subchapter;
                if ($limit !== null && count($list) >= $limit) {
                    return $list;
                }
            }
        }
        return $list;
    }

    /**
     * filter=subchapter : charge tous les sous-chapitres de la matière (liste plate).
     * @return list<Subchapter>
     */
    private function resolveSubchaptersFromSubject(Subject $subject, ?int $limit): array
    {
        $all = array_values(array_filter(
            $this->subchapterRepository->findBySubject($subject),
            static fn (Subchapter $s) => $s->isCourseType(),
        ));
        if ($limit === null) {
            return $all;
        }
        return array_slice($all, 0, $limit);
    }

    private function createPath(Subchapter $subchapter, \App\Entity\Chapter $chapter, array $types): Path
    {
        $path = new Path();
        $path->setCategory(Path::CATEGORY_H5P_INTERACTIVE_BOOK);
        $path->setChapter($chapter);
        $path->setSubchapter($subchapter);
        $path->setTypes($types);
        $path->setTitle(sprintf('%s - %s', $subchapter->getTitle(), PathTypePresets::label($types)));
        $path->setOutputPath(''); // sera mis à jour après writeToDirectory
        return $path;
    }
}
