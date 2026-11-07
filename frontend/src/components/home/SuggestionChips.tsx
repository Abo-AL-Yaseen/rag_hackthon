import { BookOpen, Clock3, GraduationCap } from 'lucide-react'
import { searchSuggestions } from '../../data/homeContent'

const icons = {
  graduation: GraduationCap,
  book: BookOpen,
  clock: Clock3,
} as const

type Props = {
  onSelect: (value: string) => void
}

export function SuggestionChips({ onSelect }: Props) {
  return (
    <div className="mt-5">
      <p className="mb-3 text-[13px] font-medium text-white/65">أمثلة على ما يمكنك سؤاله:</p>
      <div className="flex flex-wrap gap-2.5">
        {searchSuggestions.map((suggestion) => {
          const Icon = icons[suggestion.icon]
          return (
            <button
              key={suggestion.id}
              type="button"
              onClick={() => onSelect(suggestion.label)}
              className="inline-flex h-10 items-center gap-2 rounded-xl border border-white/12 bg-white/[0.06] px-3.5 text-[13px] font-medium text-white/88 transition hover:border-[rgba(167,139,250,0.4)] hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--purple-light)]"
            >
              <Icon className="h-3.5 w-3.5 shrink-0 text-[var(--purple-light)]" aria-hidden="true" />
              {suggestion.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
