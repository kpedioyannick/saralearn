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
}
