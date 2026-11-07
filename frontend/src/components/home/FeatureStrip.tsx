import { motion } from 'motion/react'
import { Clock3, Layers3, Target, Zap } from 'lucide-react'
import { featureStrip } from '../../data/homeContent'
import { Container } from '../ui/Container'

const icons = {
  zap: Zap,
  layers: Layers3,
  target: Target,
  clock: Clock3,
} as const

const tones = {
  purple: 'bg-[rgba(124,58,237,0.18)] text-[#c4b5fd]',
  blue: 'bg-[rgba(59,130,246,0.18)] text-[#93c5fd]',
  teal: 'bg-[rgba(20,184,166,0.18)] text-[#5eead4]',
  violet: 'bg-[rgba(139,92,246,0.18)] text-[#ddd6fe]',
} as const

export function FeatureStrip() {
  return (
    <Container className="relative z-10 pb-10 pt-2">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 lg:gap-4">
        {featureStrip.map((item, index) => {
          const Icon = icons[item.icon]
          return (
            <motion.article
              key={item.id}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, amount: 0.35 }}
              transition={{ delay: index * 0.05, duration: 0.35 }}
              className="flex h-full flex-col gap-3 rounded-2xl border border-white/12 bg-[rgba(255,255,255,0.07)] p-5 backdrop-blur-md transition hover:border-[rgba(167,139,250,0.35)] hover:bg-[rgba(255,255,255,0.1)]"
            >
              <span
                className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${tones[item.tone]}`}
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
              </span>
              <h3 className="text-[15px] font-semibold leading-6 text-white">{item.title}</h3>
              <p className="text-[13px] font-normal leading-6 text-white/65">{item.description}</p>
            </motion.article>
          )
        })}
      </div>
    </Container>
  )
}
