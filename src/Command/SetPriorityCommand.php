<?php

declare(strict_types=1);

namespace App\Command;

use App\Repository\ClassroomRepository;
use App\Repository\SubjectRepository;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'app:priority:set',
    description: 'Set priority on classroom and/or subject',
)]
class SetPriorityCommand extends Command
{

    private const LOW_PRIORITY_SUBJECT_SLUGS = [
        'stage',
        'lépreuve-orale', // Updated with the é 
        'technologie',
    ];

    private const HIGH_PRIORITY_CLASSROOM_NAMES = [
        '3eme',
        '4eme',
        '5eme',
        '6eme',
    ];

    public function __construct(
        private readonly ClassroomRepository $classroomRepository,
        private readonly SubjectRepository $subjectRepository,
        private readonly EntityManagerInterface $entityManager
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this
            ->addOption('classroom', 'c', InputOption::VALUE_OPTIONAL, 'The slug of the classroom')
            ->addOption('subject', 's', InputOption::VALUE_OPTIONAL, 'The slug of the subject (requires classroom)')
            ->addOption('priority', 'p', InputOption::VALUE_OPTIONAL, 'The priority to set (low, medium, high)');
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $classroomSlug = $input->getOption('classroom');
        $subjectSlug = $input->getOption('subject');
        $priority = $input->getOption('priority');

        if ($classroomSlug || $subjectSlug || $priority) {
            return $this->processManualInput($io, $classroomSlug, $subjectSlug, $priority);
        }

        $io->title('Application des priorités codées en dur (hardcoded)');
        
        $this->processHardcodedPriorities($io);

        return Command::SUCCESS;
    }

    private function processManualInput(SymfonyStyle $io, ?string $classroomSlug, ?string $subjectSlug, ?string $priority): int
    {
        if (!in_array($priority, ['low', 'medium', 'high'], true)) {
            $io->error('Priority must be low, medium, or high.');
            return Command::FAILURE;
        }

        if (!$classroomSlug) {
            $io->error('You must specify a classroom slug.');
            return Command::FAILURE;
        }

        $classroom = $this->classroomRepository->findOneBy(['slug' => $classroomSlug]);
        if (!$classroom) {
            $io->error(sprintf('Classroom "%s" not found.', $classroomSlug));
            return Command::FAILURE;
        }

        if ($subjectSlug) {
            $subject = $this->subjectRepository->findOneByClassroomAndSubject($classroom, $subjectSlug);
            if (!$subject) {
                $io->error(sprintf('Subject "%s" not found for classroom "%s".', $subjectSlug, $classroomSlug));
                return Command::FAILURE;
            }
            $subject->setPriority($priority);
            $io->success(sprintf('Priority "%s" set for subject "%s" in classroom "%s".', $priority, $subjectSlug, $classroomSlug));
        } else {
            $classroom->setPriority($priority);
            $io->success(sprintf('Priority "%s" set for classroom "%s".', $priority, $classroomSlug));
        }

        $this->entityManager->flush();

        return Command::SUCCESS;
    }

    private function processHardcodedPriorities(SymfonyStyle $io): void
    {
        $flushNeeded = false;

        // 1. Set subjects to 'low'
        foreach (self::LOW_PRIORITY_SUBJECT_SLUGS as $slug) {
            $subjects = $this->subjectRepository->findBy(['slug' => $slug]);
            if (empty($subjects)) {
                $io->warning(sprintf('Aucune matière trouvée avec le slug "%s".', $slug));
                continue;
            }

            foreach ($subjects as $subject) {
                $subject->setPriority('low');
                $io->text(sprintf(' - Matière "%s" (Classe: %s) définie en priorité "low".', $subject->getName(), $subject->getClassroom()?->getName() ?? 'N/A'));
                $flushNeeded = true;
            }
        }

        // 2. Set classrooms to 'high'
        foreach (self::HIGH_PRIORITY_CLASSROOM_NAMES as $name) {
            $classrooms = $this->classroomRepository->findBy(['name' => $name]);
            if (empty($classrooms)) {
                $io->warning(sprintf('Aucune classe trouvée avec le nom "%s".', $name));
                continue;
            }

            foreach ($classrooms as $classroom) {
                $classroom->setPriority('high');
                $io->text(sprintf(' - Classe "%s" définie en priorité "high".', $classroom->getName()));
                $flushNeeded = true;
            }
        }

        if ($flushNeeded) {
            $this->entityManager->flush();
            $io->success('Toutes les priorités en dur ont été enregistrées avec succès en base de données.');
        } else {
            $io->info('Aucun changement effectué.');
        }
    }
}
