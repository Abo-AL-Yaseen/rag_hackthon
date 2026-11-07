import { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { AdvisorHeader } from '../components/advisor/AdvisorHeader'
import { ChatSidebar } from '../components/advisor/ChatSidebar'
import { ChatWindow } from '../components/advisor/ChatWindow'
import type { SuggestionItem } from '../components/advisor/SuggestedQuestions'
import { useChatStore } from '../hooks/useChatStore'
import {
  createNewChat,
  DEFAULT_SUGGESTIONS,
  deleteConversation,
  initChatStore,
  renameConversation,
  selectConversation,
  sendUserMessage,
  TOPIC_PROMPTS,
} from '../lib/chatStore'
import '../styles/advisor.css'

type AdvisorLocationState = {
  question?: string
}

let storeReady = false

export function AdvisorPage() {
  const location = useLocation()
  const { conversations, activeId, active } = useChatStore()
  const [draft, setDraft] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showAllChats, setShowAllChats] = useState(false)
  const [activeTopic, setActiveTopic] = useState<string | null>(null)
  const [bootstrappedQuestion, setBootstrappedQuestion] = useState<string | null>(null)

  useEffect(() => {
    if (!storeReady) {
      initChatStore()
      storeReady = true
    }
  }, [])

  useEffect(() => {
    const state = (location.state ?? {}) as AdvisorLocationState
    const question = typeof state.question === 'string' ? state.question.trim() : ''
    if (!question || bootstrappedQuestion === question) return

    setBootstrappedQuestion(question)
    setDraft(question)
    createNewChat()
    sendUserMessage(question)
    setDraft('')
    window.history.replaceState({}, document.title)
  }, [location.state, bootstrappedQuestion])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setSidebarOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const suggestions: SuggestionItem[] = useMemo(() => {
    if (!activeTopic || !TOPIC_PROMPTS[activeTopic]) {
      return DEFAULT_SUGGESTIONS
    }
    const topic = TOPIC_PROMPTS[activeTopic]
    return topic.prompts.slice(0, 3).map((text, index) => ({
      id: `${activeTopic}_${index}`,
      text,
      tone: index === 0 ? topic.tone : index === 1 ? 'blue' : 'mint',
    }))
  }, [activeTopic])

  function handleSend(value: string) {
    sendUserMessage(value)
    setDraft('')
  }

  function handleSelectSuggestion(text: string) {
    setDraft(text)
  }

  function handleNewChat() {
    createNewChat()
    setDraft('')
    setActiveTopic(null)
  }

  function handleSelectTopic(topicId: string) {
    setActiveTopic(topicId)
    createNewChat()
    setDraft('')
  }

  return (
    <div className="advisor-app">
      <AdvisorHeader onToggleSidebar={() => setSidebarOpen((open) => !open)} />

      <div
        className={`advisor-overlay${sidebarOpen ? ' is-open' : ''}`}
        onClick={() => setSidebarOpen(false)}
        aria-hidden={!sidebarOpen}
      />

      <div className="advisor-body">
        <ChatWindow
          messages={active?.messages ?? []}
          suggestions={suggestions}
          draft={draft}
          onDraftChange={setDraft}
          onSend={handleSend}
          onSelectSuggestion={handleSelectSuggestion}
        />

        <ChatSidebar
          open={sidebarOpen}
          conversations={conversations}
          activeId={activeId}
          activeTopic={activeTopic}
          showAllChats={showAllChats}
          onClose={() => setSidebarOpen(false)}
          onNewChat={handleNewChat}
          onSelectChat={selectConversation}
          onRenameChat={renameConversation}
          onDeleteChat={deleteConversation}
          onSelectTopic={handleSelectTopic}
          onToggleShowMore={() => setShowAllChats((v) => !v)}
        />
      </div>
    </div>
  )
}
