"""
Simple in-memory rate limiter.
Limits chat endpoint to MAX_REQUESTS per window per user.
Uses a sliding window approach.
"""
import time
from collections import defaultdict

MAX_REQUESTS = 30       # max messages per window
WINDOW_SECONDS = 60     # rolling window in seconds

# { user_id: [timestamp, timestamp, ...] }
_request_log: dict[str, list[float]] = defaultdict(list)


def is_rate_limited(user_id: str) -> bool:
    """Returns True if the user has exceeded the rate limit."""
    now    = time.time()
    cutoff = now - WINDOW_SECONDS

    # Drop timestamps outside the window
    _request_log[user_id] = [t for t in _request_log[user_id] if t > cutoff]

    if len(_request_log[user_id]) >= MAX_REQUESTS:
        return True

    _request_log[user_id].append(now)
    return False
