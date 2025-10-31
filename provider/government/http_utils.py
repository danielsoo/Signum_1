# free_provider_apis/government/http_utils.py

import random
import time
from typing import Dict, Optional
import requests
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

from ..common.config import CONFIG

def _parse_retry_after(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        secs = float(value)
        if secs >= 0:
            return secs
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return max(0.0, (dt - now).total_seconds())
    except Exception:
        return None

class HttpClient:
    def __init__(self, timeout: Optional[int] = None):
        cfg = CONFIG["http"]
        self.timeout = timeout or cfg["timeout"]
        self.max_retries = int(cfg["max_retries"])
        self.backoff_base = float(cfg["backoff_base"])
        self.backoff_factor = float(cfg["backoff_factor"])
        self.jitter = float(cfg["jitter"])
        self.session = requests.Session()
        self.default_headers = {
            "Accept": "application/json",
            "User-Agent": cfg.get("user_agent", "free-provider-apis/1.0"),
        }

    def _backoff(self, attempt: int) -> float:
        base = self.backoff_base * (self.backoff_factor ** max(0, attempt - 1))
        return base + random.uniform(0, self.jitter)

    def get(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None):
        attempt = 0
        merged_headers = dict(self.default_headers)
        if headers:
            merged_headers.update(headers)

        while True:
            try:
                resp = self.session.get(url, params=params, headers=merged_headers, timeout=self.timeout)
                status = resp.status_code

                if 200 <= status < 300:
                    return resp

                if status == 429:
                    attempt += 1
                    if attempt > self.max_retries:
                        resp.raise_for_status()
                    delay = _parse_retry_after(resp.headers.get("Retry-After")) or self._backoff(attempt)
                    time.sleep(delay)
                    continue

                if status in (408, 502, 503, 504):
                    attempt += 1
                    if attempt > self.max_retries:
                        resp.raise_for_status()
                    time.sleep(self._backoff(attempt))
                    continue

                resp.raise_for_status()

            except (requests.ConnectionError, requests.Timeout):
                attempt += 1
                if attempt > self.max_retries:
                    raise
                time.sleep(self._backoff(attempt))

    @staticmethod
    def safe_json(resp: requests.Response):
        try:
            return resp.json()
        except ValueError:
            text = resp.text
            snippet = text[:500].replace("\n", " ") if isinstance(text, str) else str(text)[:500]
            raise RuntimeError(f"Expected JSON but failed to parse (status {resp.status_code}). Snippet: {snippet!r}")
