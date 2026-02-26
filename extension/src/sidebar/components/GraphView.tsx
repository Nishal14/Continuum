/**
 * Dimensional Governance Monitor — Graph Tab
 *
 * Three-layer architecture for a hybrid epistemic stability monitoring system:
 *
 *   Layer 1 · Heuristic Drift Modeling — continuous signal over time
 *   Layer 2 · Policy-Driven Escalation — gate that opens at Drift ≥ 2.0
 *   Layer 3 · K2 Adjudication Authority — strategic verification result
 *
 * Tone: research-grade infrastructure, not a dashboard widget.
 * Palette: deep graphite · steel blue · muted burgundy · muted purple
 */

import React, { useEffect, useRef, useState } from 'react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface DriftPoint { turn: number; score: number; }
type K2Status = 'idle' | 'pending' | 'confirmed' | 'overridden' | 'failed';
interface K2Data { status: K2Status; confidence?: number; explanation?: string; }
interface GraphViewProps { conversationId: string; apiBaseUrl: string; }

// ─── Palette — research-grade, no neon ───────────────────────────────────────
//
//   line        steel blue  — controlled, distinct from dark-navy bg
//   threshold   muted burgundy — danger without alarm
//   k2          muted purple — authority / adjudication layer
//   stable/etc  desaturated status colours

const C = {
  line:         '#4D7BC4',
  lineAlpha:    'rgba(77,123,196,',
  threshold:    '#9B3E3E',
  thresholdBg:  'rgba(155,62,62,',
  k2:           '#7055A8',
  k2Bg:         'rgba(112,85,168,',
  stable:       '#3D8A6E',
  tension:      '#8A763D',
  unstable:     '#8A3D3D',
  textHi:       'rgba(228,230,235,0.88)',
  textMid:      'rgba(175,182,195,0.70)',
  textLo:       'rgba(130,140,158,0.52)',
  textDim:      'rgba(90,100,118,0.40)',
  grid:         'rgba(255,255,255,0.042)',
  border:       'rgba(255,255,255,0.072)',
};

// ─── Chart geometry ───────────────────────────────────────────────────────────

const W   = 356;
const H   = 188;
const ML  = 42;    // left margin — room for y-axis labels
const MR  = 14;
const MT  = 22;
const MB  = 34;
const IW  = W - ML - MR;
const IH  = H - MT - MB;

const Y_MAX     = 3.5;
const THRESHOLD = 2.0;

// ─── Mock data — demo state with full escalation visible ─────────────────────

const MOCK: DriftPoint[] = [
  { turn: 0,  score: 0.00 },
  { turn: 3,  score: 0.16 },
  { turn: 6,  score: 0.48 },
  { turn: 9,  score: 0.88 },
  { turn: 12, score: 1.35 },
  { turn: 15, score: 1.78 },
  { turn: 18, score: 2.15 },
  { turn: 21, score: 2.62 },
  { turn: 24, score: 3.05 },
  { turn: 27, score: 3.30 },
];
const MOCK_MAX = 28;

// ─── Coordinate helpers ───────────────────────────────────────────────────────

const px = (turn: number, maxT: number) =>
  ML + (turn / Math.max(maxT, 1)) * IW;

const py = (score: number) =>
  MT + IH - (Math.min(score, Y_MAX) / Y_MAX) * IH;

// ─── SVG path builders ────────────────────────────────────────────────────────

function buildLine(pts: DriftPoint[], maxT: number): string {
  if (pts.length < 2) return pts.length === 1 ? `M ${px(pts[0].turn, maxT)} ${py(pts[0].score)}` : '';
  const s = pts.map(p => ({ x: px(p.turn, maxT), y: py(p.score) }));
  let d = `M ${s[0].x} ${s[0].y}`;
  for (let i = 1; i < s.length; i++) {
    const h = (s[i].x - s[i-1].x) * 0.46;
    d += ` C ${s[i-1].x+h} ${s[i-1].y}, ${s[i].x-h} ${s[i].y}, ${s[i].x} ${s[i].y}`;
  }
  return d;
}

function buildArea(pts: DriftPoint[], maxT: number): string {
  if (pts.length < 2) return '';
  const bot = MT + IH;
  return `${buildLine(pts, maxT)} L ${px(pts[pts.length-1].turn, maxT)} ${bot} L ${px(pts[0].turn, maxT)} ${bot} Z`;
}

function findEscX(pts: DriftPoint[], maxT: number): number | null {
  for (let i = 1; i < pts.length; i++) {
    if (pts[i-1].score < THRESHOLD && pts[i].score >= THRESHOLD) {
      const t = (THRESHOLD - pts[i-1].score) / (pts[i].score - pts[i-1].score);
      return px(pts[i-1].turn + t * (pts[i].turn - pts[i-1].turn), maxT);
    }
  }
  return null;
}

// ─── Component ────────────────────────────────────────────────────────────────

const GraphView: React.FC<GraphViewProps> = ({ conversationId, apiBaseUrl }) => {
  const [points,          setPoints]          = useState<DriftPoint[]>(MOCK);
  const [maxTurn,         setMaxTurn]         = useState(MOCK_MAX);
  const [driftScore,      setDriftScore]      = useState(3.30);
  const [velocity,        setVelocity]        = useState(0.44);
  const [structState,     setStructState]     = useState('Unstable');
  const [escalationCount, setEscalationCount] = useState(1);
  const [k2,              setK2]              = useState<K2Data>({ status: 'idle' });
  const [isMock,          setIsMock]          = useState(true);

  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);

  // ── Polling ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!conversationId) return;

    const poll = async () => {
      try {
        const mRes = await fetch(`${apiBaseUrl}/conversations/${conversationId}/metrics`);
        if (!mRes.ok || !alive.current) return;
        const m = await mRes.json();
        if (!alive.current) return;

        const score = m.drift?.cumulative_drift_score ?? 0;
        const vel   = m.drift?.drift_velocity ?? 0;
        setDriftScore(score);
        setVelocity(vel);
        setStructState(score >= 2.0 ? 'Unstable' : score >= 1.0 ? 'Tension' : 'Stable');
        setEscalationCount(m.escalation?.total_escalations ?? 0);

        const cRes = await fetch(`${apiBaseUrl}/conversations/${conversationId}`);
        if (!cRes.ok || !alive.current) return;
        const conv = await cRes.json();
        if (!alive.current) return;

        const events: any[] = conv.drift_events ?? [];
        const turns: any[]  = conv.turns ?? [];
        const nT = turns.length > 0 ? Math.max(...turns.map((t: any) => t.id)) : 20;
        setMaxTurn(nT);

        if (events.length > 0) {
          const sorted = [...events].sort((a, b) => a.detected_at_turn - b.detected_at_turn);
          const pts: DriftPoint[] = [{ turn: 0, score: 0 }];
          let cum = 0;
          for (const e of sorted) { cum += e.drift_magnitude; pts.push({ turn: e.detected_at_turn, score: cum }); }
          if (pts[pts.length-1].turn < nT) pts.push({ turn: nT, score });
          setPoints(pts); setIsMock(false);
        } else if (score > 0) {
          setPoints([{ turn: 0, score: 0 }, { turn: nT, score }]); setIsMock(false);
        } else if (turns.length > 0) {
          setPoints([{ turn: 0, score: 0 }, { turn: nT, score: 0 }]);
          setMaxTurn(nT); setIsMock(false);
        } else {
          setPoints(MOCK); setMaxTurn(MOCK_MAX); setIsMock(true);
        }

        const kRes = await fetch(`${apiBaseUrl}/conversations/${conversationId}/k2-status`);
        if (!kRes.ok || !alive.current) return;
        const k = await kRes.json();
        if (!alive.current) return;

        if (!k.escalation_active || !k.status)  setK2({ status: 'idle' });
        else if (k.status === 'pending')         setK2({ status: 'pending' });
        else if (k.status === 'completed')       setK2({ status: k.result_type === 'confirmed' ? 'confirmed' : 'overridden', confidence: k.k2_confidence ?? 0, explanation: k.k2_explanation ?? '' });
        else if (k.status === 'failed')          setK2({ status: 'failed', explanation: k.k2_explanation ?? '' });
      } catch { /* retain previous data */ }
    };

    poll();
    const id = setInterval(poll, 3000);
    return () => clearInterval(id);
  }, [conversationId, apiBaseUrl]);

  // ── Derived SVG values ───────────────────────────────────────────────────────
  const isEscalated = driftScore >= THRESHOLD;
  const tY          = py(THRESHOLD);
  const escX        = findEscX(points, maxTurn);
  const linePath    = buildLine(points, maxTurn);
  const areaPath    = buildArea(points, maxTurn);
  const lastPt      = points[points.length - 1];
  const calloutX    = px(lastPt.turn, maxTurn);
  const calloutY    = py(lastPt.score);

  const stateColor = structState === 'Unstable' ? C.unstable : structState === 'Tension' ? C.tension : C.stable;

  // Velocity arrow + animation
  const velArrow = velocity > 0.3 ? '▲▲' : velocity > 0.05 ? '▲' : velocity < -0.05 ? '▼' : '—';
  const velColor = velocity > 0.05 ? C.tension : velocity < -0.05 ? C.stable : C.textLo;
  const velAnimated = Math.abs(velocity) > 0.05;

  const yTicks = [0, 1, 2, 3];
  const xTicks = Array.from({ length: 6 }, (_, i) => ({
    turn: Math.round((i / 5) * maxTurn),
    x:    px(Math.round((i / 5) * maxTurn), maxTurn),
  }));

  // ── K2 styling ───────────────────────────────────────────────────────────────
  const k2AccentColor =
    k2.status === 'confirmed'  ? C.threshold :
    k2.status === 'overridden' ? 'rgba(160,165,175,0.75)' :
    k2.status === 'pending'    ? C.k2 :
                                 'rgba(110,115,125,0.55)';

  const k2BadgeStyle: React.CSSProperties =
    k2.status === 'confirmed'  ? { background: 'rgba(155,62,62,0.14)', color: '#B86060', border: '1px solid rgba(155,62,62,0.30)' } :
    k2.status === 'overridden' ? { background: 'rgba(90,95,108,0.14)', color: 'rgba(185,190,205,0.80)', border: '1px solid rgba(100,108,125,0.28)' } :
    k2.status === 'pending'    ? { background: 'rgba(112,85,168,0.14)', color: '#9070C8', border: '1px solid rgba(112,85,168,0.32)' } :
                                 { background: 'rgba(80,85,95,0.10)',   color: 'rgba(150,155,168,0.65)', border: '1px solid rgba(90,95,110,0.22)' };

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div style={{ userSelect: 'none' }}>

      {/* ── Status Strip ────────────────────────────────────────────────────── */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1px 1fr 1px 1fr',
        marginBottom: '14px',
        background: 'rgba(18,22,32,0.85)',
        border: `1px solid ${C.border}`,
        borderRadius: '9px',
        overflow: 'hidden',
      }}>

        {/* State */}
        <div style={{ padding: '10px 10px 9px', textAlign: 'center' }}>
          <div style={{ fontSize: '9px', color: C.textDim, letterSpacing: '0.9px', textTransform: 'uppercase', marginBottom: '5px' }}>
            Structural State
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}>
            {structState === 'Unstable' && (
              <span style={{
                width: '6px', height: '6px', borderRadius: '50%', flexShrink: 0,
                background: C.unstable,
                boxShadow: `0 0 5px ${C.unstable}`,
                animation: 'cg-pulse 2s ease-in-out infinite',
                display: 'inline-block',
              }} />
            )}
            <span style={{ fontSize: '13px', fontWeight: 700, color: stateColor, letterSpacing: '0.2px' }}>
              {structState}
            </span>
          </div>
          {escalationCount > 0 && (
            <div style={{ marginTop: '4px', fontSize: '9px', color: C.textDim, fontFamily: 'monospace' }}>
              {escalationCount} escalation{escalationCount !== 1 ? 's' : ''}
            </div>
          )}
        </div>

        <div style={{ background: C.border }} />

        {/* Drift Score */}
        <div style={{ padding: '10px 10px 9px', textAlign: 'center' }}>
          <div style={{ fontSize: '9px', color: C.textDim, letterSpacing: '0.9px', textTransform: 'uppercase', marginBottom: '5px' }}>
            Drift Score
          </div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: C.line, fontFamily: 'monospace', letterSpacing: '0.5px' }}>
            {driftScore.toFixed(2)}
          </div>
        </div>

        <div style={{ background: C.border }} />

        {/* Velocity */}
        <div style={{ padding: '10px 10px 9px', textAlign: 'center' }}>
          <div style={{ fontSize: '9px', color: C.textDim, letterSpacing: '0.9px', textTransform: 'uppercase', marginBottom: '5px' }}>
            Velocity
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
            <span style={{
              fontSize: '13px', fontWeight: 700, color: velColor, fontFamily: 'monospace',
            }}>
              {velocity >= 0 ? '+' : ''}{velocity.toFixed(3)}
            </span>
            <span style={{
              fontSize: '10px', color: velColor,
              animation: velAnimated ? 'cg-vel 1.6s ease-in-out infinite' : 'none',
              display: 'inline-block',
            }}>
              {velArrow}
            </span>
          </div>
        </div>
      </div>

      {/* ── Layer 1 — Heuristic Drift Chart ─────────────────────────────────── */}
      <div style={{
        background:   'rgba(10,12,20,0.96)',
        border:       `1px solid ${C.border}`,
        borderTop:    `2px solid rgba(77,123,196,0.42)`,
        borderRadius: '10px',
        padding:      '0 2px 2px',
        boxShadow:    '0 8px 40px rgba(0,0,0,0.65), 0 1px 0 rgba(255,255,255,0.05) inset',
        marginBottom: isEscalated ? '0' : '14px',
      }}>

        {/* Panel header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px 2px' }}>
          <span style={{ fontSize: '10.5px', fontWeight: 700, color: C.textMid, letterSpacing: '0.7px', textTransform: 'uppercase' }}>
            Structural Drift Over Time
          </span>
          <span style={{ fontSize: '9px', fontFamily: 'monospace', color: C.textDim }}>
            Layer 1 · Heuristics{isMock ? ' · demo' : ''}
          </span>
        </div>

        <svg width={W} height={H} style={{ display: 'block', overflow: 'visible' }}>
          <defs>
            {/* Subtle blue wash inside chart area */}
            <linearGradient id="cg-bg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="rgba(50,80,140,0.05)" />
              <stop offset="100%" stopColor="rgba(0,0,0,0)" />
            </linearGradient>

            {/* Area fill gradient */}
            <linearGradient id="cg-area" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor={C.lineAlpha + '0.28)'} />
              <stop offset="65%"  stopColor={C.lineAlpha + '0.08)'} />
              <stop offset="100%" stopColor={C.lineAlpha + '0.01)'} />
            </linearGradient>

            {/* Very subtle glow — professional, not neon */}
            <filter id="cg-glow" x="-8%" y="-80%" width="116%" height="260%">
              <feGaussianBlur stdDeviation="1.6" result="b" />
              <feComposite in="b" in2="SourceGraphic" operator="over" result="g" />
              <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          {/* Chart area tint */}
          <rect x={ML} y={MT} width={IW} height={IH} fill="url(#cg-bg)" />

          {/* Grid lines */}
          {yTicks.map(v => (
            <line key={v} x1={ML} y1={py(v)} x2={ML+IW} y2={py(v)}
              stroke={C.grid} strokeWidth="1" />
          ))}

          {/* Danger-zone fill above threshold */}
          <rect x={ML} y={MT} width={IW} height={tY - MT}
            fill={C.thresholdBg + '0.06)'} />

          {/* Threshold line — dashed, clearly visible */}
          <line x1={ML} y1={tY} x2={ML+IW} y2={tY}
            stroke={C.threshold} strokeWidth="1.5" opacity="0.85"
            strokeDasharray="7 4" />

          {/* Threshold label — left pill */}
          <rect x={ML+5} y={tY-15} width={76} height={13} rx="3"
            fill={C.thresholdBg + '0.12)'}
            stroke={C.thresholdBg + '0.32)'} strokeWidth="0.7" />
          <text x={ML+11} y={tY-5.5}
            fontSize="8" fontFamily="monospace"
            fill={C.thresholdBg + '0.88)'} letterSpacing="0.1">
            Threshold  2.0
          </text>

          {/* Accumulation area fill */}
          {areaPath && <path d={areaPath} fill="url(#cg-area)" />}

          {/* Vertical escalation beam — dashed, from crossing point up */}
          {isEscalated && escX !== null && (
            <line x1={escX} y1={MT+4} x2={escX} y2={tY-14}
              stroke={C.thresholdBg + '0.38)'}
              strokeWidth="1.5" strokeDasharray="3 4" />
          )}

          {/* Drift line — steel blue, subtle glow */}
          {linePath && (
            <path d={linePath} fill="none"
              stroke={C.line} strokeWidth="2.5"
              strokeLinecap="round" strokeLinejoin="round"
              filter="url(#cg-glow)" />
          )}

          {/* Data-point markers (hollow rings on the line) */}
          {points.map((p, i) => {
            if (i === 0 || i === points.length - 1) return null;
            return (
              <circle key={i} cx={px(p.turn, maxTurn)} cy={py(p.score)} r="2.5"
                fill="rgba(10,12,20,1)"
                stroke={C.line} strokeWidth="1.5" opacity="0.75" />
            );
          })}

          {/* Escalation crossing dot — three concentric rings */}
          {isEscalated && escX !== null && (
            <g>
              <circle cx={escX} cy={tY} r="13"
                fill={C.thresholdBg + '0.05)'}
                stroke={C.thresholdBg + '0.14)'} strokeWidth="1" />
              <circle cx={escX} cy={tY} r="7.5"
                fill={C.thresholdBg + '0.10)'}
                stroke={C.threshold} strokeWidth="1.25" opacity="0.7" />
              <circle cx={escX} cy={tY} r="3"
                fill={C.threshold} opacity="0.92" />
            </g>
          )}

          {/* Escalation trigger label — right of dot or left if near edge */}
          {isEscalated && escX !== null && (() => {
            const lW = 112, lH = 15;
            const lX = escX + 18 + lW <= ML + IW ? escX + 18 : escX - 18 - lW;
            const lY = tY - 8;
            return (
              <g>
                <rect x={lX} y={lY} width={lW} height={lH} rx="3"
                  fill={C.thresholdBg + '0.10)'}
                  stroke={C.thresholdBg + '0.26)'} strokeWidth="0.65" />
                <text x={lX + lW/2} y={lY + 10}
                  fontSize="7.5" fontFamily="monospace" textAnchor="middle"
                  fill={C.thresholdBg + '0.82)'}>
                  Escalation Trigger
                </text>
              </g>
            );
          })()}

          {/* End-of-line value callout */}
          {linePath && (() => {
            const bW = 38, bH = 17, bR = 4;
            const onLeft = calloutX > ML + IW - bW - 10;
            const bx = onLeft ? calloutX - bW - 7 : calloutX + 7;
            const by = Math.max(MT + 3, calloutY - bH / 2);
            return (
              <g>
                <circle cx={calloutX} cy={calloutY} r="4"
                  fill="rgba(10,12,20,1)"
                  stroke={C.line} strokeWidth="2" />
                <rect x={bx} y={by} width={bW} height={bH} rx={bR}
                  fill={C.lineAlpha + '0.16)'}
                  stroke={C.lineAlpha + '0.42)'}
                  strokeWidth="1" />
                <text x={bx + bW/2} y={by + bH/2 + 3.8}
                  fontSize="9.5" fontFamily="monospace" fontWeight="700"
                  textAnchor="middle" fill={C.line}>
                  {lastPt.score.toFixed(2)}
                </text>
              </g>
            );
          })()}

          {/* Y-axis labels */}
          {yTicks.map(v => (
            <text key={v} x={ML-8} y={py(v)+3.5}
              fontSize="9.5" textAnchor="end"
              fontFamily="monospace" fill={C.textLo}>
              {v}
            </text>
          ))}

          {/* Y-axis title */}
          <text x={10} y={MT + IH/2}
            fontSize="8" textAnchor="middle"
            fontFamily="monospace" fill={C.textDim}
            transform={`rotate(-90, 10, ${MT + IH/2})`}>
            Drift Score
          </text>

          {/* X-axis baseline */}
          <line x1={ML} y1={MT+IH} x2={ML+IW} y2={MT+IH}
            stroke="rgba(255,255,255,0.09)" strokeWidth="1" />

          {/* X-axis labels */}
          {xTicks.map(({ turn, x }, i) => (
            <text key={i} x={x} y={MT+IH+15}
              fontSize="9" textAnchor="middle"
              fontFamily="monospace" fill={C.textLo}>
              T{turn}
            </text>
          ))}

          {/* X-axis title */}
          <text x={ML + IW/2} y={H-2}
            fontSize="8" textAnchor="middle"
            fontFamily="monospace" fill={C.textDim}>
            Conversation Turns
          </text>
        </svg>
      </div>

      {/* ── Connector 1 → 2 ─────────────────────────────────────────────────── */}
      {isEscalated && (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <div style={{
            width: '2px', height: '16px',
            background: `linear-gradient(to bottom, ${C.threshold}, rgba(155,62,62,0.2))`,
          }} />
        </div>
      )}

      {/* ── Layer 2 — Escalation Policy ─────────────────────────────────────── */}
      {isEscalated && (
        <div style={{
          background:   'rgba(16,10,10,0.96)',
          border:       `1px solid ${C.thresholdBg}0.20)`,
          borderLeft:   `3px solid ${C.thresholdBg}0.60)`,
          borderRadius: '10px',
          padding:      '12px 16px',
          boxShadow:    `0 4px 28px rgba(0,0,0,0.5), 0 0 0 0 ${C.thresholdBg}0)`,
          marginBottom: k2.status !== 'idle' ? '0' : '14px',
          animation:    'cg-fade-in 0.35s ease forwards',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '10px' }}>
            <span style={{ fontSize: '9px', fontWeight: 700, color: C.textLo, letterSpacing: '1px', textTransform: 'uppercase' }}>
              Escalation Policy
            </span>
            <span style={{ fontSize: '9px', fontFamily: 'monospace', color: C.textDim }}>Layer 2</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '11px' }}>
            {/* Pulsing indicator */}
            <div style={{ position: 'relative', width: '9px', height: '9px', flexShrink: 0, marginTop: '2px' }}>
              <span style={{
                position: 'absolute', inset: 0,
                borderRadius: '50%',
                background: C.threshold,
                opacity: 0.25,
                animation: 'cg-pulse-ring 2.4s ease-in-out infinite',
                transform: 'scale(1)',
              }} />
              <span style={{
                position: 'absolute', inset: '2px',
                borderRadius: '50%',
                background: C.threshold,
                animation: 'cg-pulse 2.4s ease-in-out infinite',
              }} />
            </div>

            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: C.textHi, lineHeight: '1.4', marginBottom: '3px' }}>
                Policy Triggered — Strategic K2 Escalation
              </div>
              <div style={{ fontSize: '10.5px', color: C.textLo, lineHeight: '1.5' }}>
                Cost-aware invocation: heuristics gated K2
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Connector 2 → 3 — gradient red→purple to imply authority flow ───── */}
      {isEscalated && k2.status !== 'idle' && (
        <div style={{ display: 'flex', justifyContent: 'center' }}>
          <div style={{
            width: '2px', height: '14px',
            background: `linear-gradient(to bottom, ${C.thresholdBg}0.22), ${C.k2Bg}0.25))`,
          }} />
        </div>
      )}

      {/* ── Layer 3 — K2 Adjudication Authority ─────────────────────────────── */}
      {isEscalated && k2.status !== 'idle' && (
        <div style={{
          background:   'rgba(10,8,18,0.97)',
          border:       `1px solid ${C.k2Bg}0.18)`,
          borderLeft:   `3px solid ${k2AccentColor}`,
          borderRadius: '10px',
          padding:      '12px 16px',
          marginBottom: '14px',
          boxShadow:    '0 4px 28px rgba(0,0,0,0.55)',
          animation:    'cg-fade-in 0.35s ease forwards',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '10px' }}>
            <span style={{ fontSize: '9px', fontWeight: 700, color: C.textLo, letterSpacing: '1px', textTransform: 'uppercase' }}>
              K2 Adjudication Authority
            </span>
            <span style={{ fontSize: '9px', fontFamily: 'monospace', color: C.textDim }}>Layer 3</span>
          </div>

          {/* Status badge */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '8px' }}>
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: '5px',
              padding: '4px 12px', borderRadius: '5px',
              fontSize: '11.5px', fontWeight: 700, letterSpacing: '0.15px',
              ...k2BadgeStyle,
            }}>
              {k2.status === 'confirmed'  && '● Confirmed Contradiction'}
              {k2.status === 'overridden' && '○ Override — False Positive'}
              {k2.status === 'pending'    && '◌ Verifying…'}
              {k2.status === 'failed'     && '○ Verification Failed'}
            </span>
          </div>

          {/* Confidence bar — only when confirmed */}
          {k2.status === 'confirmed' && k2.confidence != null && (
            <div style={{ marginBottom: '8px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '9.5px', color: C.textLo }}>K2 Confidence</span>
                <span style={{ fontSize: '9.5px', fontFamily: 'monospace', color: C.textMid, fontWeight: 600 }}>
                  {(k2.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div style={{ height: '3px', background: 'rgba(255,255,255,0.07)', borderRadius: '2px' }}>
                <div style={{
                  width: `${(k2.confidence ?? 0) * 100}%`,
                  height: '100%',
                  background: `linear-gradient(to right, ${C.threshold}, ${C.k2})`,
                  borderRadius: '2px',
                  transition: 'width 0.9s ease',
                }} />
              </div>
            </div>
          )}

          {/* Closed-loop label */}
          {k2.status === 'confirmed' && (
            <div style={{ fontSize: '9.5px', color: C.textDim, marginBottom: '6px', letterSpacing: '0.2px' }}>
              Closed-Loop Verification Complete
            </div>
          )}

          {/* Explanation */}
          {k2.explanation && (
            <p style={{ margin: 0, fontSize: '11px', color: C.textLo, lineHeight: '1.55' }}>
              {k2.explanation}
            </p>
          )}
        </div>
      )}

      <style>{`
        @keyframes cg-pulse        { 0%,100%{opacity:1}         50%{opacity:0.28} }
        @keyframes cg-pulse-ring   { 0%,100%{transform:scale(1);opacity:0.25} 50%{transform:scale(2.2);opacity:0} }
        @keyframes cg-vel          { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-2px)} }
        @keyframes cg-fade-in      { from{opacity:0;transform:translateY(-5px)} to{opacity:1;transform:translateY(0)} }
      `}</style>
    </div>
  );
};

export default GraphView;
