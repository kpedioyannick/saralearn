/**
 * Ce que la voix lit, et le temps que ça prend.
 *
 * Deux consommateurs, une seule source : le bandeau audio l'envoie à la
 * synthèse, la barre du haut en tire sa durée. Les tenir séparés les
 * ferait dériver — c'est exactement ce qui s'était produit avec des
 * durées fixes, restées calibrées sur des questions de grammaire quand
 * le catalogue s'est rempli de questions d'informatique trois fois plus
 * longues.
 */

/** Le minimum structurel dont ce module a besoin. `ExoCard` le satisfait. */
export interface Spokenable {
  prompt: string
  body?: string
  options: string[]
  typeQuestion: string
  okTitle: string
  okLine: string
  koTitle: string
  koLine: string
  expTitle: string
  expText: string
}

export type SpokenPhase = 'q' | 'ok' | 'ko' | 'exp'

/** Ce qu'il y a à lire, phase par phase. */
export function spokenText(exo: Spokenable | null, phase: SpokenPhase): string {
  if (!exo) return ''
  const join = (parts: (string | undefined)[]) =>
    parts.filter((x) => x && x.trim()).join('. ').replace(/\.\.+/g, '.')
  switch (phase) {
    // La question ne se suffit pas à elle-même : la réponse est dans les
    // options, et les lire évite de revenir à l'écran pour savoir entre
    // quoi choisir. Elles suivent l'ordre d'affichage et ne sont pas
    // numérotées — les boutons n'en portent aucun, en annoncer un
    // inventerait un repère que l'œil ne peut pas confirmer.
    //
    // Sauf en réponse courte : là, `options` n'est pas une liste de choix
    // mais celle des graphies acceptées, et l'écran ne montre qu'un champ
    // à remplir (voir `ShortAnswer`). Les lire dicterait la réponse.
    case 'q':
      return join([
        exo.prompt,
        exo.body,
        ...(exo.typeQuestion === 'short_answer' ? [] : exo.options),
      ])
    case 'ko':
      return join([exo.koTitle, exo.koLine])
    case 'exp':
      return join([exo.expTitle, exo.expText])
    // LA FÉLICITATION SE DIT AUSSI. Elle ne se lisait pas, et le
    // bandeau disparaissait avec elle : l'écran d'une bonne réponse
    // était le seul muet de la séquence — celui, justement, où la voix
    // sert le plus. « Bravo. », « Bien vu. » se disent dans la langue
    // du lecteur sans un mot de plus à traduire : `ok_title` et
    // `ok_line` sont déjà les siens, choisis dans le jeu fermé de
    // `api/titres.py`.
    //
    // Ce silence tenait à une raison qui n'existe plus : l'écran durait
    // deux secondes et passait seul à l'explication. Depuis que rien ne
    // l'avance à la place du lecteur (`AUTO_ADVANCE`), il reste tant
    // qu'on veut, et la voix a le temps.
    case 'ok':
      return join([exo.okTitle, exo.okLine])
  }
}

/**
 * Caractères lus par seconde.
 *
 * Étalonné sur trois MP3 du serveur, mesurés à `ffprobe` : 619 car. en
 * 37,3 s, 223 en 12,1 s, 205 en 10,2 s — soit 16,6 à 20,1. On retient la
 * plus lente : une barre qui finit un peu après la voix se remarque
 * moins qu'une barre qui l'a devancée. Les longues énumérations d'options
 * tirent la vitesse vers le bas, ce sont elles qui donnent 16,6.
 */
const CHARS_PER_SECOND = 17

/**
 * Bornes. En deçà de huit secondes la barre n'est plus qu'un clignotement
 * sur une question de trois mots ; au-delà de quarante-cinq elle paraît
 * arrêtée, et le catalogue n'a de toute façon rien qui se lise plus long
 * (43 s au maximum mesuré).
 */
const MIN_MS = 8_000
const MAX_MS = 45_000

/** Le temps que met la voix à lire ce texte, en millisecondes. */
export function readingMs(text: string): number {
  const n = text.trim().length
  if (n === 0) return 0
  return Math.min(MAX_MS, Math.max(MIN_MS, (n / CHARS_PER_SECOND) * 1000))
}
