<?php

declare(strict_types=1);

namespace App\Command;

use App\Entity\Chapter;
use App\Entity\Subchapter;
use App\Repository\ClassroomRepository;
use App\Repository\SubjectRepository;
use App\Repository\SubchapterRepository;
use App\Service\ContentGenerator\ContentGeneratorService;
use App\Service\Prompt\CourseMindmapPromptProvider;
use Doctrine\ORM\EntityManagerInterface;
use Psr\Log\LoggerInterface;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:generate-course-mindmap',
    description: 'Génère les cours Reveal.js et mindmaps pour les chapitres/sous-chapitres via l\'IA.',
)]
final class GenerateCourseMindmapCommand extends Command
{
    public const FILTER_CHAPTER = 'chapter';
    public const FILTER_SUBCHAPTER = 'subchapter';

    public function __construct(
        private readonly SubjectRepository $subjectRepository,
        private readonly ClassroomRepository $classroomRepository,
        private readonly SubchapterRepository $subchapterRepository,
        private readonly EntityManagerInterface $entityManager,
        private readonly CourseMindmapPromptProvider $promptProvider,
        private readonly ContentGeneratorService $contentGeneratorService,
        private readonly LoggerInterface $logger,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addOption('classroom', null, InputOption::VALUE_OPTIONAL, 'Obligatoire pour le cron : ID ou slug de classe')
            ->addOption('subject', null, InputOption::VALUE_OPTIONAL, 'Obligatoire pour le cron : ID ou slug de matière')
            ->addOption('filter', null, InputOption::VALUE_OPTIONAL, 'Obligatoire pour le cron : chapter ou subchapter')
            ->addOption('chapter', null, InputOption::VALUE_OPTIONAL, 'ID ou slug du chapitre (traiter un seul chapitre)')
            ->addOption('subchapter', null, InputOption::VALUE_OPTIONAL, 'ID ou slug du sous-chapitre (traiter un seul sous-chapitre)')
            ->addOption('limit', null, InputOption::VALUE_OPTIONAL, 'Limiter le nombre de chapitres/sous-chapitres à traiter')
            ->addOption('provider', null, InputOption::VALUE_OPTIONAL, 'Provider IA: openai, deepseek, curl')
            ->addOption('dry-run', null, InputOption::VALUE_NONE, 'Ne pas persister en base');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $classroomOpt = $input->getOption('classroom');
        $subjectOpt = $input->getOption('subject');
        $filterOpt = $input->getOption('filter') !== null ? trim((string) $input->getOption('filter')) : null;
        $chapterOpt = $input->getOption('chapter');
        $subchapterOpt = $input->getOption('subchapter');
        $limit = $input->getOption('limit') !== null ? (int) $input->getOption('limit') : null;
        $provider = $input->getOption('provider');
        $dryRun = (bool) $input->getOption('dry-run');

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
                $io->error(sprintf('Matière introuvable : %s', $subjectOpt));
                return Command::FAILURE;
            }
            $items = $filter === self::FILTER_CHAPTER
                ? $this->resolveChapters($subject, $chapterOpt, $limit)
                : $this->resolveSubchapters($subject, $subchapterOpt, $limit);
        } else {
            $items = $this->resolveItemsLegacy($chapterOpt, $subchapterOpt, $limit);
        }

        if ($items === []) {
            $io->warning('Aucun chapitre ni sous-chapitre trouvé.');
            return Command::SUCCESS;
        }

        $generate = $provider !== null && $provider !== ''
            ? $this->getGenerateByProvider($provider)
            : fn (string $p) => $this->contentGeneratorService->generate($p);

        $niveauClasse = $items[0]['niveau'] ?? '';
        $processed = 0;

        foreach ($items as $item) {
            $chapitre = $item['chapitre'];
            $niveau = $item['niveau'];
            $prompt = $this->promptProvider->buildForCourseRevealAndMindmap($chapitre, $niveau);
            $io->text(sprintf('Génération cours : "%s"…', $chapitre));
            $this->logger->info('API input', ['prompt' => $prompt]);
            try {
                $raw = $generate($prompt);
            } catch (\Throwable $e) {
                $io->error(sprintf('IA: %s', $e->getMessage()));
                continue;
            }
            $this->logger->info('API output', ['response' => $raw]);
            $data = $this->extractJson($raw);
            if ($data === null) {
                $io->error('Réponse IA : JSON invalide.');
                continue;
            }
            if (!$dryRun && isset($item['entity'])) {
                $this->persistCourseMindmap($item['entity'], $data);
            }
            $processed++;
        }

        if (!$dryRun) {
            $this->entityManager->flush();
        }

        $io->success([
            $dryRun ? '[DRY-RUN] Aucune écriture.' : 'Génération terminée.',
            sprintf('Éléments traités : %d', $processed),
        ]);
        return Command::SUCCESS;
    }

    /**
     * @return list<array{chapitre: string, niveau: string, entity: Chapter|Subchapter}>
     */
    private function resolveChapters(\App\Entity\Subject $subject, ?string $chapterOpt, ?int $limit): array
    {
        $chapters = $subject->getChapters();
        $items = [];
        foreach ($chapters as $chapter) {
            if ($chapterOpt !== null && $chapterOpt !== '') {
                $match = (is_numeric($chapterOpt) && (int) $chapterOpt === $chapter->getId())
                    || $chapter->getSlug() === $chapterOpt
                    || $chapter->getTitle() === $chapterOpt;
                if (!$match) {
                    continue;
                }
            }
            $classroom = $subject->getClassroom();
            $items[] = [
                'chapitre' => $chapter->getTitle(),
                'niveau' => $classroom?->getName() ?? '',
                'entity' => $chapter,
            ];
            if ($limit !== null && count($items) >= $limit) {
                break;
            }
        }
        return $items;
    }

    /**
     * @return list<array{chapitre: string, niveau: string, entity: Chapter|Subchapter}>
     */
    private function resolveSubchapters(\App\Entity\Subject $subject, ?string $subchapterOpt, ?int $limit): array
    {
        $items = [];
        $classroom = $subject->getClassroom();
        $niveau = $classroom?->getName() ?? '';
        foreach ($subject->getChapters() as $chapter) {
            foreach ($chapter->getSubchapters() as $subchapter) {
                if (!$subchapter->isCourseType()) {
                    continue;
                }
                if ($subchapterOpt !== null && $subchapterOpt !== '') {
                    $match = (is_numeric($subchapterOpt) && (int) $subchapterOpt === $subchapter->getId())
                        || $subchapter->getSlug() === $subchapterOpt
                        || $subchapter->getTitle() === $subchapterOpt;
                    if (!$match) {
                        continue;
                    }
                }
                $items[] = [
                    'chapitre' => $subchapter->getTitle(),
                    'niveau' => $niveau,
                    'entity' => $subchapter,
                ];
                if ($limit !== null && count($items) >= $limit) {
                    return $items;
                }
            }
        }
        return $items;
    }

    /**
     * @return list<array{chapitre: string, niveau: string, entity: Chapter|Subchapter}>
     */
    private function resolveItemsLegacy(?string $chapterOpt, ?string $subchapterOpt, ?int $limit): array
    {
        if ($subchapterOpt !== null && $subchapterOpt !== '') {
            $sub = is_numeric($subchapterOpt)
                ? $this->subchapterRepository->find((int) $subchapterOpt)
                : $this->subchapterRepository->findOneBy(['slug' => $subchapterOpt]);
            if ($sub === null || !$sub->isCourseType()) {
                return [];
            }
            $chapter = $sub->getChapter();
            $classroom = $chapter?->getSubject()?->getClassroom();
            return [[
                'chapitre' => $sub->getTitle(),
                'niveau' => $classroom?->getName() ?? '',
                'entity' => $sub,
            ]];
        }
        if ($chapterOpt !== null && $chapterOpt !== '') {
            $chapter = is_numeric($chapterOpt)
                ? $this->entityManager->getRepository(Chapter::class)->find((int) $chapterOpt)
                : $this->entityManager->getRepository(Chapter::class)->findOneBy(['slug' => $chapterOpt]);
            if ($chapter === null) {
                return [];
            }
            $classroom = $chapter->getSubject()?->getClassroom();
            return [[
                'chapitre' => $chapter->getTitle(),
                'niveau' => $classroom?->getName() ?? '',
                'entity' => $chapter,
            ]];
        }
        $subjects = $this->subjectRepository->findBy([], ['id' => 'ASC']);
        $items = [];
        foreach ($subjects as $subject) {
            $classroom = $subject->getClassroom();
            $niveau = $classroom?->getName() ?? '';
            foreach ($subject->getChapters() as $chapter) {
                $items[] = ['chapitre' => $chapter->getTitle(), 'niveau' => $niveau, 'entity' => $chapter];
                if ($limit !== null && count($items) >= $limit) {
                    return $items;
                }
            }
        }
        return $items;
    }

    private function getGenerateByProvider(string $provider): \Closure
    {
        $p = strtolower($provider);
        return match ($p) {
            'openai' => fn (string $prompt) => $this->contentGeneratorService->generateViaOpenAI($prompt),
            'deepseek' => fn (string $prompt) => $this->contentGeneratorService->generateViaDeepSeek($prompt),
            'curl' => fn (string $prompt) => $this->contentGeneratorService->generateViaCurl($prompt),
            default => fn (string $prompt) => $this->contentGeneratorService->generate($prompt),
        };
    }

    private function persistCourseMindmap(Chapter|Subchapter $entity, array $data): void
    {
        $course = $data['course'] ?? null;
        if (is_array($course) && isset($course['title'], $course['slides'])) {
            $entity->setCourse($course);
        }
        // Génération et sauvegarde mindmap désactivées
        // $mindmap = $data['mindmap'] ?? null;
        // if (is_array($mindmap) && (isset($mindmap['content']) || isset($mindmap['text_to_audio']))) {
        //     $entity->setMindmap([
        //         'content' => (string) ($mindmap['content'] ?? ''),
        //         'text_to_audio' => (string) ($mindmap['text_to_audio'] ?? ''),
        //     ]);
        // }
    }

    private function extractJson(string $raw): ?array
    {
        $trimmed = trim($raw);
        if (preg_match('/```(?:json)?\s*([\s\S]*?)```/', $trimmed, $m)) {
            $trimmed = trim($m[1]);
        }
        
        // Fix DeepSeek frequently double escaping newlines in json strings E.g: \\r\\n or \\n
        $trimmed = str_replace(['\\\\n', '\\\\r'], ['\\n', '\\r'], $trimmed);
        
        // Escape newlines and tabs that are inside JSON string literals
        $result = '';
        $inString = false;
        $escape = false;
        for ($i = 0, $len = strlen($trimmed); $i < $len; $i++) {
            $char = $trimmed[$i];
            if ($escape) {
                $escape = false;
                $result .= $char;
                continue;
            }
            if ($char === '\\') {
                $escape = true;
                $result .= $char;
                continue;
            }
            if ($char === '"') {
                $inString = !$inString;
                $result .= $char;
                continue;
            }
            if ($inString) {
                if ($char === "\n") {
                    $result .= '\\n';
                    continue;
                }
                if ($char === "\r") {
                    continue;
                }
                if ($char === "\t") {
                    $result .= '\\t';
                    continue;
                }
            }
            $result .= $char;
        }
        
        $decoded = json_decode($result, true);
        if ($decoded === null) {
            $this->logger->error('JSON decode error', [
                'error' => json_last_error_msg(),
                'raw_snippet' => substr($trimmed, -500),
            ]);
        }
        return is_array($decoded) ? $decoded : null;
    }
}
