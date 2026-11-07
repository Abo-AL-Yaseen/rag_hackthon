/** RAG response contract v1.0.0 — mirrors docs/rag_response.schema.json */

export type Language = 'ar' | 'en'
export type AnswerStatus = 'answered' | 'insufficient_evidence' | 'error'
export type Mode = 'mock' | 'remote'

export interface Source {
  source_id: string
  chunk_id: string
  document_id: string
  document_name: string
  page_number: number
  supporting_excerpt: string
  version: string
}

export interface AnswerClaim {
  text: string
  source_ids: string[]
}

export interface Latency {
  retrieval_ms: number
  generation_ms: number
  validation_ms: number
  total_ms: number
}

export interface ValidationInfo {
  citation_references: 'verified' | 'not_applicable'
  support_check: 'exact_quote' | 'not_applicable'
  semantic_faithfulness: 'not_evaluated'
}

export interface RAGResponse {
  contract_version: '1.0.0'
  answer: string
  sources: Source[]
  claims: AnswerClaim[]
  status: AnswerStatus
  reason: string
  language: Language
  mode: Mode
  latency: Latency
  validation: ValidationInfo
}

/** Backend request shape from the integration contract. */
export interface RAGRequest {
  question: string
  language: Language
  program_id?: string | null
  plan_version?: string | null
}

export interface ProgramSummary {
  program_id: string
  name: string
  name_ar?: string | null
  name_en?: string | null
  plan_versions: string[]
  language?: string | null
}

export interface SourceLocator {
  document_id: string
  source_url: string | null
  source_type?: 'runtime_catalog' | 'course_catalog'
  language?: Language
  official_plan_sources?: { program_id: string; plan_version: string; source_url: string; document_title?: string }[]
  document_title: string
  physical_pdf_page: number | null
  engine_page_number: number
  table_index: number | null
  row_index: number | null
  article: string | null
  program_id: string | null
  plan_version: string | null
}

export type MockScenario =
  | 'answered_ar'
  | 'answered_en'
  | 'insufficient_evidence'
  | 'error'
