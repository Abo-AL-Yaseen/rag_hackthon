import { useEffect, useState } from 'react'
import type { ChatMessage as ChatMessageType } from '../../lib/chatStore'
import type { Source, SourceLocator } from '../../types/rag'
import { getSourceLocator, getCoursePage, type CoursePage } from '../../api/chatApi'

function CourseList({ locator }: { locator: SourceLocator }) {
  const [offset, setOffset] = useState(0)
  const [page, setPage] = useState<CoursePage | null>(null)
  const [error, setError] = useState('')
  const language = locator.language ?? 'ar'; const en = language === 'en'
  useEffect(() => {
    let alive = true; setPage(null); setError('')
    getCoursePage(locator.program_id!, locator.plan_version!, language, offset)
      .then((p) => { if (alive) setPage(p) }).catch((e) => { if (alive) setError(e.message) })
    return () => { alive = false }
  }, [locator.program_id, locator.plan_version, language, offset])
  if (error) return <p role="alert">{error}</p>
  if (!page) return <p role="status">{en ? 'Loading course entries…' : 'جارٍ تحميل المساقات…'}</p>
  return <section dir={en ? 'ltr' : 'rtl'}>
    <strong>{en ? `Showing ${offset + 1}–${offset + page.courses.length} of ${page.total} verified course entries` : `عرض ${offset + 1}–${offset + page.courses.length} من ${page.total} مساقًا موثقًا`}</strong>
    {!page.complete_indexed_coverage && <p>{en ? 'Incomplete subset of indexed rows.' : 'مجموعة جزئية؛ بعض الصفوف المفهرسة غير موثقة كفاية.'}</p>}
    <div style={{ overflowX: 'auto' }}><table><thead><tr>{(en ? ['Code', 'Course', 'Credits', 'Published requirement group', 'Source'] : ['الرمز', 'المساق', 'الساعات', 'مجموعة المتطلبات المنشورة', 'المصدر']).map((s) => <th key={s}>{s}</th>)}</tr></thead>
      <tbody>{page.courses.map((c) => <tr key={c.course_code}><td><bdi>{c.course_code}</bdi></td><td>{c.name}</td><td>{c.credit_hours}</td><td>{c.classification ?? (en ? 'Not verified' : 'غير موثق')}</td>
        <td>{officialLink(c.source_url) && <a href={officialLink(c.source_url)!} target="_blank" rel="noopener noreferrer">{en ? 'Official plan' : 'الخطة الرسمية'} — {c.table_index}/{c.row_index}</a>}</td></tr>)}</tbody></table></div>
    <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - page.limit))}>{en ? 'Previous' : 'السابق'}</button>
    <button disabled={page.next_offset === null} onClick={() => setOffset(page.next_offset!)}>{en ? 'Next' : 'التالي'}</button>
  </section>
}

function officialLink(url: string | null | undefined) {
  try {
    const parsed = new URL(url ?? '')
    return parsed.protocol === 'https:' && (parsed.hostname === 'najah.edu' || parsed.hostname.endsWith('.najah.edu')) ? parsed.href : null
  } catch { return null }
}

function SourceCard({ source, messageId }: { source: Source; messageId: string }) {
  const [locator, setLocator] = useState<SourceLocator | null>(null)
  useEffect(() => {
    let alive = true
    getSourceLocator(source.document_id).then((value) => { if (alive) setLocator(value) }).catch(() => {})
    return () => { alive = false }
  }, [source.document_id])
  const link = officialLink(locator?.source_url)
  return <article className="advisor-source-card" id={`${messageId}-${source.source_id}`}>
    <strong>[{source.source_id}] {locator?.document_title ?? source.document_name}</strong>
    <div><bdi>{source.document_name}</bdi> — <bdi>{source.version}</bdi></div>
    {locator && <div>{locator.source_type ? 'فهرس موثق من بيانات النظام — ليس صفحة PDF' : locator.physical_pdf_page !== null ? `صفحة PDF الفعلية: ${locator.physical_pdf_page}` :
      locator.table_index !== null ? `جدول HTML: ${locator.table_index}، الصف: ${locator.row_index}` : 'ملخص الخطة — HTML'}
      {locator.article && ` — المادة ${locator.article}`}</div>}
    <blockquote>{source.supporting_excerpt}</blockquote>
    {link && <a href={link} target="_blank" rel="noopener noreferrer">المصدر الرسمي</a>}
    {locator?.source_type === 'course_catalog' && <CourseList locator={locator} />}
    {!!locator?.official_plan_sources?.length && <details><summary>روابط الخطط الرسمية الداعمة للفهرس</summary>
      {locator.official_plan_sources.filter((r) => officialLink(r.source_url)).map((r) =>
        <div key={`${r.program_id}-${r.plan_version}-${r.source_url}`}><a href={officialLink(r.source_url)!} target="_blank" rel="noopener noreferrer">{r.document_title ?? r.program_id} — {r.plan_version}</a></div>)}
    </details>}
  </article>
}

export function ChatMessage({ message }: { message: ChatMessageType }) {
  const isUser = message.role === 'user'
  const response = message.response
  const english = (response?.language ?? message.language) === 'en'
  const sources = response?.sources ?? []
  const content = message.content.split(/(\[S\d+\])/g).map((piece, index) => {
    const source = sources.find((s) => `[${s.source_id}]` === piece)
    return source ? <a key={index} className="advisor-citation" href={`#${message.id}-${source.source_id}`}>{piece}</a> : piece
  })
  return <div className={`advisor-message ${isUser ? 'advisor-message--user' : 'advisor-message--assistant'}`}>
    <div className="advisor-message__bubble" dir={response?.language === 'en' ? 'ltr' : 'auto'}>
      {message.phase === 'pending' ? <span role="status">{english ? 'Retrieving evidence and preparing the response…' : 'جارٍ استرجاع الأدلة وإعداد الرد…'}</span> : content}
      {message.phase === 'error' && <div className="advisor-response-state" role="alert">{english ? 'The request could not be completed. You can resend it.' : 'تعذر إكمال الطلب — يمكنك إعادة الإرسال.'}</div>}
      {response && <>
        <div className="advisor-response-state" role={response.status === 'error' ? 'alert' : 'status'}>
          {response.mode === 'mock' ? 'وضع محلي دون LLM — اقتباسات من الأدلة' : 'توليد LLM عن بُعد'}
          {' · '}{response.status === 'answered' ? 'إجابة مدعومة' : response.status === 'insufficient_evidence' ? response.reason === 'ambiguous' ? 'بحاجة لتوضيح' : response.reason === 'out_of_scope' ? 'خارج نطاق المرشد' : 'الأدلة غير كافية' : 'خطأ في المحرك'}
          {' · '}<bdi>{response.reason}</bdi>
        </div>
        {!!sources.length && <section className="advisor-sources" aria-label="مصادر الإجابة">
          {sources.map((s) => <SourceCard key={s.source_id} source={s} messageId={message.id} />)}
        </section>}
      </>}
    </div>
  </div>
}
