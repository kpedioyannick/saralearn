<?php

declare(strict_types=1);

namespace App\Service\Suno;

use App\Entity\CourseMusic;
use App\Entity\Subchapter;
use App\Repository\CourseMusicRepository;
use App\Service\ContentGenerator\ContentGeneratorService;
use Doctrine\ORM\EntityManagerInterface;

/**
 * Génère le prompt (paroles slam), le style et la relevance via le provider curl.
 * Style fixe, structure slam (Verse/Hook), règles PROMPT.md. Réponse IA en JSON : title, prompt, relevance.
 */
final class CourseMusicPromptGenerator
{
    /** Style musical (toujours le même). */
    public const DEFAULT_STYLE = 'slam, afropop, serious tone, melodic african instruments, clear vocals, soft beat';

    private const MAX_PROMPT_LENGTH = 4000;
    private const VALID_RELEVANCE = ['high', 'medium', 'low'];

    public function __construct(
        private readonly ContentGeneratorService $contentGeneratorService,
        private readonly CourseMusicRepository $courseMusicRepository,
        private readonly EntityManagerInterface $entityManager,
    ) {
    }

    /**
     * Extrait le contenu essentiel du cours (titre + texte des slides) pour l’envoyer à l’IA.
     */
    public function extractCourseContentForPrompt(Subchapter $subchapter): string
    {
        $chapter = $subchapter->getChapter();
        $subject = $chapter?->getSubject();
        $classroom = $subject?->getClassroom();
        $parts = [
            'Titre : ' . ($subchapter->getTitle() ?? ''),
            'Chapitre : ' . ($chapter?->getTitle() ?? ''),
            'Matière : ' . ($subject?->getName() ?? ''),
            'Classe : ' . ($classroom?->getName() ?? ''),
        ];
   
        return implode("\n\n", $parts);
    }

    /**
     * Génère le slam (prompt) et retourne title, prompt, relevance (réponse IA en JSON).
     *
     * @return array{title: string, prompt: string, relevance: string}
     */
    public function generatePromptForSubchapter(Subchapter $subchapter): array
    {
        $subchapterTitle = $subchapter->getTitle() ?? 'Cours';
        $chapter = $subchapter->getChapter();
        $subject = $chapter?->getSubject();
        $classroom = $subject?->getClassroom();
        $niveau = $classroom?->getName() ?? 'élèves';
        $matiere = $subject?->getName() ?? '';


        $instruction = <<<PROMPT
Tu es un expert en création de slams pédagogiques pour des élèves.

Contexte :
- Sous-chapitre : {$subchapterTitle}
- Classe (niveau) : {$niveau}
- Matière : {$matiere}



Règles : Langue française. Public : élèves du niveau indiqué. Ton : sérieux, pédagogique, rythmé. Durée max trois minutes. Contenu : l'essentiel. Chiffres et dates en toutes lettres. Pas d'acronymes (écrire en toutes lettres). Paroles bien prononcées et intelligibles.

Structure obligatoire :
(Titre de la chanson)
[Verse]
(Introduction : accroche, présentation du sujet)
[Hook]
(Refrain mémorable qui résume le thème)
[Verse]
(Développement : explications claires et rythmées)
[Hook]
(Répétition du refrain)
[Verse - Ce qu'il faut retenir]
(Récapitulatif final : points essentiels à retenir)

Réponds UNIQUEMENT par un objet JSON valide avec exactement ces clés :
- "title" : titre court de la chanson (string)
- "prompt" : paroles complètes du slam avec les balises [Verse], [Hook], [Verse - Ce qu'il faut retenir] (string)
- "relevance" : "high", "medium" ou "low" selon l'importance du thème pour les élèves (string)
PROMPT;

        $raw = $this->contentGeneratorService->generateViaDeepSeek($instruction);
        $data = json_decode($raw, true);
        if (is_array($data) && isset($data['content'])) {
            $data = is_string($data['content']) ? json_decode($data['content'], true) : $data['content'];
        }
        if (!is_array($data)) {
            $data = [];
        }
        $title = isset($data['title']) && is_string($data['title']) ? trim($data['title']) : $subchapterTitle;
        $prompt = isset($data['prompt']) && is_string($data['prompt']) ? trim($data['prompt']) : $this->buildFallbackSlam($subchapterTitle);
        $relevance = isset($data['relevance']) && is_string($data['relevance']) && in_array(strtolower($data['relevance']), self::VALID_RELEVANCE, true)
            ? strtolower($data['relevance']) : 'high';

        return [
            'title' => $title,
            'prompt' => $prompt,
            'relevance' => $relevance,
        ];
    }

    private function buildFallbackSlam(string $title): string
    {
        return "{$title}\n[Verse]\nCe cours te permettra de comprendre l'essentiel. Écoute bien et retiens les points clés.\n[Hook]\nApprendre en rythme, retenir en chanson. Chaque mot compte, chaque idée résonne.\n[Verse]\nRévise à ton rythme, écoute cette leçon. La musique t'accompagne dans ta réflexion.\n[Hook]\nApprendre en rythme, retenir en chanson. Chaque mot compte, chaque idée résonne.\n[Verse - Ce qu'il faut retenir]\nRetiens l'essentiel de ce thème. La pratique et l'écoute renforceront ton savoir.";
    }

    /**
     * Génère le prompt via curl et crée ou met à jour CourseMusic (champ prompt uniquement, pas d’appel Suno).
     */
    public function createOrUpdatePromptForSubchapter(Subchapter $subchapter): CourseMusic
    {
        $result = $this->generatePromptForSubchapter($subchapter);

        $courseMusic = $this->courseMusicRepository->findOneBySubchapter($subchapter)
            ?? new CourseMusic();
        $courseMusic->setSubchapter($subchapter);
        $courseMusic->setPrompt($result['prompt']);
        $courseMusic->setTitle($result['title']);
        $courseMusic->setStyle(self::DEFAULT_STYLE);
        $courseMusic->setRelevance($result['relevance']);
        if (!$this->entityManager->contains($courseMusic)) {
            $this->entityManager->persist($courseMusic);
            $subchapter->addCourseMusic($courseMusic);
        }
        $this->entityManager->flush();

        return $courseMusic;
    }
}
