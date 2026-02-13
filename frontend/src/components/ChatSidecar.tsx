import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { MessageCircle, X, List, Plus, Send, Loader2 } from 'lucide-react'
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

type ActionStep = {
  label: string
  raw: string
}

type DashboardWidget = { title: string; value: string | number; subtext?: string }
type DashboardBarItem = { name?: string; label?: string; value: number }
type DashboardSection =
  | { type: 'widgets'; items: DashboardWidget[] }
  | { type: 'bars'; items: DashboardBarItem[]; label?: string }
  | { type: 'table'; rows: Record<string, any>[]; columns?: string[] }
  | { type: 'pills'; items: { label: string; color?: string; count?: number }[] }

type DashboardPayload = {
  type: 'dashboard'
  title?: string
  sections?: DashboardSection[]
  widgets?: DashboardWidget[]
  bars?: DashboardBarItem[]
  rows?: Record<string, any>[]
  columns?: string[]
}

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  type: 'message' | 'confirm' | 'error'
  text: string
  confirm?: ConfirmPayload
  dashboard?: DashboardPayload
  actions?: ActionStep[]
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
  if (raw.includes('psql') && raw.includes('projects')) return 'Querying projects'
  if (raw.includes('psql') && raw.includes('repositories')) return 'Querying repositories'
  if (raw.includes('psql') && raw.includes('contributors')) return 'Querying contributors'
  if (raw.includes('psql') && raw.includes('lead_scores')) return 'Querying lead scores'
  if (raw.includes('psql') && raw.includes('sourcing_jobs')) return 'Querying jobs'
  if (raw.includes('psql') && raw.includes('dashboard')) return 'Querying dashboard stats'
  if (raw.includes('psql')) return 'Running database query'
  if (raw.includes('curl')) return 'Calling API'
  if (raw.startsWith('Running: ')) return summarizeAction(raw.slice(9))
  if (raw.startsWith('ls')) return 'Listing files'
  if (raw.startsWith('cat ')) return 'Reading ' + raw.split('/').pop()
  if (raw.length > 90) return 'Running command'
  return raw
}

/* ── Dashboard rendering components ── */

const WIDGET_COLORS = [
  'from-cyan-500/10 to-cyan-500/5 border-cyan-500/20',
  'from-violet-500/10 to-violet-500/5 border-violet-500/20',
  'from-emerald-500/10 to-emerald-500/5 border-emerald-500/20',
  'from-amber-500/10 to-amber-500/5 border-amber-500/20',
]

function WidgetGrid({ items }: { items: DashboardWidget[] }) {
  if (!items?.length) return null
  return (
    <div className="grid grid-cols-2 gap-2 my-2">
      {items.map((w, i) => (
        <div
          key={i}
          className={`rounded-xl border bg-gradient-to-br p-3 ${WIDGET_COLORS[i % WIDGET_COLORS.length]}`}
        >
          <div className="text-[10px] uppercase tracking-wide text-gray-500 dark:text-gray-400">{w.title}</div>
          <div className="mt-1 text-lg font-bold text-gray-900 dark:text-gray-50">{w.value}</div>
          {w.subtext && <div className="mt-0.5 text-[10px] text-gray-500 dark:text-gray-400">{w.subtext}</div>}
        </div>
      ))}
    </div>
  )
}

function BarChart({ items, label }: { items: DashboardBarItem[]; label?: string }) {
  if (!items?.length) return null
  const max = Math.max(...items.map((i) => i.value || 0), 1)
  return (
    <div className="my-2 space-y-1.5">
      {label && <div className="text-[10px] uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">{label}</div>}
      {items.slice(0, 12).map((item, i) => {
        const pct = Math.round(((item.value || 0) / max) * 100)
        return (
          <div key={i} className="flex items-center gap-2 text-[11px]">
            <span className="w-24 truncate text-gray-600 dark:text-gray-300">{item.name || item.label || ''}</span>
            <div className="flex-1 h-4 rounded-full bg-gray-100 dark:bg-gray-800 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-violet-500 transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="w-8 text-right font-semibold text-gray-700 dark:text-gray-200">{item.value}</span>
          </div>
        )
      })}
    </div>
  )
}

function InlineTable({ rows, columns }: { rows: Record<string, any>[]; columns?: string[] }) {
  if (!rows?.length) return null
  const cols = columns || Object.keys(rows[0])
  return (
    <div className="my-2 overflow-x-auto rounded-xl border border-gray-200/60 dark:border-gray-700/60">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="bg-gray-50 dark:bg-gray-800/60">
            {cols.map((c) => (
              <th key={c} className="px-3 py-1.5 text-left font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 20).map((r, i) => (
            <tr key={i} className="border-t border-gray-100 dark:border-gray-800">
              {cols.map((c) => (
                <td key={c} className="px-3 py-1.5 text-gray-700 dark:text-gray-200">{String(r[c] ?? '')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function StatusPills({ items }: { items: { label: string; color?: string; count?: number }[] }) {
  if (!items?.length) return null
  const colorMap: Record<string, string> = {
    green: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400',
    red: 'bg-rose-500/15 text-rose-600 dark:text-rose-400',
    yellow: 'bg-amber-500/15 text-amber-600 dark:text-amber-400',
    blue: 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400',
    orange: 'bg-orange-500/15 text-orange-600 dark:text-orange-400',
  }
  const fallback = 'bg-gray-200/60 text-gray-600 dark:bg-gray-700/60 dark:text-gray-300'
  return (
    <div className="my-2 flex flex-wrap gap-1.5">
      {items.map((pill, i) => (
        <span key={i} className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${colorMap[pill.color || ''] || fallback}`}>
          {pill.label}
          {pill.count != null && <strong className="ml-0.5">{pill.count}</strong>}
        </span>
      ))}
    </div>
  )
}

function DashboardSection({ section }: { section: DashboardSection }) {
  switch (section.type) {
    case 'widgets': return <WidgetGrid items={section.items} />
    case 'bars': return <BarChart items={section.items} label={section.label} />
    case 'table': return <InlineTable rows={section.rows} columns={section.columns} />
    case 'pills': return <StatusPills items={section.items} />
    default: return null
  }
}

function DashboardView({ dashboard }: { dashboard: DashboardPayload }) {
  if (!dashboard) return null
  const sections = dashboard.sections || []
  if (sections.length) {
    return <>{sections.map((sec, i) => <DashboardSection key={i} section={sec} />)}</>
  }
  if (dashboard.widgets) return <WidgetGrid items={dashboard.widgets} />
  if (dashboard.bars) return <BarChart items={dashboard.bars} />
  if (dashboard.rows) return <InlineTable rows={dashboard.rows} columns={dashboard.columns} />
  return null
}

/* ── Typewriter ── */

const TYPEWRITER_MS = 8

function TypewriterText({ html, onDone }: { html: string; onDone?: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [visibleLen, setVisibleLen] = useState(0)
  const plainRef = useRef('')
  const doneRef = useRef(false)

  useEffect(() => {
    // Extract plain text length from the html to know total chars
    const tmp = document.createElement('div')
    tmp.innerHTML = html
    plainRef.current = tmp.textContent || ''
    const total = plainRef.current.length
    if (total === 0) {
      doneRef.current = true
      onDone?.()
      return
    }
    setVisibleLen(0)
    doneRef.current = false
    let idx = 0
    const timer = setInterval(() => {
      idx += 1
      setVisibleLen(idx)
      if (idx >= total) {
        clearInterval(timer)
        if (!doneRef.current) {
          doneRef.current = true
          onDone?.()
        }
      }
    }, TYPEWRITER_MS)
    return () => clearInterval(timer)
  }, [html])

  // We show the full HTML but clip via CSS using a character-counting overlay approach.
  // Simpler: just show the full HTML and use a text-clipping trick.
  // Actually the cleanest approach: render full HTML, but truncate the visible text content.
  useEffect(() => {
    if (!containerRef.current) return
    containerRef.current.innerHTML = html
    // Walk text nodes and hide characters beyond visibleLen
    let charCount = 0
    const walk = (node: Node) => {
      if (node.nodeType === Node.TEXT_NODE) {
        const text = node.textContent || ''
        if (charCount + text.length <= visibleLen) {
          charCount += text.length
        } else {
          const visible = visibleLen - charCount
          node.textContent = text.slice(0, visible)
          charCount = visibleLen
        }
      } else {
        const children = Array.from(node.childNodes)
        for (const child of children) {
          if (charCount >= visibleLen) {
            (child as HTMLElement).style && ((child as HTMLElement).style.display = 'none')
            continue
          }
          walk(child)
        }
      }
    }
    walk(containerRef.current)
  }, [html, visibleLen])

  return (
    <div
      ref={containerRef}
      className="chat-markdown text-sm leading-relaxed"
    />
  )
}

function ThinkingSection({ steps, messageId, isComplete }: { steps: ActionStep[]; messageId: string; isComplete: boolean }) {
  const [expanded, setExpanded] = useState(false)

  if (steps.length === 0) return null

  // While processing: show live steps
  if (!isComplete) {
    return (
      <div className="mb-2 rounded-xl border border-dashed border-gray-200/60 dark:border-gray-700/60 bg-gray-50/80 dark:bg-gray-900/40 p-2 text-[11px] text-gray-600 dark:text-gray-300">
        <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Working</span>
        </div>
        <div className="space-y-1">
          {steps.map((step, idx) => (
            <ActionStepRow key={`${messageId}-step-${idx}`} step={step} />
          ))}
        </div>
      </div>
    )
  }

  // Completed: collapsible summary
  const label = steps.length === 1 ? '1 step' : `${steps.length} steps`

  return (
    <div className="mb-2 rounded-xl border border-gray-200/60 dark:border-gray-700/60 bg-gray-50/80 dark:bg-gray-900/40 text-[11px] text-gray-600 dark:text-gray-300">
      <button
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center gap-1.5 px-2 py-1.5 hover:bg-gray-100/60 dark:hover:bg-gray-800/40 rounded-xl transition-colors"
      >
        <svg
          className={`h-3 w-3 text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
          viewBox="0 0 16 16"
          fill="currentColor"
        >
          <path d="M6 3l5 5-5 5V3z" />
        </svg>
        <span className="text-gray-500 dark:text-gray-400">Ran {label}</span>
      </button>
      {expanded && (
        <div className="px-2 pb-2 space-y-1">
          {steps.map((step, idx) => (
            <ActionStepRow key={`${messageId}-step-${idx}`} step={step} />
          ))}
        </div>
      )}
    </div>
  )
}

function ActionStepRow({ step }: { step: ActionStep }) {
  const [showRaw, setShowRaw] = useState(false)

  return (
    <div>
      <button
        onClick={() => setShowRaw((prev) => !prev)}
        className="flex items-center gap-1.5 w-full text-left hover:text-gray-800 dark:hover:text-gray-100 transition-colors"
      >
        <span className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-cyan-400" />
        <span className="flex-1 truncate">{step.label}</span>
        <svg
          className={`h-2.5 w-2.5 text-gray-400 transition-transform flex-shrink-0 ${showRaw ? 'rotate-90' : ''}`}
          viewBox="0 0 16 16"
          fill="currentColor"
        >
          <path d="M6 3l5 5-5 5V3z" />
        </svg>
      </button>
      {showRaw && (
        <pre className="mt-1 ml-3 p-2 rounded-lg bg-gray-900/80 text-gray-300 text-[10px] leading-relaxed overflow-x-auto whitespace-pre-wrap break-all">
          {step.raw}
        </pre>
      )}
    </div>
  )
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
  const pendingActionsRef = useRef<ActionStep[]>([])
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
    const envUrl = (import.meta.env.VITE_CODEX_WS_URL || '').trim()
    const isLocalhostEnv = /^wss?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/.test(envUrl)
    if (envUrl && !(import.meta.env.PROD && isLocalhostEnv)) return envUrl
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${protocol}//${window.location.host}/ws/codex`
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
        reconnectTimerRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [wsUrl])

  useEffect(() => {
    if (showHistory && activeOrg?.id) {
      refreshConversationList()
    }
  }, [showHistory, activeOrg?.id])

  const connectWebSocket = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return
    }
    if (wsRef.current) {
      wsRef.current.onclose = null
      wsRef.current.close()
    }

    setStatus('connecting')
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('ready')
    }

    ws.onclose = () => {
      if (wsRef.current !== ws) return
      setStatus('error')
      if (reconnectTimerRef.current) {
        window.clearTimeout(reconnectTimerRef.current)
      }
      reconnectTimerRef.current = window.setTimeout(() => {
        connectWebSocket()
      }, 3000)
    }

    ws.onerror = () => {
      // onclose will fire after this
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
      const rawText = msg.action === 'command'
        ? (msg.command || 'command')
        : `Tool: ${msg.tool || 'tool call'}`
      const step: ActionStep = { label: summarizeAction(rawText), raw: rawText }
      pendingActionsRef.current = [...pendingActionsRef.current, step]
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
      const content = parsed?.type === 'dashboard'
        ? (parsed.title || '')
        : (parsed?.text || parsed?.title || finalText || 'No response')
      const confirmPayload = parsed?.type === 'confirm' ? parsed : undefined
      const dashboardPayload = parsed?.type === 'dashboard' ? parsed as DashboardPayload : undefined

      const updatedMessages = messagesRef.current.map((m) => {
        if (m.id !== pendingMessageIdRef.current) return m
        return {
          ...m,
          type: messageType,
          text: content,
          confirm: confirmPayload,
          dashboard: dashboardPayload,
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
    if (!token) {
      setStatus('error')
      const errorMessage: ChatMessage = {
        id: safeId(),
        role: 'assistant',
        type: 'error',
        text: 'Missing auth token. Please log in again.',
        createdAt: new Date().toISOString(),
      }
      updateMessages((prev) => [...prev, errorMessage])
      return
    }

    const payload = {
      type: 'chat',
      message: text,
      token,
      orgId: localStorage.getItem('activeOrgId') || activeOrg?.id || undefined,
      sessionId: sessionIdRef.current || undefined,
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

  const [typewriterDoneIds, setTypewriterDoneIds] = useState<Set<string>>(new Set())

  const handleTypewriterDone = useCallback((id: string) => {
    setTypewriterDoneIds((prev) => {
      const next = new Set(prev)
      next.add(id)
      return next
    })
  }, [])

  const renderMessage = (msg: ChatMessage, idx: number) => {
    const isUser = msg.role === 'user'
    const bubbleClasses = isUser
      ? 'bg-gradient-to-r from-cyan-500 to-violet-500 text-white'
      : 'bg-white/90 dark:bg-gray-800/90 text-gray-900 dark:text-gray-100 border border-gray-200/70 dark:border-gray-700/70'

    const isLatestBot = !isUser && idx === messages.length - 1
    const shouldAnimate = isLatestBot && msg.text && !typewriterDoneIds.has(msg.id)

    return (
      <div key={msg.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
        <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm ${bubbleClasses}`}>
          {msg.actions && msg.actions.length > 0 && (
            <ThinkingSection steps={msg.actions} messageId={msg.id} isComplete={msg.text !== ''} />
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
          ) : msg.text ? (
            shouldAnimate ? (
              <TypewriterText
                html={renderMarkdown(msg.text)}
                onDone={() => handleTypewriterDone(msg.id)}
              />
            ) : (
              <div
                className="chat-markdown text-sm leading-relaxed"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}
              />
            )
          ) : !msg.dashboard ? (
            <span className="typing-dots flex gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </span>
          ) : null}

          {msg.dashboard && <DashboardView dashboard={msg.dashboard} />}
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
              placeholder="Ask about your data..."
              disabled={false}
              className="flex-1 rounded-xl border border-gray-200/70 dark:border-gray-700/70 bg-white/90 dark:bg-gray-900/60 px-3 py-2 text-sm text-gray-800 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
            />
            <button
              onClick={handleSubmit}
              disabled={!input.trim() || status === 'processing'}
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-violet-500 text-white shadow-md disabled:opacity-50"
              title="Send"
            >
              {status === 'processing' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
