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
