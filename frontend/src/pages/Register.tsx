import { useState, useEffect, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Lock, User, Mail, UserCircle, AlertCircle, CheckCircle2 } from 'lucide-react'
import NexusLogo from '../components/NexusLogo'

function RegisterMatrixBg() {
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

const passwordChecks = [
  { label: 'At least 8 characters', test: (p: string) => p.length >= 8 },
  { label: 'Contains a number', test: (p: string) => /\d/.test(p) },
  { label: 'Contains uppercase letter', test: (p: string) => /[A-Z]/.test(p) },
]

export default function Register() {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [fullName, setFullName] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const passwordValid = passwordChecks.every(c => c.test(password))
  const passwordsMatch = password === confirmPassword && confirmPassword.length > 0

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!passwordValid) {
      setError('Password does not meet requirements')
      return
    }
    if (!passwordsMatch) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      await register({ username, email, password, full_name: fullName || undefined })
      navigate('/login', { state: { registered: true } })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-gray-950">
      <RegisterMatrixBg />

      <div className="max-w-md w-full mx-4 relative z-10">
        <div className="bg-gray-900/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-gray-700/50 p-8">
          <div className="text-center mb-6">
            <div className="flex justify-center mb-4">
              <NexusLogo size={56} />
            </div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-cyan-400 via-violet-400 to-cyan-400 bg-clip-text text-transparent">
              Create Account
            </h1>
            <p className="text-gray-400 mt-2 text-sm">Join NexusLeads to start sourcing leads</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-900/30 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm flex items-start gap-2">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Username</label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="pl-10 w-full px-4 py-2.5 bg-gray-800/60 border border-gray-600/50 rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all"
                  placeholder="Choose a username"
                  required
                  minLength={3}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 w-full px-4 py-2.5 bg-gray-800/60 border border-gray-600/50 rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all"
                  placeholder="you@company.com"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">
                Full Name <span className="text-gray-500 font-normal">(optional)</span>
              </label>
              <div className="relative">
                <UserCircle className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="pl-10 w-full px-4 py-2.5 bg-gray-800/60 border border-gray-600/50 rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all"
                  placeholder="John Doe"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Password</label>
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
              {password.length > 0 && (
                <div className="mt-2 space-y-1">
                  {passwordChecks.map((check) => (
                    <div key={check.label} className="flex items-center gap-1.5 text-xs">
                      {check.test(password) ? (
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
                      ) : (
                        <AlertCircle className="w-3.5 h-3.5 text-gray-500" />
                      )}
                      <span className={check.test(password) ? 'text-green-400' : 'text-gray-500'}>
                        {check.label}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1.5">Confirm Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-500" />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={`pl-10 w-full px-4 py-2.5 bg-gray-800/60 border rounded-lg text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 transition-all ${
                    confirmPassword.length > 0
                      ? passwordsMatch
                        ? 'border-green-500/50'
                        : 'border-red-500/50'
                      : 'border-gray-600/50'
                  }`}
                  placeholder="••••••••"
                  required
                />
              </div>
              {confirmPassword.length > 0 && !passwordsMatch && (
                <p className="mt-1 text-xs text-red-400">Passwords do not match</p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || !passwordValid || !passwordsMatch}
              className="w-full py-2.5 px-4 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white shadow-lg shadow-cyan-500/20"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-400">
              Already have an account?{' '}
              <Link to="/login" className="text-cyan-400 hover:text-cyan-300 font-medium transition-colors">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
