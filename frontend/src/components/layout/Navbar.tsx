import { AnimatePresence, motion } from 'motion/react'
import { Menu, UserRound, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { navLinks, siteMeta } from '../../data/homeContent'
import { Container } from '../ui/Container'
import { useToast } from '../ui/Toast'

export function Navbar() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const { showToast } = useToast()
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    setOpen(false)
  }, [location.pathname])

  return (
    <header
      className={`sticky top-0 z-50 border-b border-white/10 bg-[#101634] transition ${
        scrolled ? 'shadow-[0_8px_28px_rgba(0,0,0,0.28)]' : ''
      }`}
    >
      <Container className="relative flex h-[74px] items-center justify-between gap-3 lg:justify-center">
        <Link to="/" className="relative z-10 flex min-w-0 items-center gap-3 lg:absolute lg:inset-y-0 lg:start-0 lg:flex">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[var(--purple)] text-white">
            <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
              <path
                fill="currentColor"
                d="M12 2.5 3.5 7v5.2c0 5.1 3.5 9.7 8.5 10.8 5-1.1 8.5-5.7 8.5-10.8V7L12 2.5Zm0 2.2 6.5 3.4v4.1c0 3.8-2.5 7.3-6.5 8.4-4-1.1-6.5-4.6-6.5-8.4V8.1L12 4.7Z"
              />
            </svg>
          </span>
          <span className="min-w-0">
            <span className="block truncate text-[14px] font-semibold text-white sm:text-[15px]">
              {siteMeta.projectName}
            </span>
            <span className="block truncate text-[12px] font-normal text-white/60">
              {siteMeta.universityName}
            </span>
          </span>
        </Link>

        <nav
          className="hidden items-center justify-center gap-1 lg:flex"
          aria-label="التنقل الرئيسي"
        >
          {navLinks.map((link) => (
            <NavLink
              key={link.id}
              to={link.to}
              className={({ isActive }) =>
                `rounded-lg px-3.5 py-2 text-[14px] font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--purple-light)] ${
                  isActive
                    ? 'bg-[rgba(117,71,237,0.28)] text-[#ddd6fe]'
                    : 'text-white/80 hover:bg-white/[0.08] hover:text-white'
                }`
              }
              onClick={(event) => {
                if ('soon' in link && link.soon) {
                  event.preventDefault()
                  showToast('هذه الصفحة قيد التجهيز وستتوفر قريبًا.')
                }
              }}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="relative z-10 flex items-center gap-2 lg:absolute lg:inset-y-0 lg:end-0 lg:flex">
          <button
            type="button"
            onClick={() => showToast('تسجيل الدخول سيُضاف لاحقًا مع تكامل المنصة.')}
            className="hidden items-center gap-2 rounded-lg border border-white/15 bg-transparent px-3.5 py-2 text-[14px] font-medium text-white/90 transition hover:border-white/25 hover:bg-white/[0.08] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--purple-light)] sm:inline-flex"
          >
            <UserRound className="h-4 w-4" aria-hidden="true" />
            تسجيل الدخول
          </button>

          <button
            type="button"
            className="inline-flex rounded-lg border border-white/15 bg-white/[0.08] p-2 text-white lg:hidden"
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? 'إغلاق القائمة' : 'فتح القائمة'}
            onClick={() => setOpen((value) => !value)}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </Container>

      <AnimatePresence>
        {open ? (
          <motion.div
            id="mobile-nav"
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="border-t border-white/10 bg-[#0d132c] lg:hidden"
          >
            <Container className="flex flex-col gap-1.5 py-4">
              {navLinks.map((link) => (
                <NavLink
                  key={link.id}
                  to={link.to}
                  className={({ isActive }) =>
                    `rounded-lg px-4 py-3 text-[14px] font-medium ${
                      isActive
                        ? 'bg-[rgba(117,71,237,0.28)] text-[#ddd6fe]'
                        : 'text-white/85 hover:bg-white/[0.08]'
                    }`
                  }
                  onClick={(event) => {
                    if ('soon' in link && link.soon) {
                      event.preventDefault()
                      showToast('هذه الصفحة قيد التجهيز وستتوفر قريبًا.')
                      setOpen(false)
                    }
                  }}
                >
                  {link.label}
                </NavLink>
              ))}
              <button
                type="button"
                onClick={() => {
                  showToast('تسجيل الدخول سيُضاف لاحقًا مع تكامل المنصة.')
                  setOpen(false)
                }}
                className="mt-1 inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-4 py-3 text-[14px] font-medium text-white"
              >
                <UserRound className="h-4 w-4" aria-hidden="true" />
                تسجيل الدخول
              </button>
            </Container>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </header>
  )
}
