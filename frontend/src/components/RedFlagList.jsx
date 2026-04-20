import { useState } from 'react'

const severityConfig = {
  Critical: { cls: 'badge-critical', dot: 'bg-red-400', order: 0 },
  High:     { cls: 'badge-high',     dot: 'bg-orange-400', order: 1 },
  Medium:   { cls: 'badge-medium',   dot: 'bg-yellow-400', order: 2 },
  Low:      { cls: 'badge-low',      dot: 'bg-blue-400', order: 3 },
}

function FlagCard({ flag, index }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = severityConfig[flag.severity] || severityConfig.Medium

  return (
    <div className="card overflow-hidden transition-all duration-200 animate-slide-up"
      style={{ animationDelay: `${index * 40}ms` }}>
      {/* Header row */}
      <div
        className="flex items-start gap-3 p-4 cursor-pointer hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${cfg.dot}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cfg.cls}`}>
              {flag.severity}
            </span>
            {flag.slide_number && (
              <span className="text-xs font-mono bg-fs-border text-fs-subtext px-2 py-0.5 rounded">
                Slide {flag.slide_number}
              </span>
            )}
            <span className="text-xs text-fs-muted">{flag.source_engine}</span>
          </div>
          <p className="text-sm font-medium text-fs-text">{flag.title}</p>
        </div>
        <span className="text-fs-muted text-xs flex-shrink-0 mt-1">
          {expanded ? '▲' : '▼'}
        </span>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-fs-border animate-fade-in space-y-4 pt-4">
          {/* Evidence */}
          {flag.evidence_quote && (
            <div>
              <p className="text-xs font-semibold text-fs-subtext uppercase tracking-wide mb-1.5">
                Evidence from Deck
              </p>
              <div className="bg-fs-bg border border-fs-border rounded-lg p-3 font-mono text-xs
                text-fs-text leading-relaxed">
                "{flag.evidence_quote}"
              </div>
            </div>
          )}

          {/* Rule */}
          <div>
            <p className="text-xs font-semibold text-fs-subtext uppercase tracking-wide mb-1.5">
              Rule Violated
            </p>
            <p className="text-xs text-fs-subtext">{flag.rule_violated}</p>
          </div>

          {/* Explanation */}
          <div>
            <p className="text-xs font-semibold text-fs-subtext uppercase tracking-wide mb-1.5">
              Why This Is a Problem
            </p>
            <p className="text-xs text-fs-text leading-relaxed">{flag.explanation}</p>
          </div>

          {/* Benchmark */}
          {flag.benchmark && (
            <div className="bg-fs-accent/5 border border-fs-accent/20 rounded-lg p-3">
              <p className="text-xs font-semibold text-fs-accent mb-1">📊 Industry Benchmark</p>
              <p className="text-xs text-fs-subtext leading-relaxed">{flag.benchmark}</p>
            </div>
          )}

          {/* Fix */}
          <div className="bg-green-500/5 border border-green-500/20 rounded-lg p-3">
            <p className="text-xs font-semibold text-fs-green mb-1">✦ How to Fix</p>
            <p className="text-xs text-fs-subtext leading-relaxed">{flag.fix_suggestion}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default function RedFlagList({ flags }) {
  if (!flags?.length) {
    return (
      <div>
        <h2 className="text-sm font-semibold text-fs-subtext uppercase tracking-wider mb-4">
          Red Flags
        </h2>
        <div className="card p-8 text-center">
          <p className="text-4xl mb-3">✅</p>
          <p className="text-fs-text font-medium">No red flags detected</p>
          <p className="text-xs text-fs-subtext mt-1">
            All financial checks and section scores passed.
          </p>
        </div>
      </div>
    )
  }

  const counts = { Critical: 0, High: 0, Medium: 0, Low: 0 }
  flags.forEach(f => { if (counts[f.severity] !== undefined) counts[f.severity]++ })

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-fs-subtext uppercase tracking-wider">
          Red Flags ({flags.length})
        </h2>
        <div className="flex gap-2">
          {Object.entries(counts).map(([sev, count]) =>
            count > 0 ? (
              <span key={sev} className={`text-xs px-2 py-0.5 rounded-full font-medium
                ${severityConfig[sev]?.cls}`}>
                {count} {sev}
              </span>
            ) : null
          )}
        </div>
      </div>
      <div className="space-y-2">
        {flags.map((flag, i) => (
          <FlagCard key={i} flag={flag} index={i} />
        ))}
      </div>
    </div>
  )
}
