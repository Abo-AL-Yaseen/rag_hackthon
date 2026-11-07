// Real local HTTP smoke through the actual frontend store and Vite proxy.
// No provider mocks, fixture answers or external requests. Run separately from unit tests.
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { performance } from 'node:perf_hooks'

const base = process.env.RAG_SMOKE_BASE_URL ?? 'http://127.0.0.1:5173'
const origin = new URL(base)
assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(origin.hostname))
const realFetch = globalThis.fetch
let requestBody = null
globalThis.fetch = async (url, init) => {
  const target = new URL(url, base)
  assert.equal(target.origin, origin.origin, 'Local-only HTTP test')
  if (init?.body) requestBody = JSON.parse(init.body)
  return realFetch(target, init)
}
const saved = new Map()
globalThis.window = { localStorage: { getItem: (k) => saved.get(k) ?? null, setItem: (k, v) => saved.set(k, v) } }
const store = await import('../src/lib/chatStore.ts')
const programs = await (await fetch('/api/programs')).json()
assert.equal(new Set(programs.map((p) => p.program_id)).size, programs.length)
const general = { program_id: null, plan_version: null }
const civil = { program_id: 'civil-engineering', plan_version: '2021-1' }
const computer = { program_id: 'computer-engineering', plan_version: '2021-1' }
const geomatics = { program_id: 'geomatics-engineering', plan_version: '2025-1' }
const cases = []
for (const [family, ar, en, scope] of [
  ['course', 'كم ساعة مساق 10871112؟', 'How many credits is course 10871112?', civil],
  ['attendance', 'شو بصير إذا غبت أكثر من المسموح؟', 'What happens if I miss too many classes?', general],
]) for (const [input, question] of [['ar', ar], ['en', en]]) for (const language of ['ar', 'en']) {
  cases.push({ id: `${family}_${input}_${language}`, question, language, scope,
    status: family === 'attendance' && language === 'en' ? 'insufficient_evidence' : 'answered', family })
}
for (const question of ['كم تخصص موجود عنا بالكلية؟', 'شو التخصصات المتوفرة؟', 'احكيلي أسماء تخصصات الهندسة.', 'What engineering programs are available?', 'How many engineering programs are listed?']) {
  for (const language of ['ar', 'en']) cases.push({ id: `catalog_${cases.length}`, question, language, scope: general, status: 'answered', family: 'catalog' })
}
for (const question of ['شو بصير اذا غبت اكثر من الحد المسموح؟', 'لو زادت غياباتي شو بصير؟', 'كم غياب بقدر أغيب؟', 'شو عقوبة الغياب؟', 'إذا غبت فوق النسبة المسموحة بنحرم من النهائي؟']) {
  for (const scope of [general, computer]) cases.push({ id: `natural_attendance_${cases.length}`, question, language: 'ar', scope, status: 'answered', family: 'attendance' })
}
for (const language of ['ar', 'en']) {
  for (const [id, question, scope, reason] of [
    ['clarify', 'كم ساعة مساق 10871112؟', general, 'ambiguous'],
    ['missing', 'How many credits is course 99999999?', civil, 'missing_evidence'],
    ['scope', 'اكتب قصيدة عن الجامعة', general, 'out_of_scope'],
    ['uncertain', 'شو المتطلبات السابقة لمساق 10641373؟', computer, 'ambiguous'],
  ]) cases.push({ id: `${id}_${language}`, question, language, scope, status: 'insufficient_evidence', reason })
  cases.push({ id: `http_error_${language}`, question: 'كم ساعة المساق؟', language,
    scope: { program_id: 'not-a-verified-program', plan_version: '2099-1' }, status: 'http_error' })
}
cases.push({ id: 'geomatics_two', question: 'How many credits is course 10871112?', language: 'ar', scope: geomatics, status: 'answered', contains: 'الساعات المعتمدة: 2' })
cases.push({ id: 'architecture_en', question: 'كم ساعة مساق 11221102؟', language: 'en', scope: { program_id: 'architectural-engineering', plan_version: '2025-1' }, status: 'answered', contains: 'Credit Hours: 2' })
const results = []
for (const c of cases) {
  saved.clear(); store.initChatStore(); store.setChatContext(c.scope, c.language); requestBody = null
  const start = performance.now()
  await store.sendUserMessage(c.question)
  const answer = store.getActiveConversation().messages.at(-1)
  const r = answer.response
  let failure = null; const locators = []
  try {
    assert.deepEqual(requestBody, { question: c.question, language: c.language, ...c.scope })
    assert.equal(answer.language, c.language)
    if (c.status === 'http_error') assert.equal(answer.phase, 'error')
    else {
      assert.equal(r.contract_version, '1.0.0'); assert.equal(r.mode, 'mock')
      assert.equal(r.status, c.status); assert.equal(r.language, c.language)
      if (c.reason) assert.equal(r.reason, c.reason)
      if (c.contains) assert.ok(r.answer.includes(c.contains))
      assert.equal(/[\u0600-\u06ff]/.test(r.answer), c.language === 'ar')
      if (r.status === 'answered') {
        assert.equal(r.validation.citation_references, 'verified'); assert.equal(r.validation.support_check, 'exact_quote')
        for (const source of r.sources) {
          assert.ok(r.answer.includes(source.supporting_excerpt))
          const response = await fetch('/api/sources/' + encodeURIComponent(source.document_id))
          assert.equal(response.status, 200)
          const locator = await response.json(); locators.push(locator)
          if (c.family === 'catalog') assert.equal(locator.source_type, 'runtime_catalog')
          else assert.ok(new URL(locator.source_url).hostname.endsWith('.najah.edu'))
        }
        if (c.family === 'catalog') {
          assert.ok(r.answer.includes(`: ${programs.length}.`))
          for (const program of programs) assert.ok(r.answer.includes(program[`name_${c.language}`]))
        }
        if (c.family === 'attendance') assert.ok(['10/ب', '10/ج', '10/د'].every((a) => locators.some((l) => l.article === a)))
      } else assert.deepEqual(r.sources, [])
    }
    if (c.language === 'en') assert.ok(!/[\u0600-\u06ff]/.test(answer.content))
  } catch (error) { failure = error.message }
  results.push({ id: c.id, request: requestBody, outcome: failure ? 'FAIL' : 'PASS', failure,
    elapsed_ms: performance.now() - start, response: r ?? null, actual_text: answer.content, source_locators: locators,
    mode: 'actual frontend store → Vite HTTP → Backend → real FacultyRuntime; local extractive, NOT LLM' })
}
const out = new URL('../../.local/final_improvements_20261107/', import.meta.url)
await mkdir(out, { recursive: true })
await writeFile(new URL('http_results.json', out), JSON.stringify(results, null, 2), 'utf8')
await writeFile(new URL('http_results.md', out), ['# Actual frontend HTTP evaluation',
  'Local extractive; NOT live LLM. English policy synthesis is unavailable and must refuse.',
  '| Case | Result | Actual text |', '|---|---|---|', ...results.map((r) => `| ${r.id} | ${r.outcome} | ${r.actual_text.replaceAll('\n', '<br>').replaceAll('|', ' / ')} |`)].join('\n'), 'utf8')
console.log(JSON.stringify({ total: results.length, passed: results.filter((r) => r.outcome === 'PASS').length,
  failed: results.filter((r) => r.outcome === 'FAIL').map((r) => ({ id: r.id, failure: r.failure, text: r.actual_text })), programs: programs.length }))
if (results.some((r) => r.outcome === 'FAIL')) process.exitCode = 1
