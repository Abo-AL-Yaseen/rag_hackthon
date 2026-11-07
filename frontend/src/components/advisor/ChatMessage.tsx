import type { ChatMessage as ChatMessageType } from '../../lib/chatStore'

type Props = {
  message: ChatMessageType
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === 'user'
  return (
    <div
      className={`advisor-message ${isUser ? 'advisor-message--user' : 'advisor-message--assistant'}`}
    >
      <div className="advisor-message__bubble">{message.content}</div>
    </div>
  )
}
