/**
 * Animated Drift Meter Component
 *
 * Displays cumulative epistemic drift with smooth animations and color transitions.
 */

import React, { useEffect, useRef } from 'react';

interface DriftMeterProps {
  driftScore: number;
  maxScore?: number;
  isEscalated?: boolean;
}

const DriftMeter: React.FC<DriftMeterProps> = ({
  driftScore,
  maxScore = 5.0,
  isEscalated = false
}) => {
  const barRef = useRef<HTMLDivElement>(null);
  const prevScoreRef = useRef<number>(0);
  const [isHovered, setIsHovered] = React.useState(false);

  // Animate bar width on score change
  useEffect(() => {
    if (barRef.current) {
      prevScoreRef.current = driftScore;
    }
  }, [driftScore]);

  // Calculate percentage and color
  const percentage = Math.min((driftScore / maxScore) * 100, 100);

  const getColor = () => {
    const normalized = driftScore / maxScore;
    if (normalized <= 0.2) return '#2ecc71'; // Green
    if (normalized <= 0.4) return '#f1c40f'; // Yellow
    if (normalized <= 0.6) return '#e67e22'; // Orange
    return '#e74c3c'; // Red
  };

  const getStatus = () => {
    const normalized = driftScore / maxScore;
    if (normalized <= 0.2) return 'Stable';
    if (normalized <= 0.4) return 'Tension Building';
    if (normalized <= 0.6) return 'High Instability';
    return 'Escalated';
  };

  const color = getColor();
  const status = getStatus();

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '20px',
        border: isEscalated ? `2px solid ${color}60` : '2px solid rgba(255, 255, 255, 0.08)',
        boxShadow: isHovered
          ? (isEscalated
            ? `0 0 40px ${color}40, 0 12px 24px rgba(0, 0, 0, 0.5), 0 4px 8px rgba(0, 0, 0, 0.3)`
            : '0 12px 24px rgba(0, 0, 0, 0.5), 0 4px 8px rgba(0, 0, 0, 0.3)')
          : (isEscalated
            ? `0 0 30px ${color}30, 0 8px 16px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.2)`
            : '0 8px 16px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.2)'),
        position: 'relative',
        overflow: 'hidden',
        transition: 'all 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        backdropFilter: 'blur(10px)',
        transform: isHovered ? 'translateY(-2px)' : 'translateY(0)',
        cursor: 'default'
      }}>
      {/* Background pulse animation when escalated */}
      {isEscalated && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: `radial-gradient(circle at center, ${color}15 0%, transparent 70%)`,
          animation: 'pulse 2s ease-in-out infinite',
          pointerEvents: 'none'
        }} />
      )}

      <div style={{ position: 'relative', zIndex: 1 }}>
        {/* Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '16px'
        }}>
          <h3 style={{
            margin: 0,
            fontSize: '13px',
            fontWeight: '700',
            color: 'rgba(255, 255, 255, 0.9)',
            letterSpacing: '1.2px',
            textTransform: 'uppercase'
          }}>
            Epistemic Stability
          </h3>
          <span style={{
            fontSize: '20px',
            fontWeight: '700',
            color: color,
            fontFamily: 'monospace',
            textShadow: `0 0 10px ${color}60`,
            letterSpacing: '1px'
          }}>
            {driftScore.toFixed(1)} / {maxScore.toFixed(1)}
          </span>
        </div>

        {/* Progress Bar Container */}
        <div style={{
          background: 'rgba(0, 0, 0, 0.3)',
          borderRadius: '10px',
          height: '28px',
          position: 'relative',
          overflow: 'hidden',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: 'inset 0 2px 4px rgba(0, 0, 0, 0.3)'
        }}>
          {/* Animated Progress Bar */}
          <div
            ref={barRef}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              bottom: 0,
              width: `${percentage}%`,
              background: `linear-gradient(90deg, ${color}cc 0%, ${color} 50%, ${color}cc 100%)`,
              transition: 'width 600ms cubic-bezier(0.4, 0, 0.2, 1)',
              boxShadow: isEscalated ? `0 0 15px ${color}80, inset 0 1px 0 rgba(255,255,255,0.2)` : 'inset 0 1px 0 rgba(255,255,255,0.2)',
              backgroundSize: '200% 100%',
              animation: isEscalated ? 'barShimmer 3s ease-in-out infinite' : 'none'
            }}
          />

          {/* Threshold markers */}
          <div style={{
            position: 'absolute',
            left: '40%',
            top: 0,
            bottom: 0,
            width: '1px',
            background: 'rgba(255, 255, 255, 0.2)'
          }} />
          <div style={{
            position: 'absolute',
            left: '60%',
            top: 0,
            bottom: 0,
            width: '1px',
            background: 'rgba(255, 255, 255, 0.2)'
          }} />
        </div>

        {/* Status */}
        <div style={{
          marginTop: '16px',
          fontSize: '13px',
          color: color,
          fontWeight: '700',
          textAlign: 'center',
          textTransform: 'uppercase',
          letterSpacing: '1.2px',
          textShadow: `0 0 8px ${color}50`,
          padding: '8px 16px',
          background: `${color}10`,
          borderRadius: '8px',
          border: `1px solid ${color}30`
        }}>
          {status}
        </div>
      </div>

      {/* CSS Animation Keyframes */}
      <style>{`
        @keyframes pulse {
          0%, 100% {
            opacity: 0.3;
            transform: scale(1);
          }
          50% {
            opacity: 0.6;
            transform: scale(1.05);
          }
        }

        @keyframes barShimmer {
          0% {
            background-position: 0% 50%;
          }
          50% {
            background-position: 100% 50%;
          }
          100% {
            background-position: 0% 50%;
          }
        }
      `}</style>
    </div>
  );
};

export default DriftMeter;
