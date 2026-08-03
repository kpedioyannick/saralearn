/**
 * La marque, écrite à un seul endroit.
 *
 * Elle était recopiée dans cinq fichiers, de trois façons différentes —
 * dont une sans le point doré. Un logo qui se réécrit à la main dérive :
 * c'est ce qui est arrivé.
 *
 * « Sara » porte le vert de la marque, « Learn » l'encre du texte, et le
 * point l'or. Les trois viennent de jetons, jamais de valeurs écrites
 * dans un écran.
 *
 * `size` reste optionnel : posé en ligne il gagnerait contre toute règle
 * responsive, ce qui figerait le logo à une seule taille. Quand la
 * taille doit varier avec l'écran, on passe une classe et on laisse le
 * CSS décider.
 */
export function Wordmark({ size, className }: { size?: number; className?: string }) {
  return (
    <span
      className={className ? `wordmark ${className}` : 'wordmark'}
      style={size ? { fontSize: size } : undefined}
    >
      <span className="wordmark-sara">Sara</span>Learn<span className="wordmark-dot">.</span>
    </span>
  )
}
