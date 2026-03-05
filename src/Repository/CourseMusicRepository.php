<?php

declare(strict_types=1);

namespace App\Repository;

use App\Entity\CourseMusic;
use App\Entity\Subchapter;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

/**
 * @extends ServiceEntityRepository<CourseMusic>
 */
class CourseMusicRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, CourseMusic::class);
    }

    public function findOneBySubchapter(Subchapter $subchapter): ?CourseMusic
    {
        return $this->findOneBy(
            ['subchapter' => $subchapter],
            ['createdAt' => 'DESC'],
        );
    }

    /**
     * Sous-chapitres de la liste qui ont déjà une CourseMusic.
     *
     * @param list<Subchapter> $subchapters
     * @return array<int, true> map subchapterId => true
     */
    public function getSubchapterIdsWithMusic(array $subchapters): array
    {
        if ($subchapters === []) {
            return [];
        }
        $ids = array_map(static fn (Subchapter $s) => $s->getId(), $subchapters);
        $result = $this->createQueryBuilder('cm')
            ->select('IDENTITY(cm.subchapter) as id')
            ->where('cm.subchapter IN (:ids)')
            ->setParameter('ids', $ids)
            ->getQuery()
            ->getSingleColumnResult();
        return array_flip(array_map('intval', $result));
    }

    /**
     * CourseMusic avec un prompt mais sans tâche Suno ou sans URL audio.
     *
     * Utilisé par la commande de gestion Suno pour (re)lancer les générations
     * uniquement là où il manque encore les données distantes.
     *
     * @return list<CourseMusic>
     */
    public function findNeedingSunoGeneration(): array
    {
        return $this->createQueryBuilder('cm')
            ->where('cm.prompt IS NOT NULL')
            ->andWhere('cm.prompt <> \'\'')
            ->andWhere('cm.sunoTaskId IS NULL OR cm.audioUrl IS NULL')
            ->orderBy('cm.id', 'ASC')
            ->getQuery()
            ->getResult();
    }
}
