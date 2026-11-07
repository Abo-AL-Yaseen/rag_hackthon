import type { ProgramSummary, RAGRequest, RAGResponse, SourceLocator } from '../types/rag'

const BASE = (import.meta.env?.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  constructor(status: number) {
    super(status === 503 ? 'المرشد غير جاهز حالياً. تحقق من تشغيل الخلفية والفهرس.' :
      status === 422 ? 'تحقق من السؤال والتخصص ونسخة الخطة المختارة.' : 'تعذر الاتصال بالخلفية. حاول لاحقاً.')
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 30000)
  try {
    const response = await fetch(BASE + path, { ...init, signal: controller.signal })
    if (!response.ok) throw new ApiError(response.status)
    return await response.json() as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(0)
  } finally { clearTimeout(timeout) }
}

export async function askAdvisor(body: RAGRequest): Promise<RAGResponse> {
  const result = await request<RAGResponse>('/api/chat', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
  if (result.contract_version !== '1.0.0' || typeof result.answer !== 'string' ||
      !['answered', 'insufficient_evidence', 'error'].includes(result.status) ||
      !['mock', 'remote'].includes(result.mode) || !Array.isArray(result.sources) || !Array.isArray(result.claims)) {
    throw new ApiError(502)
  }
  return result
}

export function getPrograms(): Promise<ProgramSummary[]> { return request('/api/programs') }
export function getSourceLocator(id: string): Promise<SourceLocator> {
  return request('/api/sources/' + encodeURIComponent(id))
}
