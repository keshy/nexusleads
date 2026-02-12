import { useState, useRef, useLayoutEffect } from 'react'
import { createPortal } from 'react-dom'
import { Star } from 'lucide-react'

interface ScoreBreakdown {
  overall_score: number
  activity_score: number
  influence_score: number
  position_score: number
  engagement_score: number
}

interface ScoreTooltipProps {
  scores: ScoreBreakdown
  colorClass: string
  size?: 'sm' | 'md'
}

const scoreDescriptions: Record<string, string> = {
  activity: 'Commit frequency, recency, PRs & issues',
  influence: 'GitHub followers & public repos',
  position: 'Seniority level (C-suite, Director, etc.)',
  engagement: 'Maintainer status & code reviews',
}

export default function ScoreTooltip({ scores, colorClass, size = 'sm' }: ScoreTooltipProps) {
  const [show, setShow] = useState(false)
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const triggerRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)
  const timeout = useRef<ReturnType<typeof setTimeout>>()

  const enter = () => { clearTimeout(timeout.current); setShow(true) }
  const leave = () => { timeout.current = setTimeout(() => setShow(false), 150) }

  useLayoutEffect(() => {
    if (show && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect()
      setPos({
        top: rect.top + window.scrollY - 8,
        left: rect.left + rect.width / 2 + window.scrollX,
      })
    }
  }, [show])

  const starSize = size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'
  const textSize = size === 'sm' ? 'text-sm' : 'text-sm'

  const bars = [
    { label: 'Activity', value: scores.activity_score, desc: scoreDescriptions.activity, color: 'bg-blue-500' },
    { label: 'Influence', value: scores.influence_score, desc: scoreDescriptions.influence, color: 'bg-purple-500' },
    { label: 'Position', value: scores.position_score, desc: scoreDescriptions.position, color: 'bg-amber-500' },
    { label: 'Engagement', value: scores.engagement_score, desc: scoreDescriptions.engagement, color: 'bg-green-500' },
  ]

  return (
    <>
      <div ref={triggerRef} className="inline-flex items-center" onMouseEnter={enter} onMouseLeave={leave}>
        <Star className={`${starSize} mr-0.5 ${colorClass} cursor-help`} />
        <span className={`${textSize} font-bold ${colorClass} cursor-help`}>
          {scores.overall_score.toFixed(0)}
        </span>
      </div>

      {show && createPortal(
        <div
          ref={tooltipRef}
          className="fixed z-[99999] w-64 bg-white dark:bg-gray-800 rounded-lg shadow-2xl border border-gray-200 dark:border-gray-600 p-3"
          style={{ top: pos.top, left: pos.left, transform: 'translate(-50%, -100%)' }}
          onMouseEnter={enter}
          onMouseLeave={leave}
        >
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px">
            <div className="w-2.5 h-2.5 bg-white dark:bg-gray-800 border-r border-b border-gray-200 dark:border-gray-600 rotate-45 -translate-y-1.5" />
          </div>

          <div className="text-xs font-semibold text-gray-900 dark:text-gray-100 mb-2 flex items-center justify-between">
            <span>Lead Score Breakdown</span>
            <span className={`text-base font-bold ${colorClass}`}>{scores.overall_score.toFixed(1)}</span>
          </div>
          <p className="text-[10px] text-gray-500 dark:text-gray-400 mb-2.5 leading-snug">
            Weighted composite of activity, influence, seniority, and engagement signals.
          </p>

          <div className="space-y-2">
            {bars.map((bar) => (
              <div key={bar.label}>
                <div className="flex items-center justify-between text-[11px] mb-0.5">
                  <span className="text-gray-700 dark:text-gray-300 font-medium">{bar.label}</span>
                  <span className="text-gray-500 dark:text-gray-400">{bar.value.toFixed(0)}/100</span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                  <div className={`${bar.color} h-1.5 rounded-full transition-all`} style={{ width: `${Math.min(bar.value, 100)}%` }} />
                </div>
                <p className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">{bar.desc}</p>
              </div>
            ))}
          </div>
        </div>,
        document.body
      )}
    </>
  )
}
