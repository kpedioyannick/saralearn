import { spokenText } from '../lib/spoken'
import { useSpeech } from '../lib/useSpeech'
import { useStore } from '../state/store'
import { Icon } from './Icon'

/**
 * Le bandeau de lecture, tout en haut de l'exercice — planche 4c.
 *
 * Un orbe de 44 px porte la lecture et la pause. Le bandeau coûte une
 * quarantaine de pixels, pris sur la zone de la question et jamais sur la
 * pile de réponses, qui reste intacte ; le loader se resserre juste
 * dessous.
 *
 * L'audio sort du rail et du pied de l'explication, où il était un lien
 * discret qu'on ne trouvait qu'après avoir répondu. Le même bandeau se
 * réutilise dans la séquence, avec un second bouton pour réécouter.
 *
 * Quand la lecture est coupée — réglage muet, ou navigateur sans voix —
 * le bandeau disparaît et le loader reprend sa position d'origine.
 */

/**
 * L'orbe du tuteur (sara.education/tutor), repris tel quel.
 *
 * Trois couches, et c'est leur combinaison qui fait l'objet : le disque
 * en dégradé avec son reflet, toujours visible ; l'onde de sept barres
 * qui bat À L'INTÉRIEUR pendant la lecture ; le voile sombre au `▶`, qui
 * ne se pose que lorsque le son est arrêté.
 *
 * Les deux derniers s'excluent — on ne montre pas ce qui se passe et ce
 * qu'on peut faire au même endroit. Voir `S.avatar`, `S.avatarPlay` et
 * `VoiceWave` dans `sara-student/src/views/tuteur/TuteurView.jsx`.
 */
const WAVE = [9, 16, 21, 13, 8, 14, 10]

export function AudioBar({ desktop = false }: { desktop?: boolean }) {
  const { s, exo, t } = useStore()
  const text = spokenText(exo, s.phase)
  const { supported, state, toggle, replay } = useSpeech(text, s.lang, !s.muted)

  if (s.muted || !supported || !text) return null

  const playing = state === 'playing'

  return (
    <div className={desktop ? 'audio-bar is-desktop' : 'audio-bar'}>
      {/* L'orbe prend la place de l'onde plate, à gauche : c'est lui qui
          lance et met en pause. Le bouton de droite, qui faisait déjà ce
          geste, disparaît — deux commandes pour la même chose dans un
          bandeau de quarante pixels. */}
      <button
        className="audio-orb"
        onClick={toggle}
        aria-label={playing ? t.pauseReading : t.resumeReading}
      >
        {/* L'anneau ne bat qu'à la lecture : il déborde de l'orbe, et
            posé en permanence il ferait vibrer un bandeau au repos. */}
        {playing && <span className="audio-orb-ring" aria-hidden="true" />}
        <span className="audio-orb-glint" aria-hidden="true" />

        {playing ? (
          <span className="audio-orb-wave" aria-hidden="true">
            {WAVE.map((h, i) => (
              <span key={i} style={{ height: h, animationDelay: `${(i * 0.09).toFixed(2)}s` }} />
            ))}
          </span>
        ) : (
          <span className="audio-orb-play" aria-hidden="true">
            <Icon name="play" size={16} stroke={2.2} fill="currentColor" />
          </span>
        )}
      </button>

      <div className="audio-acts">
        {/* Réécouter n'apparaît que dans la séquence : sur la question,
            le même geste est déjà celui du disque, qui repart du début
            une fois la lecture finie. */}
        {s.phase !== 'q' && (
          <button className="audio-btn" onClick={replay} aria-label={t.replayReading}>
            <Icon name="undo" size={17} stroke={2} />
          </button>
        )}
      </div>
    </div>
  )
}
