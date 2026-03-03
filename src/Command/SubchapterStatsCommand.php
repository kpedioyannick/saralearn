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
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:stats:subchapters',
    description: 'Statistiques sur les sous-chapitres : combien ont un cours, des modules H5P, des livres interactifs, etc.',
)]
final class SubchapterStatsCommand extends Command
{
    public function __construct(
        private readonly SubchapterRepository $subchapterRepository,
        private readonly ModuleRepository $moduleRepository,
        private readonly PathRepository $pathRepository,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this->addOption('course-type-only', null, InputOption::VALUE_NONE, 'Ne compter que les sous-chapitres de type "Cours" (comme le Manager)');
        $this->addOption('with-context-only', null, InputOption::VALUE_NONE, 'Ne compter que les sous-chapitres avec classe/matière/chapitre (contexte complet)');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $courseTypeOnly = (bool) $input->getOption('course-type-only');
        $withContextOnly = (bool) $input->getOption('with-context-only');

        $qb = $this->subchapterRepository->createQueryBuilder('s')
            ->orderBy('s.id', 'ASC');
        if ($courseTypeOnly) {
            $qb->andWhere('s.type = :type')->setParameter('type', Subchapter::TYPE_COURS);
        }
        $subchapters = $qb->getQuery()->getResult();

        if ($withContextOnly) {
            $subchapters = array_values(array_filter($subchapters, function (Subchapter $s) {
                $chapter = $s->getChapter();
                if ($chapter === null) {
                    return false;
                }
                $subject = $chapter->getSubject();
                if ($subject === null) {
                    return false;
                }
                return $subject->getClassroom() !== null;
            }));
        }

        $total = count($subchapters);
        if ($total === 0) {
            $io->warning('Aucun sous-chapitre trouvé.');
            return Command::SUCCESS;
        }

        $io->title(sprintf('Statistiques sous-chapitres (%d au total)', $total));
        if ($courseTypeOnly) {
            $io->text('Périmètre : type « Cours » uniquement.');
        }
        if ($withContextOnly) {
            $io->text('Périmètre : avec classe / matière / chapitre (contexte complet).');
        }

        $ids = array_map(static fn (Subchapter $s) => $s->getId(), $subchapters);

        // Cours (Reveal.js)
        $withCourse = 0;
        $withMindmap = 0;
        foreach ($subchapters as $s) {
            $course = $s->getCourse();
            if ($course !== null && is_array($course) && $course !== []) {
                $withCourse++;
            }
            $mindmap = $s->getMindmap();
            if ($mindmap !== null && is_array($mindmap) && ($mindmap['content'] ?? '') !== '') {
                $withMindmap++;
            }
        }
        $io->section('Cours (Reveal.js) et mindmap');
        $io->table(
            ['Indicateur', 'Nombre', 'Sur total'],
            [
                ['Avec cours', (string) $withCourse, $total > 0 ? sprintf('%d / %d (%.1f%%)', $withCourse, $total, 100 * $withCourse / $total) : '-'],
                ['Sans cours', (string) ($total - $withCourse), $total > 0 ? sprintf('%d / %d', $total - $withCourse, $total) : '-'],
                ['Avec mindmap', (string) $withMindmap, $total > 0 ? sprintf('%d / %d (%.1f%%)', $withMindmap, $total, 100 * $withMindmap / $total) : '-'],
            ]
        );

        // Modules H5P
        $subchapterBloomMap = $this->moduleRepository->getSubchapterIdsByBloomLevel($ids);
        $withAtLeastOneModule = count($subchapterBloomMap);
        $totalModules = $this->moduleRepository->countBySubchapterIds($ids);
        $bloomLevels = ['remember', 'understand', 'apply', 'analyze', 'evaluate'];
        $byBloom = [];
        foreach ($bloomLevels as $level) {
            $byBloom[$level] = 0;
        }
        foreach ($subchapterBloomMap as $levels) {
            foreach ($levels as $level) {
                if (isset($byBloom[$level])) {
                    $byBloom[$level]++;
                }
            }
        }
        $io->section('Modules H5P');
        $rows = [
            ['Avec au moins 1 module', (string) $withAtLeastOneModule, $total > 0 ? sprintf('%d / %d (%.1f%%)', $withAtLeastOneModule, $total, 100 * $withAtLeastOneModule / $total) : '-'],
            ['Total modules (tous sous-chapitres)', (string) $totalModules, '-'],
        ];
        foreach ($bloomLevels as $level) {
            $rows[] = [sprintf('Avec module « %s »', $level), (string) $byBloom[$level], $total > 0 ? sprintf('%d / %d (%.1f%%)', $byBloom[$level], $total, 100 * $byBloom[$level] / $total) : '-'];
        }
        $io->table(['Indicateur', 'Nombre', 'Sur total'], $rows);

        // Livres interactifs (Paths)
        $paths = $this->pathRepository->findBySubchapterIds($ids);
        $subchapterPathPresets = [];
        foreach ($paths as $path) {
            $sub = $path->getSubchapter();
            if ($sub === null) {
                continue;
            }
            $sid = $sub->getId();
            $types = $path->getTypes();
            if ($types !== null) {
                $key = PathTypePresets::key($types);
                if (!isset($subchapterPathPresets[$sid])) {
                    $subchapterPathPresets[$sid] = [];
                }
                $subchapterPathPresets[$sid][$key] = true;
            }
        }
        $presets = PathTypePresets::all();
        $withAtLeastOneBook = count($subchapterPathPresets);
        $io->section('Livres interactifs (Paths)');
        $bookRows = [
            ['Avec au moins 1 livre', (string) $withAtLeastOneBook, $total > 0 ? sprintf('%d / %d (%.1f%%)', $withAtLeastOneBook, $total, 100 * $withAtLeastOneBook / $total) : '-'],
        ];
        foreach ($presets as $types) {
            $key = PathTypePresets::key($types);
            $label = PathTypePresets::label($types);
            $count = 0;
            foreach ($subchapterPathPresets as $presetsForSub) {
                if (!empty($presetsForSub[$key])) {
                    $count++;
                }
            }
            $bookRows[] = [sprintf('Avec livre « %s »', $label), (string) $count, $total > 0 ? sprintf('%d / %d (%.1f%%)', $count, $total, 100 * $count / $total) : '-'];
        }
        $io->table(['Indicateur', 'Nombre', 'Sur total'], $bookRows);

        $io->success('Statistiques affichées.');
        return Command::SUCCESS;
    }
}
