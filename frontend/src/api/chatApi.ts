/**
 * Stub for future RAG backend integration.
 * No network calls — keep UI demo-only until a real endpoint is wired.
 */

export type AskRequest = {
  question: string
  conversationId?: string
  language?: 'ar' | 'en'
}

export type AskCitation = {
  title: string
  snippet: string
  sourceId?: string
}

export type AskResponse = {
  answer: string
  citations: AskCitation[]
  status: 'not_connected' | 'ok' | 'insufficient_evidence' | 'error'
}

export async function askAdvisor(_request: AskRequest): Promise<AskResponse> {
  return {
    answer:
      'نظام الاسترجاع (RAG) غير متصل حالياً. هذه واجهة تجريبية فقط، ولن تظهر إجابات أكاديمية أو مصادر حتى يتم ربط الخلفية.',
    citations: [],
    status: 'not_connected',
  }
}
