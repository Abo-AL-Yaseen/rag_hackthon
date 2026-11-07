export type ChatRole = 'user' | 'assistant'

export type ChatMessage = {
  id: string
  role: ChatRole
  content: string
  createdAt: number
}

export type Conversation = {
  id: string
  title: string
  messages: ChatMessage[]
  updatedAt: number
  isDemoSample?: boolean
}

export type ChatState = {
  conversations: Conversation[]
  activeId: string | null
}

const STORAGE_KEY = 'najah-advisor-chats-v1'

const DEMO_REPLY =
  'نظام الاسترجاع (RAG) غير متصل حالياً. هذه واجهة تجريبية فقط، ولن تظهر إجابات أكاديمية أو مصادر حتى يتم ربط الخلفية.'

export const DEFAULT_SUGGESTIONS = [
  {
    id: 's1',
    text: 'ما هي متطلبات تخصص التسويق؟',
    tone: 'mint' as const,
  },
  {
    id: 's2',
    text: 'ما المتطلب السابق لمساق BUS230؟',
    tone: 'blue' as const,
  },
  {
    id: 's3',
    text: 'كيف أعرف خطتي الدراسية؟',
    tone: 'purple' as const,
  },
]

export const TOPIC_PROMPTS: Record<
  string,
  { label: string; prompts: string[]; tone: 'purple' | 'blue' | 'green' | 'orange' | 'pink' }
> = {
  majors: {
    label: 'التخصصات والخطط',
    tone: 'purple',
    prompts: [
      'ما هي متطلبات تخصص التسويق؟',
      'كيف أعرف خطتي الدراسية؟',
      'ما الفرق بين تخصصي الحاسوب ونظم المعلومات؟',
    ],
  },
  courses: {
    label: 'المساقات',
    tone: 'blue',
    prompts: [
      'ما المتطلب السابق لمساق BUS230؟',
      'كم ساعة معتمدة لمساق مقدمة في البرمجة؟',
      'هل يمكنني تسجيل مساق اختياري من كلية أخرى؟',
    ],
  },
  admission: {
    label: 'التسجيل والقبول',
    tone: 'green',
    prompts: [
      'ما مواعيد التسجيل للفصل القادم؟',
      'كيف أقدّم طلب تحويل تخصص؟',
      'ما شروط القبول في الدراسات العليا؟',
    ],
  },
  rules: {
    label: 'الأنظمة الجامعية',
    tone: 'orange',
    prompts: [
      'ما نظام الاعتذار عن مقرر دراسي؟',
      'كم مرة يحق لي إعادة المساق؟',
      'ما إجراءات التأجيل الفصلي؟',
    ],
  },
  exams: {
    label: 'الامتحانات والعلامات',
    tone: 'pink',
    prompts: [
      'كيف أحسب معدلي التراكمي؟',
      'ما سياسة الاعتراض على العلامة؟',
      'متى تُعلن نتائج الامتحانات النهائية؟',
    ],
  },
}

function uid(prefix = 'id'): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}_${Date.now().toString(36)}`
}

function createEmptyConversation(title = 'محادثة جديدة'): Conversation {
  return {
    id: uid('conv'),
    title,
    messages: [],
    updatedAt: Date.now(),
  }
}

function seedDemoConversations(): Conversation[] {
  const now = Date.now()
  return [
    {
      id: 'demo_marketing',
      title: 'متطلبات تخصص التسويق',
      isDemoSample: true,
      updatedAt: now - 1000 * 60 * 60 * 24,
      messages: [
        {
          id: 'demo_m1',
          role: 'user',
          content: 'ما هي متطلبات تخصص التسويق؟',
          createdAt: now - 1000 * 60 * 60 * 24,
        },
        {
          id: 'demo_m2',
          role: 'assistant',
          content: DEMO_REPLY,
          createdAt: now - 1000 * 60 * 60 * 24 + 1000,
        },
      ],
    },
    {
      id: 'demo_cs',
      title: 'الخطة الدراسية لتخصص الحاسوب',
      isDemoSample: true,
      updatedAt: now - 1000 * 60 * 60 * 48,
      messages: [
        {
          id: 'demo_c1',
          role: 'user',
          content: 'كيف أعرف خطتي الدراسية لتخصص الحاسوب؟',
          createdAt: now - 1000 * 60 * 60 * 48,
        },
        {
          id: 'demo_c2',
          role: 'assistant',
          content: DEMO_REPLY,
          createdAt: now - 1000 * 60 * 60 * 48 + 1000,
        },
      ],
    },
    {
      id: 'demo_withdraw',
      title: 'الاعتذار عن مقرر دراسي',
      isDemoSample: true,
      updatedAt: now - 1000 * 60 * 60 * 72,
      messages: [
        {
          id: 'demo_w1',
          role: 'user',
          content: 'ما نظام الاعتذار عن مقرر دراسي؟',
          createdAt: now - 1000 * 60 * 60 * 72,
        },
        {
          id: 'demo_w2',
          role: 'assistant',
          content: DEMO_REPLY,
          createdAt: now - 1000 * 60 * 60 * 72 + 1000,
        },
      ],
    },
  ]
}

function defaultState(): ChatState {
  const demos = seedDemoConversations()
  const fresh = createEmptyConversation()
  return {
    conversations: [fresh, ...demos],
    activeId: fresh.id,
  }
}

function isMessage(value: unknown): value is ChatMessage {
  if (!value || typeof value !== 'object') return false
  const m = value as Record<string, unknown>
  return (
    typeof m.id === 'string' &&
    (m.role === 'user' || m.role === 'assistant') &&
    typeof m.content === 'string' &&
    typeof m.createdAt === 'number'
  )
}

function isConversation(value: unknown): value is Conversation {
  if (!value || typeof value !== 'object') return false
  const c = value as Record<string, unknown>
  return (
    typeof c.id === 'string' &&
    typeof c.title === 'string' &&
    typeof c.updatedAt === 'number' &&
    Array.isArray(c.messages) &&
    c.messages.every(isMessage)
  )
}

function safeParse(raw: string | null): ChatState | null {
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object') return null
    const data = parsed as Record<string, unknown>
    if (!Array.isArray(data.conversations) || !data.conversations.every(isConversation)) {
      return null
    }
    const conversations = data.conversations as Conversation[]
    const activeId =
      typeof data.activeId === 'string' && conversations.some((c) => c.id === data.activeId)
        ? data.activeId
        : conversations[0]?.id ?? null
    return { conversations, activeId }
  } catch {
    return null
  }
}

function loadState(): ChatState {
  if (typeof window === 'undefined') return defaultState()
  const parsed = safeParse(window.localStorage.getItem(STORAGE_KEY))
  if (!parsed || parsed.conversations.length === 0) return defaultState()

  const hasDemos = seedDemoConversations().every((demo) =>
    parsed.conversations.some((c) => c.id === demo.id),
  )
  if (!hasDemos) {
    const demos = seedDemoConversations().filter(
      (demo) => !parsed.conversations.some((c) => c.id === demo.id),
    )
    return {
      ...parsed,
      conversations: [...parsed.conversations, ...demos],
    }
  }
  return parsed
}

function persist(state: ChatState) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // ignore quota / private mode
  }
}

type Listener = () => void

let state: ChatState = typeof window === 'undefined' ? defaultState() : loadState()
const listeners = new Set<Listener>()

function emit() {
  persist(state)
  listeners.forEach((l) => l())
}

export function initChatStore() {
  state = loadState()
  emit()
}

export function subscribeChatStore(listener: Listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function getChatState(): ChatState {
  return state
}

export function getActiveConversation(): Conversation | null {
  return state.conversations.find((c) => c.id === state.activeId) ?? null
}

export function getDemoReply(): string {
  return DEMO_REPLY
}

function titleFromQuestion(question: string): string {
  const trimmed = question.trim().replace(/\s+/g, ' ')
  if (trimmed.length <= 42) return trimmed
  return `${trimmed.slice(0, 40)}…`
}

export function createNewChat() {
  const conversation = createEmptyConversation()
  state = {
    conversations: [conversation, ...state.conversations],
    activeId: conversation.id,
  }
  emit()
  return conversation
}

export function selectConversation(id: string) {
  if (!state.conversations.some((c) => c.id === id)) return
  state = { ...state, activeId: id }
  emit()
}

export function renameConversation(id: string, title: string) {
  const next = title.trim()
  if (!next) return
  state = {
    ...state,
    conversations: state.conversations.map((c) =>
      c.id === id ? { ...c, title: next, updatedAt: Date.now(), isDemoSample: false } : c,
    ),
  }
  emit()
}

export function deleteConversation(id: string) {
  const remaining = state.conversations.filter((c) => c.id !== id)
  if (remaining.length === 0) {
    const fresh = createEmptyConversation()
    state = { conversations: [fresh], activeId: fresh.id }
  } else {
    const activeId = state.activeId === id ? remaining[0].id : state.activeId
    state = { conversations: remaining, activeId }
  }
  emit()
}

export function sendUserMessage(content: string) {
  const text = content.trim()
  if (!text) return null

  let conversations = [...state.conversations]
  let activeId = state.activeId
  let active = conversations.find((c) => c.id === activeId)

  if (!active) {
    active = createEmptyConversation()
    conversations = [active, ...conversations]
    activeId = active.id
  }

  const userMsg: ChatMessage = {
    id: uid('msg'),
    role: 'user',
    content: text,
    createdAt: Date.now(),
  }

  const assistantMsg: ChatMessage = {
    id: uid('msg'),
    role: 'assistant',
    content: DEMO_REPLY,
    createdAt: Date.now() + 1,
  }

  const shouldRename = active.messages.length === 0 || active.title === 'محادثة جديدة'
  const updated: Conversation = {
    ...active,
    title: shouldRename ? titleFromQuestion(text) : active.title,
    messages: [...active.messages, userMsg, assistantMsg],
    updatedAt: Date.now(),
    isDemoSample: false,
  }

  state = {
    activeId,
    conversations: conversations.map((c) => (c.id === updated.id ? updated : c)),
  }
  emit()
  return updated
}
