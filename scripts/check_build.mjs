#!/usr/bin/env node
/**
 * Garde-fou de déploiement : le bundle ne doit pas parler à 127.0.0.1.
 *
 * `dist/` est la racine servie par Apache. Le code a pour valeur par
 * défaut `http://127.0.0.1:8010`, l'adresse de boucle locale du serveur :
 * pratique en développement, mortelle en ligne, puisqu'elle désigne alors
 * la machine du visiteur. Un bundle construit sans `VITE_API_URL` se
 * déploie sans erreur et affiche « le serveur ne répond pas » à tout le
 * monde — la panne est silencieuse au moment où on la crée.
 *
 * `.env.production` pose la bonne valeur ; ce script vérifie qu'elle a
 * bien pris, et fait échouer `npm run build` sinon.
 */
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'

const DIR = new URL('../dist/assets/', import.meta.url).pathname
const LOOPBACK = /127\.0\.0\.1:\d+|localhost:\d+/

let bad = null
for (const name of readdirSync(DIR).filter((f) => f.endsWith('.js'))) {
  const hit = readFileSync(join(DIR, name), 'utf8').match(LOOPBACK)
  if (hit) bad = `${name} → ${hit[0]}`
}

if (bad) {
  console.error(
    `\n  Le bundle pointe sur une adresse locale : ${bad}` +
      `\n  Il ne marchera que sur la machine qui l'héberge.` +
      `\n  Vérifie VITE_API_URL (voir .env.production).\n`,
  )
  process.exit(1)
}

console.log('  bundle : API sur /api, aucune adresse locale')
