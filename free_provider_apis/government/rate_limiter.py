# free_provider_apis/government/rate_limiter.py
import threading
import time
from datetime import datetime, timezone

class TokenBucket:
    """Simple token bucket limiter (capacity, refill_rate tokens/sec)."""
    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = max(1, int(capacity))
        self.refill_rate = max(0.01, float(refill_rate))
        self._tokens = float(self.capacity)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> None:
        with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
                self._last = now
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                needed = tokens - self._tokens
                wait_s = needed / self.refill_rate
                time.sleep(min(wait_s, 0.5))

class DailyQuota:
    """Process-local daily quota guard (UTC midnight reset)."""
    def __init__(self, quota: int) -> None:
        self.quota = max(1, int(quota))
        self._count = 0
        self._day = self._day_key()
        self._lock = threading.Lock()

    def _day_key(self) -> str:
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d")

    def acquire(self, units: int = 1) -> bool:
        with self._lock:
            day = self._day_key()
            if day != self._day:
                self._day = day
                self._count = 0
            if self._count + units > self.quota:
                return False
            self._count += units
            return True

class CompositeLimiter:
    """Combines token bucket + daily quota. Raises if quota exceeded."""
    def __init__(self, rps: float, bucket: int, daily_quota: int) -> None:
        self.token_bucket = TokenBucket(bucket, rps)
        self.daily_quota = DailyQuota(daily_quota)

    def acquire(self, cost: int = 1) -> None:
        if not self.daily_quota.acquire(cost):
            raise RuntimeError("Daily quota exceeded for this source.")
        self.token_bucket.acquire(cost)
