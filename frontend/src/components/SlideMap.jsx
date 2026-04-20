const categoryColors = {
  Problem:        'bg-purple-500/20 text-purple-300 border-purple-500/30',
  Solution:       'bg-blue-500/20 text-blue-300 border-blue-500/30',
  'Market Size':  'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
  'Business Model': 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
  Traction:       'bg-green-500/20 text-green-300 border-green-500/30',
  Team:           'bg-orange-500/20 text-orange-300 border-orange-500/30',
  Financials:     'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  Ask:            'bg-pink-500/20 text-pink-300 border-pink-500/30',
  Unknown:        'bg-fs-border text-fs-muted border-fs-border',
}

export default function SlideMap({ slides }) {
  if (!slides?.length) return null

  return (
    <div className="card p-4">
      <h3 className="text-xs font-semibold text-fs-subtext uppercase tracking-wider mb-4">
        Slide Map ({slides.length} slides)
      </h3>
      <div className="space-y-1 max-h-80 overflow-y-auto pr-1">
        {slides.map(slide => (
          <div
            key={slide.slide_number}
            className={`flex items-center gap-2 py-1.5 px-2 rounded-lg
              ${slide.has_red_flags ? 'bg-red-500/5 border border-red-500/20' : 'hover:bg-fs-bg'}`}
          >
            <span className="text-xs font-mono text-fs-muted w-8 flex-shrink-0">
              {slide.slide_number}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded border font-medium flex-shrink-0
              ${categoryColors[slide.primary_category] || categoryColors.Unknown}`}>
              {slide.primary_category}
            </span>
            {slide.heading_hints?.[0] && (
              <span className="text-xs text-fs-muted truncate flex-1">
                {slide.heading_hints[0]}
              </span>
            )}
            {slide.has_red_flags && (
              <span className="flex-shrink-0 w-2 h-2 rounded-full bg-red-400" title="Has red flags" />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
