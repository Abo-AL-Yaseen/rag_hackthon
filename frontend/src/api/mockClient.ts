import type { Language, MockScenario, RAGRequest, RAGResponse } from '../types/rag'

import answeredAr from '../mocks/answered_ar.json'
import answeredEn from '../mocks/answered_en.json'
import insufficientEvidence from '../mocks/insufficient_evidence.json'
import errorResponse from '../mocks/error.json'

const FIXTURES: Record<MockScenario, RAGResponse> = {
  answered_ar: answeredAr as RAGResponse,
  answered_en: answeredEn as RAGResponse,
  insufficient_evidence: insufficientEvidence as RAGResponse,
  error: errorResponse as RAGResponse,
}

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * Safe offline client until Backend `/rag/answer` is available.
 * Does not call remote APIs or load credentials.
 */
export async function askMock(
  request: RAGRequest,
  scenario?: MockScenario,
): Promise<RAGResponse> {
  await delay(250)

  if (scenario) {
    return structuredClone(FIXTURES[scenario])
  }

  const trimmed = request.question.trim()
  if (!trimmed) {
    return structuredClone(FIXTURES.error)
  }

  if (/refuse|رفض|خارج النطاق/i.test(trimmed)) {
    return structuredClone(FIXTURES.insufficient_evidence)
  }

  if (/error|خطأ/i.test(trimmed)) {
    return structuredClone(FIXTURES.error)
  }

  const language: Language = request.language === 'ar' ? 'ar' : 'en'
  return structuredClone(
    language === 'ar' ? FIXTURES.answered_ar : FIXTURES.answered_en,
  )
}

export function listMockScenarios(): MockScenario[] {
  return Object.keys(FIXTURES) as MockScenario[]
}
