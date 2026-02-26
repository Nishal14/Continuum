/**
 * Content script for ChatGPT web UI.
 *
 * Observes DOM for new messages and extracts structured turns.
 */

interface Turn {
  id: number;
  speaker: 'user' | 'model';
  text: string;
  ts: string;
}

let lastSeenTurnId = 0;
let observerActive = false;
const DEBOUNCE_MS = 800;
const NAVIGATION_SETTLE_MS = 600; // Wait for SPA to render new chat content

let currentConversationId = '';

console.log('[Continuum] Content script loaded');

/**
 * Extract turns from ChatGPT DOM.
 *
 * ChatGPT structure (as of 2024):
 * - Messages in divs with data-message-author-role attribute
 * - Text content in markdown containers
 */
function extractTurnsFromDOM(): Turn[] {
  const turns: Turn[] = [];

  // Try multiple selectors for resilience
  const selectors = [
    '[data-message-author-role]',
    '[data-testid^="conversation-turn"]',
    '.group.w-full'  // Fallback
  ];

  let messageNodes: NodeListOf<Element> | null = null;
  let matchedSelector = '';

  for (const selector of selectors) {
    messageNodes = document.querySelectorAll(selector);
    if (messageNodes.length > 0) {
      matchedSelector = selector;
      break;
    }
  }

  console.log('[Continuum] extractTurnsFromDOM: selector=', matchedSelector || 'NONE', 'count=', messageNodes?.length ?? 0);

  if (!messageNodes || messageNodes.length === 0) {
    // Log a sample of the DOM to help debug selector issues
    const sample = document.body?.innerHTML?.slice(0, 500) ?? '';
    console.log('[Continuum] No message nodes found. DOM sample:', sample);
    return [];
  }

  messageNodes.forEach((node, index) => {
    try {
      // Turn ID = 1-based DOM position. Sequential and monotonically increasing,
      // which the backend relies on for ordering commitments (prior.turn_id < current.turn_id).
      // A hash would give arbitrary out-of-order IDs that break contradiction detection.
      const id = index + 1;

      // Only send turns we haven't sent yet (new turns appended at the end)
      if (id <= lastSeenTurnId) return;

      // Determine speaker
      const roleAttr = node.getAttribute('data-message-author-role');
      const speaker: 'user' | 'model' =
        roleAttr === 'user' ? 'user' : 'model';

      // Extract text content — prefer semantic containers, fall back to node itself
      const textElement = node.querySelector('.markdown, .whitespace-pre-wrap');
      const text = ((textElement?.textContent || node.textContent) ?? '').trim().replace(/\s+/g, ' ');

      console.log(`[Continuum] Turn ${id} speaker=${speaker} textLen=${text.length} preview="${text.slice(0, 60)}"`);

      if (!text || text.length < 2) return; // Skip empty

      const ts = new Date().toISOString();
      turns.push({ id, speaker, text, ts });
    } catch (err) {
      console.error('[Continuum] Error extracting turn:', err);
    }
  });

  return turns;
}


/**
 * Send turns to background script.
 */
function sendTurnsToBackground(turns: Turn[]) {
  if (turns.length === 0) return;

  // chrome.runtime itself throws (not just returns undefined) when context is invalidated
  try {
    if (!chrome.runtime?.id) return;
  } catch {
    return; // Extension context invalidated
  }

  console.log('[Continuum] Sending to background:', turns.length, 'turns', turns);

  try {
    chrome.runtime.sendMessage({
      type: 'NEW_TURNS',
      payload: {
        conversationId: getConversationId(),
        turns
      }
    }, (_response) => {
      // Callback itself runs in an async context — needs its own guard
      try {
        if (chrome.runtime.lastError) {
          // Suppress "Extension context invalidated" — expected after reload
          return;
        }
        console.log('[Continuum] Background responded:', _response);
      } catch {
        // Context invalidated between sendMessage and callback firing
      }
    });

    lastSeenTurnId = Math.max(...turns.map(t => t.id));
  } catch {
    // Extension was reloaded/updated — stop silently
  }
}

/**
 * Extract conversation ID from URL or generate one.
 */
function getConversationId(): string {
  const url = window.location.href;
  const match = url.match(/\/c\/([a-zA-Z0-9-]+)/);
  return match ? match[1] : 'default';
}

/**
 * Debounced observer function.
 */
let debounceTimer: number | null = null;

function observeDOM() {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
  }

  debounceTimer = window.setTimeout(() => {
    const newTurns = extractTurnsFromDOM();
    if (newTurns.length > 0) {
      sendTurnsToBackground(newTurns);
    }
  }, DEBOUNCE_MS);
}

/**
 * Initialize MutationObserver to watch for new messages.
 */
function initObserver() {
  if (observerActive) return;

  const targetNode = document.body;
  const config = { childList: true, subtree: true, characterData: true };

  const observer = new MutationObserver(() => {
    // Fire on every DOM mutation — catches streaming text updates,
    // not just newly-added message container elements
    observeDOM();
  });

  observer.observe(targetNode, config);
  observerActive = true;
  console.log('[Continuum] DOM observer initialized');

  // Initial extraction
  observeDOM();
}

/**
 * Called whenever the conversation changes (SPA navigation to a different chat).
 * Resets turn tracking and re-scans the new chat's existing messages.
 */
function onConversationChanged() {
  const newId = getConversationId();
  if (newId === currentConversationId) return;

  console.log(`[Continuum] Conversation changed: ${currentConversationId} → ${newId}`);
  currentConversationId = newId;

  // Reset so all messages in the new chat are treated as unseen
  lastSeenTurnId = 0;

  // ChatGPT needs time to render the new chat's messages after navigation
  setTimeout(() => {
    const turns = extractTurnsFromDOM();
    if (turns.length > 0) {
      console.log(`[Continuum] Loaded ${turns.length} existing turns from conversation ${newId}`);
      sendTurnsToBackground(turns);
    } else {
      console.log(`[Continuum] No existing turns found in conversation ${newId} (new chat)`);
    }
  }, NAVIGATION_SETTLE_MS);
}

/**
 * Patch history.pushState and listen for popstate so we catch every
 * SPA navigation ChatGPT does (including switching between chats).
 */
function initNavigationDetection() {
  // pushState is how ChatGPT navigates between chats
  const originalPushState = history.pushState.bind(history);
  history.pushState = function(...args: Parameters<typeof history.pushState>) {
    originalPushState(...args);
    onConversationChanged();
  };

  // popstate handles browser back/forward
  window.addEventListener('popstate', onConversationChanged);

  console.log('[Continuum] Navigation detection initialized');
}

/**
 * Wait for ChatGPT to load, then initialize.
 */
function waitForChatGPT() {
  // Wait for document.body to be available
  if (!document.body) {
    console.log('[Continuum] Waiting for document.body...');
    setTimeout(waitForChatGPT, 100);
    return;
  }

  console.log('[Continuum] ChatGPT page ready, initializing observer...');
  currentConversationId = getConversationId();
  initObserver();
  initNavigationDetection();

  // Extract any existing messages in the current chat
  const existingTurns = extractTurnsFromDOM();
  if (existingTurns.length > 0) {
    console.log(`[Continuum] Found ${existingTurns.length} existing messages`);
    sendTurnsToBackground(existingTurns);
  }
}

// Start when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', waitForChatGPT);
} else {
  waitForChatGPT();
}

// Listen for messages from background
try {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'INJECT_TEXT') {
      // Auto-fill functionality: inject text into chat input
      const textarea = document.querySelector('textarea[data-id]') as HTMLTextAreaElement;
      if (textarea) {
        textarea.value = message.text;
        textarea.focus();
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        sendResponse({ success: true });
      } else {
        sendResponse({ success: false, error: 'Textarea not found' });
      }
    }
    return true; // Keep channel open for async response
  });
} catch {
  // Extension context invalidated — skip listener registration
}
