<?php

declare(strict_types=1);

namespace App\Entity;

use App\Repository\PathRepository;
use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\DBAL\Types\Types;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: PathRepository::class)]
#[ORM\Table(name: 'learning_path')]
class Path
{
    public const CATEGORY_H5P_INTERACTIVE_BOOK = 'H5pInteractiveBook';

    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(length: 64)]
    private string $category = self::CATEGORY_H5P_INTERACTIVE_BOOK;

    #[ORM\ManyToOne]
    #[ORM\JoinColumn(nullable: false)]
    private ?Chapter $chapter = null;

    #[ORM\ManyToOne]
    #[ORM\JoinColumn(nullable: true, onDelete: 'CASCADE')]
    private ?Subchapter $subchapter = null;

    #[ORM\Column(length: 1024)]
    private ?string $title = null;

    /** @var Collection<int, Module> */
    #[ORM\OneToMany(mappedBy: 'path', targetEntity: Module::class, cascade: ['persist'], orphanRemoval: false)]
    #[ORM\OrderBy(['id' => 'ASC'])]
    private Collection $modules;

    /**
     * Apprenants (users) assignés à ce path.
     *
     * @var Collection<int, User>
     */
    #[ORM\ManyToMany(targetEntity: User::class, inversedBy: 'paths', cascade: ['persist'])]
    #[ORM\JoinTable(name: 'learning_path_learner')]
    #[ORM\JoinColumn(name: 'learning_path_id', referencedColumnName: 'id', onDelete: 'CASCADE')]
    #[ORM\InverseJoinColumn(name: 'user_id', referencedColumnName: 'id', onDelete: 'CASCADE')]
    private Collection $learners;

    /**
     * Niveau(x) de Bloom couvert(s) par ce livre interactif (tableau de chaînes).
     * Ex. : ["remember"] ou ["remember", "understand", "apply"].
     * Les modules rattachés à ce Path ont leur bloomLevel parmi ces types.
     *
     * @var list<string>|null
     */
    #[ORM\Column(type: Types::JSON, nullable: true)]
    private ?array $types = null;

    #[ORM\Column(length: 1024)]
    private ?string $outputPath = null;

    #[ORM\Column(type: Types::DATETIME_IMMUTABLE)]
    private ?\DateTimeImmutable $createdAt = null;

    public function __construct()
    {
        $this->modules = new ArrayCollection();
        $this->learners = new ArrayCollection();
        $this->createdAt = new \DateTimeImmutable();
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getCategory(): string
    {
        return $this->category;
    }

    public function setCategory(string $category): static
    {
        $this->category = $category;
        return $this;
    }

    public function getChapter(): ?Chapter
    {
        return $this->chapter;
    }

    public function setChapter(?Chapter $chapter): static
    {
        $this->chapter = $chapter;
        return $this;
    }

    public function getSubchapter(): ?Subchapter
    {
        return $this->subchapter;
    }

    public function setSubchapter(?Subchapter $subchapter): static
    {
        $this->subchapter = $subchapter;
        return $this;
    }

    public function getTitle(): ?string
    {
        return $this->title;
    }

    public function setTitle(string $title): static
    {
        $this->title = $title;
        return $this;
    }

    /** @return Collection<int, Module> */
    public function getModules(): Collection
    {
        return $this->modules;
    }

    public function addModule(Module $module): static
    {
        if (!$this->modules->contains($module)) {
            $this->modules->add($module);
            $module->setPath($this);
        }
        return $this;
    }

    public function removeModule(Module $module): static
    {
        if ($this->modules->removeElement($module)) {
            if ($module->getPath() === $this) {
                $module->setPath(null);
            }
        }
        return $this;
    }

    /** @return Collection<int, User> */
    public function getLearners(): Collection
    {
        return $this->learners;
    }

    public function addLearner(User $learner): static
    {
        if (!$this->learners->contains($learner)) {
            $this->learners->add($learner);
        }
        return $this;
    }

    public function removeLearner(User $learner): static
    {
        $this->learners->removeElement($learner);
        return $this;
    }

    /**
     * @return list<string>|null
     */
    public function getTypes(): ?array
    {
        return $this->types;
    }

    /**
     * @param list<string>|null $types
     */
    public function setTypes(?array $types): static
    {
        $this->types = $types === null ? null : array_values(array_filter(array_map('trim', $types)));
        return $this;
    }

    /**
     * Retourne les niveaux Bloom couverts par ce path.
     *
     * @return list<string>
     */
    public function getBloomLevels(): array
    {
        return $this->types ?? [];
    }

    public function getOutputPath(): ?string
    {
        return $this->outputPath;
    }

    public function setOutputPath(string $outputPath): static
    {
        $this->outputPath = $outputPath;
        return $this;
    }

    public function getCreatedAt(): ?\DateTimeImmutable
    {
        return $this->createdAt;
    }

    public function setCreatedAt(\DateTimeImmutable $createdAt): static
    {
        $this->createdAt = $createdAt;
        return $this;
    }

    /**
     * Récupère la session utilisateur pour ce path (fichier JSON de reprise H5P).
     * Le répertoire de contenu est celui du path (outputPath) ; les sessions sont dans {outputPath}/sessions/.
     */
    public function getUserSession(string $userSessionId): ?array
    {
        $contentDir = $this->getOutputPath();
        if ($contentDir === null || $contentDir === '') {
            return null;
        }
        $userSessionPath = rtrim($contentDir, \DIRECTORY_SEPARATOR) . \DIRECTORY_SEPARATOR . 'sessions' . \DIRECTORY_SEPARATOR . $userSessionId . '.json';
        if (!is_file($userSessionPath)) {
            return null;
        }

        try {
            $content = file_get_contents($userSessionPath);
            if ($content === false) {
                return null;
            }
            $userSessions = json_decode($content, true);

            $modification = @filemtime($userSessionPath) ?: @filectime($userSessionPath);
            $updatedAt = $modification ? date('Y-m-d H:i:s', $modification) : null;

            if (!isset($userSessions['resume'])) {
                return null;
            }
            $progress = $this->getH5PBookProgress($userSessions);
            if ($progress === null) {
                return null;
            }

            return [
                'updatedAt' => $updatedAt,
                'progress' => $progress,
            ];
        } catch (\Throwable) {
            return null;
        }
    }

    /**
     * @param array{resume?: array<int, array{state?: string}>} $resume
     * @return array{score: int, maxScore: int, scorePercent: float, completedChapters: int, totalChapters: int, bookProgressPercent: float}|null
     */
    public function getH5PBookProgress(array $resume): ?array
    {
        if (!isset($resume['resume'][0]['state'])) {
            return null;
        }

        $stateJson = json_decode($resume['resume'][0]['state'], true);
        if (!is_array($stateJson)) {
            return null;
        }

        $score = isset($stateJson['score']) ? (int) $stateJson['score'] : 0;
        $maxScore = isset($stateJson['maxScore']) ? (int) $stateJson['maxScore'] : 0;

        $completedCount = 0;
        $totalChapters = 0;
        if (isset($stateJson['chapters']) && is_array($stateJson['chapters'])) {
            foreach ($stateJson['chapters'] as $chapter) {
                $totalChapters++;
                if (isset($chapter['completed']) && $chapter['completed'] === true) {
                    $completedCount++;
                }
            }
        }
        $bookProgressPercent = $totalChapters > 0 ? round(($completedCount / $totalChapters) * 100, 2) : 0;
        $scorePercent = $maxScore > 0 ? round(($score / $maxScore) * 100, 2) : 0;

        return [
            'score' => $score,
            'maxScore' => $maxScore,
            'scorePercent' => $scorePercent,
            'completedChapters' => $completedCount,
            'totalChapters' => $totalChapters,
            'bookProgressPercent' => $bookProgressPercent,
        ];
    }
}
