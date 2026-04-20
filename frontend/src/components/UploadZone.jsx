import { useState, useRef } from 'react'

export default function UploadZone({ onUpload, loading }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  const handleFile = (file) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Please upload a PDF file.')
      return
    }
    onUpload(file)
  }

  const onDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }

  const onDragOver = (e) => { e.preventDefault(); setDragging(true) }
  const onDragLeave = () => setDragging(false)

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6">
      {/* Logo */}
      <div className="mb-12 text-center">
        <h1 className="font-display text-5xl text-fs-text tracking-tight mb-2">
          Flow<span className="text-fs-accent">State</span>
        </h1>
        <p className="text-fs-subtext text-lg">AI-Powered Pitch Deck Analyzer</p>
      </div>

      {/* Drop Zone */}
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => !loading && inputRef.current?.click()}
        className={`
          relative w-full max-w-xl border-2 border-dashed rounded-2xl p-16 text-center
          transition-all duration-200 cursor-pointer
          ${dragging
            ? 'border-fs-accent bg-fs-accent/5 scale-[1.01]'
            : 'border-fs-border bg-fs-surface hover:border-fs-accent/50 hover:bg-fs-accent/5'
          }
          ${loading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => handleFile(e.target.files[0])}
          disabled={loading}
        />

        {/* Icon */}
        <div className={`mx-auto mb-6 w-16 h-16 rounded-2xl flex items-center justify-center
          ${dragging ? 'bg-fs-accent/20' : 'bg-fs-border'}`}>
          <svg className={`w-8 h-8 ${dragging ? 'text-fs-accent' : 'text-fs-subtext'}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>

        <p className="text-fs-text font-medium text-lg mb-1">
          {dragging ? 'Drop your pitch deck' : 'Upload your pitch deck'}
        </p>
        <p className="text-fs-subtext text-sm mb-6">
          Drag & drop or click to browse — PDF only
        </p>

        <div className="inline-flex items-center gap-2 bg-fs-accent/10 border border-fs-accent/20
          text-fs-accent text-sm px-4 py-2 rounded-lg font-medium">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Choose PDF File
        </div>
      </div>

      {/* What it checks */}
      <div className="mt-10 grid grid-cols-2 sm:grid-cols-4 gap-3 w-full max-w-xl">
        {['12 Financial Checks', '8 Section Scores', 'Red Flag Citations', 'AI Narrative'].map(item => (
          <div key={item} className="card px-3 py-2 text-center">
            <p className="text-xs text-fs-subtext">{item}</p>
          </div>
        ))}
      </div>

      <p className="mt-8 text-xs text-fs-muted text-center max-w-sm">
        Only pitch deck PDFs are accepted (5–60 slides). Reports, business plans,
        and other documents will be rejected.
      </p>
    </div>
  )
}
