import { motion } from 'motion/react'
import { Bell, Calculator, CalendarDays, Star } from 'lucide-react'
import { Link } from 'react-router-dom'
import { quickTools } from '../../data/homeContent'
import { Container } from '../ui/Container'
import { SectionHeading } from '../ui/SectionHeading'
import { useToast } from '../ui/Toast'

const icons = {
  star: Star,
  calendar: CalendarDays,
  calculator: Calculator,
  bell: Bell,
} as const

const accents = [
  'from-[#fff7ed] to-[#ffedd5] text-[#c2410c]',
  'from-[#eef2ff] to-[#e0e7ff] text-[#4338ca]',
  'from-[#ecfdf5] to-[#d1fae5] text-[#047857]',
  'from-[#f5f3ff] to-[#ede9fe] text-[#6d28d9]',
]

export function QuickTools() {
  const { showToast } = useToast()

  return (
    <section className="pb-4 pt-2 sm:pb-8">
      <Container>
        <SectionHeading
          title="أدوات تساعدك في رحلتك الجامعية"
          description="اختصارات سريعة للخدمات التي ستُبنى تدريجيًا ضمن المنصة."
          align="start"
        />

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {quickTools.map((tool, index) => {
            const Icon = icons[tool.icon]
            return (
              <motion.div
                key={tool.id}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.35 }}
                transition={{ delay: index * 0.05 }}
                className={`rounded-[1.5rem] border border-white/70 bg-gradient-to-br p-5 shadow-[0_16px_40px_rgba(16,22,52,0.06)] ${accents[index % accents.length]} ${
                  index === 0 ? 'sm:col-span-2 lg:col-span-2 lg:min-h-[180px]' : ''
                }`}
              >
                <Link
                  to={tool.to}
                  onClick={(event) => {
                    event.preventDefault()
                    showToast(`أداة «${tool.title}» قيد التجهيز.`)
                  }}
                  className="flex h-full flex-col"
                >
                  <span className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-2xl bg-white/80 shadow-sm">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </span>
                  <h3 className="text-lg font-bold text-[var(--text)]">{tool.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-[var(--text-muted)]">{tool.description}</p>
                </Link>
              </motion.div>
            )
          })}
        </div>
      </Container>
    </section>
  )
}
