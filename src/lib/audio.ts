/**
 * Trois signatures sonores synthétisées, jamais sur l'exercice :
 *   ok  — quinte montante
 *   ko  — tierce descendante douce
 *   exp — note tenue
 *
 * Rien n'est téléchargé : tout est généré par l'AudioContext, donc
 * zéro latence et zéro octet. Le contexte doit être débloqué par un
 * geste utilisateur — voir unlock(), appelée au tout premier tap.
 */

export type Cue = 'ok' | 'ko' | 'exp'

type Tone = [freq: number, at: number, dur: number]

const SEQUENCES: Record<Cue, Tone[]> = {
  ok: [
    [659, 0, 0.18],
    [988, 0.12, 0.34],
  ],
  ko: [
    [392, 0, 0.26],
    [311, 0.2, 0.4],
  ],
  exp: [[523, 0, 0.55]],
}

const PEAKS: Record<Cue, number> = { ok: 0.1, ko: 0.075, exp: 0.045 }

let ctx: AudioContext | null = null

function context(): AudioContext | null {
  const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!AC) return null
  ctx ??= new AC()
  return ctx
}

/**
 * iOS et Android refusent de jouer un son sans geste préalable. Sans
 * cet appel au premier tap, le premier son de la session est muet —
 * et ça ne se reproduit pas sur desktop.
 */
export function unlock(): void {
  const ac = context()
  if (ac && ac.state === 'suspended') void ac.resume()
}

export function play(cue: Cue, muted: boolean): void {
  if (muted) return
  const ac = context()
  if (!ac) return
  if (ac.state === 'suspended') void ac.resume()

  const peak = PEAKS[cue]
  for (const [freq, at, dur] of SEQUENCES[cue]) {
    const osc = ac.createOscillator()
    const gain = ac.createGain()
    osc.type = 'sine'
    osc.frequency.value = freq

    const t0 = ac.currentTime + at
    gain.gain.setValueAtTime(0.0001, t0)
    gain.gain.linearRampToValueAtTime(peak, t0 + 0.03)
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)

    osc.connect(gain)
    gain.connect(ac.destination)
    osc.start(t0)
    osc.stop(t0 + dur + 0.05)
  }
}
