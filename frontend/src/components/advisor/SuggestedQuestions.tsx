import { BookOpen, CalendarDays, GraduationCap, Zap } from 'lucide-react'

export type SuggestionItem = {
  id: string
  text: string
  tone: 'purple' | 'blue' | 'mint' | 'green' | 'orange' | 'pink'
}

type Props = {
  items: SuggestionItem[]
  onSelect: (text: string) => void
}

const TONE_BG: Record<SuggestionItem['tone'], string> = {
  purple: 'rgba(111, 76, 227, 0.14)',
  blue: 'rgba(69, 109, 255, 0.14)',
  mint: 'rgba(55, 215, 190, 0.16)',
  green: 'rgba(52, 190, 130, 0.14)',
  orange: 'rgba(245, 158, 90, 0.18)',
  pink: 'rgba(236, 120, 170, 0.16)',
}

const TONE_FG: Record<SuggestionItem['tone'], string> = {
  purple: '#6f4ce3',
  blue: '#456dff',
  mint: '#1fafa0',
  green: '#2f9d6a',
  orange: '#d9772f',
  pink: '#d4538c',
}

function SuggestionIcon({ tone }: { tone: SuggestionItem['tone'] }) {
  const color = TONE_FG[tone]
  if (tone === 'blue' || tone === 'green') {
    return <BookOpen className="h-5 w-5" style={{ color }} strokeWidth={1.8} aria-hidden="true" />
  }
  if (tone === 'mint' || tone === 'orange') {
    return <CalendarDays className="h-5 w-5" style={{ color }} strokeWidth={1.8} aria-hidden="true" />
  }
  return <GraduationCap className="h-5 w-5" style={{ color }} strokeWidth={1.8} aria-hidden="true" />
}

export function SuggestedQuestions({ items, onSelect }: Props) {
  return (
    <section className="advisor-suggestions" aria-label="أسئلة مقترحة">
      <h2 className="advisor-suggestions__label">
        <Zap className="h-4 w-4" strokeWidth={2.2} aria-hidden="true" />
        جرّب هذه الأسئلة
      </h2>
      <div className="advisor-suggestions__grid">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className="advisor-suggestion-card"
            onClick={() => onSelect(item.text)}
          >
            <span
              className="advisor-suggestion-card__icon"
              style={{ background: TONE_BG[item.tone] }}
            >
              <SuggestionIcon tone={item.tone} />
            </span>
            <span className="advisor-suggestion-card__text">{item.text}</span>
          </button>
        ))}
      </div>
    </section>
  )
}
