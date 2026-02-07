"""Notion Database Deduplicator.

Intelligently finds and merges duplicate entries in Notion database based on Instagram URLs.
Picks the best username from duplicates using smart scoring.

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
    """Smart deduplication for Notion database entries."""
    
    RATE_LIMIT_DELAY = 0.35
    
    def __init__(self, client: Client, database_id: str, data_source_id: str):
        """Initialize deduplicator.
        
        Args:
            client: Initialized Notion client
            database_id: Database ID
            data_source_id: Data source ID (collection ID)
        """
        self.client = client
        self.database_id = database_id
        self.data_source_id = data_source_id
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between API calls."""
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.RATE_LIMIT_DELAY:
                time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()
    
    def _score_username(self, username: str) -> int:
        """Score a username to determine quality.
        
        Higher score = better username
        
        Scoring criteria:
        - Penalize numeric prefixes like "1.", "2."
        - Reward alphabetic characters
        - Reward proper length (not too short)
        - Reward lowercase (Instagram standard)
        
        Args:
            username: Username to score
            
        Returns:
            Quality score (higher is better)
        """
        if not username:
            return 0
        
        score = 0
        
        # Heavy penalty for numeric-only or malformed usernames
        if re.match(r'^\d+\.?$', username):  # "1.", "2", etc.
            return -1000
        
        # Penalty for starting with numbers
        if username[0].isdigit():
            score -= 50
        
        # Reward for starting with letter
        if username[0].isalpha():
            score += 100
        
        # Reward for having mostly alphabetic characters
        alpha_ratio = sum(c.isalpha() for c in username) / len(username)
        score += int(alpha_ratio * 50)
        
        # Reward for reasonable length (3-30 chars is typical for Instagram)
        if 3 <= len(username) <= 30:
            score += 50
        else:
            score -= 20
        
        # Reward longer usernames (within reason)
        score += min(len(username), 15) * 2
        
        # Small reward for lowercase (Instagram standard)
        if username.islower() or username.replace('_', '').replace('.', '').islower():
            score += 10
        
        return score
    
    def _pick_best_username(self, entries: List[Dict]) -> Tuple[str, str]:
        """Pick the best username and page_id from a list of duplicate entries.
        
        Args:
            entries: List of page entries with same URL
            
        Returns:
            Tuple of (best_page_id, best_username)
        """
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
        """Find all duplicate entries grouped by Instagram URL.
        
        Args:
            property_names: Mapping of logical names to actual property names
                           {'title': 'Brand Name', 'url': 'Social Media Account'}
        
        Returns:
            Dictionary mapping URLs to list of entries:
            {
                'https://instagram.com/user1': [
                    {'page_id': '...', 'username': 'user1', 'url': '...'},
                    {'page_id': '...', 'username': '1.', 'url': '...'}
                ]
            }
        """
        title_prop = property_names.get('title', 'Brand Name')
        url_prop = property_names.get('url', 'Social Media Account')
        
        # Collect all pages
        url_to_entries = defaultdict(list)
        has_more = True
        start_cursor = None
        
        self.logger.info("🔍 Scanning database for duplicates...")
        
        while has_more:
            self._enforce_rate_limit()
            
            query_params = {"page_size": 100}
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            response = self.client.data_sources.query(
                data_source_id=self.data_source_id,
                **query_params
            )
            
            for page in response.get("results", []):
                page_id = page.get("id")
                props = page.get("properties", {})
                
                # Get username (title property)
                username_prop = props.get(title_prop, {})
                title_list = username_prop.get("title", [])
                username = title_list[0].get("plain_text", "").strip() if title_list else ""
                
                # Get URL
                url_prop_data = props.get(url_prop, {})
                url = url_prop_data.get("url", "").strip()
                
                if url:  # Only track entries with URLs
                    url_to_entries[url].append({
                        'page_id': page_id,
                        'username': username,
                        'url': url
                    })
            
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
        
        # Filter to only duplicates (URLs with more than one entry)
        duplicates = {url: entries for url, entries in url_to_entries.items() if len(entries) > 1}
        
        return duplicates
    
    def archive_page(self, page_id: str) -> bool:
        """Archive (soft delete) a page.
        
        Args:
            page_id: Page ID to archive
            
        Returns:
            True if successful, False otherwise
        """
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
        """Find and remove duplicates from the database.
        
        Args:
            property_names: Property name mappings
            dry_run: If True, only report duplicates without removing
            
        Returns:
            Statistics dictionary
        """
        stats = {
            'total_entries': 0,
            'duplicate_groups': 0,
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'errors': 0,
        }
        
        # Find duplicates
        duplicates = self.find_duplicates(property_names)
        
        stats['duplicate_groups'] = len(duplicates)
        
        if not duplicates:
            self.logger.info("✅ No duplicates found!")
            return stats
        
        # Process each duplicate group
        for url, entries in duplicates.items():
            stats['duplicates_found'] += len(entries) - 1  # -1 because we keep one
            
            self.logger.info(f"\n📍 Found {len(entries)} duplicates for: {url}")
            
            # Pick the best entry
            best_page_id, best_username = self._pick_best_username(entries)
            
            self.logger.info(f"   ✅ Keeping: '{best_username}' (score: {self._score_username(best_username)})")
            
            # Archive the others
            for entry in entries:
                if entry['page_id'] == best_page_id:
                    continue  # Skip the one we're keeping
                
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
    """Run deduplication workflow.
    
    Args:
        token: Notion integration token
        database_id: Notion database ID
        data_source_id: Data source ID (collection ID)
        property_names: Property name mappings
        dry_run: If True, only report without removing
        
    Returns:
        Statistics dictionary
    """
    client = Client(auth=token)
    deduplicator = NotionDeduplicator(client, database_id, data_source_id)
    
    return deduplicator.deduplicate(property_names, dry_run=dry_run)
