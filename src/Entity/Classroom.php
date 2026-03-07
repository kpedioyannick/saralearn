<?php

declare(strict_types=1);

namespace App\Entity;

use App\Repository\ClassroomRepository;
use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity(repositoryClass: ClassroomRepository::class)]
#[ORM\Table(name: 'classroom')]
#[ORM\UniqueConstraint(name: 'uq_classroom_cycle_slug', columns: ['cycle', 'slug'])]
class Classroom
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(length: 64)]
    private ?string $name = null;
    #[ORM\Column(length: 50, nullable: true)]
    private ?string $priority = null;

    #[ORM\Column(length: 128)]
    private ?string $slug = null;

    #[ORM\Column(length: 32)]
    private ?string $cycle = null;

    /** @var Collection<int, Subject> */
    #[ORM\OneToMany(mappedBy: 'classroom', targetEntity: Subject::class, cascade: ['persist'], orphanRemoval: true)]
    private Collection $subjects;

    public function __construct()
    {
        $this->subjects = new ArrayCollection();
    }

    public function getId(): ?int
    {
        return $this->id;
    }

    public function getName(): ?string
    {
        return $this->name;
    }

    public function getPriority(): ?string
    {
        return $this->priority;
    }

    public function setPriority(?string $priority): static
    {
        $this->priority = $priority;

        return $this;
    }

    public function setName(string $name): static
    {
        $this->name = $name;
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

    public function getCycle(): ?string
    {
        return $this->cycle;
    }

    public function setCycle(string $cycle): static
    {
        $this->cycle = $cycle;
        return $this;
    }

    /** @return Collection<int, Subject> */
    public function getSubjects(): Collection
    {
        return $this->subjects;
    }

    public function addSubject(Subject $subject): static
    {
        if (!$this->subjects->contains($subject)) {
            $this->subjects->add($subject);
            $subject->setClassroom($this);
        }
        return $this;
    }

    public function removeSubject(Subject $subject): static
    {
        if ($this->subjects->removeElement($subject)) {
            if ($subject->getClassroom() === $this) {
                $subject->setClassroom(null);
            }
        }
        return $this;
    }
}
