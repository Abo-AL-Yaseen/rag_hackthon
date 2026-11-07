import { motion } from 'motion/react'
import { BookOpenCheck, Languages, LayoutDashboard } from 'lucide-react'
import { benefits } from '../../data/homeContent'
import { Container } from '../ui/Container'
import { SectionHeading } from '../ui/SectionHeading'

const icons = {
  languages: Languages,
  'book-open': BookOpenCheck,
  layout: LayoutDashboard,
} as const

export function BenefitsSection() {
  return (
    <section className="py-10 sm:py-14">
      <Container>
        <div className="overflow-hidden rounded-[2rem] border border-[rgba(18,25,54,0.06)] bg-white p-6 shadow-[var(--shadow-soft)] sm:p-8">
          <SectionHeading
            title="لماذا تستخدم المنصة؟"
            description="مزايا ثابتة للمنصة دون الاعتماد على أرقام غير موثّقة."
            align="start"
          />
          <div className="grid gap-4 md:grid-cols-3">
            {benefits.map((item, index) => {
              const Icon = icons[item.icon]
              return (
                <motion.article
                  key={item.id}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.4 }}
                  transition={{ delay: index * 0.06 }}
                  className="rounded-3xl border border-[rgba(18,25,54,0.06)] bg-[linear-gradient(180deg,#fbfaff,#ffffff)] p-5"
                >
                  <div className="mb-4 inline-flex rounded-2xl bg-[rgba(117,71,237,0.1)] p-3 text-[var(--purple)]">
                    <Icon className="h-5 w-5" aria-hidden="true" />
                  </div>
                  <h3 className="mb-2 text-base font-bold text-[var(--text)]">{item.title}</h3>
                  <p className="text-sm leading-7 text-[var(--text-muted)]">{item.description}</p>
                </motion.article>
              )
            })}
          </div>
        </div>
      </Container>
    </section>
  )
}
