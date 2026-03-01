<?php

declare(strict_types=1);

namespace App\Command;

use App\Entity\Chapter;
use App\Entity\Classroom;
use App\Entity\Subchapter;
use App\Entity\Subject;
use App\Repository\ChapterRepository;
use App\Repository\ClassroomRepository;
use App\Repository\SubchapterRepository;
use App\Repository\SubjectRepository;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;
use Symfony\Component\Filesystem\Path;
use Symfony\Component\String\Slugger\SluggerInterface;

#[AsCommand(
    name: 'app:import:school-data',
    description: 'Importe le programme scolaire depuis school_data.json (levels → Classroom, Subject, Chapter, Subchapter).',
)]
final class ImportSchoolDataCommand extends Command
{
    public function __construct(
        private readonly ClassroomRepository $classroomRepository,
        private readonly SubjectRepository $subjectRepository,
        private readonly ChapterRepository $chapterRepository,
        private readonly SubchapterRepository $subchapterRepository,
        private readonly EntityManagerInterface $entityManager,
        private readonly SluggerInterface $slugger,
        #[Autowire('%kernel.project_dir%')]
        private readonly string $projectDir,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addOption('country', null, InputOption::VALUE_OPTIONAL, 'Code pays (filtre)', 'fr')
            ->addOption('file', null, InputOption::VALUE_OPTIONAL, 'Chemin vers le fichier JSON', 'CDC/school_data.json')
            ->addOption('dry-run', null, InputOption::VALUE_NONE, 'Ne pas écrire en base, afficher les opérations');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $country = (string) $input->getOption('country');
        $fileOption = (string) $input->getOption('file');
        $dryRun = (bool) $input->getOption('dry-run');

        $filePath = Path::isAbsolute($fileOption)
            ? $fileOption
            : Path::join($this->projectDir, $fileOption);

        if (!is_readable($filePath)) {
            $io->error(sprintf('Fichier non trouvé ou illisible : %s', $filePath));
            return Command::FAILURE;
        }

        $content = file_get_contents($filePath);
        if ($content === false) {
            $io->error('Impossible de lire le fichier.');
            return Command::FAILURE;
        }

        $data = json_decode($content, true, 512, \JSON_THROW_ON_ERROR);
        $levels = $data['levels'] ?? null;
        if (!is_array($levels)) {
            $io->error('Clé "levels" absente ou invalide dans le JSON.');
            return Command::FAILURE;
        }

        $stats = ['classrooms' => 0, 'subjects' => 0, 'chapters' => 0, 'subchapters' => 0];
        $seenSubSlugsByChapterKey = [];

        foreach ($levels as $cycle => $classroomsData) {
            if (!is_array($classroomsData)) {
                continue;
            }
            foreach ($classroomsData as $classroomData) {
                $name = $classroomData['name'] ?? null;
                $subjectsData = $classroomData['subjects'] ?? [];
                if (!is_string($name) || $name === '' || !is_array($subjectsData)) {
                    continue;
                }

                $slug = $this->normalizeSlug($name);
                $classroom = $this->classroomRepository->findOneByCycleAndSlug($cycle, $slug);
                if ($classroom === null) {
                    $classroom = new Classroom();
                    $classroom->setCycle($cycle);
                    $classroom->setName($name);
                    $classroom->setSlug($slug);
                    if (!$dryRun) {
                        $this->entityManager->persist($classroom);
                    }
                    $stats['classrooms']++;
                }

                foreach ($subjectsData as $subjectData) {
                    $subjectName = $subjectData['name'] ?? null;
                    $subjectSlug = isset($subjectData['slug']) ? (string) $subjectData['slug'] : $this->normalizeSlug((string) $subjectName);
                    $chaptersData = $subjectData['chapters'] ?? [];
                    if (!is_string($subjectName) || $subjectName === '' || !is_array($chaptersData)) {
                        continue;
                    }

                    $subject = $this->subjectRepository->findOneBy(['classroom' => $classroom, 'slug' => $subjectSlug]);
                    if ($subject === null) {
                        $subject = new Subject();
                        $subject->setClassroom($classroom);
                        $subject->setName($subjectName);
                        $subject->setSlug($subjectSlug);
                        $classroom->addSubject($subject);
                        if (!$dryRun) {
                            $this->entityManager->persist($subject);
                        }
                        $stats['subjects']++;
                    }

                    foreach ($chaptersData as $chapterData) {
                        $chapterTitle = $chapterData['title'] ?? null;
                        $chapterSlug = isset($chapterData['slug']) ? (string) $chapterData['slug'] : $this->normalizeSlug((string) $chapterTitle);
                        $subchaptersData = $chapterData['subchapters'] ?? [];
                        if (!is_string($chapterTitle) || $chapterTitle === '' || !is_array($subchaptersData)) {
                            continue;
                        }

                        $chapter = $this->chapterRepository->findOneBy(['subject' => $subject, 'slug' => $chapterSlug]);
                        if ($chapter === null) {
                            $chapter = new Chapter();
                            $chapter->setSubject($subject);
                            $chapter->setTitle($chapterTitle);
                            $chapter->setSlug($chapterSlug);
                            $subject->addChapter($chapter);
                            if (!$dryRun) {
                                $this->entityManager->persist($chapter);
                            }
                            $stats['chapters']++;
                        }

                        $chapterKey = $chapter->getId() ?? 'n' . spl_object_id($chapter);
                        if (!isset($seenSubSlugsByChapterKey[$chapterKey])) {
                            $seenSubSlugsByChapterKey[$chapterKey] = [];
                        }
                        foreach ($subchaptersData as $subchapterData) {
                            $subTitle = $subchapterData['title'] ?? null;
                            $subSlug = isset($subchapterData['slug']) ? (string) $subchapterData['slug'] : $this->normalizeSlug((string) $subTitle);
                            if (!is_string($subTitle) || $subTitle === '') {
                                continue;
                            }
                            if (isset($seenSubSlugsByChapterKey[$chapterKey][$subSlug])) {
                                continue;
                            }

                            $subchapter = $this->subchapterRepository->findOneBy(['chapter' => $chapter, 'slug' => $subSlug]);
                            if ($subchapter === null) {
                                $subchapter = new Subchapter();
                                $subchapter->setChapter($chapter);
                                $subchapter->setTitle($subTitle);
                                $subchapter->setSlug($subSlug);
                                $subchapter->setHref(isset($subchapterData['href']) ? (string) $subchapterData['href'] : null);
                                $subchapter->setType(isset($subchapterData['type']) ? (string) $subchapterData['type'] : null);
                                $chapter->addSubchapter($subchapter);
                                if (!$dryRun) {
                                    $this->entityManager->persist($subchapter);
                                }
                                $stats['subchapters']++;
                            }
                            $seenSubSlugsByChapterKey[$chapterKey][$subSlug] = true;
                        }
                    }
                }
            }
        }

        if (!$dryRun) {
            $this->entityManager->flush();
        }

        $io->success([
            $dryRun ? '[DRY-RUN] Aucune écriture en base.' : 'Import terminé.',
            sprintf('Classrooms: %d', $stats['classrooms']),
            sprintf('Subjects: %d', $stats['subjects']),
            sprintf('Chapters: %d', $stats['chapters']),
            sprintf('Subchapters: %d', $stats['subchapters']),
        ]);

        return Command::SUCCESS;
    }

    private function normalizeSlug(string $text): string
    {
        $slug = $this->slugger->slug($text)->lower()->toString();
        return $slug;
    }
}
