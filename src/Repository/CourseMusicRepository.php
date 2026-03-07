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
     * CourseMusic dont le prompt (trim) commence par le préfixe donné (ex. "[Verse]").
     *
     * @return list<CourseMusic>
     */
    public function findWherePromptStartsWith(string $prefix): array
    {
        return $this->createQueryBuilder('cm')
            ->where('cm.prompt IS NOT NULL')
            ->andWhere('TRIM(cm.prompt) LIKE :prefix')
            ->setParameter('prefix', $prefix . '%')
            ->orderBy('cm.id', 'ASC')
            ->getQuery()
            ->getResult();
    }

    /**
     * CourseMusic avec jointures (subchapter, chapter, subject, classroom) pour affichage liste.
     *
     * @param null|'active'|'disabled' $active Filtre par champ active (null = tous)
     * @return list<CourseMusic>
     */
    public function findAllOrdered(?string $active = null): array
    {
        $qb = $this->createQueryBuilder('cm')
            ->join('cm.subchapter', 'sub')
            ->join('sub.chapter', 'ch')
            ->join('ch.subject', 'subj')
            ->join('subj.classroom', 'cl')
            ->orderBy('cm.id', 'ASC');

        if ($active === 'active' || $active === 'disabled') {
            $qb->andWhere('cm.active = :active')->setParameter('active', $active);
        }

        return $qb->getQuery()->getResult();
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
     * CourseMusic avec un prompt mais sans sunoClipId, dont la Classroom a priorité haute.
     *
     * @return list<CourseMusic>
     */
    public function findWithPromptWithoutSunoClipId(int $limit = 50): array
    {
        return $this->createQueryBuilder('cm')
            ->join('cm.subchapter', 'sub')
            ->join('sub.chapter', 'ch')
            ->join('ch.subject', 'subj')
            ->join('subj.classroom', 'cl')
            ->where('cm.prompt IS NOT NULL')
            ->andWhere("cm.prompt <> ''")
            ->andWhere('cm.sunoClipId IS NULL')
            ->andWhere('cl.priority = :highPri')
            ->andWhere('subj.priority != :lowPri OR subj.priority IS NULL')
            ->andWhere('cm.active = :active')
            ->setParameter('highPri', 'high')
            ->setParameter('lowPri', 'low')
            ->setParameter('active', 'active')
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
