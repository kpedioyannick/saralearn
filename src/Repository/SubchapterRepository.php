<?php

declare(strict_types=1);

namespace App\Repository;

use App\Entity\Subject;
use App\Entity\Subchapter;
use Doctrine\Bundle\DoctrineBundle\Repository\ServiceEntityRepository;
use Doctrine\Persistence\ManagerRegistry;

/**
 * @extends ServiceEntityRepository<Subchapter>
 */
class SubchapterRepository extends ServiceEntityRepository
{
    public function __construct(ManagerRegistry $registry)
    {
        parent::__construct($registry, Subchapter::class);
    }

    public function findOneByChapterAndSlug(int $chapterId, string $slug): ?Subchapter
    {
        return $this->findOneBy(['chapter' => $chapterId, 'slug' => $slug], orderBy: []);
    }

    /**
     * Retourne tous les sous-chapitres d'une matière, ordonnés par id.
     * @return list<Subchapter>
     */
    public function findBySubject(Subject $subject): array
    {
        $qb = $this->createQueryBuilder('s')
            ->join('s.chapter', 'c')
            ->where('c.subject = :subject')
            ->setParameter('subject', $subject)
            ->orderBy('s.id', 'ASC');
        return $qb->getQuery()->getResult();
    }

    /**
     * Nombre de sous-chapitres type Cours avec contexte (chapitre → matière → classe).
     */
    public function countWithContext(): int
    {
        return (int) $this->createQueryBuilder('s')
            ->select('COUNT(s.id)')
            ->join('s.chapter', 'c')
            ->join('c.subject', 'subj')
            ->join('subj.classroom', 'cl')
            ->andWhere('s.type = :type')
            ->setParameter('type', Subchapter::TYPE_COURS)
            ->getQuery()
            ->getSingleScalarResult();
    }

    /**
     * Nombre de sous-chapitres avec contexte qui ont au moins une CourseMusic avec prompt non vide.
     */
    public function countWithContextWithPrompt(): int
    {
        return (int) $this->createQueryBuilder('s')
            ->select('COUNT(DISTINCT s.id)')
            ->join('s.chapter', 'c')
            ->join('c.subject', 'subj')
            ->join('subj.classroom', 'cl')
            ->join('s.courseMusics', 'cm')
            ->andWhere('s.type = :type')
            ->andWhere('cm.prompt IS NOT NULL')
            ->andWhere("cm.prompt != ''")
            ->setParameter('type', Subchapter::TYPE_COURS)
            ->getQuery()
            ->getSingleScalarResult();
    }

    /**
     * Sous-chapitres avec contexte qui n'ont pas encore de CourseMusic (donc pas de prompt enregistré).
     * Pour l'API liste : ne retourner que les sous-chapitres à remplir.
     *
     * @return list<Subchapter>
     */
    public function findWithContextWithoutCourseMusicOrderById(int $limit = 50): array
    {
        return $this->createQueryBuilder('s')
            ->join('s.chapter', 'c')
            ->join('c.subject', 'subj')
            ->join('subj.classroom', 'cl')
            ->andWhere('s.type = :type')
            ->andWhere('SIZE(s.courseMusics) = 0')
            ->setParameter('type', Subchapter::TYPE_COURS)
            ->orderBy('s.id', 'ASC')
            ->setMaxResults($limit)
            ->getQuery()
            ->getResult();
    }
}
