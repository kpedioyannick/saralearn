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

    /**
     * CourseMusic avec un prompt mais sans sunoClipId.
     *
     * @return list<CourseMusic>
     */
    public function findWithPromptWithoutSunoClipId(int $limit = 50): array
    {
        return $this->createQueryBuilder('cm')
            ->where('cm.prompt IS NOT NULL')
            ->andWhere("cm.prompt <> ''")
            ->andWhere('cm.sunoClipId IS NULL')
            ->orderBy('cm.id', 'ASC')
            ->setMaxResults($limit)
            ->getQuery()
            ->getResult();
    }

    /**
     * CourseMusic avec audio (ou un id Suno) mais sans videoUrl, pour --fill-video.
     *
     * @return list<CourseMusic>
     */
    public function findWithAudioWithoutVideo(int $limit = 500): array
    {
        return $this->createQueryBuilder('cm')
            ->where('cm.videoUrl IS NULL')
            ->andWhere('cm.sunoTaskId IS NOT NULL OR cm.sunoClipId IS NOT NULL')
            ->orderBy('cm.id', 'ASC')
            ->setMaxResults($limit)
            ->getQuery()
            ->getResult();
    }

    /**
     * CourseMusic avec sunoClipId mais sans videoUrl (pour ManageSunoVideoCommand).
     *
     * @return list<CourseMusic>
     */
    public function findWithClipIdWithoutVideo(int $limit = 500): array
    {
        return $this->createQueryBuilder('cm')
            ->where('cm.sunoClipId IS NOT NULL')
            ->andWhere('cm.sunoClipId <> \'\'')
            ->andWhere('cm.videoUrl IS NULL')
            ->orderBy('cm.id', 'ASC')
            ->setMaxResults($limit)
            ->getQuery()
            ->getResult();
    }

    /**
     * Nombre de sous-chapitres (parmi les ids donnés) ayant au moins une CourseMusic avec prompt non vide.
     *
     * @param list<int> $subchapterIds
     */
    public function countDistinctSubchaptersWithPrompt(array $subchapterIds): int
    {
        if ($subchapterIds === []) {
            return 0;
        }
        return (int) $this->createQueryBuilder('cm')
            ->select('COUNT(DISTINCT cm.subchapter)')
            ->where('cm.subchapter IN (:ids)')
            ->andWhere('cm.prompt IS NOT NULL')
            ->andWhere("cm.prompt <> ''")
            ->setParameter('ids', $subchapterIds)
            ->getQuery()
            ->getSingleScalarResult();
    }

    /**
     * Nombre de sous-chapitres (parmi les ids donnés) ayant au moins une CourseMusic avec audioUrl non vide.
     *
     * @param list<int> $subchapterIds
     */
    public function countDistinctSubchaptersWithAudio(array $subchapterIds): int
    {
        if ($subchapterIds === []) {
            return 0;
        }
        return (int) $this->createQueryBuilder('cm')
            ->select('COUNT(DISTINCT cm.subchapter)')
            ->where('cm.subchapter IN (:ids)')
            ->andWhere('cm.audioUrl IS NOT NULL')
            ->andWhere("cm.audioUrl <> ''")
            ->setParameter('ids', $subchapterIds)
            ->getQuery()
            ->getSingleScalarResult();
    }

    /**
     * Nombre de sous-chapitres (parmi les ids donnés) ayant au moins une CourseMusic avec audioUrl et videoUrl non vides.
     *
     * @param list<int> $subchapterIds
     */
    public function countDistinctSubchaptersWithAudioAndVideo(array $subchapterIds): int
    {
        if ($subchapterIds === []) {
            return 0;
        }
        return (int) $this->createQueryBuilder('cm')
            ->select('COUNT(DISTINCT cm.subchapter)')
            ->where('cm.subchapter IN (:ids)')
            ->andWhere('cm.audioUrl IS NOT NULL')
            ->andWhere("cm.audioUrl <> ''")
            ->andWhere('cm.videoUrl IS NOT NULL')
            ->andWhere("cm.videoUrl <> ''")
            ->setParameter('ids', $subchapterIds)
            ->getQuery()
            ->getSingleScalarResult();
    }
}
