"""
K2 Think API client for deep analysis.

Phase 3: K2 as primary reasoning engine with heuristic fallback.
"""

import os
import httpx
from typing import List, Dict, Optional
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

K2_API_BASE = "https://api.k2think.ai/v1"
K2_MODEL = "MBZUAI-IFM/K2-Think-v2"
K2_TIMEOUT = 60.0  # K2 can take 50+ seconds to respond
K2_MAX_RETRIES = 2  # Phase 3: Max 2 retries


class K2Client:
    """Client for K2 Think API - Primary reasoning engine."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("K2_API_KEY")
        self.call_count = 0  # Track API calls
        self.failure_count = 0  # Track failures
        if not self.api_key:
            logger.warning("K2_API_KEY not set - K2 features will be disabled")

    async def extract_structured_commitments(self, turn_text: str) -> Optional[List[Dict]]:
        """
        Phase 3: Extract structured claims using K2 API.

        Returns list of claim dictionaries or None on failure.
        Format:
        [
            {
                "claim": "canonical text",
                "polarity": "positive|negative|neutral",
                "confidence": 0.0-1.0,
                "assumptions": ["assumption1", "assumption2"]
            }
        ]
        """
        if not self.api_key:
            logger.warning("[Continuum DEBUG] K2 API key not available in extract_structured_commitments")
            return None

        logger.info(f"[Continuum DEBUG] K2 client making API call with key: {self.api_key[:10]}...")

        prompt = f"""You are a structured reasoning extractor.

Given the following conversational turn, extract explicit claims in JSON format.

For each claim return:
- claim (string): canonical form of the claim
- polarity (positive | negative | neutral)
- confidence (0.0 to 1.0)
- assumptions (list of strings): implicit assumptions

Return ONLY valid JSON:
{{
  "claims": [...]
}}

Turn:
\"\"\"
{turn_text}
\"\"\"
"""

        try:
            self.call_count += 1

            # Configure timeout for all operations (connect, read, write, pool)
            timeout_config = httpx.Timeout(K2_TIMEOUT, read=K2_TIMEOUT)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(
                    f"{K2_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": K2_MODEL,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "stream": False
                    }
                )

                logger.info(f"[Continuum DEBUG] HTTP status: {response.status_code}")

                response.raise_for_status()

                # Log raw response for debugging
                response_text = response.text
                logger.info(f"[Continuum DEBUG] Raw HTTP response length: {len(response_text)}")
                logger.info(f"[Continuum DEBUG] Raw HTTP response: {response_text[:1000]}")

                if not response_text:
                    logger.error("[Continuum DEBUG] Response is empty!")
                    return None

                result = response.json()
                logger.info(f"[Continuum DEBUG] Parsed JSON keys: {result.keys()}")

                # Parse response
                content = result["choices"][0]["message"]["content"]

                logger.info(f"[Continuum DEBUG] Message content length: {len(content)}")
                logger.info(f"[Continuum DEBUG] Content preview: {content[:300]}...")
                logger.info(f"[Continuum DEBUG] Content end: ...{content[-500:]}")

                # K2 Think models include reasoning before the answer
                # The JSON usually appears after </think> tag or at the end
                json_content = None

                # Try to find JSON in markdown code blocks first
                if "```json" in content:
                    json_content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_content = content.split("```")[1].split("```")[0].strip()
                elif "</think>" in content:
                    # Extract everything after </think> tag
                    json_content = content.split("</think>")[-1].strip()
                else:
                    # Find the last occurrence of {"claims":
                    import re
                    # Find all JSON-like structures starting with {
                    last_brace = content.rfind('{"claims"')
                    if last_brace != -1:
                        # Extract from that point to the end
                        potential_json = content[last_brace:]
                        # Try to find the closing brace
                        json_content = potential_json
                    else:
                        # Last resort: try the entire content
                        json_content = content

                if not json_content:
                    logger.error(f"[Continuum DEBUG] Could not find JSON in response")
                    return None

                logger.info(f"[Continuum DEBUG] Extracted JSON: {json_content[:500]}...")

                parsed = json.loads(json_content)
                claims = parsed.get("claims", [])

                logger.info(f"[Continuum DEBUG] K2 successfully extracted {len(claims)} claims")
                return claims

        except asyncio.TimeoutError as e:
            logger.warning(f"K2 API timeout after {K2_TIMEOUT}s: {e}")
            self.failure_count += 1
            return None
        except json.JSONDecodeError as e:
            logger.error(f"K2 returned invalid JSON: {e}")
            self.failure_count += 1
            return None
        except httpx.HTTPError as e:
            logger.error(f"K2 HTTP error: {e}")
            self.failure_count += 1
            return None
        except Exception as e:
            logger.error(f"K2 API error: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.failure_count += 1
            return None

    async def verify_contradiction(
        self,
        prior_claim: str,
        new_claim: str
    ) -> Optional[Dict]:
        """
        Phase 3: Verify if two claims contradict using K2.

        Returns:
        {
            "is_contradiction": bool,
            "type": "direct_contradiction|contextual_refinement|legitimate_update",
            "confidence": 0.0-1.0,
            "explanation": "short reasoning"
        }
        """
        if not self.api_key:
            logger.warning("K2 API key not available")
            return None

        prompt = f"""You are evaluating epistemic consistency.

Given two claims:

Prior:
"{prior_claim}"

New:
"{new_claim}"

Determine:
- Is this a direct contradiction? (true/false)
- Is this a contextual refinement?
- Is this a legitimate update based on new information?

Provide short reasoning.

Return ONLY valid JSON:
{{
  "is_contradiction": true/false,
  "type": "direct_contradiction|contextual_refinement|legitimate_update",
  "confidence": 0.0-1.0,
  "explanation": "brief explanation"
}}
"""

        try:
            self.call_count += 1

            # Configure timeout for all operations (connect, read, write, pool)
            timeout_config = httpx.Timeout(K2_TIMEOUT, read=K2_TIMEOUT)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(
                    f"{K2_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": K2_MODEL,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "stream": False
                    }
                )

                response.raise_for_status()
                result = response.json()

                # Parse response
                content = result["choices"][0]["message"]["content"]

                # Extract JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                verification = json.loads(content)

                logger.info(f"K2 verification: is_contradiction={verification.get('is_contradiction')}")
                return verification

        except asyncio.TimeoutError:
            logger.warning(f"K2 verification timeout after {K2_TIMEOUT}s")
            self.failure_count += 1
            return None
        except json.JSONDecodeError as e:
            logger.error(f"K2 verification returned invalid JSON: {e}")
            self.failure_count += 1
            return None
        except Exception as e:
            logger.error(f"K2 verification error: {e}")
            self.failure_count += 1
            return None

    async def generate_reconciliation(
        self,
        prior_claim: str,
        new_claim: str,
        conversation_summary: str = ""
    ) -> Optional[Dict]:
        """
        Phase 3: Generate reconciliation proposal using K2.

        Returns:
        {
            "reconciliation": "coherent reconciliation text",
            "confidence": 0.0-1.0
        }
        """
        if not self.api_key:
            logger.warning("K2 API key not available")
            return None

        prompt = f"""Given the earlier claim and later claim, generate a coherent reconciliation that preserves logical continuity if possible.

Earlier claim:
"{prior_claim}"

Later claim:
"{new_claim}"

Context summary:
{conversation_summary if conversation_summary else "No additional context"}

Generate a reconciliation that:
1. Acknowledges the earlier position
2. Explains what changed or what new information emerged
3. Provides a unified understanding

Return ONLY valid JSON:
{{
  "reconciliation": "coherent reconciliation text (2-3 sentences)",
  "confidence": 0.0-1.0
}}
"""

        try:
            self.call_count += 1

            # Configure timeout for all operations (connect, read, write, pool)
            timeout_config = httpx.Timeout(K2_TIMEOUT, read=K2_TIMEOUT)
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(
                    f"{K2_API_BASE}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": K2_MODEL,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "stream": False
                    }
                )

                response.raise_for_status()
                result = response.json()

                # Parse response
                content = result["choices"][0]["message"]["content"]

                # Extract JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                reconciliation = json.loads(content)

                logger.info(f"K2 generated reconciliation with confidence={reconciliation.get('confidence')}")
                return reconciliation

        except asyncio.TimeoutError:
            logger.warning(f"K2 reconciliation timeout after {K2_TIMEOUT}s")
            self.failure_count += 1
            return None
        except json.JSONDecodeError as e:
            logger.error(f"K2 reconciliation returned invalid JSON: {e}")
            self.failure_count += 1
            return None
        except Exception as e:
            logger.error(f"K2 reconciliation error: {e}")
            self.failure_count += 1
            return None

    def get_stats(self) -> Dict:
        """Get K2 client statistics."""
        return {
            "total_calls": self.call_count,
            "failures": self.failure_count,
            "success_rate": (self.call_count - self.failure_count) / self.call_count if self.call_count > 0 else 0.0
        }
