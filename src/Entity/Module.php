<?php

declare(strict_types=1);

namespace App\Entity;

use App\Repository\ModuleRepository;
use Doctrine\DBAL\Types\Types;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: ModuleRepository::class)]
#[ORM\Table(name: 'module')]
class Module
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\ManyToOne(inversedBy: 'modules')]
    #[ORM\JoinColumn(nullable: false)]
    private ?Subchapter $subchapter = null;

    #[ORM\Column(length: 512)]
    private ?string $title = null;

    #[ORM\ManyToOne]
    #[ORM\JoinColumn(nullable: false)]
    private ?Chapter $chapter = null;

    #[ORM\Column(length: 32)]
    private ?string $bloomLevel = null;

    #[ORM\Column(length: 32)]
    private ?string $difficulty = null;

    #[ORM\Column(length: 64)]
    private ?string $h5pType = null;

    #[ORM\Column(type: Types::TEXT)]
    private ?string $content = null;

    #[ORM\ManyToOne(inversedBy: 'modules')]
    #[ORM\JoinColumn(nullable: true, onDelete: 'SET NULL')]
    private ?Path $path = null;

    #[ORM\Column(type: Types::DATETIME_IMMUTABLE)]
    private ?\DateTimeImmutable $createdAt = null;

    public function __construct()
    {
        $this->createdAt = new \DateTimeImmutable();
    }

    public function getId(): ?int
    {
        return $this->id;
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

    public function getChapter(): ?Chapter
    {
        return $this->chapter;
    }

    public function setChapter(?Chapter $chapter): static
    {
        $this->chapter = $chapter;
        return $this;
    }

    public function getBloomLevel(): ?string
    {
        return $this->bloomLevel;
    }

    public function setBloomLevel(string $bloomLevel): static
    {
        $this->bloomLevel = $bloomLevel;
        return $this;
    }

    public function getDifficulty(): ?string
    {
        return $this->difficulty;
    }

    public function setDifficulty(string $difficulty): static
    {
        $this->difficulty = $difficulty;
        return $this;
    }

    public function getH5pType(): ?string
    {
        return $this->h5pType;
    }

    public function setH5pType(string $h5pType): static
    {
        $this->h5pType = $h5pType;
        return $this;
    }

    public function getContent(): ?string
    {
        return $this->content;
    }

    public function setContent(string $content): static
    {
        $this->content = $content;
        return $this;
    }

    public function getPath(): ?Path
    {
        return $this->path;
    }

    public function setPath(?Path $path): static
    {
        $this->path = $path;
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
}
