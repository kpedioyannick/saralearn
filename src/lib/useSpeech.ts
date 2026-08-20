import { useCallback, useEffect, useRef, useState } from 'react'
import type { Lang } from '../i18n'
import * as speech from './speech'

export type SpeechState = 'playing' | 'paused' | 'done'

/**
 * Pilote la lecture d'un texte et rend l'état que le bandeau affiche.
 *
 * Le texte change à chaque phase de la séquence — la question, puis
 * l'erreur, puis l'explication. Chaque changement relance la lecture :
 * c'est ce que la planche montre, une onde qui repart avec le contenu.
 *
 * AU RECHARGEMENT, la lecture ne peut pas démarrer seule : les
 * navigateurs refusent tout son avant un geste, et ça vaut pour le MP3
 * comme pour la voix de synthèse. On ne contourne pas la règle — elle
 * est saine — on la prend au mot : le refus arme une écoute sur le
 * PREMIER geste venu, où qu'il tombe. Un swipe, une réponse, une touche,
 * et la question se lit. Rien à trouver, rien à viser : l'orbe n'a plus
 * à être le seul moyen de lancer ce qui devait partir tout seul.
 */
export function useSpeech(text: string, lang: Lang, enabled: boolean) {
  const [state, setState] = useState<SpeechState>('done')

  // `supported` n'est pas figé au montage : tant que le serveur n'a pas
  // répondu, on ignore s'il porte une clé. Il peut donc passer à faux en
  // cours de session — et le bandeau disparaît alors, ce qui est l'état
  // « lecture coupée » attendu.
  const [available, setAvailable] = useState(() => speech.supported())
  const refresh = useCallback(() => setAvailable(speech.supported()), [])

  /** Retire l'écoute du premier geste, s'il y en a une en attente. */
  const disarm = useRef<(() => void) | null>(null)
  const forget = useCallback(() => {
    disarm.current?.()
    disarm.current = null
  }, [])

  const start = useCallback(() => {
    forget()
    setState('playing')
    speech.speak(text, lang, {
      onEnd: () => setState('done'),
      onError: () => {
        setState('done')
        refresh()
      },
      onBlocked: () => {
        // En pause, pas « terminé » : rien n'a été lu, et l'orbe doit
        // montrer le « ▶ » plutôt qu'une onde muette.
        setState('paused')
        // On relance depuis le début plutôt que de reprendre : selon le
        // moteur bloqué, il n'y a parfois rien à reprendre. Le geste
        // donne au document son activation, l'appel asynchrone qui suit
        // passe donc, même si le MP3 doit être redemandé.
        const go = () => {
          forget()
          start()
        }
        window.addEventListener('pointerdown', go, { once: true })
        window.addEventListener('keydown', go, { once: true })
        disarm.current = () => {
          window.removeEventListener('pointerdown', go)
          window.removeEventListener('keydown', go)
        }
      },
    })
    // `start` se référence elle-même dans `go` : la dépendance est
    // circulaire par nature, et la fonction est stable pour un texte donné.
    // eslint-disable-next-line @typescript-eslint/no-use-before-define
  }, [text, lang, refresh, forget])

  // La lecture repart quand le TEXTE change, pas à chaque rendu : `s` du
  // store se renouvelle à chaque drag, et sans cette dépendance étroite
  // la question se relirait à chaque pixel de swipe.
  useEffect(() => {
    if (!enabled || !text.trim()) {
      speech.cancel()
      forget()
      setState('done')
      return
    }
    start()
    return () => {
      speech.cancel()
      forget()
    }
  }, [enabled, text, start, forget])

  // L'état courant lu hors du rendu. Décider dans l'updater de `setState`
  // reviendrait à mettre en pause depuis une fonction que React s'autorise
  // à rejouer — en mode strict elle l'est, et la lecture partait deux fois.
  const live = useRef<SpeechState>('done')
  useEffect(() => {
    live.current = state
  }, [state])

  const toggle = useCallback(() => {
    if (live.current === 'playing') {
      speech.pause()
      setState('paused')
      return
    }
    if (live.current === 'paused') {
      speech.resume()
      setState('playing')
      return
    }
    // Lecture terminée : le bouton la reprend depuis le début, sinon il
    // ne ferait plus rien une fois la question lue.
    start()
  }, [start])

  const replay = useCallback(() => start(), [start])

  return { supported: available, state, toggle, replay }
}
