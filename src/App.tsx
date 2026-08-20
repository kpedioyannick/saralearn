import { useEffect } from 'react'
import { MobileBar } from './components/MobileBar'
import { Sheet } from './components/Sheet'
import { Toast } from './components/Toast'
import { StatusBar } from './components/ui'
import { SHOW_MOCK_STATUS_BAR } from './config'
import { dict } from './i18n'
import { useIsDesktop } from './lib/useIsDesktop'
import { unlock } from './lib/audio'
import { About } from './screens/About'
import { Admin } from './screens/Admin'
import { Auth } from './screens/Auth'
import { Contact } from './screens/Contact'
import { Create } from './screens/Create'
import { DesktopFrame } from './screens/DesktopFrame'
import { Exercise } from './screens/Exercise'
import { Home } from './screens/Home'
import { PickCatalogue, Refine, Welcome } from './screens/Onboarding'
import { Picker, Picker2 } from './screens/Picker'
import { Pseudo } from './screens/Pseudo'
import { Publish } from './screens/Publish'
import { Rank, RankOne } from './screens/Rank'
import { Settings } from './screens/Settings'
import { Shared, SharedOne } from './screens/Shared'
import { Themes } from './screens/Themes'
import { type Screen, useStore } from './state/store'

/** Les écrans qui portent eux-mêmes leur en-tête — voir plus bas. */
const NO_BAR = new Set<Screen>(['home', 'exo', 'onb1', 'onb2', 'onb3', 'pseudo'])

function CurrentScreen() {
  const { s } = useStore()
  switch (s.screen) {
    case 'exo':
      return <Exercise />
    case 'onb1':
      return <Welcome />
    case 'onb2':
      return <PickCatalogue />
    case 'onb3':
      return <Refine />
    case 'picker':
      return <Picker />
    case 'picker2':
      return <Picker2 />
    case 'settings':
      return <Settings />
    case 'themes':
      return <Themes />
    case 'rank':
      return <Rank />
    case 'rankOne':
      return <RankOne />
    case 'create':
      return <Create />
    case 'publish':
      return <Publish />
    case 'auth':
      return <Auth />
    case 'about':
      return <About />
    case 'home':
      return <Home />
    case 'shared':
      return <Shared />
    case 'sharedOne':
      return <SharedOne />
    case 'contact':
      return <Contact />
    case 'pseudo':
      return <Pseudo />
  }
}

export function App() {
  const { s } = useStore()
  const isDesktop = useIsDesktop()

  useEffect(() => {
    document.documentElement.className = s.dark ? 'theme-dark' : 'theme-light'
  }, [s.dark])

  // L'attribut lang gouverne la césure, la sélection vocale et les
  // guillemets typographiques du navigateur — pas seulement le SEO.
  //
  // Le titre et la description suivent la même bascule. `index.html` les
  // écrit en anglais, la langue par défaut, pour le premier rendu et pour
  // les robots qui ne jouent pas le script ; passer en français doit les
  // emmener aussi, sinon l'onglet et le lien partagé restent dans une
  // langue que l'écran n'affiche plus.
  useEffect(() => {
    const t = dict(s.lang)
    document.documentElement.lang = s.lang
    document.title = t.metaTitle
    document
      .querySelector('meta[name="description"]')
      ?.setAttribute('content', `SaraLearn — ${t.slogan}`)
  }, [s.lang])

  /**
   * iOS refuse de jouer un son sans geste préalable. Le parcours nous
   * sauve — le premier audio suit un tap — mais il faut débloquer le
   * contexte sur ce tout premier tap, quel qu'il soit.
   */
  useEffect(() => {
    const once = () => unlock()
    window.addEventListener('pointerdown', once, { once: true })
    return () => window.removeEventListener('pointerdown', once)
  }, [])

  return (
    <div className="app">
      {isDesktop ? (
        <DesktopFrame>
          <CurrentScreen />
        </DesktopFrame>
      ) : (
        <>
          {SHOW_MOCK_STATUS_BAR && <StatusBar />}
          {/* Trois familles d'écrans se passent de la barre : l'accueil
              public, qui porte déjà sa marque et son entrée « se
              connecter » ; le feed, dont la bande du haut revient au
              bandeau de lecture depuis la planche 4c — sa marque et ses
              trois points sont descendus dans `.exo-head` ; et
              l'inscription, qui porte sa marque et sa bascule de langue
              dans l'écran, et son compte d'étapes sur les deux suivants.
              Une barre par-dessus les doublait. */}
          {!NO_BAR.has(s.screen) && <MobileBar />}
          <CurrentScreen />
        </>
      )}
      <Admin />
      <Sheet />
      <Toast />
    </div>
  )
}
