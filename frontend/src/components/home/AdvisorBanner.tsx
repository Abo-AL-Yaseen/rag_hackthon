import { motion } from 'motion/react'
import { ArrowLeft, MessageCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Container } from '../ui/Container'

export function AdvisorBanner() {
  return (
    <section className="py-8 sm:py-12">
      <Container>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.4 }}
          className="relative overflow-hidden rounded-[2rem] border border-[rgba(117,71,237,0.18)] bg-[linear-gradient(120deg,#efe9ff_0%,#e7ecff_45%,#f4f0ff_100%)] p-6 shadow-[0_24px_60px_rgba(117,71,237,0.12)] sm:p-8"
        >
          <div className="pointer-events-none absolute -left-10 top-0 h-40 w-40 rounded-full bg-[rgba(117,71,237,0.18)] blur-3xl" />
          <div className="pointer-events-none absolute -right-8 bottom-0 h-36 w-36 rounded-full bg-[rgba(69,109,255,0.16)] blur-3xl" />

          <div className="relative z-10 grid items-center gap-6 lg:grid-cols-[1fr_auto]">
            <div>
              <div className="mb-4 inline-flex rounded-2xl bg-white/70 p-3 text-[var(--purple)] shadow-sm backdrop-blur">
                <MessageCircle className="h-6 w-6" aria-hidden="true" />
              </div>
              <h2 className="text-2xl font-bold text-[var(--text)] sm:text-3xl">
                مساعدك الأكاديمي، أقرب إليك
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--text-muted)] sm:text-base">
                اطرح استفسارك عن المساقات والخطط والأنظمة الجامعية، وتعرّف على المعلومات ذات الصلة
                ومصادرها.
              </p>
            </div>

            <Link
              to="/advisor"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-[var(--purple)] px-5 py-3 text-sm font-semibold text-white shadow-[0_14px_30px_rgba(117,71,237,0.35)] transition hover:brightness-110"
            >
              ابدأ المحادثة الآن
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </motion.div>
      </Container>
    </section>
  )
}
