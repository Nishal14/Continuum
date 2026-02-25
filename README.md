# Continuum

**Real-time epistemic drift monitoring for LLM conversations**

## Overview

**Continuum** monitors epistemic drift in long-form LLM conversations. When conversations span dozens of turns, subtle contradictions accumulate—users change positions, AI models adapt to inconsistent stances, and reasoning integrity degrades. Continuum detects these issues in real-time before they compound into larger reasoning failures.

### Core Idea: Epistemic Drift + Strategic K2 Escalation

**The Problem**: In extended AI conversations, reasoning inconsistencies are inevitable:
- Users revise opinions without acknowledging prior statements
- AI models follow contradictory positions to maintain agreement
- Assumptions shift mid-conversation without detection
- Structural coherence breaks down gradually

**The Solution**: A hybrid monitoring system that combines:
1. **Fast heuristics** (<200ms) for continuous drift detection
2. **Cumulative drift tracking** across entire conversations
3. **Strategic K2 Think V2 escalation** for authoritative verification when drift crosses thresholds

This architecture provides **real-time feedback** without the cost or latency of running advanced reasoning models on every turn.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User ↔ ChatGPT                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ↓
               ┌─────────────────┐
               │ Content Script  │  (Extract conversation turns)
               │ (Injected into  │
               │  ChatGPT page)  │
               └────────┬────────┘
                        │
                        ↓
               ┌─────────────────┐
               │ Service Worker  │  (Message routing)
               │  (Background)   │
               └────────┬────────┘
                        │
                        ↓
               ┌─────────────────┐
               │  FastAPI        │
               │  Backend        │
               └────────┬────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ↓               ↓               ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Heuristic   │ │   Drift      │ │  Escalation  │
│   Engine     │ │ Accumulator  │ │   Policy     │
│  (<200ms)    │ │ (Cumulative) │ │ (Threshold)  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┴────────────────┘
                        │
                        ↓
              ┌──────────────────┐
              │  K2 Think V2     │
              │  (Strategic      │
              │  Verification)   │
              └─────────┬────────┘
                        │
                        ↓
              ┌──────────────────┐
              │ Metrics + Drift  │
              │     State        │
              └─────────┬────────┘
                        │
                        ↓
              ┌──────────────────┐
              │  Sidebar UI      │
              │ (React + TS)     │
              │                  │
              │ • Drift Meter    │
              │ • Timeline       │
              │ • Escalation     │
              │ • Metrics Grid   │
              └──────────────────┘
```

---

## Backend Architecture

### Three-Layer Escalation System

#### Layer 1: Heuristic Drift Engine
Fast, local contradiction detection using:
- **Topic-anchor matching**: Extract primary subject from claims ("TypeScript", "Python")
- **Polarity inference**: Detect positive/negative stance
- **Similarity scoring**: Compare new statements with prior commitments
- **Response time**: <200ms per turn (no API calls)

#### Layer 2: Cumulative Drift Accumulator
Longitudinal tracking across entire conversation:
- **Accumulation**: Sum drift magnitudes from all detected contradictions
- **Decay**: Exponential reduction when conversations stabilize
- **Velocity**: Rate of drift change (acceleration/deceleration)
- **Threshold**: Escalation triggers when cumulative drift > 2.0/5.0

#### Layer 3: K2 Think V2 Strategic Escalation
Advanced reasoning verification (only when needed):
- **Activation**: Triggered when drift crosses threshold OR high-confidence contradiction
- **Function**: Confirms true contradictions, overrides false positives
- **Response**: Confidence score (0-100%) + natural language explanation
- **Cost optimization**: Runs ~5-10x less frequently than heuristics

### Escalation Logic Summary

```python
if cumulative_drift > 2.0:
    # ESCALATE: K2 verification required
    k2_result = verify_with_k2_think(contradiction)

    if k2_result.confirmed:
        # True contradiction detected
        alert_user(severity="critical")
    else:
        # False positive - discard heuristic alert
        override_heuristic()
else:
    # Continue monitoring with heuristics only
    track_drift_metrics()
```

---

## Extension Architecture

### Content Script → Background → Sidebar

**1. Content Script (`contentScript.ts`)**
- Injected into ChatGPT pages (`chat.openai.com`, `chatgpt.com`)
- Monitors DOM for new messages using `MutationObserver`
- Extracts turn data (speaker, text, timestamp)
- Sends to background worker

**2. Service Worker (`background.ts`)**
- Receives messages from content script
- Forwards to FastAPI backend (`http://localhost:8000`)
- Handles API errors and retries
- Stores conversation state

**3. Sidebar UI (`Sidebar.tsx`)**
React-based visual dashboard with real-time updates:

**Components**:
- **DriftMeter**: Animated progress bar (0-5.0 scale), color-coded by severity
  - 🟢 Green (0-1.0): Stable
  - 🟡 Yellow (1.0-2.0): Tension building
  - 🔴 Red (2.0+): Escalated

- **EscalationCard**: K2 verification status display
  - ⏳ Pending: Verification in progress
  - ⚠️ Confirmed: K2 verified contradiction
  - ℹ️ Override: False positive rejected
  - ❌ Failed: Timeout/error

- **DriftTimeline**: Chronological list of last 6 drift events

- **IntegritySnapshot**: 2x2 metrics grid
  - Active commitments
  - Detected contradictions
  - Drift velocity
  - Structural state

**Polling**:
- Metrics: Every 3 seconds (continuous monitoring)
- K2 status: Every 2 seconds when escalated (until completion)

---

## Tech Stack

### Backend
- **FastAPI**: Python 3.11+ web framework
- **Pydantic**: Data validation and serialization
- **httpx**: Async HTTP client for K2 Think API
- **Storage**: In-memory commitment graph

### Extension
- **React 18.3.1**: UI framework
- **TypeScript 5.7**: Type-safe development
- **Webpack 5**: Module bundling
- **Chrome Manifest V3**: Extension platform

### Integration
- **K2 Think V2**: Advanced reasoning verification
- **ChatGPT**: Primary conversation platform
- **REST API**: Backend ↔ Extension communication

---

## Setup Instructions

### Prerequisites
- Python 3.11 or higher
- Node.js 18 or higher
- Chrome Browser
- K2 Think V2 API key (optional, required for verification features)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your K2_API_KEY

# Run backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Backend will be available at `http://localhost:8000`

### Extension Setup

```bash
cd extension

# Install dependencies
npm install

# Build extension
npm run build
```

### Load Extension in Chrome

1. Navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `extension/dist/` directory

### Verify Installation

1. Open [ChatGPT](https://chat.openai.com)
2. Click the Continuum extension icon in Chrome toolbar
3. Sidebar opens showing "Epistemic Stability Monitor"
4. Start a conversation and watch metrics update in real-time

---

## Configuration

Create `backend/.env` with:

```env
# K2 Think V2 API Key (required for verification)
K2_API_KEY=your_k2_api_key_here

# Escalation Configuration
CUMULATIVE_DRIFT_THRESHOLD=2.0      # When to escalate to K2
HEURISTIC_SIMILARITY_THRESHOLD=0.7  # Topic matching sensitivity
DRIFT_DECAY_FACTOR=0.9              # Decay rate for stable conversations
STABILITY_THRESHOLD_TURNS=3         # Turns before decay activates
```

⚠️ **Security**: Never commit `.env` files. The `.gitignore` is configured to exclude them.

---

## Project Structure

```
continuum/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI routes
│   │   ├── models.py            # Data models (Graph, Commitment, Edge)
│   │   ├── heuristics.py        # Fast drift detection
│   │   ├── analyzer.py          # Hybrid analysis orchestration
│   │   ├── escalation.py        # Escalation policy
│   │   ├── k2_client.py         # K2 Think API client
│   │   ├── drift_accumulation.py # Cumulative tracking
│   │   └── metrics.py           # Metrics calculation
│   ├── tests/                   # Backend tests
│   └── requirements.txt
│
├── extension/
│   ├── src/
│   │   ├── sidebar/
│   │   │   ├── Sidebar.tsx      # Main UI component
│   │   │   ├── components/      # DriftMeter, Timeline, etc.
│   │   │   └── types.ts         # TypeScript interfaces
│   │   ├── background.ts        # Service worker
│   │   └── contentScript.ts     # ChatGPT injection
│   ├── public/
│   │   ├── popup.html
│   │   ├── sidebar.html
│   │   └── logo.png
│   ├── webpack.config.js
│   └── package.json
│
├── README.md
├── LICENSE
└── .gitignore
```

---

## Example Use Case

**Conversation:**
```
User: "TypeScript is a good choice for large projects"
AI: "TypeScript provides strong type safety and better tooling..."

[5 turns later]

User: "TypeScript is not a good choice for large projects"
AI: "I understand your concerns about TypeScript..."
```

**Continuum Response:**
1. 🟡 Heuristic detects polarity flip on topic "TypeScript"
2. 📈 Cumulative drift increases: 0.3 → 1.8 (yellow zone)
3. 🔴 After multiple contradictions, drift crosses 2.3 threshold
4. ⚡ K2 Think verification triggered
5. ✅ K2 confirms contradiction with 91% confidence
6. ⚠️ Escalation card displays: "Direct contradiction detected"

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## Contributing

Issues and pull requests are welcome. For major changes, please open an issue first to discuss proposed changes.

**Areas of interest**:
- Improved heuristic algorithms
- Support for additional LLM platforms (Claude, Gemini)
- Enhanced visualization components
- Performance optimization
- Test coverage

---

## Contact

- **Issues**: [GitHub Issues](https://github.com/yourusername/continuum/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/continuum/discussions)

---

**Built for researchers, developers, and anyone who needs reliable reasoning in long-form AI conversations.**
