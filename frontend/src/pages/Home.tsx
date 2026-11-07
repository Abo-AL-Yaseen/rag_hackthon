import { AdvisorBanner } from '../components/home/AdvisorBanner'
import { BenefitsSection } from '../components/home/BenefitsSection'
import { ExploreSection } from '../components/home/ExploreSection'
import { HeroSection } from '../components/home/HeroSection'
import { QuickTools } from '../components/home/QuickTools'

export function HomePage() {
  return (
    <>
      <HeroSection />
      <ExploreSection />
      <AdvisorBanner />
      <QuickTools />
      <BenefitsSection />
    </>
  )
}
