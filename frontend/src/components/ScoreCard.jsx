import { useState } from 'react'

const scoreColor = (score) => {
  if (score >= 7) return { text: 'text-fs-green', bar: 'bg-fs-green', bg: 'bg-green-500/10', border: 'border-green-500/20' }
  if (score >= 5) return { text: 'text-fs-yellow', bar: 'bg-fs-yellow', bg: 'bg-yellow-500/10', border: 'border-yellow-500/20' }
  return { text: 'text-fs-red', bar: 'bg-fs-red', bg: 'bg-red-500/10', border: 'border-red-500/20' }
}

const sectionIcons = {
  Problem: '🎯', Solution: '⚡', 'Market Size': '🌍',
  'Business Model': '💰', Traction: '📈', Team: '👥',
  Financials: '📊', Ask: '🤝',
}

function SectionCard({ section }) {
  const [expanded, setExpanded] = useState(false)
  const c = scoreColor(section.score)

  return (
    <div
      className={`card border ${c.border} ${c.bg} cursor-pointer transition-all duration-200
        hover:scale-[1.01] hover:shadow-lg`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">{sectionIcons[section.section] || '📌'}</span>
            <span className="font-medium text-fs-text text-sm">{section.section}</span>
          </div>
          <div className="text-right">
            <span className={`text-2xl font-bold font-mono ${c.text}`}>{section.score}</span>
            <span className="text-fs-muted text-xs">/10</span>
          </div>
        </div>

        {/* Score bar */}
        <div className="h-1.5 bg-fs-border rounded-full overflow-hidden mb-3">
          <div
            className={`h-full ${c.bar} rounded-full transition-all duration-700`}
            style={{ width: `${section.score * 10}%` }}
          />
        </div>

        <p className="text-xs text-fs-subtext leading-relaxed">{section.summary}</p>

        <div className="mt-2 flex items-center gap-1 text-xs text-fs-muted">
          <span>{expanded ? '▲' : '▼'}</span>
          <span>{expanded ? 'Collapse' : 'Expand investor feedback'}</span>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t border-fs-border/50 mt-1 pt-3 animate-fade-in">
          {/* Criteria met / missed */}
          {section.criteria_met?.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-fs-green mb-1.5">✓ Criteria Met</p>
              <div className="flex flex-wrap gap-1.5">
                {section.criteria_met.map(c => (
                  <span key={c} className="text-xs bg-green-500/10 text-green-400 border border-green-500/20
                    px-2 py-0.5 rounded-full">{c}</span>
                ))}
              </div>
            </div>
          )}
          {section.criteria_missed?.length > 0 && (
            <div className="mb-3">
              <p className="text-xs font-medium text-fs-red mb-1.5">✗ Missing</p>
              <div className="flex flex-wrap gap-1.5">
                {section.criteria_missed.map(c => (
                  <span key={c} className="text-xs bg-red-500/10 text-red-400 border border-red-500/20
                    px-2 py-0.5 rounded-full">{c}</span>
                ))}
              </div>
            </div>
          )}

          {/* AI narrative */}
          {section.narrative && (
            <div className="mt-3 pt-3 border-t border-fs-border/50">
              <p className="text-xs font-medium text-fs-accent mb-2">💬 Investor Feedback</p>
              <p className="text-xs text-fs-subtext leading-relaxed">{section.narrative}</p>
            </div>
          )}

          {/* Slide numbers */}
          {section.slide_numbers?.length > 0 && (
            <div className="mt-3 flex items-center gap-1.5">
              <span className="text-xs text-fs-muted">Found on:</span>
              {section.slide_numbers.map(n => (
                <span key={n} className="text-xs font-mono bg-fs-border text-fs-subtext
                  px-1.5 py-0.5 rounded">Slide {n}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function ScoreCard({ scoring }) {
  return (
    <div>
      <h2 className="text-sm font-semibold text-fs-subtext uppercase tracking-wider mb-4">
        Section Breakdown
      </h2>
      <div className="grid grid-cols-2 gap-3">
        {scoring.sections.map(section => (
          <SectionCard key={section.section} section={section} />
        ))}
      </div>
    </div>
  )
}
