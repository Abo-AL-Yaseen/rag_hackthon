import { useSyncExternalStore } from 'react'
import {
  getActiveConversation,
  getChatState,
  subscribeChatStore,
  type ChatState,
  type Conversation,
} from '../lib/chatStore'

export function useChatStore(): ChatState & { active: Conversation | null } {
  const state = useSyncExternalStore(subscribeChatStore, getChatState, getChatState)
  return {
    ...state,
    active: getActiveConversation(),
  }
}
