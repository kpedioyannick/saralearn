/**
 * Réglages hérités de la maquette, isolés ici pour être basculés
 * sans toucher aux écrans.
 */

/**
 * La maquette dessine une fausse barre d'état (9:41, réseau, batterie)
 * parce qu'elle représente un téléphone. Dans l'app réelle, la vraie
 * barre de l'OS se trouve au-dessus : deux barres d'état, dont une qui
 * affiche 9:41 quelle que soit l'heure. L'app étant en ligne, elle est
 * livrée : false. Repasser à true pour comparer un écran à la maquette.
 */
export const SHOW_MOCK_STATUS_BAR = false

/**
 * Le loader donne le rythme et enchaîne seul ; le swipe reste
 * disponible à tout instant. Passer à true rétablit le gate décrit
 * dans le cahier des charges initial (swipe bloqué tant que la barre
 * n'est pas pleine).
 */
export const BLOCKING_LOADER = false

/** Multiplie les durées de lecture. 0.5 = deux fois plus rapide. */
export const PACE = 1

/**
 * L'enchaînement après une réponse.
 *
 * `true` : la réussite et l'erreur passent seules à l'explication, et
 * l'explication passe seule à l'exercice suivant, sur des minuteurs
 * fixes — 2, 6 et 8 secondes. C'est ce que dessine la maquette, et ça
 * contredisait déjà `ANALYSE_TECH.md`, qui voulait l'inverse.
 *
 * `false` : rien ne bouge sans un geste. La barre continue de se
 * remplir — elle donne le rythme — mais elle ne décide plus. Deux
 * raisons, dans cet ordre :
 *
 *   · la lecture à voix haute ne consultait pas ces minuteurs. Une
 *     explication de douze secondes était coupée à huit, et l'exercice
 *     suivant démarrait par-dessus ;
 *   · passer d'un écran au suivant appartient à celui qui lit.
 *
 * Le prix : deux taps de plus par exercice. Sur cent exercices, deux
 * cents gestes ajoutés — l'app se rapproche d'un quiz classique et
 * s'éloigne du fil qui défile.
 */
export const AUTO_ADVANCE = false
