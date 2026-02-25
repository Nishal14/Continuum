/**
 * Integrity Snapshot Component
 *
 * Compact 2-column grid showing key structural metrics.
 */

import React from 'react';

interface IntegritySnapshotProps {
  activeCommitments: number;
  contradictions: number;
  driftVelocity: number;
  structuralState: string;
  trendDirection: string;
}

const IntegritySnapshot: React.FC<IntegritySnapshotProps> = ({
  activeCommitments,
  contradictions,
  driftVelocity,
  structuralState,
  trendDirection
}) => {
  // Color logic for structural state
  const structuralStateColor = structuralState === 'Unstable'
    ? '#e74c3c'
    : structuralState === 'Tension'
    ? '#f1c40f'
    : '#2ecc71';

  // Arrow and color for trend direction
  const trendArrow = trendDirection === 'Escalating'
    ? '↑'
    : trendDirection === 'Recovering'
    ? '↓'
    : '→';

  const trendColor = trendDirection === 'Escalating'
    ? '#e74c3c'
    : trendDirection === 'Recovering'
    ? '#2ecc71'
    : '#8b5cf6';

  const metrics = [
    {
      label: 'Active Commitments',
      value: activeCommitments,
      color: '#3b82f6'
    },
    {
      label: 'Contradictions',
      value: contradictions,
      color: contradictions > 0 ? '#e74c3c' : '#2ecc71'
    },
    {
      label: 'Drift Velocity',
      value: driftVelocity.toFixed(2),
      color: driftVelocity > 0.4 ? '#e74c3c' : driftVelocity > 0.2 ? '#f1c40f' : '#2ecc71'
    },
    {
      label: 'Structural State',
      value: structuralState,
      color: structuralStateColor,
      isText: true,
      secondaryValue: `${trendArrow} ${trendDirection}`,
      secondaryColor: trendColor
    }
  ];

  return (
    <div style={{
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
      borderRadius: '12px',
      padding: '16px',
      border: '1px solid rgba(255, 255, 255, 0.1)'
    }}>
      {/* Header */}
      <h3 style={{
        margin: '0 0 16px',
        fontSize: '14px',
        fontWeight: '600',
        color: '#ffffff',
        letterSpacing: '0.5px'
      }}>
        STRUCTURAL SNAPSHOT
      </h3>

      {/* Metrics Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '12px'
      }}>
        {metrics.map((metric, index) => (
          <div
            key={index}
            style={{
              background: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '8px',
              padding: '12px',
              borderLeft: `3px solid ${metric.color}`,
              transition: 'transform 200ms ease-out',
              cursor: 'default'
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLDivElement).style.transform = 'translateY(0)';
            }}
          >
            {/* Label */}
            <div style={{
              fontSize: '10px',
              textTransform: 'uppercase',
              color: 'rgba(255, 255, 255, 0.5)',
              fontWeight: '600',
              letterSpacing: '0.5px',
              marginBottom: '6px'
            }}>
              {metric.label}
            </div>

            {/* Value */}
            <div style={{
              fontSize: metric.isText ? '12px' : '20px',
              fontWeight: '700',
              color: metric.color,
              fontFamily: metric.isText ? 'system-ui' : 'monospace',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {metric.value}
            </div>

            {/* Secondary Value (Trend Direction) */}
            {metric.secondaryValue && (
              <div style={{
                fontSize: '11px',
                fontWeight: '600',
                color: metric.secondaryColor,
                marginTop: '4px',
                opacity: 0.9,
                letterSpacing: '0.3px'
              }}>
                {metric.secondaryValue}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div style={{
        marginTop: '12px',
        padding: '8px',
        background: 'rgba(255, 255, 255, 0.02)',
        borderRadius: '6px',
        fontSize: '10px',
        color: 'rgba(255, 255, 255, 0.4)',
        textAlign: 'center'
      }}>
        Real-time structural integrity monitoring
      </div>
    </div>
  );
};

export default IntegritySnapshot;
