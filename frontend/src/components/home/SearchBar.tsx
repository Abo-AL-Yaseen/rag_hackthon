import { SendHorizontal, Sparkles } from 'lucide-react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { SuggestionChips } from './SuggestionChips'

type Props = {
  value: string
  onChange: (value: string) => void
}

export function SearchBar({ value, onChange }: Props) {
  const navigate = useNavigate()

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const question = value.trim()
    if (!question) return
    navigate('/advisor', { state: { question } })
  }

  return (
    <div className="w-full">
      <form
        onSubmit={handleSubmit}
        className="relative flex h-[64px] items-center gap-2 rounded-[17px] border border-white/80 bg-white px-2 shadow-[0_16px_40px_rgba(9,15,37,0.28)] transition focus-within:border-[rgba(117,71,237,0.45)] focus-within:shadow-[0_16px_44px_rgba(117,71,237,0.22)]"
        role="search"
        aria-label="البحث الأكاديمي الذكي"
      >
        <span
          className="ms-1.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[rgba(117,71,237,0.1)] text-[var(--purple)]"
          aria-hidden="true"
        >
          <Sparkles className="h-4 w-4" />
        </span>
        <label htmlFor="hero-search" className="sr-only">
          اسأل عن تخصص أو مساق أو خطة دراسية
        </label>
        <input
          id="hero-search"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="اسأل عن تخصص، مساق، خطة دراسية أو أي خدمة جامعية..."
          className="min-w-0 flex-1 bg-transparent px-1 text-[15px] font-normal text-[var(--text)] outline-none placeholder:text-[#8b93ad]"
          maxLength={2000}
          autoComplete="off"
        />
        <button
          type="submit"
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-[var(--purple)] text-white transition hover:bg-[#6436d9] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--purple-light)]"
          aria-label="إرسال السؤال"
        >
          <SendHorizontal className="h-4 w-4 -scale-x-100" aria-hidden="true" />
        </button>
      </form>

      <SuggestionChips onSelect={onChange} />
    </div>
  )
}
