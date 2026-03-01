<?php

declare(strict_types=1);

namespace App\Entity;

use App\Repository\ChapterRepository;
use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: ChapterRepository::class)]
#[ORM\Table(name: 'chapter')]
#[ORM\UniqueConstraint(name: 'uq_chapter_subject_slug', columns: ['subject_id', 'slug'])]
class Chapter
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(length: 255)]
    private ?string $title = null;

    #[ORM\Column(length: 255)]
    private ?string $slug = null;

    #[ORM\ManyToOne(inversedBy: 'chapters')]
    #[ORM\JoinColumn(nullable: false)]
    private ?Subject $subject = null;

    /** @var Collection<int, Subchapter> */
    #[ORM\OneToMany(mappedBy: 'chapter', targetEntity: Subchapter::class, cascade: ['persist'], orphanRemoval: true)]
    private Collection $subchapters;

    /** course: tableau [{short: string, text_to_audio: string}] */
    #[ORM\Column(type: 'json', nullable: true)]
    private ?array $course = null;

    /** mindmap: {content: string (PlantUML), text_to_audio: string} */
    #[ORM\Column(type: 'json', nullable: true)]
    private ?array $mindmap = null;

    public function __construct()
    {
        $this->subchapters = new ArrayCollection();
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

    public function getSubject(): ?Subject
    {
        return $this->subject;
    }

    public function setSubject(?Subject $subject): static
    {
        $this->subject = $subject;
        return $this;
    }

    /** @return Collection<int, Subchapter> */
    public function getSubchapters(): Collection
    {
        return $this->subchapters;
    }

    public function addSubchapter(Subchapter $subchapter): static
    {
        if (!$this->subchapters->contains($subchapter)) {
            $this->subchapters->add($subchapter);
            $subchapter->setChapter($this);
        }
        return $this;
    }

    public function removeSubchapter(Subchapter $subchapter): static
    {
        if ($this->subchapters->removeElement($subchapter)) {
            if ($subchapter->getChapter() === $this) {
                $subchapter->setChapter(null);
            }
        }
        return $this;
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
}
