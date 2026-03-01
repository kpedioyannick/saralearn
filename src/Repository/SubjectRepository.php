<?php

declare(strict_types=1);

namespace App\Repository;

use App\Entity\Classroom;
use App\Entity\Subject;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

/**
 * @extends ServiceEntityRepository<Subject>
 */
class SubjectRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, Subject::class);
    }

    public function findOneByClassroomAndSlug(int $classroomId, string $slug): ?Subject
    {
        return $this->findOneBy(['classroom' => $classroomId, 'slug' => $slug], orderBy: []);
    }

    /**
     * Trouve une matière par classe + matière (ID ou slug pour chacun).
     * Pour le cron : classroom et subject obligatoires.
     */
    public function findOneByClassroomAndSubject(Classroom $classroom, int|string $subject): ?Subject
    {
        if (is_numeric($subject)) {
            $s = $this->find((int) $subject);
            return $s !== null && $s->getClassroom()?->getId() === $classroom->getId() ? $s : null;
        }
        $slug = (string) $subject;
        $bySlug = $this->findOneBy(['classroom' => $classroom, 'slug' => $slug], orderBy: []);
        if ($bySlug !== null) {
            return $bySlug;
        }
        return $this->findOneBy(['classroom' => $classroom, 'name' => $slug], orderBy: []);
    }
}
