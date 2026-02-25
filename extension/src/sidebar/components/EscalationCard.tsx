/**
 * Escalation Event Card Component
 *
 * Dynamic card that appears when escalation is triggered, shows K2 verification status.
 */

import React from 'react';

// Inject animation styles once at module load — keeping this outside the component
// prevents the <style> tag from living inside a backdrop-filter compositing layer,
// which causes Chrome to re-evaluate keyframes and restart animations on re-renders.
(() => {
  if (typeof document === 'undefined') return;
  const el = document.createElement('style');
  el.textContent = `
    @keyframes slideDown {
      from { opacity: 0; transform: translateY(-30px) scale(0.95); }
      to   { opacity: 1; transform: translateY(0)     scale(1);    }
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
    @keyframes shimmer {
      0%   { transform: translateX(0);   }
      100% { transform: translateX(50%); }
    }
    @keyframes pulse {
      0%, 100% { opacity: 0.3; transform: translate(-50%, -50%) scale(1);   }
      50%       { opacity: 0.6; transform: translate(-50%, -50%) scale(1.1); }
    }
    @keyframes iconPulse {
      0%, 100% { transform: scale(1);   }
      50%       { transform: scale(1.1); }
    }
    @keyframes dots {
      0%, 20% { opacity: 0; }
      50%      { opacity: 1; }
      100%     { opacity: 0; }
    }
    @keyframes barGlow {
      0%, 100% { opacity: 1;    }
      50%       { opacity: 0.72; }
    }
    .card-inner-content { animation: fadeIn  400ms ease-out;              }
    .confidence-row     { animation: fadeIn  400ms ease-out;              }
    .bar-glow-anim      { }
  `;
  document.head.appendChild(el);
})();

interface EscalationCardProps {
  isVisible: boolean;
  status: 'pending' | 'confirmed' | 'override' | 'failed' | null;
  reason?: string;
  k2Confidence?: number;
  k2Explanation?: string;
}

const EscalationCard: React.FC<EscalationCardProps> = React.memo(({
  isVisible,
  status,
  reason,
  k2Confidence,
  k2Explanation
}) => {
  const [hasAnimated, setHasAnimated] = React.useState(false);
  const [isHovered, setIsHovered] = React.useState(false);

  React.useEffect(() => {
    if (isVisible && !hasAnimated) {
      setHasAnimated(true);
    }
  }, [isVisible, hasAnimated]);

  if (!isVisible || !status) return null;

  const getContent = () => {
    switch (status) {
      case 'pending':
        return {
          icon: '⚡',
          title: 'Escalation Triggered',
          subtitle: reason || 'Cumulative Drift > Threshold',
          message: 'Verifying with K2...',
          color: '#f1c40f',
          showLoading: true
        };
      case 'confirmed':
        return {
          icon: '🧠',
          title: 'K2 Verification Complete',
          subtitle: 'Contradiction Confirmed',
          message: k2Explanation || 'Epistemic tension verified',
          color: '#e74c3c',
          showLoading: false,
          showConfidence: true
        };
      case 'override':
        return {
          icon: '🧠',
          title: 'K2 Override',
          subtitle: 'Heuristic False Positive',
          message: k2Explanation || 'Escalation cancelled by K2 authority',
          color: '#2ecc71',
          showLoading: false
        };
      case 'failed':
        return {
          icon: '⚠️',
          title: 'K2 Verification Timeout',
          subtitle: 'Heuristic Result Retained',
          message: k2Explanation || 'K2 reasoning timed out. Heuristic result retained.',
          color: '#95a5a6',
          showLoading: false
        };
      default:
        return null;
    }
  };

  const content = getContent();
  if (!content) return null;

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        background: `linear-gradient(135deg, ${content.color}20 0%, ${content.color}10 100%)`,
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '20px',
        border: `2px solid ${content.color}40`,
        boxShadow: isHovered
          ? `0 0 40px ${content.color}35, 0 12px 24px rgba(0, 0, 0, 0.5), 0 4px 8px rgba(0, 0, 0, 0.3)`
          : `0 0 30px ${content.color}25, 0 8px 16px rgba(0, 0, 0, 0.4), 0 2px 4px rgba(0, 0, 0, 0.2)`,
        position: 'relative',
        overflow: 'hidden',
        transition: 'box-shadow 300ms ease, transform 300ms ease',
        backdropFilter: 'blur(10px)',
        transform: isHovered ? 'translateY(-2px)' : 'translateY(0)',
        cursor: 'default',
        animation: hasAnimated ? 'slideDown 500ms cubic-bezier(0.34, 1.56, 0.64, 1)' : 'none'
      }}
    >
      {/* Animated background glow for pending state */}
      {content.showLoading && (
        <>
          <div style={{
            position: 'absolute',
            top: 0,
            left: '-100%',
            width: '200%',
            height: '100%',
            background: `linear-gradient(90deg, transparent 0%, ${content.color}40 50%, transparent 100%)`,
            animation: 'shimmer 2.5s ease-in-out infinite',
            pointerEvents: 'none'
          }} />
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            width: '150%',
            height: '150%',
            transform: 'translate(-50%, -50%)',
            background: `radial-gradient(circle, ${content.color}15 0%, transparent 70%)`,
            animation: 'pulse 2s ease-in-out infinite',
            pointerEvents: 'none'
          }} />
        </>
      )}

      <div className="card-inner-content" style={{
        position: 'relative',
        zIndex: 1
      }}>
        {/* Icon and Title */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          marginBottom: '12px'
        }}>
          <span style={{
            fontSize: '28px',
            filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))',
            animation: content.showLoading ? 'iconPulse 2s ease-in-out infinite' : 'none'
          }}>
            {content.icon}
          </span>
          <div style={{ flex: 1 }}>
            <h3 style={{
              margin: 0,
              fontSize: '17px',
              fontWeight: '700',
              color: content.color,
              letterSpacing: '0.4px',
              textShadow: `0 0 10px ${content.color}40`
            }}>
              {content.title}
            </h3>
            <p style={{
              margin: '4px 0 0',
              fontSize: '13px',
              color: 'rgba(255, 255, 255, 0.7)',
              fontWeight: '500',
              letterSpacing: '0.2px'
            }}>
              {content.subtitle}
            </p>
          </div>
        </div>

        {/* Message */}
        <div style={{
          padding: '16px',
          background: 'rgba(0, 0, 0, 0.3)',
          borderRadius: '10px',
          marginTop: '16px',
          borderLeft: `4px solid ${content.color}`,
          boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.2)',
          backdropFilter: 'blur(5px)'
        }}>
          <p style={{
            margin: 0,
            fontSize: '13px',
            color: 'rgba(255, 255, 255, 0.85)',
            lineHeight: '1.5'
          }}>
            {content.message}
            {content.showLoading && (
              <span style={{
                display: 'inline-block',
                animation: 'dots 1.5s infinite'
              }}>
                <span style={{ animationDelay: '0s' }}>.</span>
                <span style={{ animationDelay: '0.2s' }}>.</span>
                <span style={{ animationDelay: '0.4s' }}>.</span>
              </span>
            )}
          </p>
        </div>

        {/* K2 Confidence Badge */}
        {content.showConfidence && k2Confidence !== undefined && (
          <div className="confidence-row" style={{
            marginTop: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <span style={{
              fontSize: '11px',
              color: 'rgba(255, 255, 255, 0.6)',
              textTransform: 'uppercase',
              fontWeight: '700',
              letterSpacing: '0.8px'
            }}>
              Confidence
            </span>
            <div style={{
              flex: 1,
              height: '8px',
              background: 'rgba(0, 0, 0, 0.3)',
              borderRadius: '4px',
              overflow: 'hidden',
              boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.3)'
            }}>
              <div className="bar-glow-anim" style={{
                height: '100%',
                width: `${k2Confidence * 100}%`,
                background: `linear-gradient(90deg, ${content.color} 0%, ${content.color}cc 100%)`,
                transition: 'width 800ms cubic-bezier(0.4, 0, 0.2, 1)',
                boxShadow: `0 0 10px ${content.color}60`
              }} />
            </div>
            <span style={{
              fontSize: '14px',
              fontWeight: '700',
              color: content.color,
              fontFamily: 'monospace',
              textShadow: `0 0 8px ${content.color}60`,
              minWidth: '40px',
              textAlign: 'right'
            }}>
              {(k2Confidence * 100).toFixed(0)}%
            </span>
          </div>
        )}
      </div>

    </div>
  );
});

export default EscalationCard;
