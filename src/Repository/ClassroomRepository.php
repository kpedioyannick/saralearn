<?php

declare(strict_types=1);

namespace App\Repository;

use App\Entity\Classroom;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

/**
 * @extends ServiceEntityRepository<Classroom>
 */
class ClassroomRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, Classroom::class);
    }

    public function findOneByCycleAndSlug(string $cycle, string $slug): ?Classroom
    {
        return $this->findOneBy(['cycle' => $cycle, 'slug' => $slug], orderBy: []);
    }

    /**
     * Trouve une classe par ID ou slug.
     * @param int|string $classroom ID ou slug de la classe
     */
    public function resolveOne(int|string $classroom): ?Classroom
    {
        if (is_numeric($classroom)) {
            return $this->find((int) $classroom);
        }
        $c = $this->findOneBy(['slug' => (string) $classroom]);
        if ($c !== null) {
            return $c;
        }
        return $this->findOneBy(['name' => (string) $classroom]);
    }
}
