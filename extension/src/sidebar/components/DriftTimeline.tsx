/**
 * Drift Timeline Component
 *
 * Displays last 6 drift events with slide-in animations.
 */

import React, { useEffect, useState } from 'react';

interface DriftEvent {
  id: string;
  turn: number;
  magnitude: number;
  reason: string;
}

interface DriftTimelineProps {
  events: DriftEvent[];
}

const DriftTimeline: React.FC<DriftTimelineProps> = ({ events }) => {
  const [visibleEvents, setVisibleEvents] = useState<DriftEvent[]>([]);

  useEffect(() => {
    // Take last 6 events and reverse for chronological display
    const last6 = events.slice(-6).reverse();
    setVisibleEvents(last6);
  }, [events]);

  const getEventColor = (magnitude: number) => {
    if (magnitude < 0) return '#2ecc71'; // Green for decay/stabilization
    if (magnitude < 0.2) return '#f1c40f'; // Yellow for small drift
    return '#e74c3c'; // Red for significant drift
  };

  const getEventIcon = (magnitude: number) => {
    if (magnitude < 0) return '↓'; // Decay
    if (magnitude < 0.2) return '→'; // Small change
    return '↑'; // Increase
  };

  if (visibleEvents.length === 0) {
    return (
      <div style={{
        background: 'rgba(255, 255, 255, 0.03)',
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '16px',
        textAlign: 'center',
        color: 'rgba(255, 255, 255, 0.4)',
        fontSize: '13px'
      }}>
        No drift events detected
      </div>
    );
  }

  return (
    <div style={{
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
      borderRadius: '12px',
      padding: '16px',
      marginBottom: '16px',
      border: '1px solid rgba(255, 255, 255, 0.1)'
    }}>
      {/* Header */}
      <h3 style={{
        margin: '0 0 12px',
        fontSize: '14px',
        fontWeight: '600',
        color: '#ffffff',
        letterSpacing: '0.5px'
      }}>
        DRIFT TIMELINE
      </h3>

      {/* Events List */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px'
      }}>
        {visibleEvents.map((event, index) => {
          const color = getEventColor(event.magnitude);
          const icon = getEventIcon(event.magnitude);
          const opacity = 1 - (index * 0.1); // Fade older entries

          return (
            <div
              key={event.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px',
                background: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '8px',
                borderLeft: `3px solid ${color}`,
                opacity: opacity,
                animation: 'slideIn 300ms ease-out',
                animationDelay: `${index * 50}ms`,
                animationFillMode: 'backwards'
              }}
            >
              {/* Turn number */}
              <div style={{
                fontSize: '12px',
                fontWeight: '600',
                color: 'rgba(255, 255, 255, 0.5)',
                minWidth: '50px',
                fontFamily: 'monospace'
              }}>
                Turn {event.turn}
              </div>

              {/* Magnitude with icon */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                minWidth: '60px'
              }}>
                <span style={{
                  fontSize: '14px',
                  color: color
                }}>
                  {icon}
                </span>
                <span style={{
                  fontSize: '13px',
                  fontWeight: '600',
                  color: color,
                  fontFamily: 'monospace'
                }}>
                  {event.magnitude >= 0 ? '+' : ''}{event.magnitude.toFixed(2)}
                </span>
              </div>

              {/* Reason */}
              <div style={{
                flex: 1,
                fontSize: '12px',
                color: 'rgba(255, 255, 255, 0.7)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {event.reason}
              </div>
            </div>
          );
        })}
      </div>

      {/* CSS Animation */}
      <style>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-10px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
};

export default DriftTimeline;
