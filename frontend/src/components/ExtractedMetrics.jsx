const statusStyles = {
  found: 'bg-green-500/15 text-green-400 border-green-500/30',
  missing: 'bg-red-500/15 text-red-400 border-red-500/30',
}

const coreKeys = new Set([
  'funding_ask',
  'valuation',
  'tam',
  'arr',
  'mrr',
  'revenue',
  'gross_margin',
  'customers',
  'runway',
])

function MetricCard({ metric }) {
  const isFound = metric.status === 'found'

  return (
    <div className={`rounded-xl border p-3 transition-colors ${
      isFound ? 'bg-fs-bg border-fs-border' : 'bg-red-500/[0.04] border-red-500/15'
    }`}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div>
          <p className="text-xs text-fs-muted uppercase tracking-wide">{metric.label}</p>
          <p className={`text-lg font-semibold font-mono mt-0.5 ${
            isFound ? 'text-fs-text' : 'text-fs-red'
          }`}>
            {metric.value}
          </p>
        </div>
        <span className={`text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full border ${
          statusStyles[metric.status] || statusStyles.missing
        }`}>
          {metric.status}
        </span>
      </div>

      {metric.slide_number && (
        <p className="text-xs text-fs-accent mb-2">Slide {metric.slide_number}</p>
      )}

      <p className="text-xs text-fs-subtext leading-relaxed line-clamp-3">
        {metric.evidence}
      </p>
    </div>
  )
}

export default function ExtractedMetrics({ metrics, compact = false }) {
  if (!metrics?.length) return null

  const visibleMetrics = compact
    ? metrics.filter(metric => coreKeys.has(metric.key))
    : metrics

  const foundCount = visibleMetrics.filter(metric => metric.status === 'found').length

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between gap-4 mb-4">
        <div>
          <h2 className="text-sm font-semibold text-fs-subtext uppercase tracking-wider">
            Key Extracted Metrics
          </h2>
          <p className="text-xs text-fs-muted mt-1">
            Rule-based values found directly in the parsed deck text.
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-lg font-bold font-mono text-fs-text">{foundCount}/{visibleMetrics.length}</p>
          <p className="text-xs text-fs-muted">found</p>
        </div>
      </div>

      <div className={`grid gap-3 ${compact ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3'}`}>
        {visibleMetrics.map(metric => (
          <MetricCard key={metric.key} metric={metric} />
        ))}
      </div>
    </div>
  )
}
