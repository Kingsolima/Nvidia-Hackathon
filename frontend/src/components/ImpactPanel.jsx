import { useState, useEffect } from 'react'
import { Leaf, Car, TrendingUp, Building2, Home, ChevronDown, ChevronUp, ImageIcon, Loader } from 'lucide-react'
import { ScoreBar } from './ScoreBar'
import { ChatBox } from './ChatBox'
import { generateBuildingImage, buildingTypeToImageParams } from '../api'

const DIMENSIONS = [
  { key: 'environmental', label: 'Environmental',  Icon: Leaf },
  { key: 'traffic',       label: 'Traffic Load',   Icon: Car },
  { key: 'economic',      label: 'Economic',        Icon: TrendingUp },
  { key: 'infrastructure',label: 'Infrastructure',  Icon: Building2 },
  { key: 'housing',       label: 'Housing Supply',  Icon: Home },
]

function LoadingState({ message }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', flex: 1, gap: '20px', padding: '40px 24px' }}>
      {/* Animated ring */}
      <div style={{ position: 'relative', width: 56, height: 56 }}>
        <div style={{
          position: 'absolute', inset: 0,
          borderRadius: '50%',
          border: '2px solid var(--border)',
        }} />
        <div style={{
          position: 'absolute', inset: 0,
          borderRadius: '50%',
          border: '2px solid transparent',
          borderTopColor: 'var(--cyan)',
          animation: 'spin 1s linear infinite',
        }} />
        <div style={{
          position: 'absolute', inset: 8,
          borderRadius: '50%',
          border: '2px solid transparent',
          borderTopColor: 'rgba(0,212,255,0.3)',
          animation: 'spin 1.5s linear infinite reverse',
        }} />
      </div>

      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '12px', color: 'var(--cyan)', fontWeight: 500, marginBottom: '6px', minHeight: '18px', transition: 'opacity 0.3s' }}>
          {message}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-3)' }}>
          NeMoTron on DGX Spark — this takes 15–45s
        </div>
      </div>

      {/* Pipeline steps */}
      <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {['Spatial context (500m radius)', 'XGBoost ML models', 'NeMoTron reasoning'].map((step, i) => (
          <div key={step} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--text-3)' }}>
            <div style={{
              width: 5, height: 5, borderRadius: '50%',
              background: i === 0 ? 'var(--score-low)' : i === 1 ? 'var(--score-mid)' : 'var(--cyan)',
              boxShadow: `0 0 4px ${i === 0 ? 'var(--score-low)' : i === 1 ? 'var(--score-mid)' : 'var(--cyan)'}`,
              animation: 'pulse-dot 2s infinite',
              animationDelay: `${i * 0.4}s`,
            }} />
            {step}
          </div>
        ))}
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse-dot {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  )
}

function BuildingPreview({ building }) {
  const [imgSrc, setImgSrc]   = useState(null)
  const [imgLoading, setImgLoading] = useState(false)
  const [imgError,  setImgError]   = useState(false)

  useEffect(() => {
    if (!building) return
    setImgSrc(null)
    setImgError(false)
    setImgLoading(true)
    const params = buildingTypeToImageParams(building.type, building.floors)
    generateBuildingImage(params)
      .then(data => {
        if (data.image_b64) setImgSrc(`data:image/png;base64,${data.image_b64}`)
        else setImgError(true)
      })
      .catch(() => setImgError(true))
      .finally(() => setImgLoading(false))
  }, [building?.id])

  return (
    <div style={{
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      overflow: 'hidden',
      aspectRatio: '16/9',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      position: 'relative',
    }}>
      {imgLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px', color: 'var(--text-3)' }}>
          <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
          <span style={{ fontSize: '11px' }}>Rendering building...</span>
        </div>
      )}
      {imgSrc && !imgLoading && (
        <img src={imgSrc} alt="Building preview" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
      )}
      {imgError && !imgLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px', color: 'var(--text-3)' }}>
          <ImageIcon size={20} />
          <span style={{ fontSize: '11px' }}>Preview unavailable</span>
          {/* TODO: teammates — connect ML image generation here */}
        </div>
      )}
      {/* Label */}
      <div style={{
        position: 'absolute', bottom: 8, left: 8,
        background: 'rgba(0,0,0,0.7)',
        border: '1px solid var(--border)',
        borderRadius: '3px',
        padding: '2px 7px',
        fontSize: '10px',
        color: 'var(--text-2)',
        fontFamily: 'var(--mono)',
      }}>
        2D elevation · {building?.floors}F · {building?.type}
      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

export function ImpactPanel({ building, impact, loading, loadingMessage, error }) {
  const [expanded, setExpanded] = useState(true)
  const [showChat, setShowChat] = useState(false)

  if (!building && !loading) return null

  // Overall risk level
  const scores = impact ? DIMENSIONS.map(d => impact[d.key]?.score ?? 0) : []
  const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b) / scores.length) : 0

  return (
    <div style={{
      width: 'var(--panel-w)',
      height: '100%',
      background: 'var(--bg-2)',
      borderLeft: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      flexShrink: 0,
    }}>
      {/* Panel header */}
      <div style={{
        padding: '14px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-3)',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, fontSize: '14px', marginBottom: '2px' }}>
              {building?.name || 'Proposed Building'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-2)' }}>
              {building?.type} · {building?.floors}F · {Number(building?.footprint_m2).toLocaleString()} m²
            </div>
          </div>
          {impact && (
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '22px', fontWeight: 700,
                color: avgScore <= 30 ? 'var(--score-low)' : avgScore <= 60 ? 'var(--score-mid)' : avgScore <= 85 ? 'var(--score-high)' : 'var(--score-crit)' }}>
                {avgScore}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-3)' }}>avg impact</div>
            </div>
          )}
        </div>

        {/* Location */}
        {building && (
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            <span className="tag tag-dim">
              {building.lat?.toFixed(4)}, {building.lng?.toFixed(4)}
            </span>
            <span className="tag tag-dim">{building.material || 'glass'}</span>
            <span className="tag tag-cyan">{building.status || 'Under Review'}</span>
          </div>
        )}
      </div>

      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        {loading && <LoadingState message={loadingMessage} />}

        {error && (
          <div style={{ padding: '20px 16px', textAlign: 'center' }}>
            <div style={{ color: 'var(--score-crit)', fontSize: '13px', marginBottom: '8px' }}>Analysis failed</div>
            <div style={{ fontSize: '11px', color: 'var(--text-3)' }}>{error}</div>
          </div>
        )}

        {impact && !loading && (
          <>
            {/* Building preview */}
            <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
              <BuildingPreview building={building} />
            </div>

            {/* Impact scores */}
            <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                <span className="label">Impact Analysis</span>
                <button onClick={() => setExpanded(e => !e)} style={{
                  background: 'none', border: 'none', color: 'var(--text-2)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '3px', fontSize: '11px',
                }}>
                  {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  {expanded ? 'Collapse' : 'Expand'}
                </button>
              </div>

              {expanded && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {DIMENSIONS.map(({ key, label, Icon }) => (
                    <ScoreBar
                      key={key}
                      icon={Icon}
                      label={label}
                      score={impact[key]?.score ?? 0}
                      description={impact[key]?.description}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* XGBoost callout */}
            <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-3)' }}>Powered by</span>
                <span className="tag tag-green">XGBoost ML</span>
                <span className="tag tag-cyan">NeMoTron DGX Spark</span>
                <span className="tag tag-dim">Toronto Open Data</span>
              </div>
            </div>

            {/* Chat toggle */}
            <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)' }}>
              <button className="btn btn-ghost" style={{ width: '100%', fontSize: '12px' }}
                onClick={() => setShowChat(s => !s)}>
                {showChat ? 'Hide' : 'Ask NeMoTron'} — citizen Q&A assistant
                {showChat ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
            </div>
          </>
        )}
      </div>

      {/* Chat box — always pinned to bottom */}
      {showChat && impact && (
        <ChatBox buildingId={building?.id} />
      )}
    </div>
  )
}
