import { useEffect, useMemo, useRef, useState } from 'react'
import { getPrograms } from '../api/chatApi'
import type { ProgramSummary, Language } from '../types/rag'
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
  setChatContext,
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
  const submittedQuestion = useRef<string | null>(null)
  const [programs, setPrograms] = useState<ProgramSummary[]>([])
  const [catalogStatus, setCatalogStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [reload, setReload] = useState(0)
  const scope = active?.scope ?? { program_id: null, plan_version: null }
  const selectedProgram = programs.find((p) => p.program_id === scope.program_id)

  useEffect(() => {
    let alive = true
    setCatalogStatus('loading')
    getPrograms().then((items) => {
      if (!alive) return
      if (!Array.isArray(items) || !items.length) { setCatalogStatus('error'); return }
      setPrograms(items); setCatalogStatus('ready')
    }).catch(() => { if (alive) setCatalogStatus('error') })
    return () => { alive = false }
  }, [reload])

  useEffect(() => {
    if (!storeReady) {
      initChatStore()
      storeReady = true
    }
  }, [])

  useEffect(() => {
    const state = (location.state ?? {}) as AdvisorLocationState
    const question = typeof state.question === 'string' ? state.question.trim() : ''
    if (!question || submittedQuestion.current === question) return

    submittedQuestion.current = question
    setDraft(question)
    createNewChat()
    window.history.replaceState({}, document.title)
  }, [location.state])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setSidebarOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const suggestions: SuggestionItem[] = useMemo(() => {
    if (!activeTopic || !TOPIC_PROMPTS[activeTopic]) {
      return DEFAULT_SUGGESTIONS.map((item, index) => index === 0 && scope.program_id === 'geomatics-engineering' ?
        { ...item, text: 'كم ساعة مساق 10871112؟' } : item)
    }
    const topic = TOPIC_PROMPTS[activeTopic]
    return topic.prompts.slice(0, 3).map((text, index) => ({
      id: `${activeTopic}_${index}`,
      text,
      tone: index === 0 ? topic.tone : index === 1 ? 'blue' : 'mint',
    }))
  }, [activeTopic, scope.program_id])

  function handleSend(value: string) {
    void sendUserMessage(value)
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

      <section className="advisor-context" aria-label="اختيار التخصص والخطة">
        <a href="/admin/documents">إدارة المستندات / Document Management</a>
        <div className="advisor-context__fields">
          <label>التخصص الهندسي
            <select aria-label="التخصص الهندسي" value={scope.program_id ?? ''} disabled={catalogStatus !== 'ready'}
              onChange={(event) => {
                const program = programs.find((p) => p.program_id === event.target.value)
                setChatContext({ program_id: program?.program_id ?? null, plan_version: program?.plan_versions[0] ?? null }, active?.language ?? 'ar')
              }}>
              <option value="">الأنظمة العامة — دون تخصص</option>
              {programs.map((p) => <option key={p.program_id} value={p.program_id}>{p.name_ar ?? p.name}</option>)}
            </select>
          </label>
          <label>نسخة الخطة
            <select aria-label="نسخة الخطة" value={scope.plan_version ?? ''} disabled={!selectedProgram}
              onChange={(event) => setChatContext({ ...scope, plan_version: event.target.value || null }, active?.language ?? 'ar')}>
              <option value="">غير محددة</option>
              {selectedProgram?.plan_versions.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </label>
          <label>لغة الإجابة
            <select aria-label="لغة الإجابة" value={active?.language ?? 'ar'} onChange={(event) => setChatContext(scope, event.target.value as Language)}>
              <option value="ar">العربية</option><option value="en">English</option>
            </select>
          </label>
        </div>
        <p>تغطية كلية الهندسة فقط. اختر نسخة خطتك المعتمدة؛ لا تُستنتج من سنة القبول. تغيير السياق يبدأ محادثة جديدة ويحفظ السابقة.</p>
        <p className="advisor-mode-note">وضع محاكاة محلية معلن — الاسترجاع من الفهرس الحقيقي، دون استدعاء Groq أو LLM حي.</p>
        <p>إجابات محلية باقتباسات من الأدلة، دون قائمة إجابات محفوظة. الإنجليزية تتطلب أدلة إنجليزية موثقة؛ لا تُترجم اللوائح تلقائيًا.</p>
        {catalogStatus === 'loading' && <p role="status">جارٍ الاتصال بالخلفية وتحميل التخصصات…</p>}
        {catalogStatus === 'error' && <p role="alert">الخلفية غير متاحة أو الفهرس غير جاهز. <button onClick={() => setReload((v) => v + 1)}>إعادة الاتصال</button></p>}
        {catalogStatus === 'ready' && <span className="advisor-catalog-ready">{programs.length} تخصصاً هندسياً من بيانات الفهرس الموثقة</span>}
      </section>

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
          disabled={catalogStatus !== 'ready' || (!!scope.program_id && !selectedProgram)}
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
