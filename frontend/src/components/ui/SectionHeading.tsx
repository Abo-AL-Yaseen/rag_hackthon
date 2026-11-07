type Props = {
  eyebrow?: string
  title: string
  description?: string
  align?: 'start' | 'center'
  tone?: 'light' | 'dark'
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  align = 'center',
  tone = 'light',
}: Props) {
  const alignClass = align === 'center' ? 'text-center items-center' : 'text-start items-start'
  const titleColor = tone === 'dark' ? 'text-white' : 'text-[var(--text)]'
  const descColor = tone === 'dark' ? 'text-white/70' : 'text-[var(--text-muted)]'

  return (
    <div className={`mb-10 flex flex-col gap-3 ${alignClass}`}>
      {eyebrow ? (
        <span className="inline-flex rounded-full bg-[rgba(117,71,237,0.12)] px-3 py-1 text-sm font-medium text-[var(--purple)]">
          {eyebrow}
        </span>
      ) : null}
      <h2 className={`text-3xl font-bold leading-tight sm:text-4xl ${titleColor}`}>{title}</h2>
      {description ? (
        <p className={`max-w-2xl text-base leading-8 sm:text-lg ${descColor}`}>{description}</p>
      ) : null}
    </div>
  )
}
