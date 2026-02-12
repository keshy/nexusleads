import { useState, useEffect, useRef } from 'react'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Lock, User, CheckCircle2 } from 'lucide-react'
import NexusLogo from '../components/NexusLogo'

function LoginMatrixBg() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationId: number
    const resize = () => { canvas.width = canvas.offsetWidth; canvas.height = canvas.offsetHeight }
    resize()
    window.addEventListener('resize', resize)

    const chars = 'アイウエオカキクケコ0123456789ABCDEF<>/{}[]|'
    const fontSize = 14
    const columns = Math.floor(canvas.width / fontSize)
    const drops: number[] = Array(columns).fill(1)

    ctx.fillStyle = 'rgba(3, 7, 18, 1)'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    const draw = () => {
      ctx.fillStyle = 'rgba(3, 7, 18, 0.04)'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.font = `${fontSize}px monospace`
      for (let i = 0; i < drops.length; i++) {
        const char = chars[Math.floor(Math.random() * chars.length)]
        const alpha = 0.06 + Math.random() * 0.06
        ctx.fillStyle = `rgba(6, 182, 212, ${alpha})`
        ctx.fillText(char, i * fontSize, drops[i] * fontSize)
        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) drops[i] = 0
        drops[i]++
      }
      animationId = requestAnimationFrame(draw)
    }
    draw()
    return () => { window.removeEventListener('resize', resize); cancelAnimationFrame(animationId) }
  }, [])

  return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
}

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const justRegistered = (location.state as any)?.registered === true

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(username, password)
      navigate('/app')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-gray-950">
      <LoginMatrixBg />

      <div className="max-w-md w-full mx-4 relative z-10">
        <div className="bg-gray-900/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-gray-700/50 p-8">
          <div className="text-center mb-8">
            <div className="flex justify-center mb-4">
              <NexusLogo size={56} />
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
              NexusLeads
            </h1>
            <p className="text-gray-400 mt-2 text-sm">Intelligence-driven lead discovery</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {justRegistered && (
              <div className="bg-green-900/30 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                Account created successfully! Sign in to get started.
              </div>
            )}
            {error && (
              <div className="bg-red-900/30 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Username
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10 w-full px-4 py-2.5 bg-gray-800/60 border border-gray-600/50 rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all"
                  placeholder="Enter your username"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 w-full px-4 py-2.5 bg-gray-800/60 border border-gray-600/50 rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white shadow-lg shadow-cyan-500/20"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-400">
              Don't have an account?{' '}
              <Link to="/register" className="text-cyan-400 hover:text-cyan-300 font-medium transition-colors">
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
