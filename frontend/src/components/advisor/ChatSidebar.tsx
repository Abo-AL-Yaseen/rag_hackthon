import {
  BarChart3,
  BookOpen,
  ChevronLeft,
  Clock3,
  FileText,
  GraduationCap,
  Layers,
  MoreVertical,
  Plus,
  Shield,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { TOPIC_PROMPTS, type Conversation } from '../../lib/chatStore'

type Props = {
  open: boolean
  conversations: Conversation[]
  activeId: string | null
  activeTopic: string | null
  showAllChats: boolean
  onClose: () => void
  onNewChat: () => void
  onSelectChat: (id: string) => void
  onRenameChat: (id: string, title: string) => void
  onDeleteChat: (id: string) => void
  onSelectTopic: (topicId: string) => void
  onToggleShowMore: () => void
}

const TOPIC_META = [
  { id: 'majors', icon: GraduationCap, bg: 'rgba(111, 76, 227, 0.14)', fg: '#6f4ce3' },
  { id: 'courses', icon: BookOpen, bg: 'rgba(69, 109, 255, 0.14)', fg: '#456dff' },
  { id: 'admission', icon: FileText, bg: 'rgba(52, 190, 130, 0.14)', fg: '#2f9d6a' },
  { id: 'rules', icon: Shield, bg: 'rgba(245, 158, 90, 0.18)', fg: '#d9772f' },
  { id: 'exams', icon: BarChart3, bg: 'rgba(236, 120, 170, 0.16)', fg: '#d4538c' },
] as const

export function ChatSidebar({
  open,
  conversations,
  activeId,
  activeTopic,
  showAllChats,
  onClose,
  onNewChat,
  onSelectChat,
  onRenameChat,
  onDeleteChat,
  onSelectTopic,
  onToggleShowMore,
}: Props) {
  const [menuId, setMenuId] = useState<string | null>(null)
  const listRef = useRef<HTMLUListElement>(null)

  const visible = showAllChats ? conversations : conversations.slice(0, 3)

  useEffect(() => {
    function handlePointer(event: MouseEvent) {
      if (!listRef.current) return
      if (!listRef.current.contains(event.target as Node)) {
        setMenuId(null)
      }
    }
    document.addEventListener('mousedown', handlePointer)
    return () => document.removeEventListener('mousedown', handlePointer)
  }, [])

  function handleRename(id: string, current: string) {
    setMenuId(null)
    const next = window.prompt('إعادة تسمية المحادثة', current)
    if (next == null) return
    onRenameChat(id, next)
  }

  function handleDelete(id: string) {
    setMenuId(null)
    if (window.confirm('هل تريد حذف هذه المحادثة؟')) {
      onDeleteChat(id)
    }
  }

  return (
    <aside
      className={`advisor-sidebar${open ? ' is-open' : ''}`}
      aria-label="الشريط الجانبي للمحادثات"
    >
      <button
        type="button"
        className="advisor-new-chat"
        onClick={() => {
          onNewChat()
          onClose()
        }}
      >
        <Plus className="h-5 w-5" strokeWidth={2.2} aria-hidden="true" />
        محادثة جديدة
      </button>

      <div className="advisor-sidebar__scroll">
        <section>
          <h2 className="advisor-section-label">
            <Clock3 className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
            محادثاتي السابقة
          </h2>
          <ul className="advisor-chat-list" ref={listRef}>
            {visible.map((chat) => (
              <li
                key={chat.id}
                className={`advisor-chat-item${activeId === chat.id ? ' is-active' : ''}`}
              >
                <button
                  type="button"
                  className="advisor-chat-item__btn"
                  onClick={() => {
                    onSelectChat(chat.id)
                    onClose()
                  }}
                  title={chat.title}
                >
                  {chat.title}
                  {chat.isDemoSample ? (
                    <span className="advisor-demo-badge">مثال</span>
                  ) : null}
                </button>
                <button
                  type="button"
                  className="advisor-chat-item__menu-btn"
                  aria-label="خيارات المحادثة"
                  aria-expanded={menuId === chat.id}
                  onClick={(event) => {
                    event.stopPropagation()
                    setMenuId((prev) => (prev === chat.id ? null : chat.id))
                  }}
                >
                  <MoreVertical className="h-4 w-4" aria-hidden="true" />
                </button>
                {menuId === chat.id ? (
                  <div className="advisor-chat-item__dropdown" role="menu">
                    <button type="button" role="menuitem" onClick={() => handleRename(chat.id, chat.title)}>
                      إعادة تسمية
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      className="is-danger"
                      onClick={() => handleDelete(chat.id)}
                    >
                      حذف
                    </button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
          {conversations.length > 3 ? (
            <button type="button" className="advisor-more-link" onClick={onToggleShowMore}>
              {showAllChats ? 'عرض أقل' : 'عرض المزيد'}
              <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          ) : null}
        </section>

        <section>
          <h2 className="advisor-section-label">
            <Layers className="h-4 w-4" strokeWidth={2} aria-hidden="true" />
            تصفح حسب الموضوع
          </h2>
          <ul className="advisor-topic-list">
            {TOPIC_META.map((topic) => {
              const meta = TOPIC_PROMPTS[topic.id]
              const Icon = topic.icon
              return (
                <li key={topic.id}>
                  <button
                    type="button"
                    className={`advisor-topic-item${activeTopic === topic.id ? ' is-active' : ''}`}
                    onClick={() => {
                      onSelectTopic(topic.id)
                      onClose()
                    }}
                  >
                    <span
                      className="advisor-topic-item__icon"
                      style={{ background: topic.bg, color: topic.fg }}
                    >
                      <Icon className="h-4 w-4" strokeWidth={1.9} aria-hidden="true" />
                    </span>
                    <span className="advisor-topic-item__label">{meta.label}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </section>
      </div>
    </aside>
  )
}
