import { NavHead, PageBack } from '../components/ui'
import { Wordmark } from '../components/Wordmark'
import { useStore } from '../state/store'

/**
 * Vision et mission.
 *
 * C'est le seul écran de l'app qui scrolle, et c'est assumé : la règle
 * « un écran, un contenu » vaut pour le flux d'exercices, pas pour une
 * page qu'on ouvre exprès depuis les réglages.
 *
 * En desktop la page prend toute la largeur et se lit comme une page
 * imprimée : un titre qui occupe le haut, puis vision et mission en
 * vis-à-vis, et le battement de la mission en pleine largeur — c'est
 * la phrase qui porte le propos, elle ne se lit pas coincée dans une
 * colonne. La mesure de ligne reste bornée : une page large ne veut
 * pas dire des lignes de 200 caractères, qu'on relit deux fois.
 *
 * La liste des crédits d'illustrations a été retirée d'ici sur demande.
 * Attention : la licence CC BY-SA des pictogrammes français impose de
 * citer leurs auteurs. La donnée reste servie par GET /credits — il
 * faudra la reposer quelque part pour que la condition soit remplie.
 */
export function About() {
  const { go, t } = useStore()

  return (
    <div className="screen">
      <div className="desk-hide">
        <NavHead onBack={() => go('settings')} title={t.about} />
      </div>

      <div className="screen-scroll page">
        <div className="page-inner">
          <PageBack onClick={() => go('settings')} label={t.settings} />

          <header className="about-hero">
            <Wordmark className="about-wordmark" />
            <p className="serif-italic about-slogan">{t.slogan}</p>
          </header>

          <div className="about-columns">
            <section className="stack prose" style={{ gap: 12 }}>
              <span className="eyebrow">{t.visionTitle}</span>
              <p className="display about-lead">{t.visionLead}</p>
              <p className="body about-body">{t.visionBody}</p>
            </section>

            <section className="stack prose" style={{ gap: 12 }}>
              <span className="eyebrow">{t.missionTitle}</span>
              <p className="display about-lead">{t.missionLead}</p>
              <p className="body about-body">{t.missionBody}</p>
            </section>
          </div>

          {/* Le rythme du texte d'origine — trois temps, de plus en plus
              courts — est ce qui lui donne sa force. On le garde, et on
              lui donne la pleine largeur : c'est le cœur du propos. */}
          <div className="about-beat">
            <p className="display about-beat-line">{t.missionBeat}</p>
            <p className="about-beat-then">{t.missionThen}</p>
          </div>

          <section className="stack prose about-close" style={{ gap: 12 }}>
            <p className="body about-body">{t.missionBoth}</p>
            <p className="display about-final">{t.missionClose}</p>
          </section>
        </div>
      </div>
    </div>
  )
}
