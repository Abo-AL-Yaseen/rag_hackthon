import { motion } from 'motion/react'
import { ArrowLeft, BookOpen, ClipboardList, GraduationCap, Layers3 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useToast } from '../ui/Toast'

const iconMap = {
  graduation: GraduationCap,
  book: BookOpen,
  layers: Layers3,
  clipboard: ClipboardList,
} as const

const toneMap = {
  purple: 'from-[#7547ed] to-[#9b6bff]',
  blue: 'from-[#456dff] to-[#6ea0ff]',
  mint: 'from-[#19b79b] to-[#37d7be]',
  violet: 'from-[#7c3aed] to-[#c084fc]',
} as const

type Props = {
  title: string
  description: string
  icon: keyof typeof iconMap
  tone: keyof typeof toneMap
  to: string
  index: number
}

export function TopicCard({ title, description, icon, tone, to, index }: Props) {
  const Icon = iconMap[icon]
  const { showToast } = useToast()

  return (
    <motion.article
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.35 }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
      className="group flex h-full flex-col rounded-[1.6rem] border border-[rgba(18,25,54,0.06)] bg-white p-5 shadow-[0_18px_40px_rgba(16,22,52,0.06)] transition hover:-translate-y-1 hover:border-[rgba(117,71,237,0.25)] hover:shadow-[0_24px_50px_rgba(117,71,237,0.12)]"
    >
      <div
        className={`mb-5 inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br ${toneMap[tone]} text-white shadow-lg`}
      >
        <Icon className="h-6 w-6" aria-hidden="true" />
      </div>
      <h3 className="mb-2 text-lg font-bold text-[var(--text)]">{title}</h3>
      <p className="mb-6 flex-1 text-sm leading-7 text-[var(--text-muted)]">{description}</p>
      <Link
        to={to}
        onClick={(event) => {
          event.preventDefault()
          showToast(`قسم «${title}» قادم قريبًا.`)
        }}
        className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[rgba(18,25,54,0.08)] text-[var(--purple)] transition group-hover:bg-[var(--purple)] group-hover:text-white"
        aria-label={`فتح ${title}`}
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      </Link>
    </motion.article>
  )
}
