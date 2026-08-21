import { Icon } from '../components/Icon'
import { LangSwitch } from '../components/LangSwitch'
import { Wordmark } from '../components/Wordmark'
import { useIsDesktop } from '../lib/useIsDesktop'
import { useStore } from '../state/store'

/**
 * L'accueil public — planche 1j, « présentation fidèle des fonctions ·
 * essayer ou se connecter ».
 *
 * C'est le seul écran de l'app qui ne suppose pas qu'on est déjà
 * entré, et le seul qui scrolle avec la page entière : il n'a ni rail
 * ni barre de navigation, le cadre desktop le laisse passer nu (voir
 * `BARE` dans DesktopFrame).
 *
 * « Fidèle » est le mot qui gouverne : la page annonce neuf sections de
 * fonctions, et aucune n'est une promesse — le bandeau de lecture, les
 * prompts, le classement sur 30 jours, les retours par pouce existent
 * tous dans l'app. Ce qui ne peut pas être tenu ne s'écrit pas ici.
 */

/**
 * L'aperçu d'exercice posé dans la page : une image, pas un écran.
 *
 * La planche y met un vrai/faux — « Actually veut dire actuellement »,
 * qui est faux — avec les compteurs du rail. Il est écrit en dur : la
 * page s'affiche avant toute session, il n'y a pas de flux à
 * interroger à ce moment-là.
 */
function Preview() {
  const { t } = useStore()

  return (
    <div className="home-preview" aria-hidden="true">
      <span className="home-preview-wash" />

      {/* Le bandeau de lecture de la planche 4c, réduit à sa marque :
          c'est lui qui distingue l'app d'un quiz muet. */}
      <div className="home-preview-audio">
        <span className="home-preview-bar">
          <span className="home-preview-fill" />
        </span>
        <span className="home-preview-pause">
          <Icon name="pause" size={13} />
        </span>
      </div>

      <div className="home-preview-body">
        <div className="home-preview-head">
          <span className="chip home-preview-chip">
            <span className="dot" style={{ width: 6, height: 6, background: 'var(--sc-primary)' }} />
            {t.previewTheme}
          </span>
          <span className="home-preview-add">
            <Icon name="plus" size={16} stroke={2.2} />
          </span>
        </div>

        <span className="exo-type">{t.previewType}</span>
        <p className="display home-preview-q">{t.previewQuestion}</p>

        {/* La bonne réponse EN PREMIER dans la liste, marquée. C'est un
            aperçu, pas un exercice : on montre à quoi ressemble une
            carte corrigée, on ne fait pas jouer. Les trois options sont
            recopiées de l'exercice 58, la quatrième est tombée — la
            carte n'a pas la hauteur, et trois suffisent à montrer la
            forme. */}
        <div className="home-preview-opts">
          {t.previewOptions.map((label, i) => (
            <div key={label} className={i === 0 ? 'option is-good' : 'option'}>
              {label}
              {i === 0 && <Icon name="check" size={18} stroke={2.4} />}
            </div>
          ))}
        </div>
      </div>

      {/* Le rail, à droite et sur le contenu, comme dans la planche. */}
      <div className="home-preview-rail">
        <span className="home-preview-tally is-ok">
          <Icon name="check" size={15} stroke={2.4} />
          128
        </span>
        <span className="home-preview-tally is-ko">
          <Icon name="undo" size={15} stroke={2.2} />
          12
        </span>
        <span className="home-preview-tally">
          <Icon name="heart" size={15} />
          2,1k
        </span>
        <span className="home-preview-tally">
          <Icon name="thumbDown" size={15} />
        </span>
        <span className="home-preview-tally">
          <Icon name="message" size={15} />
        </span>
      </div>
    </div>
  )
}

/** Une entrée numérotée : le numéro en mono, le titre, la ligne. */
function Numbered({ n, title, line }: { n: number; title: string; line: string }) {
  return (
    <article className="home-item">
      <span className="mono home-item-n">{String(n).padStart(2, '0')}</span>
      <h3>{title}</h3>
      <p>{line}</p>
    </article>
  )
}

/**
 * Une intention : le mot seul, un filet à gauche.
 *
 * Pas de numéro, contrairement à `Numbered` : la curiosité ne vient
 * pas « avant » l’autonomie, les quatre tiennent ensemble. Numéroter
 * aurait annoncé une progression qui n'existe pas.
 */
function Aim({ label }: { label: string }) {
  return <h3 className="home-aim">{label}</h3>
}

export function Home() {
  const { go, set, enterFeed, t } = useStore()
  const isDesktop = useIsDesktop()

  const start = () => enterFeed()
  const signIn = () => set({ screen: 'auth', authMode: 'login', sheet: null, authError: null })

  return (
    <div className="screen home screen-scroll">
      <header className="home-top">
        <Wordmark size={isDesktop ? 22 : 20} />

        {/* « Partager une connaissance » a disparu de la barre, du héros
            et de la clôture. Le bouton menait à `goCreate(1)`, et ce
            chemin est fermé : `create_theme` cherche `SELECT id FROM
            category`, table supprimée avec l'ancien modèle. Un appel à
            l'action principal qui rend 403 coûte plus cher qu'une
            fonction non annoncée. */}
        <nav className="home-nav">
          {isDesktop && (
            <button className="btn-quiet" onClick={() => go('about')}>
              {t.homeHow}
            </button>
          )}

          {/* La bascule de langue vit dans l'écran : c'est la première
              page qu'un visiteur anglophone voit, et changer de langue
              change le catalogue servi, pas seulement les libellés. */}
          <LangSwitch compact />

          <button className="chip home-chip" onClick={signIn}>
            {t.signIn}
          </button>
          <button className="chip home-chip is-primary" onClick={start}>
            {t.homeTry}
          </button>
        </nav>
      </header>

      <section className="home-hero">
        <div className="stack" style={{ gap: 22 }}>
          <span className="home-kicker">{t.homeKicker}</span>

          <h1 className="home-title">{t.homeTitle}</h1>

          <p className="home-lead">{t.homeLead}</p>

          <div className="wrap" style={{ gap: 12 }}>
            <button className="btn-primary home-cta" onClick={start}>
              {t.homeStartLearning}
            </button>
          </div>

        </div>

        {/* L'aperçu était réservé au desktop. C'est la seule preuve
            visuelle du produit sur toute la page, et l'app vise le
            téléphone en premier — le cacher là était un contresens. */}
        <Preview />
      </section>

      {/* L'OBJECTIF, AVANT LES FONCTIONS. Le héros dit sur quoi on
          apprend, cette bande dit à quoi ça sert, et tout ce qui suit
          dit comment. Elle est la seule de la page à ne pas décrire
          une fonction — c'est pour ça qu'elle n'a ni carte ni numéro. */}
      <section className="home-band home-aims-band">
        <h2 className="home-band-title">{t.homeAimsTitle}</h2>

        <div className="home-grid home-aims">
          {t.homeAims.map((a) => (
            <Aim key={a} label={a} />
          ))}
        </div>
      </section>

      {/* La section « Trois piliers » vivait ici. Elle disait une
          troisième fois ce que le titre annonce (« Apprenez. Créez.
          Partagez. ») et ce que « Ce que la communauté rend possible »
          détaille juste après. */}
      <section className="home-band is-sunk">
        <span className="eyebrow">{t.homeLoopEyebrow}</span>
        <h2 className="home-band-title">{t.homeLoopTitle}</h2>

        <div className="home-grid is-three">
          {t.homeLoop.map((p, i) => (
            <Numbered key={p.title} n={i + 1} title={p.title} line={p.line} />
          ))}
        </div>
      </section>

      <section className="home-band">
        <h2 className="home-band-title">{t.homeCommunityTitle}</h2>

        <div className="home-grid is-three">
          {t.homeCommunity.map((p, i) => (
            <Numbered key={p.title} n={i + 1} title={p.title} line={p.line} />
          ))}
        </div>
      </section>

      {/* IL Y AVAIT UNE TROISIÈME BANDE ICI, et elle a porté deux
          contenus successifs, retirés tous les deux.

          D'abord la création : « Vous avez une connaissance à partager ? »
          et une carte de prompt. Le chemin est fermé — `create_theme` et
          `generate.py` interrogent une table `category` supprimée.

          Puis l'écriture à la demande : l'extrait d'article et la
          question qui en sortait. Juste, mais c'est de la fabrication —
          le visiteur n'a pas à savoir d'où sortent les questions pour
          décider d'essayer.

          La page va donc du héros à la boucle, de la boucle aux
          fonctions, des fonctions à la clôture. Trois bandes au lieu de
          quatre. */}
      <section className="home-close">
        <h2 className="home-close-title">{t.homeClosing}</h2>
        <p className="home-close-line">{t.homeClosingLine}</p>

        <div className="wrap home-close-actions">
          <button className="btn-primary home-cta" onClick={start}>
            {t.homeStartLearning}
          </button>
        </div>
      </section>
    </div>
  )
}
