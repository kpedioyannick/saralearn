/**
 * La voix de l'app.
 *
 * Deux moteurs derrière la même API, dans cet ordre :
 *
 *   · `google` — le MP3 rendu par `POST /tts` (Google Cloud TTS, voix
 *     WaveNet). C'est le moteur de la classe avec Sara, et c'est celui
 *     qu'on veut : une seule voix, la même sur tous les appareils ;
 *   · `web` — `speechSynthesis`, en repli seulement. La voix du
 *     navigateur dépend de ce que la machine du visiteur a installé :
 *     absente sur certaines, robotique sur d'autres. Elle vaut mieux que
 *     le silence, pas mieux que la première.
 *
 * Le repli est automatique et silencieux pour l'apprenant : clé absente
 * (501), serveur muet, lecture refusée — il reste une voix.
 *
 * Le MP3 apporte au passage ce que `speechSynthesis` ne sait pas faire
 * proprement : une pause et une reprise fiables. Un élément `<audio>` se
 * met en pause où il en est ; `speechSynthesis.pause()` reste bloqué sur
 * plusieurs moteurs, ce qui obligeait à relire depuis le début.
 */

import type { Lang } from '../i18n'
import { api } from './api'

/** Les étiquettes BCP-47 attendues par les voix du navigateur. */
const TAG: Record<Lang, string> = { fr: 'fr-FR', en: 'en-US' }

function synth(): SpeechSynthesis | null {
  if (typeof window === 'undefined') return null
  return window.speechSynthesis ?? null
}

/**
 * Une fois le serveur déclaré muet — 501, pas de clé sur ce déploiement —
 * on cesse de le rappeler pour la durée de la session : chaque exercice
 * relancerait sinon un aller-retour qui échoue avant de parler.
 */
let serverMute = false

function webSupported(): boolean {
  return (
    typeof window !== 'undefined' &&
    'speechSynthesis' in window &&
    typeof window.SpeechSynthesisUtterance === 'function'
  )
}

/**
 * Y a-t-il encore une voix quelque part ?
 *
 * Tant que le serveur n'a pas dit non, oui — on ne sait qu'il manque une
 * clé qu'après un premier appel. Une fois qu'il l'a dit, il reste le
 * navigateur. Si les deux manquent, la réponse est non, et le bandeau de
 * lecture disparaît : c'est exactement l'état « lecture coupée » de la
 * planche 4c.
 *
 * À relire après un échec — sa valeur change en cours de session.
 */
export function supported(): boolean {
  if (typeof window === 'undefined') return false
  return !serverMute || webSupported()
}

interface Handlers {
  onEnd?: () => void
  onError?: () => void
  /**
   * Le navigateur refuse de jouer AVANT un geste. Ce n'est ni une fin ni
   * une panne : la voix est là, c'est l'autorisation qui manque. Le
   * distinguer permet à l'appelant d'attendre le premier geste venu au
   * lieu d'afficher une lecture qui n'a pas lieu.
   */
  onBlocked?: () => void
}

/**
 * Chaque lecture porte son numéro. Une réponse qui arrive après un
 * `cancel()` — le feed a avancé pendant le téléchargement du MP3 —
 * appartient à une génération périmée : on la jette au lieu de la jouer
 * par-dessus la question suivante.
 */
let generation = 0

let audio: HTMLAudioElement | null = null
let audioUrl: string | null = null

function dropAudio(): void {
  if (audio) {
    try {
      audio.pause()
    } catch {
      /* l'élément est déjà mort */
    }
    audio = null
  }
  if (audioUrl) {
    URL.revokeObjectURL(audioUrl)
    audioUrl = null
  }
}

// --------------------------------------------------------------------------
// Repli : la voix du navigateur
// --------------------------------------------------------------------------

/**
 * Chrome coupe une utterance qui dépasse une quinzaine de secondes et
 * laisse `speaking` bloqué à true. La parade retenue dans la classe est
 * de découper en phrases courtes mises en file : chaque morceau reste
 * sous le seuil, et aucun bricolage pause/reprise n'est nécessaire.
 */
const CHUNK_MAX = 180

function chunk(text: string): string[] {
  const sentences = text.match(/[^.!?…]+[.!?…]*/g) ?? [text]
  const out: string[] = []
  let buf = ''
  const push = () => {
    if (buf.trim()) out.push(buf.trim())
    buf = ''
  }
  for (const sentence of sentences) {
    if ((buf + sentence).length <= CHUNK_MAX) {
      buf += sentence
      continue
    }
    push()
    if (sentence.length <= CHUNK_MAX) {
      buf = sentence
      continue
    }
    let rest = sentence
    while (rest.length > CHUNK_MAX) {
      let cut = rest.lastIndexOf(',', CHUNK_MAX)
      if (cut < 40) cut = rest.lastIndexOf(' ', CHUNK_MAX)
      if (cut < 40) cut = CHUNK_MAX
      out.push(rest.slice(0, cut + 1).trim())
      rest = rest.slice(cut + 1)
    }
    buf = rest
  }
  push()
  return out
}

function voiceFor(lang: Lang): SpeechSynthesisVoice | null {
  const s = synth()
  if (!s) return null
  const tag = TAG[lang]
  const all = s.getVoices()
  return (
    all.find((v) => /google|natural|neural|premium/i.test(v.name) && v.lang.startsWith(lang)) ??
    all.find((v) => v.lang === tag) ??
    all.find((v) => v.lang.startsWith(lang)) ??
    null
  )
}

function speakWeb(text: string, lang: Lang, rate: number, gen: number, handlers: Handlers): void {
  const s = synth()
  if (!s || !webSupported()) {
    handlers.onError?.()
    return
  }
  const parts = chunk(text)
  const voice = voiceFor(lang)
  let left = parts.length

  for (const part of parts) {
    const utter = new SpeechSynthesisUtterance(part)
    if (voice) utter.voice = voice
    utter.lang = voice?.lang ?? TAG[lang]
    utter.rate = rate
    const done = () => {
      if (gen !== generation) return
      left -= 1
      if (left <= 0) handlers.onEnd?.()
    }
    utter.onend = done
    utter.onerror = (e) => {
      if (gen !== generation) return
      // `not-allowed` = le geste manque, comme pour le MP3. Compté comme
      // une fin, il faisait disparaître le bandeau d'une lecture qui
      // n'avait jamais commencé.
      if (e.error === 'not-allowed') {
        handlers.onBlocked?.()
        return
      }
      done()
    }
    s.speak(utter)
  }
}

// --------------------------------------------------------------------------
// API publique
// --------------------------------------------------------------------------

/** Coupe net : le MP3 en cours, la file du navigateur, et les réponses en vol. */
export function cancel(): void {
  generation += 1
  dropAudio()
  synth()?.cancel()
}

export function speak(text: string, lang: Lang, handlers: Handlers = {}, rate = 1): void {
  const clean = text.trim()
  if (!clean) {
    handlers.onEnd?.()
    return
  }

  cancel()
  const gen = generation

  if (serverMute) {
    speakWeb(clean, lang, rate, gen, handlers)
    return
  }

  void api
    .tts(clean, lang, rate)
    .then(async (blob) => {
      if (gen !== generation) return
      audioUrl = URL.createObjectURL(blob)
      const el = new Audio(audioUrl)
      audio = el
      el.onended = () => {
        if (gen !== generation) return
        dropAudio()
        handlers.onEnd?.()
      }
      el.onerror = () => {
        if (gen !== generation) return
        dropAudio()
        handlers.onError?.()
      }
      await el.play()
    })
    .catch((err: unknown) => {
      if (gen !== generation) return
      // Deux refus disent « ce déploiement ne sait pas parler », pas
      // « réessaie plus tard » : 501, la clé manque ; 404, l'API servie
      // est antérieure à la route. Dans les deux cas on bascule sur le
      // navigateur pour la session, sinon chaque exercice relance un
      // aller-retour perdu d'avance. Une 502 passagère, elle, ne coupe
      // rien : le prochain exercice retentera le serveur.
      // Un refus d'autoplay n'est pas un serveur muet : basculer sur
      // `speechSynthesis` ne servirait à rien, la même règle le bloque.
      // On garde le MP3 tel quel — il repartira au premier geste sans
      // être retéléchargé.
      if (err instanceof DOMException && err.name === 'NotAllowedError') {
        handlers.onBlocked?.()
        return
      }
      const msg = err instanceof Error ? err.message : ''
      if (msg.includes('501') || msg.includes('404')) serverMute = true
      dropAudio()
      speakWeb(clean, lang, rate, gen, handlers)
    })
}

export function pause(): void {
  if (audio) {
    audio.pause()
    return
  }
  synth()?.pause()
}

export function resume(): void {
  if (audio) {
    void audio.play()
    return
  }
  synth()?.resume()
}
