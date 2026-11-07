import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Language, RAGResponse } from '../types/rag'
import '../styles/advisor.css'

type Document = { id: string; filename: string; pages: number; chunks: number }
const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export function DocumentsPage() {
  const [language, setLanguage] = useState<Language>('ar'); const en = language === 'en'
  const [token, setToken] = useState(''); const [authorized, setAuthorized] = useState(false)
  const [documents, setDocuments] = useState<Document[]>([]); const [selected, setSelected] = useState('')
  const [file, setFile] = useState<File | null>(null); const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<RAGResponse | null>(null); const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function call<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(BASE + '/api/admin/documents' + path, {
      ...init, headers: { ...init?.headers, Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(90000),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : en ? 'The request was rejected.' : 'تم رفض الطلب.')
    return data as T
  }
  async function work(action: () => Promise<void>) {
    setBusy(true); setError('')
    try { await action() } catch (e) { setError(e instanceof Error && !(e instanceof TypeError) && !['TimeoutError', 'AbortError'].includes(e.name) ? e.message : en ? 'Unable to complete the request. Check the Backend and try again.' : 'تعذر إكمال الطلب. تحقق من الخلفية وحاول مجددًا.') }
    finally { setBusy(false) }
  }
  return <main className="advisor-app" dir={en ? 'ltr' : 'rtl'} style={{ overflow: 'auto', padding: '2rem' }}>
    <Link to="/advisor">{en ? 'Back to academic advisor' : 'العودة للمرشد الأكاديمي'}</Link>
    <h1>{en ? 'Document Management' : 'إدارة المستندات'}</h1>
    <label>{en ? 'Answer language' : 'لغة الإجابة'} <select value={language} onChange={(e) => { setLanguage(e.target.value as Language); setAnswer(null); setError('') }}>
      <option value="ar">العربية</option><option value="en">English</option></select></label>
    <p>{en ? 'Administrator only. Uploaded material is isolated and unofficial; it does not amend official university regulations. Answers are local exact passages, not an LLM.' : 'للمسؤول فقط. المستندات المرفوعة معزولة وغير رسمية ولا تعدّل اللوائح الجامعية. الإجابات اقتباسات محلية وليست توليد LLM.'}</p>
    {!authorized ? <form onSubmit={(e) => { e.preventDefault(); void work(async () => { setDocuments(await call<Document[]>(`?language=${language}`)); setAuthorized(true) }) }}>
      <label>{en ? 'Administrator token configured by the operator' : 'رمز المسؤول المُعدّ على الخادم'} <input type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} /></label>
      <button disabled={busy || !token}>{en ? 'Authorize' : 'تفويض'}</button>
      <p>{en ? 'No default credentials. The token is held in memory only and is never added to a URL or local storage.' : 'لا توجد بيانات دخول افتراضية. يُحفظ الرمز في الذاكرة فقط ولا يُضاف إلى الروابط أو التخزين المحلي.'}</p>
    </form> : <>
      <button onClick={() => { setAuthorized(false); setToken(''); setDocuments([]); setAnswer(null) }}>{en ? 'Log out and clear token' : 'خروج ومسح الرمز'}</button>
      <form onSubmit={(e) => { e.preventDefault(); if (!file) return; void work(async () => {
        const uploaded = await call<Document>(`?filename=${encodeURIComponent(file.name)}&language=${language}`, { method: 'POST', headers: { 'Content-Type': 'application/pdf' }, body: file })
        setDocuments(await call<Document[]>(`?language=${language}`)); setSelected(uploaded.id); setAnswer(null)
      }) }}>
        <input aria-label={en ? 'PDF file' : 'ملف PDF'} type="file" accept="application/pdf,.pdf" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button disabled={busy || !file}>{en ? 'Upload and index PDF' : 'رفع وفهرسة PDF'}</button>
        <p>{en ? 'Text PDFs only: up to 5 MiB, 25 pages, 50,000 characters and 128 chunks. Encrypted, scanned and invalid files are rejected.' : 'PDF نصي فقط: حتى 5 ميغابايت و25 صفحة و50 ألف محرف و128 مقطعًا. تُرفض الملفات المشفرة والممسوحة وغير الصالحة.'}</p>
      </form>
      <label>{en ? 'Explicit document scope' : 'نطاق المستند المحدد'} <select value={selected} onChange={(e) => { setSelected(e.target.value); setAnswer(null) }}>
        <option value="">{en ? 'Select an uploaded document' : 'اختر مستندًا مرفوعًا'}</option>
        {documents.map((d) => <option key={d.id} value={d.id}>{d.filename} — {d.pages} {en ? 'pages' : 'صفحات'} / {d.chunks} {en ? 'chunks' : 'مقاطع'}</option>)}</select></label>
      <form onSubmit={(e) => { e.preventDefault(); void work(async () => { setAnswer(await call<RAGResponse>(`/${selected}/ask`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, language }),
      })) }) }}>
        <label>{en ? 'Ask about a specific fact in the selected PDF' : 'اسأل عن معلومة محددة في PDF المختار'}<textarea maxLength={2000} value={question} onChange={(e) => setQuestion(e.target.value)} /></label>
        <button disabled={busy || !selected || !question.trim()}>{en ? 'Retrieve cited passage' : 'استرجاع اقتباس موثق'}</button>
      </form>
      {answer && <section aria-live="polite"><p style={{ whiteSpace: 'pre-wrap' }}>{answer.answer}</p><small>{answer.status} / {answer.reason} — {en ? 'Local extractive, no LLM' : 'اقتباس محلي دون LLM'}</small>
        {answer.sources.map((s) => <article key={s.source_id}><strong>[{s.source_id}] {s.document_name} — {en ? 'physical PDF page' : 'صفحة PDF الفعلية'} {s.page_number}</strong><blockquote>{s.supporting_excerpt}</blockquote></article>)}</section>}
    </>}
    {busy && <p role="status">{en ? 'Processing locally…' : 'جارٍ المعالجة محليًا…'}</p>}
    {error && <p role="alert">{error}</p>}
  </main>
}
