/**
 * Background service worker for Continuum extension.
 *
 * Handles:
 * - Rate limiting and batching
 * - API calls to FastAPI backend
 * - Message routing between content script and sidebar
 */

const BACKEND_URL = 'http://localhost:8000';
const MAX_RETRIES = 3;

interface Turn {
  id: number;
  speaker: 'user' | 'model';
  text: string;
  ts: string;
}

// Per-conversation promise chain — ensures turns are sent in order and
// processing starts immediately (no setTimeout delay that risks MV3 service
// worker suspension and in-memory data loss).
const processingQueues: Map<string, Promise<void>> = new Map();

console.log('[Continuum] Background service worker loaded');

/**
 * Handle new turns from content script.
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[Continuum] Received message:', message.type);

  if (message.type === 'NEW_TURNS') {
    // Return true to keep the message port (and service worker) alive.
    // Chrome suspends MV3 service workers when the port closes — so we must
    // NOT call sendResponse until all turns are fully processed.
    handleNewTurns(message.payload).finally(() => {
      sendResponse({ status: 'done' });
    });
    return true; // CRITICAL: keeps service worker alive during async processing
  } else if (message.type === 'RECONCILE') {
    handleReconcile(message.payload).then(sendResponse);
    return true; // Async response
  } else if (message.type === 'AUTO_FILL') {
    handleAutoFill(message.payload).then(sendResponse);
    return true;
  }

  return false;
});

/**
 * Queue turns for sequential processing.
 * Chains onto the existing queue so turns always arrive at the backend
 * in order, and the first fetch() call keeps the service worker alive.
 */
function handleNewTurns(payload: { conversationId: string; turns: Turn[] }): Promise<void> {
  const { conversationId, turns } = payload;
  console.log(`[Continuum] Queuing ${turns.length} turns for ${conversationId}`);

  const prev = processingQueues.get(conversationId) ?? Promise.resolve();
  const next = prev.then(async () => {
    console.log(`[Continuum] Processing ${turns.length} turns for ${conversationId}`);
    for (const turn of turns) {
      await analyzeTurn(conversationId, turn);
    }
  });

  processingQueues.set(conversationId, next);

  // Clean up reference once this batch finishes
  next.finally(() => {
    if (processingQueues.get(conversationId) === next) {
      processingQueues.delete(conversationId);
    }
  });

  return next;
}

/**
 * Analyze a single turn via backend API.
 */
async function analyzeTurn(conversationId: string, turn: Turn, retries = 0): Promise<void> {
  console.log('[Continuum] Sending to backend:', conversationId, turn);

  try {
    const response = await fetch(`${BACKEND_URL}/analyze-turn`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        new_turn: turn
      })
    });

    console.log('[Continuum] Backend response status:', response.status);

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const result = await response.json();

    console.log('[Continuum] Backend analysis result:', result);

    // If there are new alerts, notify user
    if (result.alerts && result.alerts.length > 0) {
      showNotification(result.alerts[0]);

      // Store alerts in extension storage
      chrome.storage.local.get(['alerts'], (data) => {
        const alerts = data.alerts || [];
        alerts.push(...result.alerts);
        chrome.storage.local.set({ alerts });
      });
    }

    // Update badge
    updateBadge(result.alerts?.length || 0);

  } catch (error) {
    console.error('[Continuum] API error:', error);

    if (retries < MAX_RETRIES) {
      console.log(`[Continuum] Retrying... (${retries + 1}/${MAX_RETRIES})`);
      await new Promise(resolve => setTimeout(resolve, 2000 * (retries + 1)));
      return analyzeTurn(conversationId, turn, retries + 1);
    }
  }
}

/**
 * Handle reconciliation request.
 */
async function handleReconcile(payload: { conversationId: string; alertId: string }) {
  try {
    const response = await fetch(`${BACKEND_URL}/reconcile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        conversation_id: payload.conversationId,
        alert_id: payload.alertId,
        mode: 'suggest'
      })
    });

    const result = await response.json();
    return { success: true, data: result };
  } catch (error) {
    console.error('[Continuum] Reconcile error:', error);
    return { success: false, error: String(error) };
  }
}

/**
 * Handle auto-fill request.
 */
async function handleAutoFill(payload: { text: string }) {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab.id) {
      return { success: false, error: 'No active tab' };
    }

    const response = await chrome.tabs.sendMessage(tab.id, {
      type: 'INJECT_TEXT',
      text: payload.text
    });

    return response;
  } catch (error) {
    console.error('[Continuum] Auto-fill error:', error);
    return { success: false, error: String(error) };
  }
}

/**
 * Show notification for new alert.
 */
function showNotification(alert: any) {
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'logo.png',
    title: 'Continuum Alert',
    message: alert.message || 'Epistemic drift detected',
    priority: alert.severity === 'high' ? 2 : 1
  });
}

/**
 * Update extension badge.
 */
function updateBadge(count: number) {
  if (count > 0) {
    chrome.action.setBadgeText({ text: String(count) });
    chrome.action.setBadgeBackgroundColor({ color: '#FF6B6B' });
  } else {
    chrome.action.setBadgeText({ text: '' });
  }
}
