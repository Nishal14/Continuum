/**
 * Type definitions for Continuum Sidebar
 */

export interface Alert {
  id: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  alert_type: string;
  message: string;
  related_commitments: string[];
  suggested_action?: string;
}

export interface DriftEvent {
  id: string;
  turn: number;
  magnitude: number;
  reason: string;
}

export interface MetricsResponse {
  drift: {
    cumulative_drift_score: number;
    drift_velocity: number;
    turns_since_last_drift: number;
    total_drift_events: number;
    is_recovering: boolean;
  };
  commitments: {
    total: number;
    active: number;
    inactive: number;
  };
  contradictions: {
    count: number;
    rate: number;
  };
  escalation: {
    total_escalations: number;
    escalation_rate: number;
  };
}

export interface K2StatusResponse {
  conversation_id: string;
  escalation_active: boolean;
  status: 'pending' | 'completed' | 'override' | 'failed' | null;
  result_type?: 'confirmed' | 'overridden';
  reason?: string;
  k2_confidence?: number;
  k2_explanation?: string;
  timestamp?: string;
}
