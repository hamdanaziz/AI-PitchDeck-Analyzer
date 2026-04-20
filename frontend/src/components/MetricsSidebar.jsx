export default function MetricsSidebar({ metrics, financial }) {
  if (!metrics) return null

  const MetricRow = ({ label, value, unit = '', barValue = null, color = 'bg-fs-accent' }) => (
    <div className="mb-4">
      <div className="flex justify-between items-baseline mb-1.5">
        <span className="text-xs text-fs-subtext">{label}</span>
        <span className="text-sm font-semibold font-mono text-fs-text">{value}{unit}</span>
      </div>
      {barValue !== null && (
        <div className="h-1 bg-fs-border rounded-full overflow-hidden">
          <div
            className={`h-full ${color} rounded-full transition-all duration-700`}
            style={{ width: `${Math.min(barValue, 100)}%` }}
          />
        </div>
      )}
    </div>
  )

  const citationColor = metrics.citation_accuracy_rate >= 80
    ? 'bg-fs-green' : metrics.citation_accuracy_rate >= 50
    ? 'bg-fs-yellow' : 'bg-fs-red'

  const confidenceColor = metrics.overall_confidence_score >= 80
    ? 'bg-fs-green' : metrics.overall_confidence_score >= 50
    ? 'bg-fs-yellow' : 'bg-fs-red'

  return (
    <div className="space-y-4">
      <div className="card p-4">
        <h3 className="text-xs font-semibold text-fs-subtext uppercase tracking-wider mb-4">
          Analysis Metrics
        </h3>

        <MetricRow
          label="Total Red Flags"
          value={metrics.total_red_flags}
        />
        <MetricRow
          label="Citation Accuracy"
          value={metrics.citation_accuracy_rate}
          unit="%"
          barValue={metrics.citation_accuracy_rate}
          color={citationColor}
        />
        <MetricRow
          label="Confidence Score"
          value={metrics.overall_confidence_score}
          unit="%"
          barValue={metrics.overall_confidence_score}
          color={confidenceColor}
        />
        <MetricRow
          label="Financial Checks Run"
          value={`${metrics.financial_checks_run}`}
        />
        <MetricRow
          label="Checks with Findings"
          value={metrics.financial_checks_with_findings}
          barValue={(metrics.financial_checks_with_findings / Math.max(metrics.financial_checks_run, 1)) * 100}
          color="bg-fs-yellow"
        />
        <MetricRow
          label="Weak Sections (<5)"
          value={metrics.weak_sections_count}
        />

        <div className="flex items-center justify-between pt-2 border-t border-fs-border">
          <span className="text-xs text-fs-subtext">Hallucinated Claims</span>
          <span className={`text-sm font-mono font-semibold ${
            metrics.hallucinated_claims_detected === 0 ? 'text-fs-green' : 'text-fs-orange'
          }`}>
            {metrics.hallucinated_claims_detected}
          </span>
        </div>
      </div>

      {/* Financial check summary */}
      {financial && (
        <div className="card p-4">
          <h3 className="text-xs font-semibold text-fs-subtext uppercase tracking-wider mb-4">
            Financial Checks
          </h3>
          <div className="grid grid-cols-2 gap-2 mb-3">
            {[
              { label: 'Pass', value: financial.pass_count, color: 'text-fs-green' },
              { label: 'Warn', value: financial.warn_count, color: 'text-fs-yellow' },
              { label: 'Fail', value: financial.fail_count, color: 'text-fs-red' },
              { label: 'Skipped', value: financial.skipped_count, color: 'text-fs-muted' },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-fs-bg rounded-lg p-2 text-center">
                <p className={`text-lg font-bold font-mono ${color}`}>{value}</p>
                <p className="text-xs text-fs-muted">{label}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-fs-subtext leading-relaxed">{financial.summary}</p>
        </div>
      )}
    </div>
  )
}
