"""
Debug topic anchor extraction to see what's being extracted.
"""

import sys
sys.path.insert(0, '.')

from app.heuristics import extract_topic_anchor, _infer_polarity

test_cases = [
    "Python is the best language for everything.",
    "Python has many strengths.",
    "Actually, Python is terrible for performance.",

    "Microservices are better for scalability.",
    "Microservices have advantages.",
    "But monoliths are better for simplicity.",

    "TypeScript is excellent for large codebases.",
    "Type safety has benefits.",
    "Actually, TypeScript is terrible for productivity.",

    "Functional programming is elegant.",
    "Functional programming is difficult to learn.",

    "Object-oriented programming is intuitive.",
    "Object-oriented programming is overly complex.",
]

print("\n" + "=" * 70)
print("TOPIC ANCHOR EXTRACTION DEBUG")
print("=" * 70)

for text in test_cases:
    anchor = extract_topic_anchor(text)
    polarity = _infer_polarity(text)

    print(f"\nText: {text}")
    print(f"  Anchor: '{anchor}'")
    print(f"  Polarity: {polarity}")

print("\n" + "=" * 70)
