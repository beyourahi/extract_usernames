"""notion-client wrapper for the "Client Hunt"-style lead-tracking database.

Schema autodetection: rather than hard-coding property names, `_detect_property_names`
scans the DB schema for: title (always exactly one in Notion), URL property
(prefers names containing "social"), and status property. Falls back to
hard-coded defaults if detection fails.

`__init__` performs network I/O (`_verify_connection`) and prewarms two caches
(data_source_id, property_names) so callers don't pay per-method round-trips.
Raises Exception with a multi-line troubleshooting message on connect failure.

Author: Rahi Khan (Dropout Studio)
License: MIT
"""

import time
import logging
from typing import Dict, List, Set, Optional

from notion_client import Client
from notion_client.errors import APIResponseError


class NotionDatabaseManager:
    # See notion_deduplicator.RATE_LIMIT_DELAY — same 3 req/sec budget.
    RATE_LIMIT_DELAY = 0.35

    def __init__(self, token: str, database_id: str):
        # `_verify_connection` does network I/O and raises with a help text
        # on failure — callers must be prepared for Exception at construction.
        self.client = Client(auth=token)
        self.database_id = self._clean_database_id(database_id)
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0
        # Lazy caches populated by `_verify_connection`; subsequent reads
        # are O(1) and don't hit the network.
        self._existing_usernames_cache: Optional[Set[str]] = None
        self._data_source_id: Optional[str] = None
        self._property_names: Optional[Dict[str, str]] = None
        self._verify_connection()

    def _clean_database_id(self, db_id: str) -> str:
        """Normalize input to the 32-char hex ID Notion's API expects.

        Accepts: raw hex, dashed UUID, full notion.so URL with or without `?v=`
        query string. Order matters: URL strip → query strip → dash strip.
        """
        if 'notion.so/' in db_id:
            db_id = db_id.split('notion.so/')[-1]

        if '?' in db_id:
            db_id = db_id.split('?')[0]

        db_id = db_id.replace('-', '')

        return db_id

    def _enforce_rate_limit(self):
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.RATE_LIMIT_DELAY:
                time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get_data_source_id(self) -> str:
        """Resolve the data_source_id used by Notion's new data_sources API.

        Returns cached value on subsequent calls. For single-source DBs returns
        the only ID. For multi-source DBs returns the first and logs a warning.
        On any error, falls back to `database_id` (works against legacy API
        surfaces in notion-client).
        """
        if self._data_source_id:
            return self._data_source_id

        try:
            self._enforce_rate_limit()
            db = self.client.databases.retrieve(database_id=self.database_id)

            data_sources = db.get('data_sources', [])

            if not data_sources:
                self._data_source_id = self.database_id
            else:
                self._data_source_id = data_sources[0]['id']

                if len(data_sources) > 1:
                    self.logger.warning(
                        f"Database has {len(data_sources)} data sources. Using first one: {self._data_source_id}"
                    )

            return self._data_source_id
        except Exception as e:
            self.logger.warning(f"Could not get data source ID: {e}. Using database_id as fallback.")
            self._data_source_id = self.database_id
            return self._data_source_id

    def _detect_property_names(self) -> Dict[str, str]:
        """Map logical names → actual Notion property names by inspecting schema.

        Detection order:
        1. title type → 'title' (Notion enforces exactly one title prop).
        2. url type WITH 'social' substring in name → 'url' (specific match first).
        3. status type → 'status'.
        4. Fallback pass: first url prop / first status prop regardless of name.

        Cached after first call. On total failure returns hard-coded defaults
        ('Brand Name', 'Social Media Account', 'Status') without caching —
        so a transient API error doesn't pin bad defaults.
        """
        if self._property_names:
            return self._property_names

        try:
            self._enforce_rate_limit()
            db = self.client.databases.retrieve(database_id=self.database_id)
            properties = db.get('properties', {})

            prop_map = {}

            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get('type')
                if prop_type == 'title':
                    prop_map['title'] = prop_name
                elif prop_type == 'url' and 'social' in prop_name.lower():
                    prop_map['url'] = prop_name
                elif prop_type == 'status':
                    prop_map['status'] = prop_name

            # Second pass: any url/status prop regardless of name (less specific).
            if 'url' not in prop_map:
                for prop_name in properties.keys():
                    if properties[prop_name].get('type') == 'url':
                        prop_map['url'] = prop_name
                        break

            if 'status' not in prop_map:
                for prop_name in properties.keys():
                    if properties[prop_name].get('type') == 'status':
                        prop_map['status'] = prop_name
                        break

            self._property_names = prop_map
            self.logger.info(f"✅ Detected properties: {prop_map}")
            return prop_map

        except Exception as e:
            # Intentionally NOT cached — transient failures shouldn't pin defaults.
            self.logger.warning(f"Could not detect property names: {e}. Using defaults.")
            return {
                'title': 'Brand Name',
                'url': 'Social Media Account',
                'status': 'Status'
            }

    def _verify_connection(self):
        """Probe DB; on failure raise Exception with a long troubleshooting message.

        Also pre-fetches data_source_id and property_names caches so first
        real operation doesn't pay extra round trips.
        """
        try:
            self._enforce_rate_limit()
            db = self.client.databases.retrieve(database_id=self.database_id)
            db_title = db.get("title", [{}])[0].get("plain_text", "Unknown")
            self.logger.info(f"✅ Connected to Notion database: {db_title}")

            self._get_data_source_id()
            self._detect_property_names()
        except APIResponseError as e:
            error_code = getattr(e, 'code', 'unknown')
            error_msg = str(e)

            # Raised as bare Exception (not chained) so the help text is what
            # the user sees first; original APIResponseError is in `error_msg`.
            help_msg = self._build_connection_error_help(error_code, error_msg)
            raise Exception(help_msg)

    def _build_connection_error_help(self, error_code: str, error_msg: str) -> str:
        """Compose a multi-line setup-troubleshooting string for CLI display."""
        base_msg = f"\n\n❌ Could not connect to Notion database\n"
        base_msg += f"Error: {error_msg}\n\n"
        
        base_msg += "🔧 Troubleshooting Steps:\n\n"
        
        if "object_not_found" in error_msg.lower() or "could not find database" in error_msg.lower():
            base_msg += "1. ✓ Make sure the database is SHARED with your integration:\n"
            base_msg += "   • Open your Notion database\n"
            base_msg += "   • Click '...' (three dots) in the top right\n"
            base_msg += "   • Select 'Add connections'\n"
            base_msg += "   • Find and add your integration\n\n"
            
            base_msg += "2. ✓ Verify the database ID is correct:\n"
            base_msg += f"   • Current ID: {self.database_id}\n"
            base_msg += "   • Get it from the database URL: https://notion.so/YOUR-ID-HERE?v=...\n"
            base_msg += "   • The ID is the part between notion.so/ and ?v=\n\n"
            
        elif "unauthorized" in error_msg.lower():
            base_msg += "1. ✓ Check your integration token:\n"
            base_msg += "   • Go to https://www.notion.so/my-integrations\n"
            base_msg += "   • Make sure your integration is active\n"
            base_msg += "   • Copy the 'Internal Integration Token'\n\n"
            
            base_msg += "2. ✓ Update your configuration:\n"
            base_msg += "   • Run: extract-usernames --reconfigure\n"
            base_msg += "   • Choose 'notion' and enter the correct token\n\n"
        
        else:
            base_msg += "1. ✓ Verify database sharing (most common issue):\n"
            base_msg += "   • Open the database in Notion\n"
            base_msg += "   • Click 'Share' button\n"
            base_msg += "   • Add your integration to the database\n\n"
            
            base_msg += "2. ✓ Check integration token:\n"
            base_msg += "   • Visit: https://www.notion.so/my-integrations\n"
            base_msg += "   • Verify the token is correct\n\n"
            
            base_msg += "3. ✓ Verify database ID:\n"
            base_msg += f"   • Current: {self.database_id}\n"
            base_msg += "   • Get from URL: https://notion.so/[DATABASE-ID]?v=...\n\n"
        
        base_msg += "📖 Full Setup Guide:\n"
        base_msg += "   https://github.com/beyourahi/extract_usernames#notion-integration\n\n"
        
        base_msg += "💡 Quick Fix: Run 'extract-usernames --reconfigure' to update settings\n"
        
        return base_msg
    
    def get_all_existing_usernames(self, force_refresh: bool = False) -> Set[str]:
        """Returns set of lowercased usernames currently in the DB title column.

        Used by `batch_create_pages` for dedup. Cached in
        `_existing_usernames_cache`; `create_page` updates the cache in-place
        on success so subsequent batches don't need to refetch.
        Paginates 100 rows/page.
        """
        if self._existing_usernames_cache is not None and not force_refresh:
            return self._existing_usernames_cache

        usernames = set()
        has_more = True
        start_cursor = None
        data_source_id = self._get_data_source_id()
        prop_names = self._detect_property_names()
        title_prop = prop_names.get('title', 'Brand Name')

        while has_more:
            self._enforce_rate_limit()

            query_params = {"page_size": 100}
            if start_cursor:
                query_params["start_cursor"] = start_cursor

            # Uses new `data_sources.query` API (not legacy `databases.query`).
            response = self.client.data_sources.query(
                data_source_id=data_source_id,
                **query_params
            )

            for page in response.get("results", []):
                props = page.get("properties", {})
                brand_name_prop = props.get(title_prop, {})
                title_list = brand_name_prop.get("title", [])
                if title_list:
                    username = title_list[0].get("plain_text", "").strip().lower()
                    if username:
                        usernames.add(username)

            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")

        self._existing_usernames_cache = usernames
        return usernames

    def create_page(self, username: str, instagram_url: str, status: str = "Didn't Approach") -> Dict:
        """POST a new page; mutates the existing-usernames cache on success.

        `status="Didn't Approach"` matches the canonical Notion status-option
        name on the original DB. If the status property is not present in the
        detected schema, the status field is omitted from the payload (page
        still created without it).

        Returns: `{'success': bool, 'page_id': str|None, 'url': str|None, 'error': str|None}`.
        Never raises — all exceptions captured into `error`.
        """
        result = {'success': False, 'page_id': None, 'url': None, 'error': None}

        try:
            self._enforce_rate_limit()

            prop_names = self._detect_property_names()
            title_prop = prop_names.get('title', 'Brand Name')
            url_prop = prop_names.get('url', 'Social Media Account')
            status_prop = prop_names.get('status', 'Status')

            properties = {
                title_prop: {
                    "title": [
                        {
                            "text": {
                                "content": username
                            }
                        }
                    ]
                },
                url_prop: {
                    "url": instagram_url
                }
            }

            # Status omitted from payload if not detected — failing here would
            # break DBs without a status column.
            if status_prop:
                properties[status_prop] = {
                    "status": {
                        "name": status
                    }
                }

            # New Notion API: page parent must be `data_source_id`, not `database_id`.
            data_source_id = self._get_data_source_id()

            page = self.client.pages.create(
                parent={"data_source_id": data_source_id},
                properties=properties
            )
            result['success'] = True
            result['page_id'] = page.get("id")
            result['url'] = page.get("url")

            self.logger.info(f"✅ Created page for @{username}")

            # Keep cache coherent so batch callers don't double-create.
            if self._existing_usernames_cache is not None:
                self._existing_usernames_cache.add(username.lower())

        except APIResponseError as e:
            error_msg = str(e)
            self.logger.error(f"❌ Notion API error for @{username}: {error_msg}")
            result['error'] = f"Notion API error: {error_msg}"
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"❌ Unexpected error for @{username}: {error_msg}")
            result['error'] = f"Unexpected error: {error_msg}"

        return result

    def batch_create_pages(self, validated_accounts: List[Dict], skip_duplicates: bool = True) -> Dict[str, int]:
        """Sequential page creation with pre-fetched dedup set.

        `validated_accounts` items must have keys `username` and `url`;
        missing either bumps `failed`. `skip_duplicates=True` fetches the full
        existing-set once (cached) at start.

        Failure mode: if existing-set fetch itself raises, `existing` stays
        empty and dedup silently degrades to "create everything" — not raised.
        """
        stats = {'total': len(validated_accounts), 'created': 0, 'failed': 0, 'skipped': 0, 'errors': []}

        existing = set()
        if skip_duplicates:
            try:
                existing = self.get_all_existing_usernames()
            except Exception:
                # Silent degrade: missing dedup set means we MIGHT create dups,
                # but the post-sync deduplicator will catch them.
                pass

        for account in validated_accounts:
            username = account.get('username', '')
            url = account.get('url', '')

            if not username or not url:
                stats['failed'] += 1
                continue

            if skip_duplicates and username.lower() in existing:
                stats['skipped'] += 1
                continue

            result = self.create_page(username, url)
            if result['success']:
                stats['created'] += 1
            else:
                stats['failed'] += 1
                stats['errors'].append(f"{username}: {result['error']}")

        return stats

    def get_database_info(self) -> Dict:
        """DB metadata snapshot. Returns `{}` on any error (no exception propagation)."""
        try:
            self._enforce_rate_limit()
            db = self.client.databases.retrieve(database_id=self.database_id)
            return {
                'id': db.get('id'),
                'title': db.get("title", [{}])[0].get("plain_text", "Unknown"),
                'url': db.get('url'),
                'properties': list(db.get('properties', {}).keys())
            }
        except Exception:
            return {}
