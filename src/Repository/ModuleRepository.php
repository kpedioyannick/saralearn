<?php

declare(strict_types=1);

namespace App\Repository;

use App\Entity\Module;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

/**
 * @extends ServiceEntityRepository<Module>
 */
class ModuleRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, Module::class);
    }

    /**
     * @return Module[]
     */
    public function findBySubchapterAndBloomLevel(int $subchapterId, string $bloomLevel): array
    {
        return $this->findBy(
            ['subchapter' => $subchapterId, 'bloomLevel' => $bloomLevel],
            ['difficulty' => 'ASC', 'id' => 'ASC'],
        );
    }

    /**
     * Modules d'un sous-chapitre dont le niveau Bloom est dans la liste.
     *
     * @param list<string> $bloomLevels
     * @return Module[]
     */
    public function findBySubchapterAndBloomLevels(int $subchapterId, array $bloomLevels): array
    {
        if ($bloomLevels === []) {
            return [];
        }
        $qb = $this->createQueryBuilder('m')
            ->andWhere('m.subchapter = :subchapterId')
            ->andWhere('m.bloomLevel IN (:levels)')
            ->setParameter('subchapterId', $subchapterId)
            ->setParameter('levels', $bloomLevels)
            ->orderBy('m.bloomLevel', 'ASC')
            ->addOrderBy('m.difficulty', 'ASC')
            ->addOrderBy('m.id', 'ASC');
        return $qb->getQuery()->getResult();
    }

    /**
     * Pour une liste de sous-chapitres, retourne les paires (subchapter_id, bloom_level) présentes.
     * Utile pour des stats : combien de sous-chapitres ont au moins un module par niveau Bloom.
     *
     * @param list<int> $subchapterIds
     * @return array<int, list<string>> subchapterId => liste des bloom_level présents
     */
    public function getSubchapterIdsByBloomLevel(array $subchapterIds): array
    {
        if ($subchapterIds === []) {
            return [];
        }
        $qb = $this->createQueryBuilder('m')
            ->select('s.id AS subchapterId', 'm.bloomLevel')
            ->join('m.subchapter', 's')
            ->andWhere('s.id IN (:ids)')
            ->setParameter('ids', $subchapterIds)
            ->groupBy('s.id', 'm.bloomLevel');
        $rows = $qb->getQuery()->getResult();
        $bySubchapter = [];
        foreach ($rows as $row) {
            $id = (int) $row['subchapterId'];
            if (!isset($bySubchapter[$id])) {
                $bySubchapter[$id] = [];
            }
            $bySubchapter[$id][] = $row['bloomLevel'];
        }
        return $bySubchapter;
    }

    /**
     * Nombre total de modules pour les sous-chapitres donnés.
     *
     * @param list<int> $subchapterIds
     */
    public function countBySubchapterIds(array $subchapterIds): int
    {
        if ($subchapterIds === []) {
            return 0;
        }
        return (int) $this->createQueryBuilder('m')
            ->select('COUNT(m.id)')
            ->andWhere('m.subchapter IN (:ids)')
            ->setParameter('ids', $subchapterIds)
            ->getQuery()
            ->getSingleScalarResult();
    }
}
