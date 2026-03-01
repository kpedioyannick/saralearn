<?php

declare(strict_types=1);

namespace App\Command;

use App\Repository\ClassroomRepository;
use App\Repository\CourseMusicRepository;
use App\Repository\SubchapterRepository;
use App\Repository\SubjectRepository;
use App\Service\Suno\CourseMusicPromptGenerator;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:generate-course-music-prompt',
    description: 'Génère le prompt (max 400 car.) pour la musique du cours via le provider curl, et le sauvegarde dans CourseMusic.',
)]
final class GenerateCourseMusicPromptCommand extends Command
{
    public function __construct(
        private readonly SubchapterRepository $subchapterRepository,
        private readonly CourseMusicRepository $courseMusicRepository,
        private readonly ClassroomRepository $classroomRepository,
        private readonly SubjectRepository $subjectRepository,
        private readonly CourseMusicPromptGenerator $promptGenerator,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addOption('classroom', null, InputOption::VALUE_OPTIONAL, 'ID ou slug de la classe (à utiliser avec --subject)')
            ->addOption('subject', null, InputOption::VALUE_OPTIONAL, 'ID ou slug de la matière (à utiliser avec --classroom)')
            ->addOption('subchapter', null, InputOption::VALUE_OPTIONAL, 'ID ou slug d\'un seul sous-chapitre à traiter')
            ->addOption('dry-run', null, InputOption::VALUE_NONE, 'Afficher le prompt sans créer/mettre à jour CourseMusic')
            ->addOption('force', null, InputOption::VALUE_NONE, 'Régénérer le prompt même si CourseMusic existe déjà');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $classroomOpt = $input->getOption('classroom') !== null ? trim((string) $input->getOption('classroom')) : null;
        $subjectOpt = $input->getOption('subject') !== null ? trim((string) $input->getOption('subject')) : null;
        $subchapterOpt = $input->getOption('subchapter') !== null ? trim((string) $input->getOption('subchapter')) : null;
        $dryRun = (bool) $input->getOption('dry-run');
        $force = (bool) $input->getOption('force');

        if ($subchapterOpt !== null && $subchapterOpt !== '') {
            $subchapter = is_numeric($subchapterOpt)
                ? $this->subchapterRepository->find((int) $subchapterOpt)
                : $this->subchapterRepository->findOneBy(['slug' => $subchapterOpt]);
            if ($subchapter === null) {
                $io->error(sprintf('Sous-chapitre introuvable : %s', $subchapterOpt));
                return Command::FAILURE;
            }
            if (!$subchapter->isCourseType()) {
                $io->error('Seuls les sous-chapitres de type "Cours" sont traités.');
                return Command::FAILURE;
            }
            $subchapters = [$subchapter];
        } elseif ($classroomOpt !== null && $classroomOpt !== '' && $subjectOpt !== null && $subjectOpt !== '') {
            $classroom = $this->classroomRepository->resolveOne($classroomOpt);
            if ($classroom === null) {
                $io->error(sprintf('Classe introuvable : %s', $classroomOpt));
                return Command::FAILURE;
            }
            $subject = $this->subjectRepository->findOneByClassroomAndSubject($classroom, $subjectOpt);
            if ($subject === null) {
                $io->error(sprintf('Matière introuvable pour la classe : %s', $subjectOpt));
                return Command::FAILURE;
            }
            $subchapters = array_values(array_filter(
                $this->subchapterRepository->findBySubject($subject),
                static fn (\App\Entity\Subchapter $s) => $s->isCourseType(),
            ));
        } else {
            $subchapters = array_values(array_filter(
                $this->subchapterRepository->findBy([], ['id' => 'ASC']),
                static fn (\App\Entity\Subchapter $s) => $s->isCourseType(),
            ));
        }

        $withCourse = array_filter($subchapters, static function ($s) {
            $c = $s->getCourse();
            return $c !== null && is_array($c) && $c !== [];
        });
        if ($withCourse === []) {
            $io->warning('Aucun sous-chapitre avec un cours trouvé.');
            return Command::SUCCESS;
        }

        if (!$force) {
            $withMusicIds = $this->courseMusicRepository->getSubchapterIdsWithMusic(array_values($withCourse));
            $toProcess = array_values(array_filter($withCourse, static fn ($s) => !isset($withMusicIds[$s->getId()])));
        } else {
            $toProcess = array_values($withCourse);
        }

        if ($toProcess === []) {
            $io->success('Aucun sous-chapitre à traiter (tous ont déjà un prompt, utilisez --force pour régénérer).');
            return Command::SUCCESS;
        }

        $io->title(sprintf('Génération prompt musique (curl, max 400 car.) : %d sous-chapitre(s)', count($toProcess)));
        if ($dryRun) {
            foreach ($toProcess as $subchapter) {
                $io->section($subchapter->getTitle() ?? '(sans titre)');
                try {
                    $prompt = $this->promptGenerator->generatePromptForSubchapter($subchapter);
                    $io->text($prompt);
                    $io->text(sprintf('[%d caractères]', mb_strlen($prompt)));
                } catch (\Throwable $e) {
                    $io->error($e->getMessage());
                }
            }
            return Command::SUCCESS;
        }

        $ok = 0;
        foreach ($toProcess as $subchapter) {
            $io->text(sprintf('Prompt : %s…', $subchapter->getTitle()));
            try {
                $this->promptGenerator->createOrUpdatePromptForSubchapter($subchapter);
                $io->text('  → OK');
                $ok++;
            } catch (\Throwable $e) {
                $io->warning(sprintf('  → Erreur : %s', $e->getMessage()));
            }
        }

        $io->success(sprintf('Terminé. %d prompt(s) créé(s) ou mis à jour.', $ok));
        return Command::SUCCESS;
    }
}
