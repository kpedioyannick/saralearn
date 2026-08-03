#!/usr/bin/env node
/**
 * Contraintes de mise en page, vérifiées dans un vrai navigateur.
 *
 * Ces règles viennent du cahier des charges, pas d'un goût personnel :
 * « un écran, un contenu, pas de scroll », des cibles tactiles d'au
 * moins 44 px, et un rail qui ne recouvre jamais une réponse. Elles se
 * cassent silencieusement — d'où ce fichier.
 *
 *     node tests/test_layout.mjs
 *     SARA_URL=https://learn.sara.education node tests/test_layout.mjs
 *
 * Nécessite le Chromium de Playwright (ou CHROME=/chemin/vers/chrome).
 */
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'

const URL_BASE = (process.env.SARA_URL ?? 'http://localhost:4178').replace(/\/$/, '')
const CHROME =
  process.env.CHROME ??
  '/home/ubuntu/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome'
const PORT = 9455

if (!existsSync(CHROME)) {
  console.error(`Chromium introuvable : ${CHROME}\nDéfinis CHROME=/chemin/vers/chrome`)
  process.exit(2)
}

let ok = 0
let fail = 0
const chk = (label, expected, got) => {
  if (JSON.stringify(expected) === JSON.stringify(got)) {
    console.log(`  ok    ${label}`)
    ok++
  } else {
    console.log(`  ÉCHEC ${label} — attendu ${JSON.stringify(expected)}, obtenu ${JSON.stringify(got)}`)
    fail++
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const chrome = spawn(CHROME, [
  '--headless',
  '--no-sandbox',
  '--disable-gpu',
  '--hide-scrollbars',
  `--remote-debugging-port=${PORT}`,
  'about:blank',
])

let page
for (let i = 0; i < 60 && !page; i++) {
  try {
    const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json()
    page = list.find((t) => t.type === 'page')
  } catch {}
  if (!page) await sleep(250)
}

const ws = new WebSocket(page.webSocketDebuggerUrl)
let id = 0
const pending = new Map()
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data)
  if (m.id && pending.has(m.id)) {
    pending.get(m.id)(m)
    pending.delete(m.id)
  }
})
await new Promise((r) => ws.addEventListener('open', r))
const send = (method, params = {}) =>
  new Promise((res) => {
    const n = ++id
    pending.set(n, res)
    ws.send(JSON.stringify({ id: n, method, params }))
  })

async function audit(hash, width = 390, height = 844) {
  await send('Emulation.setDeviceMetricsOverride', {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: width < 1024,
  })
  await send('Page.navigate', { url: URL_BASE + '/' + hash })
  await sleep(3000)
  const r = await send('Runtime.evaluate', {
    expression: `(() => {
      const out = { problems: [], small: [] }
      const exo = document.querySelector('.exo')
      if (exo && exo.scrollHeight > exo.clientHeight + 1)
        out.problems.push('exercice scrolle : ' + exo.scrollHeight + ' > ' + exo.clientHeight)
      if (document.documentElement.scrollWidth > innerWidth + 1)
        out.problems.push('scroll horizontal')

      const rail = document.querySelector('.rail')
      if (rail) {
        const rr = rail.getBoundingClientRect()
        if (rr.top < 0 || rr.bottom > innerHeight) out.problems.push('rail hors écran')
        for (const el of document.querySelectorAll('.option, .exo-foot .btn-primary')) {
          const r = el.getBoundingClientRect()
          if (r.right > rr.left && r.left < rr.right && r.bottom > rr.top && r.top < rr.bottom)
            out.problems.push('rail recouvre « ' + el.textContent.trim().slice(0, 22) + ' »')
        }
        // Chaque bouton du rail doit rester une cible d'au moins 44 px.
        for (const b of rail.querySelectorAll('button')) {
          const disc = b.querySelector('.rail-disc')
          if (!disc) continue
          const d = disc.getBoundingClientRect()
          if (d.width < 44 || d.height < 44)
            out.small.push('rail ' + Math.round(d.width) + '×' + Math.round(d.height))
        }
      }
      // Le titre de la barre de navigation compte comme contenu : les
      // écrans hors exercice n'ont ni .display ni .option, et s'en tenir
      // à ces deux-là rendait la vérification muette sur la moitié de
      // l'app — elle passait sans jamais avoir quitté l'exercice.
      out.hasContent = !!document.querySelector('.display, .option, .nav-title')
      return out
    })()`,
    returnByValue: true,
  })
  return r.result?.result?.value ?? { problems: ['évaluation impossible'], small: [] }
}

// Les adresses sont en anglais et publiques : ce sont elles qu'on
// partage, et c'est par elles que le test entre dans chaque écran.
for (const [label, hash] of [
  ['exercice', ''],
  ['erreur', '#exercise/ko'],
  ['explication', '#exercise/exp'],
  ['mes thèmes', '#themes'],
  ['réglages', '#settings'],
  ['classement', '#leaderboard'],
  ['à propos', '#about'],
]) {
  console.log(`\n== ${label} ==`)
  const a = await audit(hash)
  chk('aucun problème de mise en page', [], a.problems)
  chk('cibles du rail ≥ 44 px', [], a.small)
  chk('du contenu est rendu', true, a.hasContent)
}

console.log(`\n== desktop ==`)
const d = await audit('', 1440, 900)
chk('cadre desktop sans problème', [], d.problems)

console.log(`\nRÉSULTAT : ${ok} réussis, ${fail} échoués`)
ws.close()
chrome.kill()
process.exit(fail === 0 ? 0 : 1)
