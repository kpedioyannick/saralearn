<?php

declare(strict_types=1);

namespace App\Repository;

use App\Entity\Path;
use App\Entity\Subchapter;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

/**
 * @extends ServiceEntityRepository<Path>
 */
class PathRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, Path::class);
    }

    /**
     * Trouve un Path par sous-chapitre et types (ordre des types normalisé pour comparaison).
     */
    public function findOneBySubchapterAndTypes(Subchapter $subchapter, array $types): ?Path
    {
        $normalized = array_values(array_filter(array_map('trim', $types)));
        sort($normalized);
        $candidates = $this->createQueryBuilder('p')
            ->andWhere('p.category = :category')
            ->andWhere('p.subchapter = :subchapter')
            ->setParameter('category', Path::CATEGORY_H5P_INTERACTIVE_BOOK)
            ->setParameter('subchapter', $subchapter)
            ->getQuery()
            ->getResult();
        foreach ($candidates as $path) {
            $pathTypes = $path->getTypes();
            if ($pathTypes !== null) {
                $sorted = $pathTypes;
                sort($sorted);
                if ($sorted === $normalized) {
                    return $path;
                }
            }
        }
        return null;
    }

    /**
     * Paths de type livre interactif ayant un sous-chapitre.
     *
     * @return Path[]
     */
    public function findInteractiveBooksBySubchapter(Subchapter $subchapter): array
    {
        return $this->createQueryBuilder('p')
            ->andWhere('p.category = :category')
            ->andWhere('p.subchapter = :subchapter')
            ->setParameter('category', Path::CATEGORY_H5P_INTERACTIVE_BOOK)
            ->setParameter('subchapter', $subchapter)
            ->orderBy('p.id', 'ASC')
            ->getQuery()
            ->getResult();
    }

    /**
     * Paths (livres interactifs) pour les sous-chapitres donnés.
     * Utile pour des stats : combien de sous-chapitres ont un livre par preset.
     *
     * @param list<int> $subchapterIds
     * @return Path[]
     */
    public function findBySubchapterIds(array $subchapterIds): array
    {
        if ($subchapterIds === []) {
            return [];
        }
        return $this->createQueryBuilder('p')
            ->andWhere('p.category = :category')
            ->andWhere('p.subchapter IN (:ids)')
            ->setParameter('category', Path::CATEGORY_H5P_INTERACTIVE_BOOK)
            ->setParameter('ids', $subchapterIds)
            ->orderBy('p.subchapter', 'ASC')
            ->addOrderBy('p.id', 'ASC')
            ->getQuery()
            ->getResult();
    }
}
