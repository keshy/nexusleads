import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import NexusLogo from '../components/NexusLogo'
import {
  Zap, Shield, Search, Users, Star, GitBranch, ArrowRight, Check,
  ChevronDown, Sparkles, Target, BarChart3, Lock, Globe,
  Brain, Layers, TrendingUp, ExternalLink, Blocks
} from 'lucide-react'

/* ─── Matrix Background (dark only, subtle) ─── */
function LandingMatrixBg() {
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
        const alpha = 0.04 + Math.random() * 0.04
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

/* ─── Smooth scroll helper ─── */
function scrollTo(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })
}

/* ─── Main Landing Page ─── */
export default function Landing() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()
  useEffect(() => {
    if (isAuthenticated) navigate('/app')
  }, [isAuthenticated, navigate])

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 overflow-x-hidden">
      {/* ═══════ NAV ═══════ */}
      <nav className="fixed top-0 w-full z-50 bg-gray-950/80 backdrop-blur-xl border-b border-gray-800/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => scrollTo('hero')}>
            <NexusLogo size={32} />
            <span className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">
              NexusLeads
            </span>
          </div>

          <div className="hidden md:flex items-center gap-8 text-sm text-gray-400">
            <button onClick={() => scrollTo('problem')} className="hover:text-white transition-colors">Problem</button>
            <button onClick={() => scrollTo('approach')} className="hover:text-white transition-colors">Approach</button>
            <button onClick={() => scrollTo('features')} className="hover:text-white transition-colors">Features</button>
            <button onClick={() => scrollTo('pricing')} className="hover:text-white transition-colors">Pricing</button>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/login')}
              className="px-4 py-2 text-sm text-gray-300 hover:text-white transition-colors"
            >
              Log in
            </button>
            <button
              onClick={() => navigate('/login')}
              className="px-5 py-2 text-sm font-medium rounded-lg bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white transition-all shadow-lg shadow-cyan-500/20"
            >
              Get Started Free
            </button>
          </div>
        </div>
      </nav>

      {/* ═══════ HERO ═══════ */}
      <section id="hero" className="relative min-h-screen flex items-center justify-center pt-16">
        <LandingMatrixBg />
        <div className="relative z-10 max-w-5xl mx-auto px-4 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 rounded-full border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 text-sm">
            <Sparkles className="w-4 h-4" />
            Intelligence-driven lead discovery from open source
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-tight mb-6">
            <span className="bg-gradient-to-r from-white via-gray-200 to-gray-400 bg-clip-text text-transparent">
              Turn GitHub Activity
            </span>
            <br />
            <span className="bg-gradient-to-r from-cyan-400 via-violet-400 to-pink-400 bg-clip-text text-transparent">
              Into Qualified Leads
            </span>
          </h1>

          <p className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            NexusLeads analyzes repository contributors and stargazers, enriches their profiles
            with social and professional data, and surfaces decision-makers who are already
            engaged with technology in your space.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <button
              onClick={() => navigate('/login')}
              className="px-8 py-3.5 text-base font-semibold rounded-xl bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white transition-all shadow-xl shadow-cyan-500/25 flex items-center gap-2"
            >
              Start Free <ArrowRight className="w-5 h-5" />
            </button>
            <button
              onClick={() => scrollTo('approach')}
              className="px-8 py-3.5 text-base font-semibold rounded-xl border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white transition-all flex items-center gap-2"
            >
              See How It Works <ChevronDown className="w-5 h-5" />
            </button>
          </div>

          {/* Stats row */}
          <div className="grid grid-cols-3 gap-8 max-w-lg mx-auto">
            {[
              { value: '10x', label: 'Faster than manual sourcing' },
              { value: '87%', label: 'Lead accuracy rate' },
              { value: '< 5min', label: 'Time to first leads' },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">
                  {stat.value}
                </div>
                <div className="text-xs text-gray-500 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <ChevronDown className="w-6 h-6 text-gray-600" />
        </div>
      </section>

      {/* ═══════ PROBLEM SPACE ═══════ */}
      <section id="problem" className="relative py-24 sm:py-32">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <span className="text-sm font-medium text-red-400 uppercase tracking-wider">The Problem</span>
            <h2 className="text-3xl sm:text-4xl font-bold mt-3 mb-4">
              PLG Lead Sourcing Is <span className="text-red-400">Broken</span>
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto text-lg">
              Product-led growth companies sit on a goldmine of intent signals, but extracting
              actionable leads from open-source activity is painful.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                icon: Search,
                title: 'Manual Research Hell',
                desc: 'Sales teams spend hours clicking through GitHub profiles, LinkedIn, and company pages trying to identify who matters.',
                color: 'text-red-400',
                bg: 'bg-red-500/10 border-red-500/20',
              },
              {
                icon: Users,
                title: 'No Signal From Noise',
                desc: 'Thousands of contributors and stargazers, but no way to tell a VP of Engineering from a hobbyist student.',
                color: 'text-orange-400',
                bg: 'bg-orange-500/10 border-orange-500/20',
              },
              {
                icon: Layers,
                title: 'Fragmented Data',
                desc: 'GitHub, LinkedIn, company databases, enrichment APIs - stitching together a complete lead profile requires multiple tools and manual effort.',
                color: 'text-yellow-400',
                bg: 'bg-yellow-500/10 border-yellow-500/20',
              },
            ].map((item) => (
              <div
                key={item.title}
                className={`rounded-2xl border ${item.bg} p-6 sm:p-8`}
              >
                <item.icon className={`w-10 h-10 ${item.color} mb-4`} />
                <h3 className="text-lg font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ OUR APPROACH ═══════ */}
      <section id="approach" className="relative py-24 sm:py-32 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <span className="text-sm font-medium text-cyan-400 uppercase tracking-wider">Our Approach</span>
            <h2 className="text-3xl sm:text-4xl font-bold mt-3 mb-4">
              From Repository to <span className="bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">Revenue Pipeline</span>
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto text-lg">
              NexusLeads automates the entire journey from discovering open-source activity
              to delivering scored, classified, sales-ready leads.
            </p>
          </div>

          <div className="grid md:grid-cols-4 gap-6">
            {[
              {
                step: '01',
                icon: GitBranch,
                title: 'Connect Repos',
                desc: 'Point us at any GitHub repository - yours or competitors. We track contributors and stargazers.',
                color: 'from-cyan-500 to-cyan-600',
              },
              {
                step: '02',
                icon: Brain,
                title: 'AI Enrichment',
                desc: 'We search the web, extract LinkedIn profiles, company info, and professional context automatically.',
                color: 'from-violet-500 to-violet-600',
              },
              {
                step: '03',
                icon: Target,
                title: 'Smart Classification',
                desc: 'AI classifies each person as Decision Maker, High Impact, Key Contributor, or Contributor with reasoning.',
                color: 'from-pink-500 to-pink-600',
              },
              {
                step: '04',
                icon: TrendingUp,
                title: 'Score & Prioritize',
                desc: 'Multi-dimensional scoring on activity, influence, position, and engagement surfaces your best leads first.',
                color: 'from-amber-500 to-amber-600',
              },
            ].map((item) => (
              <div key={item.step} className="relative group">
                <div className="rounded-2xl border border-gray-800 bg-gray-900/80 p-6 h-full hover:border-gray-700 transition-colors">
                  <div className={`inline-flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br ${item.color} text-white text-sm font-bold mb-4`}>
                    {item.step}
                  </div>
                  <item.icon className="w-6 h-6 text-gray-400 mb-3" />
                  <h3 className="text-base font-semibold text-white mb-2">{item.title}</h3>
                  <p className="text-gray-500 text-sm leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ FEATURES ═══════ */}
      <section id="features" className="relative py-24 sm:py-32">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <span className="text-sm font-medium text-violet-400 uppercase tracking-wider">Features</span>
            <h2 className="text-3xl sm:text-4xl font-bold mt-3 mb-4">
              Everything You Need to <span className="bg-gradient-to-r from-violet-400 to-pink-400 bg-clip-text text-transparent">Source Smarter</span>
            </h2>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              { icon: Star, title: 'Stargazer Analysis', desc: 'Discover who is watching your repo and surface high-value prospects from your star list.' },
              { icon: GitBranch, title: 'Contributor Intelligence', desc: 'Analyze commit patterns, PR activity, and code reviews to identify engaged technical leaders.' },
              { icon: Search, title: 'Auto Enrichment', desc: 'Automatically find LinkedIn profiles, job titles, companies, and industries for every lead.' },
              { icon: Brain, title: 'AI Classification', desc: 'GPT-powered classification with transparent reasoning explains why each lead matters.' },
              { icon: BarChart3, title: 'Multi-Signal Scoring', desc: 'Activity, influence, position, and engagement scores combine into a single priority ranking.' },
              { icon: Shield, title: 'Competitor Tracking', desc: 'Monitor competitor repos to find their most engaged users - your next potential customers.' },
              { icon: Zap, title: 'Real-Time Jobs', desc: 'Live progress tracking on every sourcing and enrichment job with step-by-step visibility.' },
              { icon: Globe, title: 'Similar Repo Discovery', desc: 'Find related repositories in your space and automatically source their contributor networks.' },
              { icon: Lock, title: 'Self-Hosted Option', desc: 'Deploy on your own infrastructure for complete data control and compliance.' },
              { icon: Blocks, title: 'Sales Stack Integrations', desc: 'Push enriched leads to Clay, Salesforce, HubSpot, and more. One click from lead to pipeline.' },
            ].map((item) => (
              <div
                key={item.title}
                className="rounded-xl border border-gray-800 bg-gray-900/50 p-6 hover:border-gray-700 hover:bg-gray-900/80 transition-all group"
              >
                <item.icon className="w-8 h-8 text-gray-500 group-hover:text-cyan-400 transition-colors mb-4" />
                <h3 className="text-base font-semibold text-white mb-2">{item.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ INTEGRATIONS ═══════ */}
      <section className="relative py-24 sm:py-32 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <span className="text-sm font-medium text-cyan-400 uppercase tracking-wider">Integrations</span>
            <h2 className="text-3xl sm:text-4xl font-bold mt-3 mb-4">
              From Insight to <span className="bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">Action</span>
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto text-lg">
              NexusLeads doesn't just find leads — it delivers them where your sellers already work.
              One click to push enriched, scored, classified leads into your sales stack.
            </p>
          </div>

          <div className="flex items-center justify-center gap-3 mb-10">
            <span className="text-sm text-gray-400">Source</span>
            <ArrowRight className="w-4 h-4 text-gray-600" />
            <span className="text-sm text-gray-400">Enrich</span>
            <ArrowRight className="w-4 h-4 text-gray-600" />
            <span className="text-sm text-gray-400">Score</span>
            <ArrowRight className="w-4 h-4 text-cyan-400" />
            <span className="text-sm font-semibold text-cyan-400">ACT</span>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { name: 'Clay', status: 'Live', color: 'border-green-500/40 bg-green-950/20' },
              { name: 'Salesforce', status: 'Coming Soon', color: 'border-gray-700 bg-gray-900/50' },
              { name: 'HubSpot', status: 'Coming Soon', color: 'border-gray-700 bg-gray-900/50' },
              { name: 'Outreach', status: 'Coming Soon', color: 'border-gray-700 bg-gray-900/50' },
            ].map((item) => (
              <div key={item.name} className={`rounded-xl border ${item.color} p-5 text-center`}>
                <div className="text-lg font-semibold text-white mb-1">{item.name}</div>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                  item.status === 'Live'
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-gray-700/50 text-gray-500'
                }`}>
                  {item.status === 'Live' ? '✅ ' : ''}{item.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════ PRICING ═══════ */}
      <section id="pricing" className="relative py-24 sm:py-32 bg-gray-900/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <span className="text-sm font-medium text-green-400 uppercase tracking-wider">Pricing</span>
            <h2 className="text-3xl sm:text-4xl font-bold mt-3 mb-4">
              Start Free, Scale as You Grow
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto text-lg">
              No credit card required. Upgrade when you need more power.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
            {/* Free Tier */}
            <div className="rounded-2xl border border-gray-800 bg-gray-900/80 p-8 flex flex-col">
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-white">Starter</h3>
                <p className="text-gray-500 text-sm mt-1">For individuals exploring PLG leads</p>
              </div>
              <div className="mb-6">
                <span className="text-4xl font-bold text-white">$0</span>
                <span className="text-gray-500 text-sm ml-1">/month</span>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {[
                  '2 projects',
                  '3 repositories per project',
                  '50 enrichment searches / month',
                  'Contributor + stargazer analysis',
                  'AI classification & scoring',
                  'Basic filters & dashboard',
                  'Community support',
                ].map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-400">
                    <Check className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => navigate('/login')}
                className="w-full py-3 rounded-xl border border-gray-700 text-gray-300 hover:border-gray-500 hover:text-white font-medium transition-all"
              >
                Get Started Free
              </button>
            </div>

            {/* Pro Tier */}
            <div className="rounded-2xl border-2 border-cyan-500/50 bg-gray-900/80 p-8 flex flex-col relative">
              <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-cyan-600 to-violet-600 text-xs font-semibold text-white">
                Most Popular
              </div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-white">Pro</h3>
                <p className="text-gray-500 text-sm mt-1">For growing teams with serious pipeline goals</p>
              </div>
              <div className="mb-6">
                <span className="text-4xl font-bold text-white">$79</span>
                <span className="text-gray-500 text-sm ml-1">/month</span>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {[
                  'Unlimited projects',
                  'Unlimited repositories',
                  '1,000 enrichment searches / month',
                  'Everything in Starter',
                  'LinkedIn deep enrichment',
                  'Multiple enrichment sources',
                  'Advanced filters & export',
                  'CRM integrations (Salesforce, HubSpot)',
                  'Priority email support',
                ].map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-300">
                    <Check className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => navigate('/login')}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white font-medium transition-all shadow-lg shadow-cyan-500/20"
              >
                Start Pro Trial
              </button>
            </div>

            {/* Enterprise Tier */}
            <div className="rounded-2xl border border-gray-800 bg-gray-900/80 p-8 flex flex-col">
              <div className="mb-6">
                <h3 className="text-lg font-semibold text-white">Enterprise</h3>
                <p className="text-gray-500 text-sm mt-1">For organizations needing full control</p>
              </div>
              <div className="mb-6">
                <span className="text-4xl font-bold text-white">Custom</span>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {[
                  'Everything in Pro',
                  'Unlimited enrichment searches',
                  'Custom on-premise deployment',
                  'Internal data source connectors',
                  'Private GitHub Enterprise support',
                  'SSO / SAML authentication',
                  'Custom AI model fine-tuning',
                  'Dedicated account manager',
                  'SLA & priority support',
                  'Custom integrations & API access',
                ].map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-400">
                    <Check className="w-4 h-4 text-violet-400 mt-0.5 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => window.location.href = 'mailto:sales@nexusleads.io'}
                className="w-full py-3 rounded-xl border border-gray-700 text-gray-300 hover:border-violet-500/50 hover:text-white font-medium transition-all flex items-center justify-center gap-2"
              >
                Contact Sales <ExternalLink className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ═══════ CTA ═══════ */}
      <section className="relative py-24 sm:py-32">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Ready to Turn Open Source Into Your
            <span className="bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent"> Growth Engine</span>?
          </h2>
          <p className="text-gray-400 text-lg mb-8">
            Join teams already using NexusLeads to discover high-value leads hiding in plain sight on GitHub.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => navigate('/login')}
              className="px-8 py-3.5 text-base font-semibold rounded-xl bg-gradient-to-r from-cyan-600 to-violet-600 hover:from-cyan-500 hover:to-violet-500 text-white transition-all shadow-xl shadow-cyan-500/25 flex items-center gap-2"
            >
              Get Started Free <ArrowRight className="w-5 h-5" />
            </button>
            <button
              onClick={() => scrollTo('pricing')}
              className="px-8 py-3.5 text-base font-semibold rounded-xl border border-gray-700 hover:border-gray-500 text-gray-300 hover:text-white transition-all"
            >
              Compare Plans
            </button>
          </div>
        </div>
      </section>

      {/* ═══════ FOOTER ═══════ */}
      <footer className="border-t border-gray-800 py-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <NexusLogo size={24} />
            <span className="text-sm font-semibold bg-gradient-to-r from-cyan-400 to-violet-400 bg-clip-text text-transparent">
              NexusLeads
            </span>
          </div>
          <p className="text-xs text-gray-600">&copy; {new Date().getFullYear()} NexusLeads. All rights reserved.</p>
          <div className="flex items-center gap-6 text-xs text-gray-500">
            <a href="#" className="hover:text-gray-300 transition-colors">Privacy</a>
            <a href="#" className="hover:text-gray-300 transition-colors">Terms</a>
            <a href="#" className="hover:text-gray-300 transition-colors">Docs</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
