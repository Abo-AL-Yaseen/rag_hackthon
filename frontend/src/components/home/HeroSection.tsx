import { motion } from 'motion/react'
import { useState } from 'react'
import { siteMeta } from '../../data/homeContent'
import { Container } from '../ui/Container'
import { FeatureStrip } from './FeatureStrip'
import { HeroIllustration } from './HeroIllustration'
import { SearchBar } from './SearchBar'

export function HeroSection() {
  const [question, setQuestion] = useState('')

  return (
    <section className="relative overflow-hidden text-white">
      <div className="absolute inset-0 bg-[#101634]" />
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(ellipse at 18% 20%, rgba(117,71,237,0.28), transparent 42%), radial-gradient(ellipse at 78% 70%, rgba(69,109,255,0.14), transparent 40%), linear-gradient(160deg, #101634 0%, #0c1230 55%, #0a0f28 100%)',
        }}
        aria-hidden="true"
      />

      {/* Campus photo: desktop left only, soft fade into navy */}
      <div className="hero-campus" aria-hidden="true" />
      <div
        className="pointer-events-none absolute inset-0 hidden lg:block"
        style={{
          background:
            'linear-gradient(90deg, rgba(16,22,52,0.12) 0%, rgba(16,22,52,0.5) 36%, #101634 64%)',
        }}
        aria-hidden="true"
      />

      <Container className="relative z-10 pb-6 pt-10 lg:pb-8 lg:pt-14">
        <div className="grid items-center gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] lg:gap-16">
          {/* Text column (right in RTL) */}
          <div className="min-w-0">
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 text-[14px] font-medium text-[#c4b5fd]"
            >
              {siteMeta.projectName}
            </motion.p>

            <motion.h1
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.04 }}
              className="max-w-[18ch] text-[34px] font-bold leading-[1.4] sm:text-[42px] lg:text-[50px]"
            >
              دليلك الذكي في جامعة النجاح الوطنية
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.08 }}
              className="mt-4 max-w-xl text-[16px] font-normal leading-[1.85] text-white/72 sm:text-[17px]"
            >
              {siteMeta.description}
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.12 }}
              className="mt-7 w-full"
            >
              <SearchBar value={question} onChange={setQuestion} />
            </motion.div>
          </div>

          {/* Visual column (left in RTL) */}
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.08, duration: 0.45 }}
            className="min-w-0"
          >
            <HeroIllustration />
          </motion.div>
        </div>
      </Container>

      <FeatureStrip />

      <svg
        className="section-wave relative z-10 -mb-px text-[var(--background)]"
        viewBox="0 0 1440 90"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path
          fill="currentColor"
          d="M0,40 C220,100 420,0 720,35 C1020,70 1240,90 1440,30 L1440,90 L0,90 Z"
        />
      </svg>
    </section>
  )
}
