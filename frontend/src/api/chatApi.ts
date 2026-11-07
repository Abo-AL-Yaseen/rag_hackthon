import type { Language, ProgramSummary, RAGRequest, RAGResponse, SourceLocator } from '../types/rag'

const BASE = (import.meta.env?.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  constructor(status: number, language: Language = 'ar') {
    super(language === 'en' ? status === 503 ? 'The advisor is not ready. Check the Backend and index.' :
      status === 422 ? 'Please check the question, program and selected plan.' : 'Unable to connect to the Backend. Please try later.' :
      status === 503 ? 'المرشد غير جاهز حالياً. تحقق من تشغيل الخلفية والفهرس.' :
      status === 422 ? 'تحقق من السؤال والتخصص ونسخة الخطة المختارة.' : 'تعذر الاتصال بالخلفية. حاول لاحقاً.')
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit, language: Language = 'ar'): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 30000)
  try {
    const response = await fetch(BASE + path, { ...init, signal: controller.signal })
    if (!response.ok) throw new ApiError(response.status, language)
    return await response.json() as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(0, language)
  } finally { clearTimeout(timeout) }
}

export async function askAdvisor(body: RAGRequest): Promise<RAGResponse> {
  const result = await request<RAGResponse>('/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  }, body.language)
  if (result.contract_version !== '1.0.0' || result.language !== body.language || typeof result.answer !== 'string' ||
      !['answered', 'insufficient_evidence', 'error'].includes(result.status) ||
      !['mock', 'remote'].includes(result.mode) || !Array.isArray(result.sources) || !Array.isArray(result.claims)) {
    throw new ApiError(502, body.language)
  }
  return result
}

export function getPrograms(): Promise<ProgramSummary[]> { return request('/api/programs') }
export function getSourceLocator(id: string): Promise<SourceLocator> {
  return request('/api/sources/' + encodeURIComponent(id))
}

export type CoursePage = { total: number; offset: number; limit: number; next_offset: number | null; complete_indexed_coverage: boolean;
  courses: { course_code: string; name: string; credit_hours: number; classification: string | null; source_url: string; table_index: number; row_index: number }[] }
export function getCoursePage(program: string, plan: string, language: Language, offset = 0): Promise<CoursePage> {
  return request(`/api/programs/${encodeURIComponent(program)}/plans/${encodeURIComponent(plan)}/courses?language=${language}&offset=${offset}&limit=20`, undefined, language)
}
