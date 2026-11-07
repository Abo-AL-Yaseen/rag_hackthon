import { Paperclip, SendHorizontal } from 'lucide-react'
import {
  useEffect,
  useRef,
  type ChangeEvent,
  type FormEvent,
  type KeyboardEvent,
} from 'react'

type Props = {
  value: string
  onChange: (value: string) => void
  onSend: (value: string) => void
  disabled?: boolean
}

export function MessageComposer({ value, onChange, onSend, disabled = false }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const canSend = value.trim().length > 0 && !disabled

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }, [value])

  function submit() {
    if (!canSend) return
    onSend(value)
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    submit()
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  function handleChange(event: ChangeEvent<HTMLTextAreaElement>) {
    onChange(event.target.value)
  }

  return (
    <form className="advisor-composer" onSubmit={handleSubmit} aria-label="كتابة سؤال">
      <button
        type="button"
        className="advisor-composer__attach"
        aria-label="إرفاق ملف (قريباً)"
        title="إرفاق ملف — قريباً"
      >
        <Paperclip className="h-5 w-5" strokeWidth={1.8} aria-hidden="true" />
      </button>

      <textarea
        ref={textareaRef}
        className="advisor-composer__input"
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder="اكتب سؤالك هنا..."
        rows={1}
        maxLength={4000}
        aria-label="نص السؤال"
      />

      <button
        type="submit"
        className="advisor-composer__send"
        disabled={!canSend}
        aria-label="إرسال السؤال"
      >
        <SendHorizontal className="h-5 w-5 -scale-x-100" strokeWidth={2} aria-hidden="true" />
      </button>
    </form>
  )
}
