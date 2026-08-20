import { useStore, type ExoCard } from '../state/store'
import { ClozeText, clozeExpected, clozeGiven } from './Cloze'
import { Icon } from './Icon'
import { Confetti } from './ui'

/**
 * Les quatre contenus de la séquence, partagés entre mobile et
 * desktop. Seules les tailles changent d'un cadre à l'autre.
 */

interface Props {
  desktop?: boolean
}

/**
 * Où pointe le nom de la banque, sous la photo. Pexels demande
 * nommément « a prominent link to Pexels », Unsplash veut ses
 * paramètres de provenance sur les liens qu'on lui fait ; les trois
 * gagnent à être cliquables. Une banque inconnue rend `#` plutôt que
 * de casser la ligne de crédit.
 */
const BANQUES: Record<string, string> = {
  Unsplash: 'https://unsplash.com/?utm_source=SaraLearn&utm_medium=referral',
  Pexels: 'https://www.pexels.com',
  Pixabay: 'https://pixabay.com',
}

/**
 * Le corps de la question est-il du code ?
 *
 * `body` porte deux choses très différentes selon la connaissance. En
 * français, une phrase à trou — « Les enfants … dans le jardin ». En
 * Git ou en SQL, une requête ou une sortie de terminal, qui ne survit
 * pas à une police proportionnelle : les colonnes cessent de s'aligner,
 * et surtout le HTML replie les retours à la ligne, si bien qu'une
 * requête de quatre lignes s'affiche sur une seule.
 *
 * Le type d'exercice ne permet pas de trancher — `find_error` sert aux
 * deux. On tranche donc sur le texte lui-même. Les motifs sont pris
 * sensibles à la casse et ancrés en début de corps : « where » dans une
 * phrase anglaise ne doit pas la faire passer pour une requête.
 */
function isCode(body: string): boolean {
  return (
    body.includes('\n') ||
    /^\s*(git|npm|docker|\$|>)\s/.test(body) ||
    /^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH)\b/.test(body)
  )
}

export function QuestionBlock({ desktop }: Props) {
  const { exo } = useStore()
  if (!exo) return null
  return (
    <div className="stack anim-fade-up" style={{ gap: 18 }}>
      {/* Le type d'exercice est descendu de l'en-tête au corps : il
          appartient à la question qu'il qualifie, et l'en-tête revient
          à ce qui concerne l'apprentissage — sa pastille et l'ajout. */}
      <span className="exo-type">{exo.type}</span>
      {/* L'illustration passe AVANT la question : sur « que signifie ce
          panneau ? », c'est elle qui porte l'information. Hauteur bornée
          en unités de viewport pour que l'écran ne scrolle jamais. */}
      {exo.image && (
        /* Deux images de nature différente passent par ce même champ, et
           elles ne se montrent pas pareil. Un PICTOGRAMME — le vestige
           du catalogue de panneaux — est un dessin sur fond blanc qu'on
           laisse à sa taille. Une PHOTO D'AMBIANCE est un paysage qui
           doit occuper la largeur : plante la scène ou ne sert à rien.
           Le crédit les distingue, parce que seule la photo en a un. */
        <figure className={exo.imageCredit ? 'exo-photo' : 'exo-image-cadre'}>
          <img
            src={exo.image}
            alt={exo.imageAlt ?? ''}
            className={exo.imageCredit ? 'exo-photo-img' : 'exo-image'}
            style={{ maxHeight: desktop ? 200 : '26dvh' }}
          />
          {exo.imageCredit && (
            /* NON NÉGOCIABLE : les trois banques imposent de créditer le
               photographe avec un lien vers son profil, ET de nommer la
               banque. Retirer cette ligne met l'usage des photos hors
               règles. Le nom vient de la carte, pas d'une constante :
               il a été écrit en dur ici du temps d'Unsplash seule, et
               créditer Pexels sous le nom d'Unsplash serait pire que de
               ne rien créditer du tout. */
            <figcaption className="exo-photo-credit">
              <a href={exo.imageCreditUrl ?? '#'} target="_blank" rel="noreferrer noopener">
                {exo.imageCredit}
              </a>
              {' · '}
              <a
                href={BANQUES[exo.imageSource ?? ''] ?? '#'}
                target="_blank"
                rel="noreferrer noopener"
              >
                {exo.imageSource ?? 'Unsplash'}
              </a>
            </figcaption>
          )}
        </figure>
      )}
      <p
        className="display"
        style={{
          // 20 px, quelle que soit la place et qu'il y ait une image ou
          // non. Les 40 px d'origine étaient calibrés sur des questions
          // courtes — « quelle est la forme correcte du verbe ? », 54
          // caractères de médiane. Le catalogue informatique en fait 100
          // de médiane et jusqu'à 240 : au-delà de 120 caractères, un
          // exercice sur cinq, la question mangeait l'écran et poussait
          // les réponses hors du champ.
          fontSize: 20,
          // L'interlignage serré appartenait à l'affiche. À 20 px, un
          // texte qui court sur trois lignes a besoin de respirer.
          lineHeight: 1.4,
        }}
      >
        {exo.prompt}
      </p>
      {/* Un texte à trous EST le corps de la question : ses trous se
          remplissent là où on les lit, pas dans un bloc à part. */}
      {exo.typeQuestion === 'cloze' ? (
        <ClozeText desktop={desktop} />
      ) : (
        exo.body && (
          <div
            style={{
              padding: desktop ? '18px 20px' : '18px 20px',
              borderRadius: 14,
              background: desktop ? 'var(--sc-sunk)' : 'var(--sc-surface)',
              border: '1px solid var(--sc-line)',
              fontSize: desktop ? 18 : 17,
              lineHeight: 1.6,
              color: 'var(--sc-text2)',
              boxShadow: desktop ? 'none' : 'var(--shadow-sm)',
              // `pre-wrap` garde les retours à la ligne ET replie les
              // lignes trop longues : sur un téléphone, une requête qui
              // déborde vaut mieux repliée qu'en défilement latéral.
              // `overflowX` ne sert que pour un identifiant insécable.
              ...(isCode(exo.body)
                ? {
                    fontFamily: 'var(--font-mono)',
                    whiteSpace: 'pre-wrap' as const,
                    overflowX: 'auto' as const,
                    fontSize: desktop ? 16 : 15,
                    lineHeight: 1.5,
                  }
                : null),
            }}
          >
            {exo.body}
          </div>
        )
      )}
    </div>
  )
}

/** Les douze rayons de la félicitation, un tous les trente degrés. */
const RAYS = Array.from({ length: 12 }, (_, i) => ({
  angle: `${i * 30}deg`,
  color: i % 2 === 0 ? '#FFFFFF' : 'var(--confetti-3)',
  delay: `${(i * 0.06).toFixed(2)}s`,
}))

/**
 * Bravo : deux secondes de vert plein, confettis, rayons et une coche
 * qui rebondit.
 *
 * Le fond vert est peint par `.exo.is-ok` sur l'écran entier, pas ici :
 * une célébration cantonnée à la carte se lit comme un encart, alors
 * que c'est le moment le plus fort de la séquence.
 */
export function SuccessBlock({ desktop }: Props) {
  const { s, exo, t } = useStore()
  if (!exo) return null

  const streakLine = s.streak > 1 ? t.streakMany(s.streak) : t.streakOne(s.win)

  return (
    <div
      className="stack anim-fade-up"
      style={{ alignItems: 'center', gap: desktop ? 26 : 24, textAlign: 'center' }}
    >
      <Confetti />

      <div className="celebrate">
        <span className="celebrate-burst" />
        <span className="celebrate-burst" style={{ animationDelay: '0.5s', opacity: 0.6 }} />
        {RAYS.map((r) => (
          <span
            key={r.angle}
            className="celebrate-ray"
            style={
              {
                '--a': r.angle,
                background: r.color,
                animationDelay: r.delay,
              } as React.CSSProperties
            }
          />
        ))}
        <span className="celebrate-disc">
          <Icon name="check" size={desktop ? 54 : 48} stroke={2.4} />
        </span>
      </div>

      <p
        className="display"
        style={{
          fontSize: desktop ? 60 : 52,
          lineHeight: 1,
          fontWeight: 700,
          letterSpacing: '-0.03em',
          color: 'inherit',
          animation: 'slBounce 600ms var(--ease-spring) 120ms both',
        }}
      >
        {exo.okTitle}
      </p>
      <p
        style={{
          margin: 0,
          fontSize: desktop ? 20 : 19,
          lineHeight: 1.5,
          color: 'rgba(255,255,255,.9)',
          maxWidth: '34ch',
        }}
      >
        {exo.okLine}
      </p>
      <span
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 18px',
          borderRadius: 999,
          background: 'rgba(255,255,255,.16)',
          fontSize: 16,
          fontWeight: 700,
        }}
      >
        {streakLine}
      </span>
    </div>
  )
}

/**
 * Erreur non punitive : aucune croix, aucun rouge. Un ambre de reprise,
 * la réponse attendue en vert calme, une ligne en italique qui
 * dédramatise.
 */
/**
 * Ce que l'apprenant a répondu. Sur un QCM c'est l'option touchée ; sur
 * une réponse courte, ce qu'il a écrit ; sur un texte à trous, ce qu'il
 * a posé trou par trou. Pour ces deux derniers, la réponse donnée n'est
 * pas dans `options` — la relire dedans afficherait autre chose.
 */
function givenAnswer(
  exo: ExoCard,
  s: { chosen: number | null; typed: string; fills: (number | null)[] },
): string {
  const chosen = s.chosen !== null ? (exo.options[s.chosen] ?? '') : ''
  if (exo.typeQuestion === 'short_answer') return s.typed || chosen
  if (exo.typeQuestion === 'cloze') return clozeGiven(exo, s.fills).join(' · ')
  return chosen
}

/** Ce qu'il fallait répondre — la graphie canonique, ou un trou par trou. */
function expectedAnswer(exo: ExoCard): string {
  if (exo.typeQuestion === 'cloze') return clozeExpected(exo).join(' · ')
  return exo.options[exo.correct] ?? ''
}

export function MissBlock({ desktop }: Props) {
  const { s, exo, t } = useStore()
  if (!exo) return null
  const chosenLabel = givenAnswer(exo, s)

  return (
    <div className="stack anim-fade-up" style={{ gap: desktop ? 22 : 20 }}>
      <span
        className="anim-pop"
        style={{
          width: desktop ? 84 : 72,
          height: desktop ? 84 : 72,
          borderRadius: 999,
          background: 'var(--sc-miss-bg)',
          color: 'var(--sc-miss-ink)',
          display: 'grid',
          placeItems: 'center',
          flex: 'none',
        }}
      >
        <Icon name="undo" size={desktop ? 36 : 32} stroke={1.9} />
      </span>

      <p
        className="display"
        style={{ fontSize: desktop ? 40 : 34, lineHeight: 1.1, fontWeight: 700 }}
      >
        {exo.koTitle}
      </p>

      {/* La ligne qui dédramatise passe AVANT les deux réponses : on
          explique, puis on montre. L'ordre inverse faisait lire la
          correction comme une sanction. */}
      <p className="body" style={{ fontSize: desktop ? 19 : 18 }}>
        {exo.koLine}
      </p>

      <div className="stack" style={{ gap: 8 }}>
        <div className="answer-row is-good">
          <span>{expectedAnswer(exo)}</span>
          <span style={{ color: 'var(--sc-good-ink)', fontSize: 15 }}>{t.rightAnswer}</span>
        </div>
        <div className="answer-row is-miss">
          <span>{chosenLabel}</span>
          <span style={{ color: 'var(--sc-miss-ink)', fontSize: 15 }}>{t.yourAnswer}</span>
        </div>
      </div>
    </div>
  )
}

/**
 * L'explication en étapes numérotées.
 *
 * L'API renvoie un paragraphe libre. La planche le montre découpé en
 * temps successifs — on suit un raisonnement, on ne lit pas un pavé.
 * On coupe donc sur les retours à la ligne quand l'auteur en a mis,
 * sinon sur les phrases. En dessous de deux morceaux le découpage
 * n'apporte rien : le paragraphe reste entier.
 */
function steps(text: string): string[] {
  const lines = text
    .split(/\r?\n+/)
    .map((x) => x.replace(/^\s*[-–•*]\s*|^\s*\d+[.)]\s*/, '').trim())
    .filter(Boolean)
  if (lines.length > 1) return lines
  const sentences = text.match(/[^.!?]+[.!?]*/g)?.map((x) => x.trim()).filter(Boolean) ?? []
  return sentences.length > 1 ? sentences : [text]
}

export function ExplanationBlock({ desktop }: Props) {
  const { exo, t } = useStore()
  if (!exo) return null
  const parts = steps(exo.expText)

  return (
    <div className="stack anim-fade-up" style={{ gap: desktop ? 22 : 20 }}>
      <span className="eyebrow">{t.explanation}</span>

      <p
        className="display"
        style={{ fontSize: desktop ? 34 : 28, lineHeight: 1.2, fontWeight: 500 }}
      >
        {exo.expTitle}
      </p>

      <div className="steps">
        {parts.map((line, i) => (
          <div key={i} className="step">
            <span className="step-num">{i + 1}</span>
            <span>{line}</span>
          </div>
        ))}
        {/* Un `exp_tip` suivait ici, en dernière étape avec une ampoule à
            la place du numéro. Rien d'autre ne le distinguait — même
            taille, même interligne, même cadre — donc il se lisait comme
            une phrase de plus de l'explication, et il s'écrivait comme
            telle : 3 % seulement des 280 étaient l'expérience à faire
            qu'ils annonçaient. Retiré (migration 017). L'explication
            tient dans `exp_text`, et rien ne vient après. */}
      </div>

      {/* Le lien « son activé / coupé » vivait ici, sous l'explication.
          La planche 4c sort l'audio du pied de page : il tient dans le
          bandeau de lecture, tout en haut, et la coupure reste dans les
          réglages. Un réglage caché sous le dernier écran de la séquence
          ne se trouvait qu'après avoir répondu. */}
    </div>
  )
}

export function PhaseBody({ desktop }: Props) {
  const { s } = useStore()
  switch (s.phase) {
    case 'q':
      return <QuestionBlock desktop={desktop} />
    case 'ok':
      return <SuccessBlock desktop={desktop} />
    case 'ko':
      return <MissBlock desktop={desktop} />
    case 'exp':
      return <ExplanationBlock desktop={desktop} />
  }
}
