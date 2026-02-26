/**
 * React sidebar UI for Continuum - Premium Drift Visualization Panel
 *
 * Features:
 * - Animated drift meter with smooth transitions
 * - Drift timeline showing last 6 events
 * - Dynamic escalation card with K2 verification
 * - Structural integrity snapshot
 */

import React, { useState, useEffect, useRef } from 'react';
import DriftMeter from './components/DriftMeter';
import DriftTimeline from './components/DriftTimeline';
import EscalationCard from './components/EscalationCard';
import IntegritySnapshot from './components/IntegritySnapshot';
import GraphView from './components/GraphView';
import type { Alert, DriftEvent, MetricsResponse, K2StatusResponse } from './types';

const API_BASE_URL = 'http://localhost:8000';
const METRICS_POLL_INTERVAL = 1500; // 1.5 seconds
const K2_POLL_INTERVAL = 2000; // 2 seconds when escalated
const K2_TIMEOUT = 90000; // 90 seconds timeout

// Explicit state machine for escalation lifecycle
type EscalationState = 'idle' | 'escalated_pending' | 'k2_confirmed' | 'k2_overridden' | 'k2_failed';

const Sidebar: React.FC = () => {
  // State
  const [conversationId, setConversationId] = useState<string>('');
  const [driftScore, setDriftScore] = useState<number>(0);
  const [driftVelocity, setDriftVelocity] = useState<number>(0);
  const [driftEvents, setDriftEvents] = useState<DriftEvent[]>([]);
  const [isRecovering, setIsRecovering] = useState<boolean>(false);
  const [activeCommitments, setActiveCommitments] = useState<number>(0);
  const [contradictions, setContradictions] = useState<number>(0);

  // Tab state
  const [activeTab, setActiveTab] = useState<'overview' | 'graph'>('overview');

  // Escalation state machine
  const [escalationState, setEscalationState] = useState<EscalationState>('idle');
  const [escalationReason, setEscalationReason] = useState<string>('');
  const [k2Confidence, setK2Confidence] = useState<number>(0);
  const [k2Explanation, setK2Explanation] = useState<string>('');

  // Refs for tracking
  const escalationStartTimeRef = useRef<number>(0);
  const escalationStateRef = useRef<EscalationState>(escalationState);
  escalationStateRef.current = escalationState;

  // Extract conversation ID from a ChatGPT URL
  const extractConversationId = (url: string): string => {
    const match = url.match(/\/c\/([a-zA-Z0-9-]+)/);
    return match ? match[1] : 'default';
  };

  // Get conversation ID from URL, and update it on navigation
  useEffect(() => {
    // Safety check for Chrome extension context
    if (typeof chrome === 'undefined' || !chrome.tabs) {
      console.warn('[Continuum] Chrome tabs API not available');
      setConversationId('default');
      return;
    }

    // Set initial conversation ID from current tab URL
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const url = tabs[0]?.url || '';
      console.log('[Continuum] Current URL:', url);
      const id = extractConversationId(url);
      console.log('[Continuum] Conversation ID extracted:', id);
      setConversationId(id);
    });

    // Listen for URL changes (SPA navigation to new chats)
    const onTabUpdated = (tabId: number, changeInfo: chrome.tabs.TabChangeInfo) => {
      if (!changeInfo.url) return;
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]?.id === tabId) {
          const id = extractConversationId(changeInfo.url!);
          console.log('[Continuum] URL changed, new conversation ID:', id);
          setConversationId(id);
        }
      });
    };

    chrome.tabs.onUpdated.addListener(onTabUpdated);
    return () => {
      chrome.tabs.onUpdated.removeListener(onTabUpdated);
    };
  }, []);

  // Reset all state when switching to a different conversation
  const prevConversationIdRef = useRef<string>('');
  useEffect(() => {
    if (!conversationId || conversationId === prevConversationIdRef.current) return;
    prevConversationIdRef.current = conversationId;

    setDriftScore(0);
    setDriftVelocity(0);
    setDriftEvents([]);
    setIsRecovering(false);
    setActiveCommitments(0);
    setContradictions(0);
    setEscalationState('idle');
    setEscalationReason('');
    setK2Confidence(0);
    setK2Explanation('');
  }, [conversationId]);

  // Setup polling
  useEffect(() => {
    if (!conversationId) return;

    let isMounted = true;

    const pollMetrics = async () => {
      if (!conversationId || !isMounted) {
        return;
      }

      try {
        const url = `${API_BASE_URL}/conversations/${conversationId}/metrics`;
        const response = await fetch(url);

        if (!response.ok || !isMounted) {
          return;
        }

        const data: MetricsResponse = await response.json();
        if (!isMounted) return;

        // Update drift state
        setDriftScore(data.drift?.cumulative_drift_score || 0);
        setDriftVelocity(data.drift?.drift_velocity || 0);
        setIsRecovering(data.drift?.is_recovering || false);

        // Update structural metrics
        setActiveCommitments(data.commitments?.active || 0);
        setContradictions(data.contradictions?.count || 0);

        // Check for escalation trigger (only transition from idle to pending)
        if (data.escalation?.total_escalations > 0 && escalationStateRef.current === 'idle') {
          console.log('[Continuum] Escalation triggered');
          setEscalationState('escalated_pending');
          setEscalationReason('Cumulative Drift > Threshold');
          escalationStartTimeRef.current = Date.now();
        }
      } catch (error) {
        if (isMounted) {
          console.warn('[Continuum] Failed to fetch metrics:', error);
        }
      }
    };

    // Initial fetch
    pollMetrics();

    // Poll metrics every 3 seconds
    const intervalId = setInterval(pollMetrics, METRICS_POLL_INTERVAL);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [conversationId]);

  // Setup K2 polling when escalated
  useEffect(() => {
    // Only start polling if we transition INTO escalated_pending state
    // Once polling is active, state changes should be handled by the polling logic itself
    if (!conversationId || escalationState !== 'escalated_pending') {
      return;
    }

    console.log('[Continuum] Starting K2 polling');

    // Track if this effect instance is still mounted
    let isMounted = true;

    // Wrap fetch in a closure that respects the mounted state
    const pollK2 = async () => {
      if (!isMounted) return;

      try {
        const response = await fetch(`${API_BASE_URL}/conversations/${conversationId}/k2-status`);

        if (!response.ok || !isMounted) {
          return;
        }

        const data: K2StatusResponse = await response.json();
        if (!isMounted) return;

        console.log('[Continuum] K2 status response:', data);

        // State transitions based on K2 response
        if (data.status === 'completed') {
          if (data.result_type === 'confirmed') {
            console.log('[Continuum] K2 CONFIRMED contradiction');
            setEscalationState('k2_confirmed');
            setK2Confidence(data.k2_confidence || 0);
            setK2Explanation(data.k2_explanation || 'Contradiction confirmed by K2 reasoning');
          } else if (data.result_type === 'overridden') {
            console.log('[Continuum] K2 OVERRIDDEN - false positive');
            setEscalationState('k2_overridden');
            setK2Explanation(data.k2_explanation || 'Heuristic false positive - no actual contradiction');
          }
        } else if (data.status === 'failed') {
          console.log('[Continuum] K2 verification FAILED');
          setEscalationState('k2_failed');
          setK2Explanation('K2 reasoning failed. Heuristic result retained.');
        } else if (data.status === 'pending') {
          console.log('[Continuum] K2 status: pending (still verifying)');
          // Continue polling - timeout will handle failures
        }
      } catch (error) {
        if (isMounted) {
          console.error('[Continuum] Failed to fetch K2 status:', error);
        }
      }
    };

    // Initial fetch
    pollK2();

    // Poll K2 status every 2 seconds
    const intervalId = setInterval(pollK2, K2_POLL_INTERVAL);

    // Set timeout to prevent infinite polling
    const timeoutId = setTimeout(() => {
      if (isMounted) {
        console.warn('[Continuum] K2 verification TIMEOUT (90s safety limit)');
        setEscalationState('k2_failed');
        setK2Explanation('K2 reasoning timed out. Heuristic result retained.');
      }
    }, K2_TIMEOUT);

    return () => {
      console.log('[Continuum] Cleanup: stopping K2 polling');
      isMounted = false;
      clearInterval(intervalId);
      clearTimeout(timeoutId);
    };
  }, [conversationId, escalationState]);

  // Mock drift events (replace with real data from backend)
  useEffect(() => {
    // In production, fetch drift events from metrics endpoint
    // For now, generate mock events based on drift score
    const mockEvents: DriftEvent[] = [];
    const eventCount = Math.min(Math.floor(driftScore * 2), 6);

    for (let i = 0; i < eventCount; i++) {
      mockEvents.push({
        id: `drift_${i + 1}`,
        turn: 8 - i,
        magnitude: Math.random() * 0.5 + 0.2,
        reason: ['Polarity Flip', 'Stance Shift', 'Structural Break', 'Confidence Drop'][Math.floor(Math.random() * 4)]
      });
    }

    setDriftEvents(mockEvents);
  }, [driftScore]);

  // A) Primary Structural State (based on drift_score only)
  const structuralState = driftScore >= 2.0
    ? 'Unstable'
    : driftScore >= 1.0
    ? 'Tension'
    : 'Stable';

  // B) Secondary Trend Indicator (based on velocity & recovery)
  // Escalating: drift_velocity > 0.3 (escalation threshold)
  // Recovering: drift_velocity < 0 AND is_recovering flag
  // Steady: otherwise
  const trendDirection = driftVelocity > 0.3
    ? 'Escalating'
    : (driftVelocity < 0 && isRecovering)
    ? 'Recovering'
    : 'Steady';

  return (
    <div style={{
      padding: '20px',
      fontFamily: 'system-ui, -apple-system, "Segoe UI", sans-serif',
      width: '400px',
      minHeight: '600px',
      background: 'linear-gradient(180deg, #0a0a15 0%, #141428 50%, #1a1a2e 100%)',
      color: '#ffffff',
      position: 'relative'
    }}>
      {/* Ambient background glow */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: '200px',
        background: 'radial-gradient(ellipse at top, rgba(102, 126, 234, 0.1) 0%, transparent 70%)',
        pointerEvents: 'none'
      }} />

      <div style={{ position: 'relative', zIndex: 1 }}>
        {/* Header */}
        <header style={{
          marginBottom: '24px',
          borderBottom: '2px solid rgba(255, 255, 255, 0.08)',
          paddingBottom: '16px'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            <img
              src={chrome.runtime.getURL('logo.png')}
              alt="Continuum Logo"
              style={{
                width: '44px',
                height: '32px',
                imageRendering: 'crisp-edges'
              }}
            />
            <h1 style={{
              margin: 0,
              fontSize: '24px',
              fontWeight: '800',
              color: '#667eea',
              letterSpacing: '1px',
              textShadow: '0 0 20px rgba(102, 126, 234, 0.4)'
            }}>
              CONTINUUM
            </h1>
          </div>
          <p style={{
            margin: '8px 0 0',
            fontSize: '12px',
            color: 'rgba(255, 255, 255, 0.6)',
            letterSpacing: '0.8px',
            fontWeight: '500'
          }}>
            Epistemic Stability Monitor
          </p>
        </header>

      {/* Tab Switcher */}
      <div style={{
        display: 'flex',
        gap: '4px',
        marginBottom: '20px',
        background: 'rgba(255,255,255,0.05)',
        borderRadius: '10px',
        padding: '4px',
      }}>
        {(['overview', 'graph'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              flex: 1,
              padding: '7px 0',
              borderRadius: '7px',
              border: 'none',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: '600',
              letterSpacing: '0.5px',
              textTransform: 'uppercase',
              background: activeTab === tab ? 'rgba(102,126,234,0.22)' : 'transparent',
              color: activeTab === tab ? '#667eea' : 'rgba(255,255,255,0.38)',
              transition: 'background 200ms ease, color 200ms ease',
            }}
          >
            {tab === 'overview' ? 'Overview' : 'Graph'}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
      <div>
        {/* 1. Drift Meter */}
        <DriftMeter
          driftScore={driftScore}
          maxScore={5.0}
          isEscalated={driftScore > 2.0}
        />

        {/* 2. Escalation Card (conditional) */}
        <EscalationCard
          isVisible={escalationState !== 'idle'}
          status={
            escalationState === 'escalated_pending' ? 'pending' :
            escalationState === 'k2_confirmed' ? 'confirmed' :
            escalationState === 'k2_overridden' ? 'override' :
            escalationState === 'k2_failed' ? 'failed' :
            null
          }
          reason={escalationReason}
          k2Confidence={k2Confidence}
          k2Explanation={k2Explanation}
        />

        {/* 3. Drift Timeline */}
        <DriftTimeline events={driftEvents} />

        {/* 4. Integrity Snapshot */}
        <IntegritySnapshot
          activeCommitments={activeCommitments}
          contradictions={contradictions}
          driftVelocity={driftVelocity}
          structuralState={structuralState}
          trendDirection={trendDirection}
        />
      </div>
      )}

      {/* Graph Tab */}
      {activeTab === 'graph' && (
        <GraphView conversationId={conversationId} apiBaseUrl={API_BASE_URL} />
      )}

        {/* Footer */}
        <footer style={{
          marginTop: '24px',
          paddingTop: '16px',
          borderTop: '2px solid rgba(255, 255, 255, 0.08)',
          fontSize: '11px',
          color: 'rgba(255, 255, 255, 0.5)',
          textAlign: 'center'
        }}>
          <p style={{
            margin: 0,
            fontWeight: '500',
            letterSpacing: '0.5px'
          }}>
            Powered by K2 Think · Real-time Analysis
          </p>
          <p style={{
            margin: '6px 0 0',
            fontSize: '10px',
            fontFamily: 'monospace',
            color: 'rgba(255, 255, 255, 0.3)',
            letterSpacing: '0.5px'
          }}>
            {conversationId.slice(0, 8)}... · {new Date().toLocaleTimeString()}
          </p>
        </footer>

      {/* Global Styles */}
      <style>{`
        * {
          box-sizing: border-box;
        }

        ::-webkit-scrollbar {
          width: 6px;
        }

        ::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
        }

        ::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.2);
          border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.3);
        }
      `}</style>
      </div>
    </div>
  );
};

export default Sidebar;
