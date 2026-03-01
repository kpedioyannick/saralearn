<?php

declare(strict_types=1);

namespace App\Entity;

use App\Repository\CourseMusicRepository;
use Doctrine\DBAL\Types\Types;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: CourseMusicRepository::class)]
#[ORM\Table(name: 'course_music')]
class CourseMusic
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\ManyToOne(inversedBy: 'courseMusics')]
    #[ORM\JoinColumn(nullable: false, onDelete: 'CASCADE')]
    private ?Subchapter $subchapter = null;

    #[ORM\Column(length: 255, nullable: true)]
    private ?string $sunoTaskId = null;

    #[ORM\Column(length: 2048, nullable: true)]
    private ?string $audioUrl = null;

    #[ORM\Column(type: Types::TEXT, nullable: true)]
    private ?string $prompt = null;

    #[ORM\Column(length: 255, nullable: true)]
    private ?string $title = null;

    #[ORM\Column(type: Types::FLOAT, nullable: true)]
    private ?float $duration = null;

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

    public function getSunoTaskId(): ?string
    {
        return $this->sunoTaskId;
    }

    public function setSunoTaskId(?string $sunoTaskId): static
    {
        $this->sunoTaskId = $sunoTaskId;
        return $this;
    }

    public function getAudioUrl(): ?string
    {
        return $this->audioUrl;
    }

    public function setAudioUrl(?string $audioUrl): static
    {
        $this->audioUrl = $audioUrl;
        return $this;
    }

    public function getPrompt(): ?string
    {
        return $this->prompt;
    }

    public function setPrompt(?string $prompt): static
    {
        $this->prompt = $prompt;
        return $this;
    }

    public function getTitle(): ?string
    {
        return $this->title;
    }

    public function setTitle(?string $title): static
    {
        $this->title = $title;
        return $this;
    }

    public function getDuration(): ?float
    {
        return $this->duration;
    }

    public function setDuration(?float $duration): static
    {
        $this->duration = $duration;
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
