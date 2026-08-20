import { useMemo } from 'react'
import type { ApiTheme } from '../lib/api'
import { useStore } from '../state/store'
import { Icon } from './Icon'

/**
 * Le catalogue en rayons — planche 2c.
 *
 * Le deux-panneaux tombait sur 390 px : la colonne de catégories se
 * réduisait à 118 px et la liste à 250, illisibles avec onze catégories
 * et cinquante apprentissages par catégorie. La direction retenue
 * renonce à l'arbre. On ne descend plus, on balaie : la recherche prend
 * le haut de l'écran, puis viennent deux ou trois rayons éditoriaux,
 * puis une ligne défilante par catégorie.
 *
 * Ça passe l'échelle sans rien changer : trois cents ou trois mille
 * apprentissages, l'écran est le même — seule la longueur des rayons
 * bouge, et un rayon défile.
 *
 * Ces pièces servent deux écrans : « Ajouter » et la première étape de
 * l'inscription. C'est le même geste, il n'a pas à être écrit deux fois.
 */

/** Ce qu'un rayon porte : un titre, un compte, et ce qu'on y trouve. */
export interface ShelfSpec {
  key: string
  title: string
  /** Le compte total de la catégorie, affiché à côté du titre. */
  count?: number
  items: ApiTheme[]
}

/**
 * Un rayon ne montre pas tout : au-delà, « tout voir » prend le relais.
 * Le rayon garde la liste entière — c'est elle que « tout voir » ouvre —
 * et n'en pose que les douze premières cartes.
 */
const SHELF_MAX = 12

/**
 * Les rayons, calculés depuis le catalogue servi. Un par catégorie, et
 * rien d'autre.
 *
 * IL Y AVAIT TROIS RAYONS ÉDITORIAUX AU-DESSUS, ils sont partis avec les
 * boutons « Populaires » et « Nouveaux » du desktop, et pour la même
 * raison : aucun des trois ne mesurait ce que son titre annonçait.
 *
 *   · « Les plus suivis » lisait `subscriber_count`, qui vaut zéro
 *     partout tant que personne n'a joué. Il retombait donc sur l'ordre
 *     alphabétique. Et depuis que suivre un chapitre suit sa branche, ce
 *     compte monte de 78 d'un seul clic : il mesure la taille de la
 *     branche, pas l'intérêt qu'on lui porte ;
 *   · « Nouveaux » lisait l'identifiant, c'est-à-dire l'ordre du crawl
 *     de Wikipédia — les feuilles les plus lointaines en tête ;
 *   · « Parce que vous suivez X » proposait le voisinage de ce qu'on
 *     suit. L'abonnement par branche emporte déjà tout ce voisinage :
 *     le rayon proposait ce qu'on venait de prendre.
 *
 * Trois rayons pour un seul ordre réel, c'est trois façons de faire
 * croire qu'on choisit. Reste l'ordre qui, lui, est renseigné : le POIDS
 * — le nombre d'articles qui descendent du chapitre.
 */
export function useShelves(): { byCategory: ShelfSpec[] } {
  const { themes, categories } = useStore()

  return useMemo(() => {
    // L'étage d'abord, le poids ensuite — le même ordre que l'API et que
    // le desktop. L'article racine ouvre donc le rayon : sur un rayon qui
    // défile et n'en pose que douze, c'est la seule position sûre, et
    // c'est celle qu'on veut voir d'abord.
    //
    // Le rayon se rangeait par nombre d'abonnés — donc en pratique par
    // ordre alphabétique : c'étaient les douze premières lettres, pas les
    // douze sujets qui portent le plus.
    const byCategory: ShelfSpec[] = []
    for (const cat of categories) {
      const all = themes
        .filter((th) => th.category_id === cat.id)
        .sort(
          (a, b) =>
            a.depth - b.depth ||
            b.child_count - a.child_count ||
            a.title.localeCompare(b.title),
        )
      if (all.length === 0) continue
      byCategory.push({
        key: `cat-${cat.id}`,
        title: cat.label,
        count: all.length,
        items: all,
      })
    }

    return { byCategory }
  }, [themes, categories])
}

/**
 * Le code de partage d'un apprentissage — six caractères qu'on dicte ou
 * qu'on recopie, et qui ouvrent le quiz sans passer par le catalogue.
 *
 * Un `span`, pas un bouton : ces pastilles vivent DANS des rangées qui
 * sont elles-mêmes des boutons — imbriquer deux interactifs est invalide,
 * et un clic sur le code déclencherait l'abonnement de la rangée. On le
 * rend donc sélectionnable et rien de plus ; c'est ce qu'on lui demande.
 *
 * `aria-label` épelle le code : lu d'un trait, « NQPJE9 » sort comme un
 * mot, et un code se recopie caractère par caractère.
 */
export function CodeChip({ code }: { code: string | null }) {
  const { t } = useStore()
  if (!code) return null
  return (
    <span className="code-chip" title={t.codeLabel} aria-label={`${t.codeLabel} ${code.split('').join(' ')}`}>
      {code}
    </span>
  )
}

/**
 * La carte d'un apprentissage, 148 px de large.
 *
 * Le bouton d'ajout est DANS la carte plutôt que la carte entière : sur
 * un rayon qui défile, une carte cliquable dans son ensemble s'abonne au
 * moindre glissement du doigt.
 */
export function LearnCard({ th, showCategory = true }: { th: ApiTheme; showCategory?: boolean }) {
  const { toggleSubscribe, t } = useStore()
  const meta = showCategory && th.category_label
    ? `${th.category_label} · ${t.exercisesShort(th.exercise_count)}`
    : t.exercisesShort(th.exercise_count)

  return (
    <div className="learn-card">
      <span className="learn-card-name">{th.title}</span>
      {/* Le méta et le bouton sur UNE ligne, et non l'un sous l'autre.

          Le bouton était une barre pleine largeur : le méta au-dessus,
          lui en dessous. Réduit à un carré de 36 px, il laissait un vide
          de cent px à sa gauche. Le pied les met côte à côte — « 8 ex. »
          à gauche, le signe à droite — et c'est ce pied qui porte
          désormais le `margin-top: auto` qui aligne les boutons d'une
          rangée de cartes. */}
      <span className="learn-card-foot">
        <span className="learn-card-meta">
          {meta}
          <CodeChip code={th.code} />
        </span>
        {/* Le signe seul, sans le mot. « Ajouter » et « Ajouté » prenaient
          toute la largeur de la carte pour dire ce que le + et le ✓
          disent déjà, et c'est la même paire de signes que la rangée du
          catalogue emploie sans légende depuis toujours.

          Le mot passe donc dans `aria-label` — il n'est pas perdu, il
          n'est plus dessiné. Sans lui, un lecteur d'écran annoncerait un
          bouton sans nom : le + n'a pas de texte à lire. */}
        <button
          className={th.subscribed ? 'learn-card-add is-on' : 'learn-card-add'}
          aria-pressed={th.subscribed}
          aria-label={th.subscribed ? t.addedThis : t.addThis}
          title={th.subscribed ? t.addedThis : t.addThis}
          onClick={() => toggleSubscribe(th.id)}
        >
          <Icon name={th.subscribed ? 'check' : 'plus'} size={17} stroke={2.4} />
        </button>
      </span>
    </div>
  )
}

export function Shelf({
  spec,
  showCategory = true,
  onSeeAll,
}: {
  spec: ShelfSpec
  showCategory?: boolean
  onSeeAll?: () => void
}) {
  const { t } = useStore()
  return (
    <section className="learn-shelf">
      <div className="learn-shelf-head">
        <span className="learn-shelf-title">
          {spec.title}
          {spec.count !== undefined && <span className="learn-shelf-count"> · {spec.count}</span>}
        </span>
        {onSeeAll && (
          <button className="learn-shelf-all" onClick={onSeeAll}>
            {t.seeAll}
          </button>
        )}
      </div>
      <div className="learn-shelf-row">
        {spec.items.slice(0, SHELF_MAX).map((th) => (
          <LearnCard key={th.id} th={th} showCategory={showCategory} />
        ))}
      </div>
    </section>
  )
}

/** La ligne d'un résultat : le nom, ce que ça pèse, et la cible de 44 px.
 *
 * Le préfixe `cat-` n'est pas décoratif. Ces lignes s'appelaient
 * `learn-row`, du même nom que les rangées de « Mes apprentissages » —
 * et comme elles sont déclarées plus bas dans la même feuille, elles
 * gagnaient la cascade et repeignaient l'écran des thèmes : rangée en
 * ligne au lieu de la grille, fond blanc au lieu du voile, rayon 14 au
 * lieu de 16. Deux écrans, deux familles de classes. */
export function LearnRow({ th }: { th: ApiTheme }) {
  const { toggleSubscribe, t } = useStore()
  return (
    <button
      className={th.subscribed ? 'cat-row is-on' : 'cat-row'}
      aria-pressed={th.subscribed}
      onClick={() => toggleSubscribe(th.id)}
    >
      <span className="stack" style={{ flex: 1, gap: 2, minWidth: 0 }}>
        <span className="cat-row-name">{th.title}</span>
        <span className="cat-row-meta">
          {t.questionsCount(th.exercise_count)}
          <CodeChip code={th.code} />
        </span>
      </span>
      <span className="cat-row-add" aria-hidden="true">
        <Icon name={th.subscribed ? 'check' : 'plus'} size={20} stroke={2.4} />
      </span>
    </button>
  )
}

/**
 * Une liste groupée par catégorie — l'état de recherche, et « tout
 * voir ». Chercher « fraction » sans savoir qu'il faut d'abord ouvrir
 * « Maths » est le cas normal : le groupe dit où l'on a trouvé, il ne
 * demande pas d'y descendre.
 */
export function GroupedList({ items }: { items: ApiTheme[] }) {
  const { t } = useStore()

  const groups = useMemo(() => {
    const map = new Map<string, ApiTheme[]>()
    for (const th of items) {
      const key = th.category_label ?? ''
      const list = map.get(key) ?? []
      list.push(th)
      map.set(key, list)
    }
    return [...map.entries()]
  }, [items])

  if (items.length === 0) return <p className="learn-empty">{t.noMatch}</p>

  return (
    <div className="learn-groups">
      {groups.map(([label, list]) => (
        <div key={label} className="learn-group">
          {label && <span className="mono learn-group-head">{t.inCategory(label)}</span>}
          {list.map((th) => (
            <LearnRow key={th.id} th={th} />
          ))}
        </div>
      ))}
    </div>
  )
}

/** Le nombre de catégories distinctes touchées par une recherche. */
export function categoriesTouched(items: ApiTheme[]): number {
  return new Set(items.map((th) => th.category_label ?? '')).size
}
