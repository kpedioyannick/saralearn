<?php

declare(strict_types=1);

namespace App\Entity;

use App\Repository\SubchapterRepository;
use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: SubchapterRepository::class)]
#[ORM\Table(name: 'subchapter')]
class Subchapter
{
    /** Type « Cours » : sous-chapitre de type leçon (génération cours, modules, livres). Les « Quiz » sont exclus. */
    public const TYPE_COURS = 'Cours';

    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(length: 1024)]
    private ?string $title = null;

    #[ORM\Column(length: 1024)]
    private ?string $slug = null;

    #[ORM\Column(length: 1024, nullable: true)]
    private ?string $href = null;

    #[ORM\Column(length: 32, nullable: true)]
    private ?string $type = null;

    #[ORM\ManyToOne(inversedBy: 'subchapters')]
    #[ORM\JoinColumn(nullable: false)]
    private ?Chapter $chapter = null;

    /** @var Collection<int, Module> */
    #[ORM\OneToMany(mappedBy: 'subchapter', targetEntity: Module::class)]
    private Collection $modules;

    /** @var Collection<int, CourseMusic> */
    #[ORM\OneToMany(mappedBy: 'subchapter', targetEntity: CourseMusic::class, cascade: ['persist', 'remove'])]
    private Collection $courseMusics;

    /** course: tableau [{short: string, text_to_audio: string}] */
    #[ORM\Column(type: 'json', nullable: true)]
    private ?array $course = null;

    /** mindmap: {content: string (PlantUML), text_to_audio: string} */
    #[ORM\Column(type: 'json', nullable: true)]
    private ?array $mindmap = null;

    public function __construct()
    {
        $this->modules = new ArrayCollection();
        $this->courseMusics = new ArrayCollection();
    }

    public function getId(): ?int
    {
        return $this->id;
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

    public function getSlug(): ?string
    {
        return $this->slug;
    }

    public function setSlug(string $slug): static
    {
        $this->slug = $slug;
        return $this;
    }

    public function getHref(): ?string
    {
        return $this->href;
    }

    public function setHref(?string $href): static
    {
        $this->href = $href;
        return $this;
    }

    public function getType(): ?string
    {
        return $this->type;
    }

    public function isCourseType(): bool
    {
        return $this->type === self::TYPE_COURS;
    }

    public function setType(?string $type): static
    {
        $this->type = $type;
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

    /** @return Collection<int, Module> */
    public function getModules(): Collection
    {
        return $this->modules;
    }

    /** @return array<int, array{short?: string, text_to_audio?: string}>|null */
    public function getCourse(): ?array
    {
        return $this->course;
    }

    /** @param array<int, array{short?: string, text_to_audio?: string}>|null $course */
    public function setCourse(?array $course): static
    {
        $this->course = $course;
        return $this;
    }

    /** @return array{content?: string, text_to_audio?: string}|null */
    public function getMindmap(): ?array
    {
        return $this->mindmap;
    }

    /** @param array{content?: string, text_to_audio?: string}|null $mindmap */
    public function setMindmap(?array $mindmap): static
    {
        $this->mindmap = $mindmap;
        return $this;
    }

    /** @return Collection<int, CourseMusic> */
    public function getCourseMusics(): Collection
    {
        return $this->courseMusics;
    }

    public function addCourseMusic(CourseMusic $courseMusic): static
    {
        if (!$this->courseMusics->contains($courseMusic)) {
            $this->courseMusics->add($courseMusic);
            $courseMusic->setSubchapter($this);
        }
        return $this;
    }
}
