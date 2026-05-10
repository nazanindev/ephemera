from __future__ import annotations
import re
import hashlib


def classify_vibe(topic: str) -> float:
    """
    0.0 = sparse/poetic, 1.0 = dense/layered.
    Based on topic shape: word count, years, proper nouns, word length.
    """
    words = [w for w in topic.strip().split() if w]
    n = len(words)

    if n == 1:
        base = 0.20
    elif n == 2:
        base = 0.40
    elif n == 3:
        base = 0.55
    else:
        base = 0.65

    boost = 0.0

    # Year → historically specific → denser
    if re.search(r'\b(19|20)\d\d\b', topic):
        boost += 0.25

    # Proper nouns beyond first word → concrete/named → denser
    proper = sum(1 for w in words[1:] if w and w[0].isupper() and len(w) > 2)
    boost += proper * 0.10

    # Short avg word length → abstract → sparser
    avg_len = sum(len(w) for w in words) / n
    if avg_len <= 4:
        boost -= 0.08
    elif avg_len >= 8:
        boost += 0.06

    score = max(0.05, min(0.95, base + boost))

    # Neutral zone: deterministic variation via topic hash
    if 0.38 < score < 0.62:
        h = int(hashlib.md5(topic.lower().encode()).hexdigest(), 16) % 1000 / 1000.0
        score = 0.38 + h * 0.24

    return score
