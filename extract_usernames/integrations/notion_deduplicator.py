"""Group Notion pages by Instagram URL and archive losers via quality scoring.

The "best" username in a duplicate group is chosen by `_score_username`, not
by recency. Losers are archived (`archived=True`) — Notion treats this as soft
delete; restorable from trash for ~30 days.

Author: Rahi Khan (Dropout Studio)
License: MIT
"""

import re
import time
import logging
from typing import Dict, List, Set, Tuple
from collections import defaultdict

from notion_client import Client
from notion_client.errors import APIResponseError


class NotionDeduplicator:
    # Notion published rate limit is ~3 req/sec; 0.35s gap keeps us under it
    # with a safety margin. Single-threaded enforcement only — not safe for
    # concurrent dedup runs against the same DB.
    RATE_LIMIT_DELAY = 0.35

    def __init__(self, client: Client, database_id: str, data_source_id: str):
        """`data_source_id` is the new Notion data_sources API surface (≠ database_id
        for multi-source DBs). Caller must resolve it via
        `NotionDatabaseManager._get_data_source_id()`."""
        self.client = client
        self.database_id = database_id
        self.data_source_id = data_source_id
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0

    def _enforce_rate_limit(self):
        # Residual-sleep gate; see InstagramValidator._enforce_rate_limit for
        # identical pattern.
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.RATE_LIMIT_DELAY:
                time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _score_username(self, username: str) -> int:
        """Heuristic quality score. Higher = better username to keep.

        Score components (additive unless noted):
        - `^\\d+\\.?$` (purely "1.", "2", etc.): hard floor -1000, returned early.
        - starts with digit: -50
        - starts with alpha: +100
        - alpha char ratio * 50 (rounded)
        - length in [3, 30]: +50, else -20
        - +2 * min(len, 15) length reward, capped at +30
        - lowercase (ignoring _ and .): +10

        Special cases worth knowing:
        - Mostly-alpha lowercase 5-char names cluster around score ~190.
        - Pure-digit pages and OCR garbage like "1." get filtered to -1000.
        """
        if not username:
            return 0

        score = 0

        if re.match(r'^\d+\.?$', username):
            return -1000

        if username[0].isdigit():
            score -= 50

        if username[0].isalpha():
            score += 100

        alpha_ratio = sum(c.isalpha() for c in username) / len(username)
        score += int(alpha_ratio * 50)

        if 3 <= len(username) <= 30:
            score += 50
        else:
            score -= 20

        # Length reward saturates at 15 chars — prevents long garbage strings
        # from dominating short clean ones.
        score += min(len(username), 15) * 2

        # Lowercase check ignores . and _ separators so "user_name" still wins.
        if username.islower() or username.replace('_', '').replace('.', '').islower():
            score += 10

        return score

    def _pick_best_username(self, entries: List[Dict]) -> Tuple[str, str]:
        """Returns `(best_page_id, best_username)`. Ties broken by iteration order."""
        best_score = -9999
        best_entry = None

        for entry in entries:
            username = entry['username']
            score = self._score_username(username)

            self.logger.debug(f"Username '{username}' scored: {score}")

            if score > best_score:
                best_score = score
                best_entry = entry

        return best_entry['page_id'], best_entry['username']

    def find_duplicates(self, property_names: Dict[str, str]) -> Dict[str, List[Dict]]:
        """Paginate the data source, group rows by URL property, return groups with len > 1.

        `property_names` keys: 'title' (defaults "Brand Name"), 'url' (defaults
        "Social Media Account"). Entries with empty/None URL are silently dropped.
        Pagination uses Notion's `start_cursor` / `has_more` protocol with 100 rows/page.
        On query exception the partial result is returned (logged, not raised).
        """
        title_prop = property_names.get('title', 'Brand Name')
        url_prop = property_names.get('url', 'Social Media Account')

        url_to_entries = defaultdict(list)
        has_more = True
        start_cursor = None

        self.logger.info("🔍 Scanning database for duplicates...")

        while has_more:
            self._enforce_rate_limit()

            query_params = {"page_size": 100}
            if start_cursor:
                query_params["start_cursor"] = start_cursor

            try:
                response = self.client.data_sources.query(
                    data_source_id=self.data_source_id,
                    **query_params
                )
            except Exception as e:
                # Partial-result return: caller still sees what we found so far.
                self.logger.error(f"Error querying data source: {e}")
                break

            for page in response.get("results", []):
                page_id = page.get("id")
                props = page.get("properties", {})

                # Notion title is a list of rich_text spans; we take the first
                # span's plain_text and treat the rest as decoration.
                username_prop = props.get(title_prop, {})
                title_list = username_prop.get("title", [])
                username = ""
                if title_list:
                    username = title_list[0].get("plain_text", "")
                    # `plain_text` can be literal None for empty cells — `str.strip()` would crash.
                    username = username.strip() if username else ""

                # URL property is `{'url': str | None}`; explicit None coalesce
                # before strip to handle blank-URL rows.
                url_prop_data = props.get(url_prop, {})
                url = url_prop_data.get("url")
                url = (url or "").strip()

                # Entries without a URL can't be deduped by URL — skip silently.
                if url:
                    url_to_entries[url].append({
                        'page_id': page_id,
                        'username': username,
                        'url': url
                    })

            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

        # Singletons (len == 1) are dropped — only groups with collisions matter.
        duplicates = {url: entries for url, entries in url_to_entries.items() if len(entries) > 1}

        return duplicates

    def archive_page(self, page_id: str) -> bool:
        """Soft delete (Notion `archived=True`). Restorable from Notion trash."""
        try:
            self._enforce_rate_limit()
            self.client.pages.update(
                page_id=page_id,
                archived=True
            )
            return True
        except APIResponseError as e:
            self.logger.error(f"Failed to archive page {page_id}: {e}")
            return False

    def deduplicate(self, property_names: Dict[str, str], dry_run: bool = False) -> Dict[str, int]:
        """End-to-end: find groups → pick winner → archive losers.

        `dry_run=True` skips the archive call but still reports what would happen.
        Returns stats: `total_entries` (currently always 0 — bug, never populated),
        `duplicate_groups`, `duplicates_found` (len-1 per group), `duplicates_removed`, `errors`.
        """
        stats = {
            'total_entries': 0,
            'duplicate_groups': 0,
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'errors': 0,
        }

        duplicates = self.find_duplicates(property_names)

        stats['duplicate_groups'] = len(duplicates)

        if not duplicates:
            self.logger.info("✅ No duplicates found!")
            return stats

        for url, entries in duplicates.items():
            # -1 because the winner is kept; only losers count as "found duplicates".
            stats['duplicates_found'] += len(entries) - 1

            self.logger.info(f"\n📍 Found {len(entries)} duplicates for: {url}")

            best_page_id, best_username = self._pick_best_username(entries)

            self.logger.info(f"   ✅ Keeping: '{best_username}' (score: {self._score_username(best_username)})")

            for entry in entries:
                if entry['page_id'] == best_page_id:
                    continue

                username = entry['username']
                score = self._score_username(username)

                if dry_run:
                    self.logger.info(f"   🗑️  Would remove: '{username}' (score: {score})")
                else:
                    if self.archive_page(entry['page_id']):
                        self.logger.info(f"   🗑️  Removed: '{username}' (score: {score})")
                        stats['duplicates_removed'] += 1
                    else:
                        self.logger.error(f"   ❌ Failed to remove: '{username}'")
                        stats['errors'] += 1

        return stats


def run_deduplication(
    token: str,
    database_id: str,
    data_source_id: str,
    property_names: Dict[str, str],
    dry_run: bool = False,
) -> Dict[str, int]:
    """Module-level convenience: instantiate client + deduplicator + invoke `.deduplicate`.

    Distinct from the (currently-broken) `NotionDeduplicator.run_deduplication`
    call site in cli_merge_duplicates.py — that one passes `keep_strategy`
    which this code path does not support.
    """
    client = Client(auth=token)
    deduplicator = NotionDeduplicator(client, database_id, data_source_id)

    return deduplicator.deduplicate(property_names, dry_run=dry_run)
