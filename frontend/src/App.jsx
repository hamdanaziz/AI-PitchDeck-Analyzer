import { useState } from 'react'
import UploadZone from './components/UploadZone'
import ScoreCard from './components/ScoreCard'
import RedFlagList from './components/RedFlagList'
import MetricsSidebar from './components/MetricsSidebar'
import SlideMap from './components/SlideMap'
import BiasPanel from './components/BiasPanel'
import ExtractedMetrics from './components/ExtractedMetrics'

const STEPS = [
  'Validating pitch deck...',
  'Parsing slides and extracting data...',
  'Running financial engine checks...',
  'Scoring 8 sections...',
  'Detecting red flags...',
  'Generating AI investor feedback...',
  'Computing metrics...',
]

function ProgressScreen({ step }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="mb-10 text-center">
        <h1 className="font-display text-4xl text-fs-text tracking-tight mb-2">
          Flow<span className="text-fs-accent">State</span>
        </h1>
        <p className="text-fs-subtext">Analyzing your pitch deck</p>
      </div>
      <div className="w-full max-w-md">
        <div className="space-y-3">
          {STEPS.map((s, i) => (
            <div key={i} className={`flex items-center gap-3 py-2 px-4 rounded-lg transition-all duration-300
              ${i === step ? 'bg-fs-accent/10 border border-fs-accent/30' : ''}
              ${i < step ? 'opacity-40' : ''}
              ${i > step ? 'opacity-20' : ''}`}>
              <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0
                ${i < step ? 'bg-fs-green' : i === step ? 'bg-fs-accent animate-pulse-slow' : 'bg-fs-border'}`}>
                {i < step && (
                  <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </div>
              <span className={`text-sm ${i === step ? 'text-fs-text font-medium' : 'text-fs-subtext'}`}>{s}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function RejectedScreen({ reason, onReset }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-md text-center">
        <div className="text-5xl mb-6">🚫</div>
        <h2 className="text-xl font-semibold text-fs-text mb-3">Not a Pitch Deck</h2>
        <p className="text-fs-subtext text-sm leading-relaxed mb-8">{reason}</p>
        <button
          onClick={onReset}
          className="bg-fs-accent hover:bg-fs-accentHover text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          Try Another File
        </button>
      </div>
    </div>
  )
}

function ErrorScreen({ message, onReset }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      <div className="w-full max-w-md text-center">
        <div className="text-5xl mb-6">⚠️</div>
        <h2 className="text-xl font-semibold text-fs-text mb-3">Analysis Failed</h2>
        <p className="text-fs-subtext text-sm leading-relaxed mb-8 font-mono">{message}</p>
        <button
          onClick={onReset}
          className="bg-fs-accent hover:bg-fs-accentHover text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
        >
          Try Again
        </button>
      </div>
    </div>
  )
}

function ScoreRing({ score }) {
  const color = score >= 7 ? 'text-fs-green' : score >= 5 ? 'text-fs-yellow' : 'text-fs-red'
  const label = score >= 7 ? 'Strong' : score >= 5 ? 'Average' : 'Weak'
  return (
    <div className="text-center">
      <div className={`text-6xl font-bold font-mono ${color}`}>{score}</div>
      <div className="text-fs-muted text-xs mt-1">/ 10 &nbsp;·&nbsp; {label}</div>
    </div>
  )
}

function Dashboard({ data, onReset }) {
  const [tab, setTab] = useState('overview')

  return (
    <div className="min-h-screen bg-fs-bg">
      {/* Top bar */}
      <div className="sticky top-0 z-10 bg-fs-bg/90 backdrop-blur border-b border-fs-border px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <h1 className="font-display text-xl text-fs-text">
              Flow<span className="text-fs-accent">State</span>
            </h1>
            <span className="text-xs text-fs-muted hidden sm:block truncate max-w-xs">
              {data.filename}
            </span>
          </div>

          {/* Metrics strip */}
          <div className="hidden md:flex items-center gap-4 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-fs-accent" />
              <span className="text-fs-subtext">Citation Accuracy:</span>
              <span className="text-fs-text font-semibold">{data.metrics.citation_accuracy_rate}%</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${data.metrics.hallucinated_claims_detected === 0 ? 'bg-fs-green' : 'bg-fs-orange'}`} />
              <span className="text-fs-subtext">Hallucinations:</span>
              <span className="text-fs-text font-semibold">{data.metrics.hallucinated_claims_detected}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-fs-red" />
              <span className="text-fs-subtext">Red Flags:</span>
              <span className="text-fs-text font-semibold">{data.metrics.total_red_flags}</span>
            </div>
          </div>

          <button
            onClick={onReset}
            className="text-xs text-fs-subtext hover:text-fs-text border border-fs-border hover:border-fs-accent/50
              px-3 py-1.5 rounded-lg transition-colors flex-shrink-0"
          >
            New Analysis
          </button>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Summary header */}
        <div className="card p-6 mb-6">
          <div className="flex flex-col md:flex-row gap-6 items-start">
            <div className="flex-shrink-0">
              <ScoreRing score={data.scoring.weighted_score} />
            </div>
            <div className="flex-1">
              <p className="text-xs font-semibold text-fs-accent uppercase tracking-wider mb-2">
                Executive Summary
              </p>
              <p className="text-sm text-fs-text leading-relaxed">
                {data.feedback.executive_summary}
              </p>
              {data.feedback.hallucination_warnings?.length > 0 && (
                <div className="mt-3 p-2 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                  <p className="text-xs text-orange-400 font-semibold mb-1">⚠ AI Consistency Warnings</p>
                  {data.feedback.hallucination_warnings.map((w, i) => (
                    <p key={i} className="text-xs text-orange-300">{w}</p>
                  ))}
                </div>
              )}
            </div>
            <div className="flex-shrink-0 w-full md:w-48">
              <p className="text-xs font-semibold text-fs-subtext uppercase tracking-wider mb-3">
                Priority Actions
              </p>
              <ol className="space-y-2">
                {data.feedback.priority_actions.map((action, i) => (
                  <li key={i} className="flex gap-2 text-xs text-fs-subtext">
                    <span className="flex-shrink-0 w-4 h-4 bg-fs-accent/20 text-fs-accent rounded-full
                      flex items-center justify-center text-[10px] font-bold mt-0.5">{i + 1}</span>
                    <span className="leading-relaxed">{action}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>

        {/* Tab nav */}
        <div className="flex gap-1 mb-6 border-b border-fs-border">
          {['overview', 'red flags', 'financials', 'metrics', 'bias audit'].map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 text-xs font-medium capitalize transition-colors border-b-2 -mb-px
                ${tab === t
                  ? 'border-fs-accent text-fs-accent'
                  : 'border-transparent text-fs-subtext hover:text-fs-text'}`}
            >
              {t}
              {t === 'red flags' && data.red_flags.length > 0 && (
                <span className="ml-1.5 bg-fs-red/20 text-fs-red px-1.5 py-0.5 rounded-full text-[10px]">
                  {data.red_flags.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === 'overview' && (
          <div className="space-y-6">
            <ExtractedMetrics metrics={data.extracted_metrics} compact />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <ScoreCard scoring={data.scoring} />
              </div>
              <div className="space-y-4">
                <SlideMap slides={data.slide_map} />
              </div>
            </div>
          </div>
        )}

        {tab === 'red flags' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <RedFlagList flags={data.red_flags} />
            </div>
            <div>
              <MetricsSidebar metrics={data.metrics} financial={data.financial} />
            </div>
          </div>
        )}

        {tab === 'financials' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <div className="mb-6">
                <ExtractedMetrics metrics={data.extracted_metrics} />
              </div>
              <h2 className="text-sm font-semibold text-fs-subtext uppercase tracking-wider mb-4">
                Financial Checks ({data.financial.checks.length})
              </h2>
              <div className="space-y-2">
                {data.financial.checks.map((check, i) => (
                  <FinancialCheckCard key={i} check={check} />
                ))}
              </div>
            </div>
            <div>
              <MetricsSidebar metrics={data.metrics} financial={data.financial} />
            </div>
          </div>
        )}

        {tab === 'metrics' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <MetricsSidebar metrics={data.metrics} financial={data.financial} />
            <div className="card p-4">
              <h3 className="text-xs font-semibold text-fs-subtext uppercase tracking-wider mb-4">
                Validation Info
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-fs-subtext">Pages</span>
                  <span className="text-fs-text font-mono">{data.validation.page_count}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-fs-subtext">Deck Confidence</span>
                  <span className="text-fs-text font-mono">{data.validation.confidence}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-fs-subtext">Avg Words/Slide</span>
                  <span className="text-fs-text font-mono">{data.validation.avg_words_per_page}</span>
                </div>
                <div>
                  <p className="text-fs-subtext mb-2">Keywords Matched</p>
                  <div className="flex flex-wrap gap-1.5">
                    {data.validation.keyword_matches.map(kw => (
                      <span key={kw} className="text-xs bg-fs-accent/10 text-fs-accent border border-fs-accent/20 px-2 py-0.5 rounded-full">
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {tab === 'bias audit' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <BiasPanel bias={data.bias} />
            <div className="card p-4">
              <h3 className="text-xs font-semibold text-fs-subtext uppercase tracking-wider mb-4">
                What We Check For
              </h3>
              <div className="space-y-3 text-xs text-fs-subtext leading-relaxed">
                <p><span className="text-fs-text font-medium">Gender Bias</span> — We detect founder name gender signals and verify that no scoring criteria depend on demographic information.</p>
                <p><span className="text-fs-text font-medium">Geographic Bias</span> — We detect non-US market references and non-USD currencies, and flag where global benchmarks may not perfectly apply.</p>
                <p><span className="text-fs-text font-medium">Linguistic Bias</span> — We measure language complexity and confirm that semantic scoring evaluates meaning, not writing sophistication.</p>
                <p><span className="text-fs-text font-medium">Scoring Neutrality</span> — All 34 scoring criteria are verified to be content-based and demographic-free. None depend on founder identity, company origin, or language style.</p>
                <p className="pt-2 border-t border-fs-border text-fs-muted">AI (Groq/Llama) is only used for narrative feedback generation after all scoring is complete. Demographic signals are never passed to the AI prompt.</p>
              </div>
            </div>
          </div>
        )}
        
      </div>
    </div>
  )
}

function FinancialCheckCard({ check }) {
  const [expanded, setExpanded] = useState(false)
  const colors = {
    pass: { badge: 'bg-green-500/15 text-green-400 border-green-500/30', dot: 'bg-fs-green' },
    warn: { badge: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30', dot: 'bg-fs-yellow' },
    fail: { badge: 'bg-red-500/15 text-red-400 border-red-500/30', dot: 'bg-fs-red' },
    skipped: { badge: 'bg-gray-500/15 text-gray-400 border-gray-500/30', dot: 'bg-fs-muted' },
  }
  const c = colors[check.result] || colors.skipped

  return (
    <div className="card overflow-hidden">
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${c.dot}`} />
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${c.badge} flex-shrink-0`}>
          {check.result.toUpperCase()}
        </span>
        <span className="text-sm text-fs-text flex-1">{check.check_name}</span>
        {check.slide_number && (
          <span className="text-xs font-mono bg-fs-border text-fs-subtext px-2 py-0.5 rounded flex-shrink-0">
            Slide {check.slide_number}
          </span>
        )}
        <span className="text-fs-muted text-xs">{expanded ? '▲' : '▼'}</span>
      </div>
      {expanded && (
        <div className="px-4 pb-4 border-t border-fs-border pt-3 space-y-3 animate-fade-in">
          {check.evidence_text && (
            <div>
              <p className="text-xs font-semibold text-fs-subtext uppercase tracking-wide mb-1">Evidence</p>
              <p className="text-xs font-mono bg-fs-bg border border-fs-border rounded p-2 text-fs-text">
                "{check.evidence_text}"
              </p>
            </div>
          )}
          <div>
            <p className="text-xs font-semibold text-fs-subtext uppercase tracking-wide mb-1">Rule Applied</p>
            <p className="text-xs text-fs-subtext">{check.rule_applied}</p>
          </div>
          {check.detail && (
            <div>
              <p className="text-xs font-semibold text-fs-subtext uppercase tracking-wide mb-1">Detail</p>
              <p className="text-xs text-fs-text leading-relaxed">{check.detail}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [state, setState] = useState('upload') // upload | loading | rejected | error | done
  const [loadingStep, setLoadingStep] = useState(0)
  const [result, setResult] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [rejectionMsg, setRejectionMsg] = useState('')

  const handleUpload = async (file) => {
    setState('loading')
    setLoadingStep(0)

    // Simulate step progression while waiting for API
    const stepInterval = setInterval(() => {
      setLoadingStep(prev => {
        if (prev < STEPS.length - 2) return prev + 1
        return prev
      })
    }, 1800)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('http://localhost:8000/analyze', {
        method: 'POST',
        body: formData,
      })

      clearInterval(stepInterval)
      setLoadingStep(STEPS.length - 1)

      const data = await res.json()

      if (res.status === 422 && data.status === 'rejected') {
        setRejectionMsg(data.reason)
        setState('rejected')
        return
      }

      if (!res.ok) {
        setErrorMsg(data.detail || 'Unknown error from server.')
        setState('error')
        return
      }

      setResult(data)
      setState('done')
    } catch (err) {
      clearInterval(stepInterval)
      setErrorMsg(`Could not reach the backend. Is it running on port 8000?\n\n${err.message}`)
      setState('error')
    }
  }

  const reset = () => {
    setState('upload')
    setResult(null)
    setLoadingStep(0)
    setErrorMsg('')
    setRejectionMsg('')
  }

  if (state === 'upload') return <UploadZone onUpload={handleUpload} loading={false} />
  if (state === 'loading') return <ProgressScreen step={loadingStep} />
  if (state === 'rejected') return <RejectedScreen reason={rejectionMsg} onReset={reset} />
  if (state === 'error') return <ErrorScreen message={errorMsg} onReset={reset} />
  if (state === 'done') return <Dashboard data={result} onReset={reset} />
  return null
}
