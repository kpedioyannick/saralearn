import { useEffect } from 'react'
import { MobileBar } from './components/MobileBar'
import { Sheet } from './components/Sheet'
import { Toast } from './components/Toast'
import { StatusBar } from './components/ui'
import { SHOW_MOCK_STATUS_BAR } from './config'
import { useIsDesktop } from './lib/useIsDesktop'
import { unlock } from './lib/audio'
import { About } from './screens/About'
import { Admin } from './screens/Admin'
import { Auth } from './screens/Auth'
import { Create } from './screens/Create'
import { DesktopFrame } from './screens/DesktopFrame'
import { Exercise } from './screens/Exercise'
import { PickCategories, PickSubcategories, Welcome } from './screens/Onboarding'
import { Picker, Picker2 } from './screens/Picker'
import { Publish } from './screens/Publish'
import { Rank, RankOne } from './screens/Rank'
import { Settings } from './screens/Settings'
import { Themes } from './screens/Themes'
import { useStore } from './state/store'

function CurrentScreen() {
  const { s } = useStore()
  switch (s.screen) {
    case 'exo':
      return <Exercise />
    case 'onb1':
      return <Welcome />
    case 'onb2':
      return <PickCategories />
    case 'onb3':
      return <PickSubcategories />
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
  useEffect(() => {
    document.documentElement.lang = s.lang
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
          <MobileBar />
          <CurrentScreen />
        </>
      )}
      <Admin />
      <Sheet />
      <Toast />
    </div>
  )
}
