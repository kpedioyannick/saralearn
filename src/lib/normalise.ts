/**
 * Normalisation des réponses écrites — reprise telle quelle de la
 * maquette, sans rien y ajouter.
 *
 * Elle tolère la casse, les accents et la ponctuation : « L'Aorte »,
 * « l aorte » et « l'aorte » se rejoignent. Elle ne retire PAS les
 * articles — « l'aorte » devient « l aorte », pas « aorte ». C'est
 * pourquoi les graphies avec article figurent explicitement dans les
 * options servies par l'API : mieux vaut une liste que l'API contrôle
 * qu'une heuristique côté client, qui finirait par accepter une graphie
 * franchement fausse.
 */
export function normalise(value: unknown): string {
  return (value == null ? '' : String(value))
    .toLowerCase()
    .normalize('NFD')
    // Les diacritiques détachés par NFD. La maquette écrit la plage en
    // caractères combinants nus ; on l'échappe ici — même plage, mais un
    // signe combinant seul dans une source finit toujours par se coller à
    // la lettre d'à côté au premier copier-coller.
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

/**
 * Une réponse est juste dès qu'elle rejoint UNE des graphies acceptées.
 * Toutes les options d'une `short_answer` sont bonnes — la première est
 * seulement celle qu'on affiche en correction.
 */
export function accepts(value: string, labels: string[]): boolean {
  const target = normalise(value)
  return target !== '' && labels.some((label) => normalise(label) === target)
}
