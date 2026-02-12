import { useEffect, useRef } from 'react'
import { useTheme } from '../contexts/ThemeContext'

export default function MatrixBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { theme } = useTheme()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationId: number

    const resize = () => {
      canvas.width = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
    }
    resize()
    window.addEventListener('resize', resize)

    const chars = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF<>/{}[]|'
    const fontSize = 14
    const columns = Math.floor(canvas.width / fontSize)
    const drops: number[] = Array(columns).fill(1)

    const draw = () => {
      const isDark = theme === 'dark'
      // Fade effect — slower fade in light mode so characters linger longer
      ctx.fillStyle = isDark ? 'rgba(3, 7, 18, 0.04)' : 'rgba(249, 250, 251, 0.03)'
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      ctx.font = `${fontSize}px monospace`

      for (let i = 0; i < drops.length; i++) {
        const char = chars[Math.floor(Math.random() * chars.length)]
        const x = i * fontSize
        const y = drops[i] * fontSize

        // Light mode: use a deeper indigo/violet at higher opacity so it's clearly visible
        const alpha = isDark ? 0.08 + Math.random() * 0.06 : 0.12 + Math.random() * 0.08
        ctx.fillStyle = isDark
          ? `rgba(34, 197, 94, ${alpha})`    // green for dark
          : `rgba(99, 102, 241, ${alpha})`   // indigo for light

        ctx.fillText(char, x, y)

        if (y > canvas.height && Math.random() > 0.975) {
          drops[i] = 0
        }
        drops[i]++
      }

      animationId = requestAnimationFrame(draw)
    }

    // Initial clear
    ctx.fillStyle = theme === 'dark' ? 'rgba(3, 7, 18, 1)' : 'rgba(249, 250, 251, 1)'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    draw()

    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(animationId)
    }
  }, [theme])

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 0 }}
    />
  )
}
