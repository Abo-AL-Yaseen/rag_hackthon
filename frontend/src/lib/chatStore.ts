import { askAdvisor } from '../api/chatApi.ts'
import type { Language, RAGResponse } from '../types/rag'

export type ChatRole = 'user' | 'assistant'
export type Scope = { program_id: string | null; plan_version: string | null }
export type ChatMessage = {
  id: string; role: ChatRole; content: string; createdAt: number
  phase?: 'pending' | 'complete' | 'error'
  response?: RAGResponse
}
export type Conversation = {
  id: string; title: string; messages: ChatMessage[]; updatedAt: number
  scope: Scope; language: Language; isDemoSample?: boolean
}
export type ChatState = { conversations: Conversation[]; activeId: string | null }

// Versioned storage preserves old demo data without importing it as real answers.
const STORAGE_KEY = 'najah-engineering-chats-v2'
const GENERAL: Scope = { program_id: null, plan_version: null }

export const DEFAULT_SUGGESTIONS = [
  { id: 's1', text: 'ما عدد الساعات المعتمدة للمساق 10871112؟', tone: 'mint' as const },
  { id: 's2', text: 'كم مجموع ساعات التخرج حسب هذه الخطة تحديداً؟', tone: 'blue' as const },
  { id: 's3', text: 'لحد إمتى بقدر أسحب مادة؟ وهل بحتفظ بالحق المالي؟', tone: 'purple' as const },
]
export const TOPIC_PROMPTS: Record<string, { label: string; prompts: string[]; tone: 'purple' | 'blue' | 'green' | 'orange' | 'pink' }> = {
  majors: { label: 'خطط الهندسة', tone: 'purple', prompts: ['كم مجموع ساعات التخرج حسب هذه الخطة تحديداً؟', 'أي نسخة خطة بتنطبق علي؟'] },
  courses: { label: 'المساقات', tone: 'blue', prompts: ['ما عدد الساعات المعتمدة للمساق 10871112؟', 'شو المتطلبات السابقة لمساق 10641373؟'] },
  admission: { label: 'التسجيل', tone: 'green', prompts: ['متى بقدر أضيف أو أسحب مساق بأول الفصل العادي والصيفي؟'] },
  rules: { label: 'الأنظمة الجامعية', tone: 'orange', prompts: ['لحد إمتى بقدر أسحب مادة؟ وهل بحتفظ بالحق المالي؟'] },
  exams: { label: 'المواظبة والإنذار', tone: 'pink', prompts: ['إذا غبت أكثر من 12.5% بدون عذر مقبول، بقدر أقدم النهائي؟'] },
}

function uid(prefix = 'id') { return `${prefix}_${Math.random().toString(36).slice(2)}_${Date.now().toString(36)}` }
function empty(scope: Scope = GENERAL, language: Language = 'ar'): Conversation {
  return { id: uid('conv'), title: 'محادثة جديدة', messages: [], updatedAt: Date.now(), scope: { ...scope }, language }
}
function initial(): ChatState { const chat = empty(); return { conversations: [chat], activeId: chat.id } }
function load(): ChatState {
  try {
    if (typeof window === 'undefined') return initial()
    const raw: unknown = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? 'null')
    if (!raw || typeof raw !== 'object' || !('conversations' in raw) || !Array.isArray(raw.conversations)) return initial()
    const conversations = raw.conversations.filter((c): c is Conversation =>
      c && typeof c.id === 'string' && typeof c.title === 'string' && Array.isArray(c.messages) &&
      c.messages.every((m: ChatMessage) => typeof m.id === 'string' && typeof m.content === 'string' && ['user', 'assistant'].includes(m.role)) &&
      c.scope && (c.scope.program_id === null || typeof c.scope.program_id === 'string') &&
      (c.scope.plan_version === null || typeof c.scope.plan_version === 'string') && ['ar', 'en'].includes(c.language),
    ).map((c) => ({ ...c, messages: c.messages.map((m) => m.phase === 'pending' ?
      { ...m, phase: 'error' as const, content: 'انقطع الطلب عند إغلاق الصفحة. أعد إرسال السؤال عند الحاجة.' } : m) }))
    if (!conversations.length) return initial()
    const selected = 'activeId' in raw && conversations.some((c) => c.id === raw.activeId) ? String(raw.activeId) : conversations[0].id
    return { conversations, activeId: selected }
  } catch { return initial() }
}
let state: ChatState = load()
const listeners = new Set<() => void>()
function emit() {
  try { if (typeof window !== 'undefined') window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state)) } catch { /* unavailable storage */ }
  listeners.forEach((listener) => listener())
}
function update(id: string, fn: (chat: Conversation) => Conversation) {
  state = { ...state, conversations: state.conversations.map((c) => c.id === id ? fn(c) : c) }; emit()
}
export function initChatStore() { state = load(); emit() }
export function subscribeChatStore(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener) } }
export function getChatState(): ChatState { return state }
export function getActiveConversation(): Conversation | null { return state.conversations.find((c) => c.id === state.activeId) ?? null }
export function createNewChat(scope?: Scope, language?: Language) {
  const current = getActiveConversation()
  const chat = empty(scope ?? current?.scope ?? GENERAL, language ?? current?.language ?? 'ar')
  state = { conversations: [chat, ...state.conversations], activeId: chat.id }; emit(); return chat
}
export function setChatContext(scope: Scope, language: Language) {
  const chat = getActiveConversation()
  if (!chat || chat.messages.length) return createNewChat(scope, language)
  update(chat.id, (c) => ({ ...c, scope: { ...scope }, language })); return getActiveConversation()
}
export function selectConversation(id: string) { if (state.conversations.some((c) => c.id === id)) { state = { ...state, activeId: id }; emit() } }
export function renameConversation(id: string, title: string) { if (title.trim()) update(id, (c) => ({ ...c, title: title.trim(), updatedAt: Date.now() })) }
export function deleteConversation(id: string) {
  const conversations = state.conversations.filter((c) => c.id !== id)
  if (!conversations.length) { state = initial() } else {
    state = { conversations, activeId: state.activeId === id ? conversations[0].id : state.activeId }
  }
  emit()
}

export async function sendUserMessage(content: string) {
  const text = content.trim()
  if (!text || text.length > 2000) return null
  const chat = getActiveConversation() ?? createNewChat()
  if (chat.messages.some((m) => m.phase === 'pending')) return null
  const id = chat.id; const messageId = uid('answer')
  const context = { ...chat.scope }; const language = chat.language
  update(id, (c) => ({ ...c, title: c.messages.length ? c.title : text.slice(0, 42), updatedAt: Date.now(),
    messages: [...c.messages, { id: uid('question'), role: 'user', content: text, createdAt: Date.now() },
      { id: messageId, role: 'assistant', content: '', createdAt: Date.now(), phase: 'pending' }] }))
  try {
    const response = await askAdvisor({ question: text, language, ...context })
    update(id, (c) => ({ ...c, updatedAt: Date.now(), messages: c.messages.map((m) => m.id === messageId ?
      { ...m, phase: 'complete', content: response.answer, response } : m) }))
  } catch (error) {
    update(id, (c) => ({ ...c, messages: c.messages.map((m) => m.id === messageId ?
      { ...m, phase: 'error', content: error instanceof Error ? error.message : 'تعذر الاتصال بالخلفية.' } : m) }))
  }
  // Update only the captured conversation/message, even after switch/delete.
  return state.conversations.find((c) => c.id === id) ?? null
}
