export default function BiasPanel({ bias }) {
  if (!bias) return null

  const riskColor = {
    Low: 'text-fs-green',
    'Low-Medium': 'text-fs-yellow',
    Medium: 'text-fs-orange',
    High: 'text-fs-red',
  }

  const severityColor = {
    Info: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
    Low: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400',
    Medium: 'bg-orange-500/10 border-orange-500/20 text-orange-400',
  }

  return (
    <div className="space-y-4">
      {/* Summary card */}
      <div className="card p-4">
        <h3 className="text-xs font-semibold text-fs-subtext uppercase tracking-wider mb-4">
          Bias Audit
        </h3>

        <div className="flex items-center justify-between mb-4">
          <span className="text-xs text-fs-subtext">Overall Bias Risk</span>
          <span className={`text-sm font-bold ${riskColor[bias.overall_bias_risk] || 'text-fs-text'}`}>
            {bias.overall_bias_risk}
          </span>
        </div>

        <p className="text-xs text-fs-subtext leading-relaxed mb-4">
          {bias.audit_summary}
        </p>

        <div className="grid grid-cols-2 gap-2">
          {[
            { label: 'Gender Neutral', value: bias.scoring_is_gender_neutral },
            { label: 'Geography Neutral', value: bias.scoring_is_geography_neutral },
          ].map(({ label, value }) => (
            <div key={label} className="bg-fs-bg rounded-lg p-2 text-center">
              <p className={`text-sm font-bold ${value ? 'text-fs-green' : 'text-fs-red'}`}>
                {value ? '✓ Yes' : '✗ No'}
              </p>
              <p className="text-xs text-fs-muted">{label}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="card p-4">
        <h3 className="text-xs font-semibold text-fs-subtext uppercase tracking-wider mb-3">
          Scoring Neutrality
        </h3>
        <div className="space-y-3">
          <div className="flex justify-between text-xs">
            <span className="text-fs-subtext">Criteria Evaluated</span>
            <span className="text-fs-text font-mono">{bias.criteria_checked}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-fs-subtext">Demographic-Free Criteria</span>
            <span className="text-fs-green font-mono">{bias.criteria_demographic_free}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-fs-subtext">Gender Signals</span>
            <span className="text-fs-text font-mono">{bias.gender_detected}</span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-fs-subtext">Linguistic Complexity</span>
            <span className="text-fs-text font-mono">{bias.linguistic_complexity_score}/10</span>
          </div>
          {bias.currency_detected && (
            <div className="flex justify-between text-xs">
              <span className="text-fs-subtext">Currency Detected</span>
              <span className="text-fs-yellow font-mono">{bias.currency_detected}</span>
            </div>
          )}
          {bias.non_us_market && (
            <div className="flex justify-between text-xs">
              <span className="text-fs-subtext">Market Context</span>
              <span className="text-fs-text font-mono">Non-US</span>
            </div>
          )}
        </div>
      </div>

      {/* Bias flags */}
      {bias.flags?.length > 0 && (
        <div className="card p-4">
          <h3 className="text-xs font-semibold text-fs-subtext uppercase tracking-wider mb-3">
            Audit Findings
          </h3>
          <div className="space-y-3">
            {bias.flags.map((flag, i) => (
              <div key={i} className={`border rounded-lg p-3 ${severityColor[flag.severity]}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold">{flag.category}</span>
                  <span className="text-xs opacity-70">{flag.severity}</span>
                </div>
                <p className="text-xs mb-2 opacity-90">{flag.finding}</p>
                <p className="text-xs opacity-70 leading-relaxed mb-1">{flag.detail}</p>
                <p className="text-xs font-medium">
                  Mitigation: <span className="opacity-80">{flag.mitigation}</span>
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}