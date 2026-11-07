import assert from 'node:assert/strict'
import { beforeEach, test } from 'node:test'

const saved = new Map()
globalThis.window = { localStorage: { getItem: (k) => saved.get(k) ?? null, setItem: (k, v) => saved.set(k, v) } }
const store = await import('../src/lib/chatStore.ts')
const civil = { program_id: 'civil-engineering', plan_version: '2021-1' }
const geomatics = { program_id: 'geomatics-engineering', plan_version: '2025-1' }
function response(answer) {
  return new Response(JSON.stringify({ contract_version: '1.0.0', answer, sources: [], claims: [],
    status: 'answered', reason: 'supported', language: 'ar', mode: 'mock',
    latency: { retrieval_ms: 1, generation_ms: 0, validation_ms: 0, total_ms: 1 }, validation: {} }), { status: 200 })
}
beforeEach(() => { saved.clear(); store.initChatStore() })

test('sends exact scope/language and stores actual mock response', async () => {
  let body
  globalThis.fetch = async (_url, init) => { body = JSON.parse(init.body); return response('3 credits fixture') }
  store.setChatContext(civil, 'ar')
  await store.sendUserMessage('Credit question')
  assert.deepEqual(body, { question: 'Credit question', language: 'ar', ...civil })
  assert.equal(store.getActiveConversation().messages.at(-1).content, '3 credits fixture')
  assert.equal(store.getActiveConversation().messages.at(-1).response.mode, 'mock')
})

test('late replies remain in originating conversation after switching chats', async () => {
  const resolve = []
  globalThis.fetch = () => new Promise((done) => resolve.push(done))
  store.setChatContext(civil, 'ar')
  const firstId = store.getActiveConversation().id
  const first = store.sendUserMessage('first')
  const secondChat = store.createNewChat(geomatics, 'ar')
  const second = store.sendUserMessage('second')
  resolve[1](response('Geomatics fixture')); await second
  resolve[0](response('Civil fixture')); await first
  assert.equal(store.getActiveConversation().id, secondChat.id)
  assert.equal(store.getActiveConversation().messages.at(-1).content, 'Geomatics fixture')
  assert.equal(store.getChatState().conversations.find((c) => c.id === firstId).messages.at(-1).content, 'Civil fixture')
})

test('deleted conversation does not receive a late answer in another chat', async () => {
  let resolve
  globalThis.fetch = () => new Promise((done) => { resolve = done })
  const id = store.getActiveConversation().id
  const pending = store.sendUserMessage('pending')
  store.deleteConversation(id)
  resolve(response('must not leak')); await pending
  assert.equal(store.getActiveConversation().messages.length, 0)
  assert.ok(!store.getChatState().conversations.some((c) => c.id === id))
})

test('context change preserves old messages and scope in a separate conversation', async () => {
  globalThis.fetch = async () => response('Civil fixture')
  store.setChatContext(civil, 'ar'); await store.sendUserMessage('first')
  const id = store.getActiveConversation().id
  store.setChatContext(geomatics, 'ar')
  assert.notEqual(store.getActiveConversation().id, id)
  assert.deepEqual(store.getChatState().conversations.find((c) => c.id === id).scope, civil)
  assert.deepEqual(store.getActiveConversation().scope, geomatics)
})

test('HTTP unavailable response becomes an error, never a canned answer', async () => {
  globalThis.fetch = async () => new Response('{}', { status: 503 })
  await store.sendUserMessage('question')
  const answer = store.getActiveConversation().messages.at(-1)
  assert.equal(answer.phase, 'error'); assert.equal(answer.response, undefined)
})

test('oversized question never reaches HTTP', async () => {
  globalThis.fetch = () => { throw new Error('must not call') }
  assert.equal(await store.sendUserMessage('x'.repeat(2001)), null)
  assert.equal(store.getActiveConversation().messages.length, 0)
})

test('invalid contract response is rejected', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ answer: 'wrong schema', contract_version: '2.0.0' }))
  await store.sendUserMessage('question')
  assert.equal(store.getActiveConversation().messages.at(-1).phase, 'error')
})
