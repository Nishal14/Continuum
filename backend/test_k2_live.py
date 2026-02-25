"""
Direct K2 Client Test Script

Tests K2 API connection and extraction directly.
"""

import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)

# Load environment variables
load_dotenv()

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.k2_client import K2Client

async def test_k2_extraction():
    """Test K2 extraction with a simple statement."""
    print("=" * 60)
    print("K2 CLIENT DIRECT TEST")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("K2_API_KEY")
    print(f"\n1. API Key Status:")
    if api_key:
        print(f"   [OK] K2_API_KEY found: {api_key[:10]}...{api_key[-4:]}")
    else:
        print(f"   [FAIL] K2_API_KEY not found in environment")
        return

    # Create client
    print(f"\n2. Creating K2Client...")
    client = K2Client()
    print(f"   Client API key set: {client.api_key is not None}")

    # Test extraction
    test_text = "Decentralization improves robustness but reduces efficiency."
    print(f"\n3. Testing extraction with text:")
    print(f"   '{test_text}'")

    try:
        print(f"\n4. Calling extract_structured_commitments()...")
        result = await client.extract_structured_commitments(test_text)

        print(f"\n5. Result:")
        if result is None:
            print(f"   [FAIL] Result is None (K2 call failed or API key issue)")
        elif len(result) == 0:
            print(f"   [WARN] Result is empty list (K2 returned no claims)")
        else:
            print(f"   [OK] K2 extracted {len(result)} claims:")
            for idx, claim in enumerate(result):
                print(f"\n   Claim {idx + 1}:")
                print(f"     - claim: {claim.get('claim')}")
                print(f"     - polarity: {claim.get('polarity')}")
                print(f"     - confidence: {claim.get('confidence')}")
                print(f"     - assumptions: {claim.get('assumptions')}")

        print(f"\n6. Client Stats:")
        print(f"   - Total calls: {client.call_count}")
        print(f"   - Failures: {client.failure_count}")

    except Exception as e:
        print(f"\n[ERROR]: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test_k2_extraction())
