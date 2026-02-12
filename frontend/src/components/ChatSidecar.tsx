import { useEffect, useMemo, useRef, useState } from 'react'
import { MessageCircle, X, List, Plus, Send, Loader2, AlertTriangle } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../contexts/AuthContext'

const MIN_WIDTH = 320
const MAX_WIDTH = 720
const DEFAULT_WIDTH = 380

const STATUS_LABELS: Record<string, string> = {
  connecting: 'Connecting',
  ready: 'Ready',
  processing: 'Thinking',
  error: 'Disconnected',
}

type ConfirmPayload = {
  id: string
  title?: string
  summary?: string
  method?: string
  path?: string
  body?: Record<string, any>
}

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  type: 'message' | 'confirm' | 'error'
  text: string
  confirm?: ConfirmPayload
  actions?: string[]
  createdAt: string
}

type ConversationMeta = {
  id: string
  title: string
  created_at: string
  updated_at: string
}

function safeId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
}

function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function inlineMarkdown(text: string) {
  let s = escapeHtml(text)
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>')
  s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  s = s.replace(/\*(.+?)\*/g, '<em>$1</em>')
  return s
}

function renderMarkdown(text: string) {
  if (!text) return ''
  const codeBlocks: string[] = []
  let src = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length
    codeBlocks.push(`<pre><code class="lang-${escapeHtml(lang)}">${escapeHtml(code.trimEnd())}</code></pre>`)
    return `\x00CODE${idx}\x00`
  })

  const lines = src.split('\n')
  const out: string[] = []
  let inList = false

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]
    const trimmed = line.trim()

    if (trimmed.startsWith('\x00CODE')) {
      if (inList) {
        out.push('</ul>')
        inList = false
      }
      const idx = Number.parseInt(trimmed.match(/\d+/)?.[0] || '0', 10)
      out.push(codeBlocks[idx])
      continue
    }

    if (!trimmed) {
      if (inList) {
        out.push('</ul>')
        inList = false
      }
      continue
    }

    const h3 = trimmed.match(/^### (.+)$/)
    if (h3) {
      if (inList) {
        out.push('</ul>')
        inList = false
      }
      out.push(`<h4>${inlineMarkdown(h3[1])}</h4>`)
      continue
    }
    const h2 = trimmed.match(/^## (.+)$/)
    if (h2) {
      if (inList) {
        out.push('</ul>')
        inList = false
      }
      out.push(`<h3>${inlineMarkdown(h2[1])}</h3>`)
      continue
    }
    const h1 = trimmed.match(/^# (.+)$/)
    if (h1) {
      if (inList) {
        out.push('</ul>')
        inList = false
      }
      out.push(`<h2>${inlineMarkdown(h1[1])}</h2>`)
      continue
    }

    const bullet = trimmed.match(/^[-*] (.+)$/)
    const numbered = trimmed.match(/^\d+\. (.+)$/)
    if (bullet || numbered) {
      if (!inList) {
        out.push('<ul>')
        inList = true
      }
      out.push(`<li>${inlineMarkdown((bullet || numbered)![1])}</li>`)
      continue
    }

    if (inList) {
      out.push('</ul>')
      inList = false
    }
    out.push(`<p>${inlineMarkdown(trimmed)}</p>`)
  }

  if (inList) out.push('</ul>')
  return out.join('')
}

function tryParseResponse(text: string) {
  if (!text) return null
  const trimmed = text.trim()
  try {
    return JSON.parse(trimmed)
  } catch {
    const first = trimmed.indexOf('{')
    const last = trimmed.lastIndexOf('}')
    if (first !== -1 && last > first) {
      try {
        return JSON.parse(trimmed.slice(first, last + 1))
      } catch {
        return null
      }
    }
  }
  return null
}

function summarizeAction(raw: string) {
  if (!raw) return 'Running command'
  if (raw.includes('curl')) return 'Calling API'
  if (raw.includes('/api/projects')) return 'Fetching projects'
  if (raw.includes('/api/repositories')) return 'Fetching repositories'
  if (raw.includes('/api/contributors') || raw.includes('/api/leads')) return 'Fetching leads'
  if (raw.includes('/api/jobs')) return 'Fetching jobs'
  if (raw.includes('/api/dashboard')) return 'Fetching dashboard stats'
  if (raw.includes('/api/integrations')) return 'Fetching integrations'
  if (raw.length > 90) return 'Running command'
  return raw
}

export default function ChatSidecar() {
  const { activeOrg } = useAuth()
  const [open, setOpen] = useState(localStorage.getItem('chatOpen') === 'true')
  const [width, setWidth] = useState(() => {
    const saved = Number.parseInt(localStorage.getItem('chatWidth') || '', 10)
    return Number.isFinite(saved) ? saved : DEFAULT_WIDTH
  })
  const [isResizing, setIsResizing] = useState(false)
  const [status, setStatus] = useState<'connecting' | 'ready' | 'processing' | 'error'>('connecting')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [showHistory, setShowHistory] = useState(false)
  const [conversations, setConversations] = useState<ConversationMeta[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const pendingMessageIdRef = useRef<string | null>(null)
  const pendingTextRef = useRef<string>('')
  const pendingActionsRef = useRef<string[]>([])
  const reconnectTimerRef = useRef<number | null>(null)
  const messagesRef = useRef<ChatMessage[]>([])

  const updateMessages = (updater: (prev: ChatMessage[]) => ChatMessage[]) => {
    setMessages((prev) => {
      const next = updater(prev)
      messagesRef.current = next
      return next
    })
  }

  const wsUrl = useMemo(() => {
    const envUrl = import.meta.env.VITE_CODEX_WS_URL
    if (envUrl) return envUrl
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/codex`
  }, [])

  const apiBaseUrl = useMemo(() => {
    return import.meta.env.VITE_API_URL || window.location.origin
  }, [])

  useEffect(() => {
    document.documentElement.style.setProperty('--chat-sidecar-width', `${width}px`)
    localStorage.setItem('chatWidth', String(width))
  }, [width])

  useEffect(() => {
    if (open) {
      document.body.classList.add('chat-open')
    } else {
      document.body.classList.remove('chat-open')
    }
    localStorage.setItem('chatOpen', open ? 'true' : 'false')
  }, [open])

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      if (!isResizing) return
      const nextWidth = Math.min(Math.max(window.innerWidth - event.clientX, MIN_WIDTH), MAX_WIDTH)
      setWidth(nextWidth)
    }

    const handleMouseUp = () => {
      if (!isResizing) return
      setIsResizing(false)
    }

    if (isResizing) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

  useEffect(() => {
    connectWebSocket()
    return () => {
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current)
      }
      wsRef.current?.close()
    }
  }, [wsUrl])

  useEffect(() => {
    if (showHistory && activeOrg?.id) {
      refreshConversationList()
    }
  }, [showHistory, activeOrg?.id])

  const connectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close()
    }

    setStatus('connecting')
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('ready')
    }

    ws.onclose = () => {
      setStatus('error')
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current)
      }
      reconnectTimerRef.current = window.setTimeout(() => {
        connectWebSocket()
      }, 3000)
    }

    ws.onerror = () => {
      setStatus('error')
    }

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      handleServerMessage(msg)
    }
  }

  const handleServerMessage = (msg: any) => {
    if (msg.type === 'session.id') {
      sessionIdRef.current = msg.sessionId
      return
    }

    if (msg.type === 'turn.started') {
      setStatus('processing')
      const messageId = safeId()
      pendingMessageIdRef.current = messageId
      pendingTextRef.current = ''
      pendingActionsRef.current = []
      const botMessage: ChatMessage = {
        id: messageId,
        role: 'assistant',
        type: 'message',
        text: '',
        actions: [],
        createdAt: new Date().toISOString(),
      }
      updateMessages((prev) => [...prev, botMessage])
      return
    }

    if (msg.type === 'agent.action') {
      if (!pendingMessageIdRef.current) return
      const actionText = summarizeAction(msg.command || msg.tool || '')
      pendingActionsRef.current = [...pendingActionsRef.current, actionText]
      updateMessages((prev) =>
        prev.map((m) =>
          m.id === pendingMessageIdRef.current ? { ...m, actions: [...pendingActionsRef.current] } : m
        )
      )
      return
    }

    if (msg.type === 'agent.text') {
      pendingTextRef.current = msg.text || ''
      if (pendingMessageIdRef.current && msg.status === 'streaming') {
        updateMessages((prev) =>
          prev.map((m) =>
            m.id === pendingMessageIdRef.current ? { ...m, text: pendingTextRef.current } : m
          )
        )
      }
      return
    }

    if (msg.type === 'turn.completed') {
      setStatus('ready')
      const finalText = pendingTextRef.current || msg.text || ''
      const parsed = tryParseResponse(finalText)
      const messageType: ChatMessage['type'] = parsed?.type === 'confirm' ? 'confirm' : 'message'
      const content = parsed?.text || parsed?.title || finalText || 'No response'
      const confirmPayload = parsed?.type === 'confirm' ? parsed : undefined

      const updatedMessages = messagesRef.current.map((m) => {
        if (m.id !== pendingMessageIdRef.current) return m
        return {
          ...m,
          type: messageType,
          text: content,
          confirm: confirmPayload,
          actions: pendingActionsRef.current,
        }
      })
      updateMessages(() => updatedMessages)
      pendingMessageIdRef.current = null
      pendingTextRef.current = ''
      pendingActionsRef.current = []
      persistConversation(updatedMessages)
      return
    }

    if (msg.type === 'error') {
      setStatus('error')
      const errorMessage: ChatMessage = {
        id: safeId(),
        role: 'assistant',
        type: 'error',
        text: msg.message || 'Error processing request',
        createdAt: new Date().toISOString(),
      }
      updateMessages((prev) => [...prev, errorMessage])
      return
    }
  }

  const refreshConversationList = async () => {
    if (!activeOrg?.id) return
    try {
      const data = await api.listChatConversations(activeOrg.id)
      setConversations(data || [])
    } catch {
      setConversations([])
    }
  }

  const persistConversation = async (nextMessages: ChatMessage[]) => {
    if (!activeOrg?.id) return
    const title = deriveTitle(nextMessages)
    const payload = { title, messages: nextMessages }
    try {
      if (!conversationId) {
        const created = await api.createChatConversation(payload, activeOrg.id)
        setConversationId(created.id)
        if (showHistory) refreshConversationList()
      } else {
        await api.updateChatConversation(conversationId, payload, activeOrg.id)
        if (showHistory) refreshConversationList()
      }
    } catch {
      // ignore persistence failures
    }
  }

  const deriveTitle = (msgs: ChatMessage[]) => {
    const firstUser = msgs.find((m) => m.role === 'user')
    if (!firstUser) return 'New conversation'
    return firstUser.text.slice(0, 60)
  }

  const sendMessage = (text: string) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      setStatus('error')
      return
    }

    const token = localStorage.getItem('token')
    const payload = {
      type: 'chat',
      message: text,
      sessionId: sessionIdRef.current || undefined,
      token,
      orgId: activeOrg?.id,
      apiBaseUrl,
    }
    ws.send(JSON.stringify(payload))
  }

  const handleSubmit = () => {
    const text = input.trim()
    if (!text) return
    const userMessage: ChatMessage = {
      id: safeId(),
      role: 'user',
      type: 'message',
      text,
      createdAt: new Date().toISOString(),
    }
    const nextMessages = [...messagesRef.current, userMessage]
    updateMessages(() => nextMessages)
    setInput('')
    sendMessage(text)
  }

  const handleConfirm = (payload: ConfirmPayload) => {
    const confirmText = `CONFIRM_ACTION: ${payload.id}`
    const userMessage: ChatMessage = {
      id: safeId(),
      role: 'user',
      type: 'message',
      text: `Confirmed: ${payload.title || payload.id}`,
      createdAt: new Date().toISOString(),
    }
    const nextMessages = [...messagesRef.current, userMessage]
    updateMessages(() => nextMessages)
    sendMessage(confirmText)
  }

  const handleCancel = (payload: ConfirmPayload) => {
    const userMessage: ChatMessage = {
      id: safeId(),
      role: 'user',
      type: 'message',
      text: `Canceled: ${payload.title || payload.id}`,
      createdAt: new Date().toISOString(),
    }
    const nextMessages = [...messagesRef.current, userMessage]
    updateMessages(() => nextMessages)
  }

  const handleNewConversation = () => {
    updateMessages(() => [])
    setConversationId(null)
    setShowHistory(false)
    if (sessionIdRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'reset', sessionId: sessionIdRef.current }))
    }
    sessionIdRef.current = null
  }

  const handleLoadConversation = async (id: string) => {
    if (!activeOrg?.id) return
    try {
      const convo = await api.getChatConversation(id, activeOrg.id)
      setConversationId(convo.id)
      updateMessages(() => convo.messages || [])
      setShowHistory(false)
      if (sessionIdRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'reset', sessionId: sessionIdRef.current }))
      }
      sessionIdRef.current = null
    } catch {
      // ignore
    }
  }

  const handleDeleteConversation = async (id: string) => {
    if (!activeOrg?.id) return
    try {
      await api.deleteChatConversation(id, activeOrg.id)
      refreshConversationList()
    } catch {
      // ignore
    }
  }

  const renderMessage = (msg: ChatMessage) => {
    const isUser = msg.role === 'user'
    const bubbleClasses = isUser
      ? 'bg-gradient-to-r from-cyan-500 to-violet-500 text-white'
      : 'bg-white/90 dark:bg-gray-800/90 text-gray-900 dark:text-gray-100 border border-gray-200/70 dark:border-gray-700/70'

    return (
      <div key={msg.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm ${bubbleClasses}`}>
          {msg.actions && msg.actions.length > 0 && (
            <div className="mb-2 rounded-xl border border-dashed border-gray-200/60 dark:border-gray-700/60 bg-gray-50/80 dark:bg-gray-900/40 p-2 text-[11px] text-gray-600 dark:text-gray-300">
              <div className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400">
                <span>Steps</span>
              </div>
              <ul className="mt-1 space-y-1">
                {msg.actions.map((action, idx) => (
                  <li key={`${msg.id}-action-${idx}`} className="flex items-start gap-2">
                    <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-cyan-400" />
                    <span>{action}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {msg.type === 'confirm' && msg.confirm ? (
            <div className="space-y-3">
              <div>
                <div className="text-sm font-semibold">{msg.confirm.title || 'Confirm action'}</div>
                {msg.confirm.summary && <p className="mt-1 text-xs text-gray-600 dark:text-gray-300">{msg.confirm.summary}</p>}
              </div>
              <div className="rounded-lg border border-gray-200/70 dark:border-gray-700/70 bg-gray-50/80 dark:bg-gray-900/40 p-2 text-xs text-gray-600 dark:text-gray-300">
                <div className="font-mono">{msg.confirm.method} {msg.confirm.path}</div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleConfirm(msg.confirm!)}
                  className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-600"
                >
                  Confirm
                </button>
                <button
                  onClick={() => handleCancel(msg.confirm!)}
                  className="rounded-lg border border-gray-200/70 dark:border-gray-700/70 px-3 py-1.5 text-xs font-semibold text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div
              className="chat-markdown text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}
            />
          )}
        </div>
      </div>
    )
  }

  return (
    <>
      <button
        className={`fixed bottom-6 right-6 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-r from-cyan-500 to-violet-500 text-white shadow-lg transition-transform ${open ? 'scale-0' : 'scale-100'}`}
        onClick={() => setOpen(true)}
        title="Open chat"
      >
        <MessageCircle className="h-5 w-5" />
      </button>

      <aside
        className={`fixed top-0 right-0 z-50 flex h-full flex-col border-l border-gray-200/70 dark:border-gray-700/70 bg-white/95 dark:bg-gray-900/95 backdrop-blur-xl transition-transform duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}
        style={{ width }}
      >
        <div
          className="absolute left-0 top-0 h-full w-2 cursor-ew-resize"
          onMouseDown={() => setIsResizing(true)}
        />

        <div className="flex items-center justify-between border-b border-gray-200/70 dark:border-gray-700/70 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-cyan-400" />
            <div className="text-sm font-semibold text-gray-800 dark:text-gray-100">AI Copilot</div>
            <span className={`ml-2 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${status === 'processing' ? 'bg-amber-500/20 text-amber-500' : status === 'ready' ? 'bg-emerald-500/20 text-emerald-500' : status === 'error' ? 'bg-rose-500/20 text-rose-500' : 'bg-gray-200/70 text-gray-500'}`}>
              {STATUS_LABELS[status]}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="rounded-lg border border-gray-200/70 dark:border-gray-700/70 p-1.5 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
              onClick={() => setShowHistory((prev) => !prev)}
              title="Past conversations"
            >
              <List className="h-4 w-4" />
            </button>
            <button
              className="rounded-lg border border-gray-200/70 dark:border-gray-700/70 p-1.5 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
              onClick={handleNewConversation}
              title="New conversation"
            >
              <Plus className="h-4 w-4" />
            </button>
            <button
              className="rounded-lg border border-gray-200/70 dark:border-gray-700/70 p-1.5 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
              onClick={() => setOpen(false)}
              title="Close"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {showHistory && (
          <div className="border-b border-gray-200/70 dark:border-gray-700/70 px-4 py-3">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Conversations
            </div>
            <div className="max-h-48 space-y-2 overflow-auto">
              {conversations.length === 0 && (
                <div className="text-xs text-gray-500">No conversations yet</div>
              )}
              {conversations.map((c) => (
                <div
                  key={c.id}
                  className={`flex items-center justify-between rounded-lg border border-gray-200/70 dark:border-gray-700/70 px-3 py-2 text-xs ${conversationId === c.id ? 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-300' : 'bg-gray-50/80 dark:bg-gray-900/40 text-gray-600 dark:text-gray-300'}`}
                >
                  <button className="text-left" onClick={() => handleLoadConversation(c.id)}>
                    <div className="font-semibold">{c.title}</div>
                    <div className="text-[10px] text-gray-500">{new Date(c.updated_at).toLocaleString()}</div>
                  </button>
                  <button
                    className="text-gray-400 hover:text-rose-500"
                    onClick={() => handleDeleteConversation(c.id)}
                    title="Delete"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex-1 space-y-4 overflow-auto px-4 py-4">
          {messages.length === 0 && (
            <div className="rounded-2xl border border-dashed border-gray-200/70 dark:border-gray-700/70 bg-gray-50/80 dark:bg-gray-900/40 p-4 text-xs text-gray-500">
              Ask questions about projects, leads, jobs, integrations, or billing. The assistant will use your session to call the API.
            </div>
          )}
          {messages.map(renderMessage)}
        </div>

        <div className="border-t border-gray-200/70 dark:border-gray-700/70 p-3">
          <div className="flex items-center gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSubmit()
                }
              }}
              placeholder={activeOrg ? 'Ask about your data...' : 'Select an org to chat'}
              disabled={!activeOrg}
              className="flex-1 rounded-xl border border-gray-200/70 dark:border-gray-700/70 bg-white/90 dark:bg-gray-900/60 px-3 py-2 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
            />
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || status === 'processing' || !activeOrg}
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-violet-500 text-white shadow-md disabled:opacity-50"
              title="Send"
            >
              {status === 'processing' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
          {!activeOrg && (
            <div className="mt-2 flex items-center gap-2 text-[11px] text-amber-500">
              <AlertTriangle className="h-3.5 w-3.5" />
              Select an organization to enable chat.
            </div>
          )}
        </div>
      </aside>
    </>
  )
}
