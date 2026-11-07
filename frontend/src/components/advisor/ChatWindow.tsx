import { useEffect, useRef } from 'react'
import type { ChatMessage as ChatMessageType } from '../../lib/chatStore'
import { ChatMessage } from './ChatMessage'
import { MessageComposer } from './MessageComposer'
import { WelcomeScreen } from './WelcomeScreen'
import type { SuggestionItem } from './SuggestedQuestions'

type Props = {
  messages: ChatMessageType[]
  suggestions: SuggestionItem[]
  draft: string
  onDraftChange: (value: string) => void
  onSend: (value: string) => void
  onSelectSuggestion: (text: string) => void
  disabled?: boolean
}

function WaveDecoration() {
  return (
    <svg
      className="advisor-chat__wave"
      viewBox="0 0 1200 180"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M0 110 C 180 40, 320 160, 500 100 C 680 40, 820 150, 1000 90 C 1100 60, 1160 80, 1200 70 L1200 180 L0 180 Z"
        fill="rgba(167, 139, 250, 0.16)"
      />
      <path
        d="M0 130 C 220 70, 360 170, 540 120 C 740 60, 880 160, 1060 110 C 1130 90, 1170 100, 1200 95 L1200 180 L0 180 Z"
        fill="rgba(111, 76, 227, 0.1)"
      />
    </svg>
  )
}

export function ChatWindow({
  messages,
  suggestions,
  draft,
  onDraftChange,
  onSend,
  onSelectSuggestion,
  disabled = false,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const showWelcome = messages.length === 0

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages])

  return (
    <section className="advisor-chat" aria-label="مساحة المحادثة">
      <WaveDecoration />
      <div className="advisor-chat__scroll" ref={scrollRef}>
        {showWelcome ? (
          <WelcomeScreen suggestions={suggestions} onSelectSuggestion={onSelectSuggestion} />
        ) : (
          <div className="advisor-messages" role="log" aria-live="polite" aria-relevant="additions">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
          </div>
        )}
      </div>
      <div className="advisor-chat__composer-wrap">
        <MessageComposer value={draft} onChange={onDraftChange} onSend={onSend}
          disabled={disabled || messages.some((m) => m.phase === 'pending')} />
      </div>
    </section>
  )
}
