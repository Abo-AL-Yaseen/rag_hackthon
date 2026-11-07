import { Link } from 'react-router-dom'
import { footerGroups, siteMeta } from '../../data/homeContent'
import { Container } from '../ui/Container'
import { useToast } from '../ui/Toast'

export function Footer() {
  const { showToast } = useToast()

  return (
    <footer className="relative overflow-hidden bg-[var(--navy-deep)] text-white">
      <svg
        className="section-wave absolute inset-x-0 top-0 -translate-y-[99%] text-[var(--navy-deep)]"
        viewBox="0 0 1440 90"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path
          fill="currentColor"
          d="M0,64 C240,110 480,10 720,40 C960,70 1200,110 1440,40 L1440,90 L0,90 Z"
        />
      </svg>

      <Container className="relative z-10 grid gap-10 py-16 md:grid-cols-[1.3fr_1fr_1fr]">
        <div>
          <div className="mb-4 flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-2xl bg-[linear-gradient(145deg,#7547ed,#456dff)]">
              <svg viewBox="0 0 24 24" className="h-6 w-6" aria-hidden="true">
                <path
                  fill="currentColor"
                  d="M12 2.5 3.5 7v5.2c0 5.1 3.5 9.7 8.5 10.8 5-1.1 8.5-5.7 8.5-10.8V7L12 2.5Z"
                />
              </svg>
            </span>
            <div>
              <p className="font-bold">{siteMeta.projectName}</p>
              <p className="text-sm text-white/65">{siteMeta.universityName}</p>
            </div>
          </div>
          <p className="max-w-md text-sm leading-7 text-white/70">
            منصة مساعدة أكاديمية لإرشاد الطلبة حول التخصصات والخطط والمساقات استنادًا إلى المصادر
            المتاحة داخل النظام.
          </p>
          <p className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm leading-7 text-white/80">
            {siteMeta.disclaimer}
          </p>
        </div>

        {footerGroups.map((group) => (
          <div key={group.title}>
            <h3 className="mb-4 text-sm font-semibold text-white">{group.title}</h3>
            <ul className="space-y-3 text-sm text-white/70">
              {group.links.map((link) => (
                <li key={link.label}>
                  <Link
                    to={link.to}
                    className="transition hover:text-white"
                    onClick={(event) => {
                      if (link.to !== '/' && link.to !== '/advisor') {
                        event.preventDefault()
                        showToast('هذه الصفحة قيد التجهيز وستتوفر قريبًا.')
                      }
                    }}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </Container>

      <div className="border-t border-white/10">
        <Container className="flex flex-col gap-3 py-5 text-xs text-white/55 sm:flex-row sm:items-center sm:justify-between">
          <p>
            © {new Date().getFullYear()} {siteMeta.projectName}. مشروع طلابي مساعد — ليس منصة رسمية
            تابعة للجامعة.
          </p>
          <a
            href={siteMeta.officialSite}
            target="_blank"
            rel="noreferrer"
            className="hover:text-white"
          >
            الموقع الرسمي للجامعة
          </a>
        </Container>
      </div>

      <div
        className="pointer-events-none absolute inset-x-0 bottom-0 h-24 opacity-30"
        aria-hidden="true"
        style={{
          background:
            'linear-gradient(transparent, rgba(117,71,237,0.18)), radial-gradient(circle at 20% 100%, rgba(69,109,255,0.25), transparent 40%), radial-gradient(circle at 80% 100%, rgba(55,215,190,0.15), transparent 35%)',
        }}
      />
    </footer>
  )
}
