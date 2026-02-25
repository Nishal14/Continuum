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

  for (const selector of selectors) {
    messageNodes = document.querySelectorAll(selector);
    if (messageNodes.length > 0) break;
  }

  if (!messageNodes || messageNodes.length === 0) {
    return [];
  }

  messageNodes.forEach((node, index) => {
    try {
      // Determine speaker
      const roleAttr = node.getAttribute('data-message-author-role');
      const speaker: 'user' | 'model' =
        roleAttr === 'user' ? 'user' : 'model';

      // Extract text content
      const textElement = node.querySelector('.markdown, .whitespace-pre-wrap, [class*="text"]');
      const text = textElement?.textContent?.trim() || '';

      if (!text || text.length < 2) return; // Skip empty

      // Generate stable ID (hash of content + position)
      const id = hashCode(text + index);

      // Timestamp
      const ts = new Date().toISOString();

      if (id > lastSeenTurnId) {
        turns.push({ id, speaker, text, ts });
      }
    } catch (err) {
      console.error('[Continuum] Error extracting turn:', err);
    }
  });

  return turns;
}

/**
 * Simple hash function for generating turn IDs.
 */
function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash);
}

/**
 * Send turns to background script.
 */
function sendTurnsToBackground(turns: Turn[]) {
  if (turns.length === 0) return;

  console.log('[Continuum] Sending to background:', turns.length, 'turns', turns);

  chrome.runtime.sendMessage({
    type: 'NEW_TURNS',
    payload: {
      conversationId: getConversationId(),
      turns
    }
  }, (response) => {
    if (chrome.runtime.lastError) {
      console.error('[Continuum] Message send error:', chrome.runtime.lastError);
    } else {
      console.log('[Continuum] Background responded:', response);
    }
  });

  lastSeenTurnId = Math.max(...turns.map(t => t.id));
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
  const config = { childList: true, subtree: true };

  const observer = new MutationObserver((mutations) => {
    // Check if any mutation affects message containers
    const hasRelevantChange = mutations.some(m =>
      Array.from(m.addedNodes).some(node =>
        node instanceof Element &&
        (node.matches('[data-message-author-role]') ||
         node.querySelector('[data-message-author-role]'))
      )
    );

    if (hasRelevantChange) {
      console.log('[Continuum] Mutation detected - message container added');
      observeDOM();
    }
  });

  observer.observe(targetNode, config);
  observerActive = true;
  console.log('[Continuum] DOM observer initialized');

  // Initial extraction
  observeDOM();
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
  initObserver();

  // Extract any existing messages
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
