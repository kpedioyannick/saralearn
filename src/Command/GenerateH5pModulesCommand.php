<?php

declare(strict_types=1);

namespace App\Command;

use App\Entity\Chapter;
use App\Entity\Module;
use App\Entity\Subchapter;
use App\Repository\ClassroomRepository;
use App\Repository\ModuleRepository;
use App\Repository\SubchapterRepository;
use App\Repository\SubjectRepository;
use App\Service\ContentGenerator\ContentGeneratorService;
use App\Service\Prompt\BloomH5pTypeMap;
use App\Service\Prompt\PromptTemplateProvider;
use Doctrine\ORM\EntityManagerInterface;
use Psr\Log\LoggerInterface;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;
use Symfony\Component\String\Slugger\SluggerInterface;

#[AsCommand(
    name: 'app:h5p:generate-modules',
    description: 'Génère les modules H5P par chapitre × niveau Bloom (Proposition 2) ou sous-chapitre × Bloom (Proposition 3) via le service IA.',
)]
final class GenerateH5pModulesCommand extends Command
{
    public function __construct(
        private readonly SubjectRepository $subjectRepository,
        private readonly ClassroomRepository $classroomRepository,
        private readonly SubchapterRepository $subchapterRepository,
        private readonly ModuleRepository $moduleRepository,
        private readonly EntityManagerInterface $entityManager,
        private readonly PromptTemplateProvider $promptTemplateProvider,
        private readonly ContentGeneratorService $contentGeneratorService,
        private readonly SluggerInterface $slugger,
        private readonly LoggerInterface $logger,
    ) {
        parent::__construct();
    }

    public const FILTER_CHAPTER = 'chapter';
    public const FILTER_SUBCHAPTER = 'subchapter';

    protected function configure(): void
    {
        $this
            ->addOption('classroom', null, InputOption::VALUE_OPTIONAL, 'Obligatoire pour le cron : ID ou slug de classe (ex: 1 ou cm2)')
            ->addOption('subject', null, InputOption::VALUE_OPTIONAL, 'Obligatoire pour le cron : ID ou slug de matière')
            ->addOption('filter', null, InputOption::VALUE_OPTIONAL, 'Obligatoire pour le cron : chapter ou subchapter (charge les chapitres ou les sous-chapitres)')
            ->addOption('subchapter', null, InputOption::VALUE_OPTIONAL, 'ID ou slug du sous-chapitre (traiter un seul sous-chapitre, à utiliser avec --classroom et --subject)')
            ->addOption('bloom-types', null, InputOption::VALUE_OPTIONAL, 'Niveaux Bloom à traiter, séparés par des virgules (défaut: tous). Ex: remember,understand,apply')
            ->addOption('limit', null, InputOption::VALUE_OPTIONAL, 'Limiter le nombre de chapitres/sous-chapitres à traiter (pour tests)')
            ->addOption('provider', null, InputOption::VALUE_OPTIONAL, 'Provider IA: openai, deepseek, curl (sinon CONTENT_GENERATOR_DEFAULT)')
            ->addOption('strategy', null, InputOption::VALUE_OPTIONAL, 'Stratégie: chapter_bloom (défaut) ou subchapter_bloom')
            ->addOption('dry-run', null, InputOption::VALUE_NONE, 'Ne pas persister en base, seulement appeler l\'IA et afficher');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $classroomOpt = $input->getOption('classroom');
        $subjectOpt = $input->getOption('subject');
        $filterOpt = $input->getOption('filter') !== null ? trim((string) $input->getOption('filter')) : null;
        $bloomTypesOpt = $input->getOption('bloom-types') !== null ? trim((string) $input->getOption('bloom-types')) : null;
        $limit = $input->getOption('limit') !== null ? (int) $input->getOption('limit') : null;
        $provider = $input->getOption('provider');
        $strategy = $input->getOption('strategy') ?? PromptTemplateProvider::DEFAULT_STRATEGY;
        $dryRun = (bool) $input->getOption('dry-run');

        $bloomLevels = $this->resolveBloomLevels($bloomTypesOpt);
        if ($bloomLevels === []) {
            $io->error('Option --bloom-types : aucun niveau Bloom valide. Valeurs acceptées : remember, understand, apply, analyze, evaluate.');
            return Command::FAILURE;
        }

        $subchapterOpt = $input->getOption('subchapter') !== null ? trim((string) $input->getOption('subchapter')) : null;

        // Mode découpage : un seul sous-chapitre (Manager appelle avec --classroom --subject --subchapter)
        if ($subchapterOpt !== null && $subchapterOpt !== '') {
            if ($classroomOpt === null || $classroomOpt === '' || $subjectOpt === null || $subjectOpt === '') {
                $io->error('Avec --subchapter, indiquez --classroom et --subject.');
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
            $subchapter = is_numeric($subchapterOpt)
                ? $this->subchapterRepository->find((int) $subchapterOpt)
                : $this->subchapterRepository->findOneBy(['slug' => $subchapterOpt]);
            if ($subchapter === null) {
                $io->error(sprintf('Sous-chapitre introuvable : %s', $subchapterOpt));
                return Command::FAILURE;
            }
            $chapter = $subchapter->getChapter();
            if ($chapter === null || $chapter->getSubject() !== $subject) {
                $io->error('Le sous-chapitre ne appartient pas à la matière indiquée.');
                return Command::FAILURE;
            }
            if (!$subchapter->isCourseType()) {
                $io->error('Seuls les sous-chapitres de type "Cours" sont traités. Ce sous-chapitre est de type "' . ($subchapter->getType() ?? '') . '".');
                return Command::FAILURE;
            }
            $matiere = $subject->getName();
            $niveauClasse = $classroom->getName();
            $generate = $provider !== null && $provider !== ''
                ? $this->getGenerateByProvider($provider)
                : fn (string $p) => $this->contentGeneratorService->generate($p);
            $modulesCreated = 0;
            foreach ($bloomLevels as $bloomLevel) {
                $modulesCreated += $this->processSubchapterBloom(
                    $subchapter,
                    $chapter,
                    $matiere,
                    $niveauClasse,
                    $bloomLevel,
                    $generate,
                    $dryRun,
                    $io,
                );
            }
            if (!$dryRun) {
                $this->entityManager->flush();
            }
            $io->success([
                $dryRun ? '[DRY-RUN] Aucune écriture en base.' : 'Génération terminée (1 sous-chapitre).',
                sprintf('Modules créés : %d', $modulesCreated),
            ]);
            return Command::SUCCESS;
        }

        // Cron : classroom + subject + filter obligatoires ensemble
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
            $subjects = [$subject];
            $useFilterChapter = ($filter === self::FILTER_CHAPTER);
        } else {
            $subjects = $this->resolveSubjects($classroomOpt);
            $useFilterChapter = null; // mode legacy : on itère tous les chapitres
        }

        if ($subjects === []) {
            $io->warning('Aucune matière trouvée. Exécutez d\'abord app:import:school-data.');
            return Command::SUCCESS;
        }

        $generate = $provider !== null && $provider !== ''
            ? $this->getGenerateByProvider($provider)
            : fn (string $p) => $this->contentGeneratorService->generate($p);

        $chaptersProcessed = 0;
        $modulesCreated = 0;

        foreach ($subjects as $subject) {
            $classroom = $subject->getClassroom();
            if ($classroom === null) {
                continue;
            }
            $matiere = $subject->getName();
            $niveauClasse = $classroom->getName();

            if ($useFilterChapter === true) {
                $chapters = $subject->getChapters();
                foreach ($chapters as $chapter) {
                    if ($limit !== null && $chaptersProcessed >= $limit) {
                        break 2;
                    }
                    $modulesCreated += $this->processChapter($chapter, $matiere, $niveauClasse, $bloomLevels, $strategy, $generate, $dryRun, $io);
                    $chaptersProcessed++;
                }
                continue;
            }

            if ($useFilterChapter === false) {
                $subchaptersProcessed = 0;
                foreach ($subject->getChapters() as $chapter) {
                    foreach ($chapter->getSubchapters() as $subchapter) {
                        if (!$subchapter->isCourseType()) {
                            continue;
                        }
                        if ($limit !== null && $subchaptersProcessed >= $limit) {
                            break 2;
                        }
                        foreach ($bloomLevels as $bloomLevel) {
                            $modulesCreated += $this->processSubchapterBloom(
                                $subchapter,
                                $chapter,
                                $matiere,
                                $niveauClasse,
                                $bloomLevel,
                                $generate,
                                $dryRun,
                                $io,
                            );
                        }
                        $subchaptersProcessed++;
                    }
                }
                $chaptersProcessed = $subchaptersProcessed;
                continue;
            }

            foreach ($subject->getChapters() as $chapter) {
                if ($limit !== null && $chaptersProcessed >= $limit) {
                    break 2;
                }
                $modulesCreated += $this->processChapter($chapter, $matiere, $niveauClasse, $bloomLevels, $strategy, $generate, $dryRun, $io);
                $chaptersProcessed++;
            }
        }

        if (!$dryRun) {
            $this->entityManager->flush();
        }

        $io->success([
            $dryRun ? '[DRY-RUN] Aucune écriture en base.' : 'Génération terminée.',
            sprintf('Chapitres traités : %d', $chaptersProcessed),
            sprintf('Modules créés : %d', $modulesCreated),
        ]);
        return Command::SUCCESS;
    }

    /**
     * Traite un chapitre (Proposition 2 ou 3 selon la stratégie).
     * @param list<string> $bloomLevels
     * @return int nombre de modules créés
     */
    private function processChapter(
        Chapter $chapter,
        string $matiere,
        string $niveauClasse,
        array $bloomLevels,
        string $strategy,
        \Closure $generate,
        bool $dryRun,
        SymfonyStyle $io,
    ): int {
        $subchaptersCours = array_values(array_filter(
            $chapter->getSubchapters()->toArray(),
            static fn (Subchapter $s) => $s->isCourseType(),
        ));
        if ($subchaptersCours === []) {
            return 0;
        }
        $created = 0;

        if ($strategy === PromptTemplateProvider::STRATEGY_SUBCHAPTER_BLOOM) {
            foreach ($subchaptersCours as $subchapter) {
                if (!$subchapter->isCourseType()) {
                    continue;
                }
                foreach ($bloomLevels as $bloomLevel) {
                    $created += $this->processSubchapterBloom(
                        $subchapter,
                        $chapter,
                        $matiere,
                        $niveauClasse,
                        $bloomLevel,
                        $generate,
                        $dryRun,
                        $io,
                    );
                }
            }
            return $created;
        }

        $nomsSousChapitres = implode(', ', array_map(static fn (Subchapter $s) => $s->getTitle(), $subchaptersCours));
        foreach ($bloomLevels as $bloomLevel) {
            $prompt = $this->promptTemplateProvider->buildForChapterAndBloom(
                $matiere,
                $niveauClasse,
                $nomsSousChapitres,
                $bloomLevel,
            );
            $io->text(sprintf('Chapitre "%s" / Bloom %s…', $chapter->getTitle(), $bloomLevel));
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
                $io->error('Réponse IA : JSON invalide ou introuvable.');
                continue;
            }
            $subchaptersData = $data['subchapters'] ?? [];
            if (!is_array($subchaptersData)) {
                $io->error('Réponse IA : clé "subchapters" absente ou invalide.');
                continue;
            }
            $created += $this->persistModulesFromChapterResponse(
                $chapter,
                $data,
                $bloomLevel,
                $dryRun,
                $io,
            );
        }
        return $created;
    }

    /**
     * Retourne les niveaux Bloom à traiter. Par défaut : tous. Sinon les valeurs de --bloom-types (séparées par des virgules).
     * @return list<string>
     */
    private function resolveBloomLevels(?string $bloomTypesOpt): array
    {
        $all = BloomH5pTypeMap::getAllBloomLevels();
        if ($bloomTypesOpt === null || $bloomTypesOpt === '') {
            return $all;
        }
        $requested = array_map('trim', explode(',', $bloomTypesOpt));
        $valid = array_intersect($requested, $all);
        return array_values($valid);
    }

    /**
     * @return list<\App\Entity\Subject>
     */
    private function resolveSubjects(?string $classroomFilter): array
    {
        if ($classroomFilter === null || $classroomFilter === '') {
            return $this->subjectRepository->findBy([], ['id' => 'ASC']);
        }
        if (is_numeric($classroomFilter)) {
            return $this->subjectRepository->findBy(['classroom' => (int) $classroomFilter], ['id' => 'ASC']);
        }
        $classroom = $this->classroomRepository->findOneBy(['slug' => $classroomFilter]);
        if ($classroom === null) {
            $classroom = $this->classroomRepository->findOneBy(['name' => $classroomFilter]);
        }
        if ($classroom === null) {
            return [];
        }
        return $this->subjectRepository->findBy(['classroom' => $classroom], ['id' => 'ASC']);
    }

    /**
     * @return \Closure(string): string
     */
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

    private function processSubchapterBloom(
        Subchapter $subchapter,
        Chapter $chapter,
        string $matiere,
        string $niveauClasse,
        string $bloomLevel,
        \Closure $generate,
        bool $dryRun,
        SymfonyStyle $io,
    ): int {
        $prompt = $this->promptTemplateProvider->buildForSubchapterAndBloom(
            $matiere,
            $niveauClasse,
            $subchapter->getTitle(),
            $bloomLevel,
        );
        $io->text(sprintf('Sous-chapitre "%s" / Bloom %s…', $subchapter->getTitle(), $bloomLevel));
        $this->logger->info('API input', ['prompt' => $prompt]);
        try {
            $raw = $generate($prompt);
        } catch (\Throwable $e) {
            $io->error(sprintf('IA: %s', $e->getMessage()));
            return 0;
        }
        $this->logger->info('API output', ['response' => $raw]);
        $data = $this->extractJson($raw);
        if ($data === null) {
            $io->error('Réponse IA : JSON invalide.');
            file_put_contents('/tmp/invalid_json.txt', $raw);
            return 0;
        }
        $subchaptersData = $data['subchapters'] ?? [];
        if (!is_array($subchaptersData) || count($subchaptersData) < 1) {
            $io->error('Réponse IA : "subchapters" vide.');
            return 0;
        }
        return $this->persistModulesFromChapterResponse($chapter, $data, $bloomLevel, $dryRun, $io);
    }

    /**
     * @param array{chapter?: array{course?: mixed, mindmap?: mixed}, subchapters?: array<int, mixed>} $data
     */
    private function persistModulesFromChapterResponse(
        Chapter $chapter,
        array $data,
        string $bloomLevel,
        bool $dryRun,
        SymfonyStyle $io,
    ): int {
        $subchaptersData = $data['subchapters'] ?? [];
        if (!is_array($subchaptersData)) {
            return 0;
        }

        $created = 0;
        $subchaptersBySlug = [];
        $subchaptersByNormalizedSlug = [];
        foreach ($chapter->getSubchapters() as $sub) {
            $s = $sub->getSlug();
            $subchaptersBySlug[$s] = $sub;
            $subchaptersByNormalizedSlug[$this->normalizeSlugForMatch($s)] = $sub;
        }
        foreach ($subchaptersData as $scData) {
            if (!is_array($scData)) {
                continue;
            }
            $slug = $scData['slug'] ?? null;
            $title = $scData['title'] ?? null;
            $subchapter = $this->findSubchapterBySlugOrTitle($chapter, $slug, $title, $subchaptersBySlug, $subchaptersByNormalizedSlug);
            if ($subchapter === null) {
                $io->warning(sprintf('Sous-chapitre non trouvé (slug: %s, title: %s). Comparaison par slug uniquement.', $slug ?? '?', $title ?? '?'));
                continue;
            }

            $bloomLevelsData = $scData['bloom_levels'] ?? [];
            if (!is_array($bloomLevelsData) || !isset($bloomLevelsData[$bloomLevel])) {
                continue;
            }
            $levelData = $bloomLevelsData[$bloomLevel];
            if (!is_array($levelData)) {
                continue;
            }
            if (!$dryRun) {
                foreach ($this->moduleRepository->findBySubchapterAndBloomLevel($subchapter->getId(), $bloomLevel) as $old) {
                    $this->entityManager->remove($old);
                }
            }
            foreach (['débutant' => 'débutant', 'intermédiaire' => 'intermédiaire'] as $diffKey => $diffValue) {
                $exercises = $levelData[$diffKey] ?? [];
                if (!is_array($exercises)) {
                    continue;
                }
                foreach ($exercises as $index => $exercise) {
                    if (!is_array($exercise)) {
                        continue;
                    }
                    $type = $exercise['type'] ?? null;
                    $content = $this->extractExerciseContent($exercise);
                    if ($type === null || $content === null) {
                        continue;
                    }
                    $contentJson = is_string($content) ? $content : json_encode($content, \JSON_THROW_ON_ERROR | \JSON_UNESCAPED_UNICODE);
                    if (!$dryRun) {
                        $module = new Module();
                        $module->setSubchapter($subchapter);
                        $module->setChapter($chapter);
                        $module->setTitle(sprintf('%s - %s %s', $subchapter->getTitle(), $diffValue, $index + 1));
                        $module->setBloomLevel($bloomLevel);
                        $module->setDifficulty($diffValue);
                        $module->setH5pType((string) $type);
                        $module->setContent($contentJson);
                        $this->entityManager->persist($module);
                    }
                    $created++;
                }
            }
        }
        return $created;
    }

    /**
     * Trouve un sous-chapitre par slug ou titre (slugifié) pour éviter les écarts d'accents titre IA vs BDD.
     * Comparaison uniquement via les slugs (exact puis normalisé).
     * @param array<string, Subchapter> $subchaptersBySlug
     * @param array<string, Subchapter> $subchaptersByNormalizedSlug
     */
    private function findSubchapterBySlugOrTitle(
        Chapter $chapter,
        mixed $slug,
        mixed $title,
        array $subchaptersBySlug,
        array $subchaptersByNormalizedSlug,
    ): ?Subchapter {
        if (is_string($slug) && $slug !== '') {
            if (isset($subchaptersBySlug[$slug])) {
                return $subchaptersBySlug[$slug];
            }
            $normalized = $this->normalizeSlugForMatch($slug);
            if (isset($subchaptersByNormalizedSlug[$normalized])) {
                return $subchaptersByNormalizedSlug[$normalized];
            }
        }
        if (is_string($title) && $title !== '') {
            $slugFromTitle = $this->normalizeSlugForMatch($title);
            if (isset($subchaptersByNormalizedSlug[$slugFromTitle])) {
                return $subchaptersByNormalizedSlug[$slugFromTitle];
            }
            // Fallback: search by checking if all words from the AI title exist in the DB title
            $aiWords = array_filter(explode('-', $slugFromTitle), fn($w) => mb_strlen($w) > 3);
            if (count($aiWords) > 0) {
                foreach ($chapter->getSubchapters() as $sub) {
                    $dbSlug = $this->normalizeSlugForMatch($sub->getSlug());
                    $matchesAll = true;
                    foreach ($aiWords as $word) {
                        if (!str_contains($dbSlug, $word)) {
                            $matchesAll = false;
                            break;
                        }
                    }
                    if ($matchesAll) {
                        return $sub;
                    }
                }
            }
        }
        return null;
    }

    private function normalizeSlugForMatch(string $text): string
    {
        return $this->slugger->slug($text)->lower()->toString();
    }

    /**
     * Extrait le contenu H5P d'un exercice. L'IA peut mettre les données dans "content", "params" ou à la racine.
     * Ordre de priorité : content > params > racine (sans type, level, library).
     * @return array<string, mixed>|string|null
     */
    private function extractExerciseContent(array $exercise): array|string|null
    {
        $content = $exercise['content'] ?? null;
        if ($content !== null && (is_array($content) || is_string($content)) && !empty($content)) {
            return $content;
        }
        $params = $exercise['params'] ?? null;
        if ($params !== null && (is_array($params) || is_string($params)) && !empty($params)) {
            return $params;
        }
        $metadataKeys = ['type', 'level', 'library'];
        $root = array_diff_key($exercise, array_flip($metadataKeys));
        if ($root !== []) {
            return $root;
        }
        return null;
    }

    private function extractJson(string $raw): ?array
    {
        $trimmed = trim($raw);
        if (preg_match('/```(?:json)?\s*([\s\S]*?)```/', $trimmed, $m)) {
            $trimmed = trim($m[1]);
        }
        $decoded = json_decode($trimmed, true);
        if (is_array($decoded)) {
            return $decoded;
        }
        return null;
    }

}
