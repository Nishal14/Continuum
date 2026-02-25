/**
 * Demo/Testing version of Sidebar with mock data controls
 *
 * Use this file to test visual states without backend connection.
 * Replace Sidebar.tsx import in entry point with this for testing.
 */

import React, { useState } from 'react';
import DriftMeter from './components/DriftMeter';
import DriftTimeline from './components/DriftTimeline';
import EscalationCard from './components/EscalationCard';
import IntegritySnapshot from './components/IntegritySnapshot';
import type { DriftEvent } from './types';

// Mock test states
const TEST_STATES = {
  stable: {
    name: 'Stable Conversation',
    driftScore: 0.3,
    driftVelocity: 0.05,
    activeCommitments: 8,
    contradictions: 0,
    structuralState: 'Stable',
    trendDirection: 'Steady',
    escalationVisible: false,
    escalationStatus: null,
    k2Confidence: undefined,
    k2Explanation: undefined,
    events: []
  },
  tension: {
    name: 'Tension Building',
    driftScore: 1.8,
    driftVelocity: 0.32,
    activeCommitments: 10,
    contradictions: 2,
    structuralState: 'Tension',
    trendDirection: 'Escalating',
    escalationVisible: false,
    escalationStatus: null,
    k2Confidence: undefined,
    k2Explanation: undefined,
    events: [
      { id: '1', turn: 8, magnitude: 0.28, reason: 'Polarity Flip' },
      { id: '2', turn: 7, magnitude: 0.35, reason: 'Stance Shift' },
      { id: '3', turn: 6, magnitude: 0.22, reason: 'Confidence Drop' },
      { id: '4', turn: 5, magnitude: -0.08, reason: 'Stabilization' }
    ]
  },
  escalating: {
    name: 'Escalation Triggered',
    driftScore: 2.3,
    driftVelocity: 0.47,
    activeCommitments: 12,
    contradictions: 3,
    structuralState: 'Unstable',
    trendDirection: 'Escalating',
    escalationVisible: true,
    escalationStatus: 'pending',
    k2Confidence: undefined,
    k2Explanation: undefined,
    events: [
      { id: '1', turn: 10, magnitude: 0.42, reason: 'Structural Break' },
      { id: '2', turn: 9, magnitude: 0.31, reason: 'Stance Shift' },
      { id: '3', turn: 8, magnitude: 0.28, reason: 'Polarity Flip' },
      { id: '4', turn: 7, magnitude: 0.35, reason: 'Confidence Drop' },
      { id: '5', turn: 6, magnitude: -0.05, reason: 'Stabilization' },
      { id: '6', turn: 5, magnitude: 0.19, reason: 'Minor Drift' }
    ]
  },
  k2Confirmed: {
    name: 'K2 Confirmed',
    driftScore: 2.5,
    driftVelocity: 0.41,
    activeCommitments: 12,
    contradictions: 4,
    structuralState: 'Unstable',
    trendDirection: 'Escalating',
    escalationVisible: true,
    escalationStatus: 'confirmed',
    k2Confidence: 0.91,
    k2Explanation: 'Direct contradiction detected between turn 7 and turn 11. User initially claimed Python superior for data science, now states it is problematic for concurrent programming.',
    events: [
      { id: '1', turn: 11, magnitude: 0.52, reason: 'Direct Contradiction' },
      { id: '2', turn: 10, magnitude: 0.42, reason: 'Structural Break' },
      { id: '3', turn: 9, magnitude: 0.31, reason: 'Stance Shift' },
      { id: '4', turn: 8, magnitude: 0.28, reason: 'Polarity Flip' },
      { id: '5', turn: 7, magnitude: 0.35, reason: 'Confidence Drop' },
      { id: '6', turn: 6, magnitude: -0.05, reason: 'Stabilization' }
    ]
  },
  k2Override: {
    name: 'K2 Override',
    driftScore: 2.1,
    driftVelocity: 0.25,
    activeCommitments: 10,
    contradictions: 2,
    structuralState: 'Unstable',
    trendDirection: 'Steady',
    escalationVisible: true,
    escalationStatus: 'override',
    k2Confidence: undefined,
    k2Explanation: 'Heuristic detected false positive - user statement represents contextual refinement, not epistemic contradiction.',
    events: [
      { id: '1', turn: 8, magnitude: 0.38, reason: 'Contextual Shift' },
      { id: '2', turn: 7, magnitude: 0.29, reason: 'Refinement' },
      { id: '3', turn: 6, magnitude: 0.22, reason: 'Clarification' }
    ]
  },
  recovering: {
    name: 'Recovery Phase - Unstable but Recovering',
    driftScore: 2.2,
    driftVelocity: -0.15,
    activeCommitments: 9,
    contradictions: 1,
    structuralState: 'Unstable',
    trendDirection: 'Recovering',
    escalationVisible: false,
    escalationStatus: null,
    k2Confidence: undefined,
    k2Explanation: undefined,
    events: [
      { id: '1', turn: 12, magnitude: -0.12, reason: 'Decay' },
      { id: '2', turn: 11, magnitude: -0.08, reason: 'Stabilization' },
      { id: '3', turn: 10, magnitude: -0.05, reason: 'Recovery' },
      { id: '4', turn: 9, magnitude: 0.02, reason: 'Minor Adjustment' }
    ]
  }
};

const SidebarDemo: React.FC = () => {
  const [currentState, setCurrentState] = useState<keyof typeof TEST_STATES>('stable');

  const state = TEST_STATES[currentState];

  return (
    <div style={{
      padding: '16px',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      width: '400px',
      minHeight: '600px',
      background: 'linear-gradient(180deg, #0f0f1e 0%, #1a1a2e 100%)',
      color: '#ffffff'
    }}>
      {/* Header */}
      <header style={{
        marginBottom: '20px',
        borderBottom: '2px solid rgba(255, 255, 255, 0.1)',
        paddingBottom: '12px'
      }}>
        <h1 style={{
          margin: 0,
          fontSize: '22px',
          fontWeight: 'bold',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          letterSpacing: '0.5px'
        }}>
          🧭 CONTINUUM
        </h1>
        <p style={{
          margin: '4px 0 0',
          fontSize: '12px',
          color: 'rgba(255, 255, 255, 0.5)',
          letterSpacing: '0.5px'
        }}>
          Epistemic Stability Monitor (DEMO)
        </p>
      </header>

      {/* Test State Selector */}
      <div style={{
        marginBottom: '20px',
        padding: '12px',
        background: 'rgba(102, 126, 234, 0.1)',
        borderRadius: '8px',
        border: '1px solid rgba(102, 126, 234, 0.3)'
      }}>
        <div style={{
          fontSize: '11px',
          fontWeight: '600',
          color: 'rgba(255, 255, 255, 0.6)',
          marginBottom: '8px',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          Test State: {state.name}
        </div>
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '6px'
        }}>
          {Object.keys(TEST_STATES).map((key) => (
            <button
              key={key}
              onClick={() => setCurrentState(key as keyof typeof TEST_STATES)}
              style={{
                padding: '6px 12px',
                fontSize: '11px',
                fontWeight: '500',
                background: currentState === key
                  ? 'rgba(102, 126, 234, 0.6)'
                  : 'rgba(255, 255, 255, 0.1)',
                color: '#ffffff',
                border: currentState === key
                  ? '1px solid rgba(102, 126, 234, 0.8)'
                  : '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '4px',
                cursor: 'pointer',
                transition: 'all 150ms ease'
              }}
            >
              {TEST_STATES[key as keyof typeof TEST_STATES].name}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div>
        {/* 1. Drift Meter */}
        <DriftMeter
          driftScore={state.driftScore}
          maxScore={5.0}
          isEscalated={state.driftScore > 2.0}
        />

        {/* 2. Escalation Card (conditional) */}
        <EscalationCard
          isVisible={state.escalationVisible}
          status={state.escalationStatus as any}
          reason="Cumulative Drift > Threshold"
          k2Confidence={state.k2Confidence}
          k2Explanation={state.k2Explanation}
        />

        {/* 3. Drift Timeline */}
        <DriftTimeline events={state.events} />

        {/* 4. Integrity Snapshot */}
        <IntegritySnapshot
          activeCommitments={state.activeCommitments}
          contradictions={state.contradictions}
          driftVelocity={state.driftVelocity}
          structuralState={state.structuralState}
          trendDirection={state.trendDirection}
        />
      </div>

      {/* Footer */}
      <footer style={{
        marginTop: '20px',
        paddingTop: '12px',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)',
        fontSize: '11px',
        color: 'rgba(255, 255, 255, 0.4)',
        textAlign: 'center'
      }}>
        <p style={{ margin: 0 }}>
          Powered by K2 Think · Demo Mode
        </p>
        <p style={{
          margin: '4px 0 0',
          fontSize: '10px',
          fontFamily: 'monospace'
        }}>
          Test States Available
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
  );
};

export default SidebarDemo;
