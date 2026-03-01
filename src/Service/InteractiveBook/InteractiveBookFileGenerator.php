<?php

declare(strict_types=1);

namespace App\Service\InteractiveBook;

use App\Entity\Module;
use App\Entity\Path;

/**
 * Génère content.json et h5p.json pour un livre interactif à partir des modules d'un Path.
 */
final class InteractiveBookFileGenerator
{
    public function __construct(
        private readonly string $projectDir,
        private readonly string $contentBasePath = 'h5p/server/content',
    ) {
    }

    /**
     * Construit le JSON de contenu du livre (structure attendue par H5P.InteractiveBook).
     *
     * @param Module[] $modules
     */
    public function buildContentJson(Path $path, array $modules): string
    {
        $chapters = [];
        foreach ($modules as $module) {
            $contentItem = $this->moduleToContentItem($module);
            $chapters[] = [
                'params' => [
                    'content' => [$contentItem],
                ],
                'library' => H5pLibraryVersionMap::getColumnLibrary(),
                'subContentId' => $this->generateSubContentId(),
                'metadata' => [
                    'contentType' => 'Page',
                    'license' => 'U',
                    'title' => $module->getTitle() ?? 'Untitled Page',
                    'authors' => [],
                    'changes' => [],
                    'extraTitle' => $module->getTitle() ?? 'Untitled Page',
                ],
            ];
        }

        $content = [
            'showCoverPage' => false,
            'bookCover' => [
                'coverDescription' => '<p style="text-align: center;"></p>',
                'coverMedium' => ['params' => (object) []],
            ],
            'chapters' => $chapters,
            'behaviour' => [
                'baseColor' => '#1768c4',
                'defaultTableOfContents' => true,
                'progressIndicators' => true,
                'progressAuto' => true,
                'displaySummary' => true,
                'enableRetry' => true,
            ],
        ];

        $content = array_merge($content, $this->getBookTranslations());

        return json_encode($content, \JSON_THROW_ON_ERROR | \JSON_UNESCAPED_UNICODE | \JSON_UNESCAPED_SLASHES);
    }

    /**
     * Construit h5p.json (identique pour tous les livres, titre personnalisable).
     */
    public function buildH5pJson(string $title): string
    {
        $data = [
            'title' => $title,
            'language' => 'en',
            'mainLibrary' => 'H5P.InteractiveBook',
            'license' => 'U',
            'defaultLanguage' => 'en',
            'embedTypes' => ['div'],
            'preloadedDependencies' => $this->getPreloadedDependencies(),
            'extraTitle' => $title,
        ];

        return json_encode($data, \JSON_THROW_ON_ERROR | \JSON_UNESCAPED_UNICODE);
    }

    /**
     * Écrit content.json et h5p.json dans le dossier du livre (id = Path::id).
     */
    public function writeToDirectory(Path $path, string $contentJson, string $h5pJson): void
    {
        $dir = $this->getDirectoryForPath($path);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
        file_put_contents($dir . '/content.json', $contentJson);
        file_put_contents($dir . '/h5p.json', $h5pJson);
    }

    public function getDirectoryForPath(Path $path): string
    {
        return rtrim($this->projectDir, '/') . '/' . trim($this->contentBasePath, '/') . '/' . $path->getId();
    }

    /**
     * Transforme un Module en entrée "content" pour un chapitre (Column content item).
     */
    private function moduleToContentItem(Module $module): array
    {
        $params = $this->decodeModuleContent($module->getContent());
        $library = H5pLibraryVersionMap::getLibrary($module->getH5pType() ?? '');
        $contentType = $this->libraryToContentType($library);

        return [
            'content' => [
                'params' => $params,
                'library' => $library,
                'metadata' => [
                    'contentType' => $contentType,
                    'license' => 'U',
                    'title' => $module->getTitle() ?? 'Untitled',
                    'authors' => [],
                    'changes' => [],
                    'extraTitle' => $module->getTitle() ?? 'Untitled',
                ],
                'subContentId' => $this->generateSubContentId(),
            ],
            'useSeparator' => 'auto',
        ];
    }

    private function decodeModuleContent(?string $content): array
    {
        if ($content === null || $content === '') {
            return [];
        }
        $decoded = json_decode($content, true, 512, \JSON_THROW_ON_ERROR);
        return is_array($decoded) ? $decoded : [];
    }

    private function generateSubContentId(): string
    {
        return str_replace('-', '', sprintf(
            '%04x%04x-%04x-%04x-%04x-%04x%04x%04x',
            random_int(0, 0xffff),
            random_int(0, 0xffff),
            random_int(0, 0xffff),
            random_int(0, 0x0fff) | 0x4000,
            random_int(0, 0x3fff) | 0x8000,
            random_int(0, 0xffff),
            random_int(0, 0xffff),
            random_int(0, 0xffff),
        ));
    }

    private function libraryToContentType(string $library): string
    {
        $base = explode(' ', $library)[0] ?? '';
        $parts = explode('.', $base);
        return end($parts) ?: 'Content';
    }

    /** @return array<int, array{machineName: string, majorVersion: int, minorVersion: int}> */
    private function getPreloadedDependencies(): array
    {
        return [
            ['machineName' => 'FontAwesome', 'majorVersion' => 4, 'minorVersion' => 5],
            ['machineName' => 'H5P.Transition', 'majorVersion' => 1, 'minorVersion' => 0],
            ['machineName' => 'H5P.FontIcons', 'majorVersion' => 1, 'minorVersion' => 0],
            ['machineName' => 'H5P.JoubelUI', 'majorVersion' => 1, 'minorVersion' => 3],
            ['machineName' => 'H5P.Column', 'majorVersion' => 1, 'minorVersion' => 18],
            ['machineName' => 'H5P.MultiChoice', 'majorVersion' => 1, 'minorVersion' => 16],
            ['machineName' => 'H5P.TrueFalse', 'majorVersion' => 1, 'minorVersion' => 8],
            ['machineName' => 'H5P.Blanks', 'majorVersion' => 1, 'minorVersion' => 14],
            ['machineName' => 'H5P.DragText', 'majorVersion' => 1, 'minorVersion' => 10],
            ['machineName' => 'H5P.MarkTheWords', 'majorVersion' => 1, 'minorVersion' => 11],
            ['machineName' => 'H5P.Summary', 'majorVersion' => 1, 'minorVersion' => 10],
            ['machineName' => 'H5P.SingleChoiceSet', 'majorVersion' => 1, 'minorVersion' => 11],
            ['machineName' => 'H5P.Essay', 'majorVersion' => 1, 'minorVersion' => 5],
            ['machineName' => 'H5P.Dialogcards', 'majorVersion' => 1, 'minorVersion' => 9],
            ['machineName' => 'H5P.InteractiveBook', 'majorVersion' => 1, 'minorVersion' => 11],
        ];
    }

    private function getBookTranslations(): array
    {
        return [
            'read' => 'Read',
            'displayTOC' => "Display 'Table of contents'",
            'hideTOC' => "Hide 'Table of contents'",
            'nextPage' => 'Next page',
            'previousPage' => 'Previous page',
            'chapterCompleted' => 'Page completed!',
            'partCompleted' => '@pages of @total completed',
            'incompleteChapter' => 'Incomplete page',
            'navigateToTop' => 'Navigate to the top',
            'markAsFinished' => 'I have finished this page',
            'fullscreen' => 'Fullscreen',
            'exitFullscreen' => 'Exit fullscreen',
            'bookProgressSubtext' => '@count of @total pages',
            'interactionsProgressSubtext' => '@count of @total interactions',
            'submitReport' => 'Submit Report',
            'restartLabel' => 'Restart',
            'summaryHeader' => 'Summary',
            'allInteractions' => 'All interactions',
            'unansweredInteractions' => 'Unanswered interactions',
            'scoreText' => '@score / @maxscore',
            'leftOutOfTotalCompleted' => '@left of @max interactions completed',
            'noInteractions' => 'No interactions',
            'score' => 'Score',
            'summaryAndSubmit' => 'Summary & submit',
            'noChapterInteractionBoldText' => 'You have not interacted with any pages.',
            'noChapterInteractionText' => 'You have to interact with at least one page before you can see the summary.',
            'yourAnswersAreSubmittedForReview' => 'Your answers are submitted for review!',
            'bookProgress' => 'Book progress',
            'interactionsProgress' => 'Interactions progress',
            'totalScoreLabel' => 'Total score',
            'a11y' => ['progress' => 'Page @page of @total.', 'menu' => 'Toggle navigation menu'],
        ];
    }
}
