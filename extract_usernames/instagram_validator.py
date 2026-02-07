"""Instagram Username Validator.

Validates Instagram usernames by making HTTP requests to profile URLs.
Implements retry logic, rate limiting, and comprehensive error handling.

Author: Rahi Khan (Dropout Studio)
License: MIT
"""

import time
import logging
from typing import Dict, List
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)


class InstagramValidator:
    """Validates Instagram usernames via HTTP requests."""
    
    BASE_URL = "https://www.instagram.com"
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    ]
    
    def __init__(self, delay_between_requests: float = 2.0):
        self.delay = delay_between_requests
        self.session = self._create_session()
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0
        self._request_count = 0
    
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _sanitize_username(self, username: str) -> str:
        username = username.strip().lstrip('@')
        username = ''.join(c for c in username if c.isalnum() or c in '._')
        return username.lower()
    
    def _enforce_rate_limit(self):
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, requests.Timeout)),
        reraise=True
    )
    def _make_request(self, username: str) -> requests.Response:
        url = f"{self.BASE_URL}/{quote(username)}/"
        headers = {
            "User-Agent": self.USER_AGENTS[self._request_count % len(self.USER_AGENTS)],
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.5",
        }
        response = self.session.get(url, headers=headers, timeout=10, allow_redirects=True)
        return response
    
    def validate_username(self, username: str) -> Dict[str, any]:
        sanitized = self._sanitize_username(username)
        url = f"{self.BASE_URL}/{sanitized}/"
        
        result = {
            'username': sanitized,
            'exists': False,
            'url': url,
            'status_code': None,
            'error': None
        }
        
        if not sanitized:
            result['error'] = "Invalid username format"
            return result
        
        try:
            self._enforce_rate_limit()
            response = self._make_request(sanitized)
            result['status_code'] = response.status_code
            
            if response.status_code == 200:
                if '/accounts/login' not in response.url:
                    result['exists'] = True
                else:
                    result['error'] = "Account requires login"
            elif response.status_code == 404:
                result['error'] = "Account not found"
            else:
                result['error'] = f"Status: {response.status_code}"
            
            self._request_count += 1
            
        except requests.Timeout:
            result['error'] = "Request timeout"
        except requests.RequestException as e:
            result['error'] = f"Request failed: {str(e)}"
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
        
        return result
    
    def validate_batch(self, usernames: List[str]) -> List[Dict]:
        results = []
        for username in usernames:
            result = self.validate_username(username)
            results.append(result)
        return results
    
    def close(self):
        if self.session:
            self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
