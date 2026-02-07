"""Notion Database Deduplicator.

Merges duplicate entries in Notion database based on Instagram URL.
Keeps the most complete record and archives duplicates.

Author: Rahi Khan (Dropout Studio)
License: MIT
"""

import logging
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from datetime import datetime

from notion_client import Client
from notion_client.errors import APIResponseError


class NotionDeduplicator:
    """Handles duplicate detection and merging in Notion databases."""
    
    def __init__(self, client: Client, database_id: str, data_source_id: str):
        """Initialize deduplicator.
        
        Args:
            client: Authenticated Notion client
            database_id: Database ID
            data_source_id: Data source ID for querying
        """
        self.client = client
        self.database_id = database_id
        self.data_source_id = data_source_id
        self.logger = logging.getLogger(__name__)
    
    def find_duplicates(self) -> Dict[str, List[Dict]]:
        """Find all duplicate entries grouped by Instagram URL.
        
        Returns:
            Dictionary mapping URLs to list of duplicate pages
        """
        url_to_pages = defaultdict(list)
        has_more = True
        start_cursor = None
        
        self.logger.info("🔍 Scanning database for duplicates...")
        
        while has_more:
            query_params = {"page_size": 100}
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            try:
                response = self.client.data_sources.query(
                    data_source_id=self.data_source_id,
                    **query_params
                )
                
                for page in response.get("results", []):
                    page_id = page.get("id")
                    props = page.get("properties", {})
                    created_time = page.get("created_time")
                    
                    # Extract Instagram URL from properties
                    instagram_url = None
                    for prop_name, prop_data in props.items():
                        if prop_data.get("type") == "url":
                            instagram_url = prop_data.get("url")
                            if instagram_url:
                                break
                    
                    if instagram_url:
                        # Normalize URL (remove trailing slashes, lowercase)
                        normalized_url = instagram_url.lower().rstrip('/')
                        
                        url_to_pages[normalized_url].append({
                            'id': page_id,
                            'created_time': created_time,
                            'properties': props,
                            'url': page.get('url'),
                        })
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
                
            except Exception as e:
                self.logger.error(f"Error querying database: {e}")
                break
        
        # Filter to only URLs with duplicates
        duplicates = {url: pages for url, pages in url_to_pages.items() if len(pages) > 1}
        
        return duplicates
    
    def merge_duplicates(
        self,
        duplicates: Dict[str, List[Dict]],
        keep_strategy: str = "oldest",
        dry_run: bool = False
    ) -> Dict[str, int]:
        """Merge duplicate entries, keeping one and archiving others.
        
        Args:
            duplicates: Dictionary of URL -> list of duplicate pages
            keep_strategy: Which entry to keep ('oldest' or 'newest')
            dry_run: If True, only report what would be done without making changes
        
        Returns:
            Statistics dictionary with merge counts
        """
        stats = {
            'duplicate_groups': len(duplicates),
            'total_duplicates': sum(len(pages) - 1 for pages in duplicates.values()),
            'archived': 0,
            'kept': 0,
            'errors': 0,
        }
        
        if dry_run:
            self.logger.info("\n🔍 DRY RUN MODE - No changes will be made\n")
        
        for instagram_url, pages in duplicates.items():
            # Sort by creation time
            sorted_pages = sorted(
                pages,
                key=lambda p: p['created_time'],
                reverse=(keep_strategy == "newest")
            )
            
            # Keep the first one based on strategy
            page_to_keep = sorted_pages[0]
            pages_to_archive = sorted_pages[1:]
            
            # Extract username for logging
            username = self._extract_username_from_url(instagram_url)
            
            self.logger.info(f"\n📌 @{username}")
            self.logger.info(f"   Found {len(pages)} copies")
            self.logger.info(f"   ✅ Keeping: {page_to_keep['created_time'][:10]} ({page_to_keep['url']})")
            
            # Archive duplicates
            for page in pages_to_archive:
                self.logger.info(f"   🗑️  Archiving: {page['created_time'][:10]} ({page['url']})")
                
                if not dry_run:
                    success = self._archive_page(page['id'])
                    if success:
                        stats['archived'] += 1
                    else:
                        stats['errors'] += 1
                else:
                    stats['archived'] += 1
            
            stats['kept'] += 1
        
        return stats
    
    def _archive_page(self, page_id: str) -> bool:
        """Archive a page by setting archived=True.
        
        Args:
            page_id: ID of page to archive
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.pages.update(
                page_id=page_id,
                archived=True
            )
            return True
        except APIResponseError as e:
            self.logger.error(f"Failed to archive page {page_id}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error archiving page {page_id}: {e}")
            return False
    
    def _extract_username_from_url(self, url: str) -> str:
        """Extract Instagram username from URL.
        
        Args:
            url: Instagram URL
        
        Returns:
            Username or URL if extraction fails
        """
        try:
            parts = url.rstrip('/').split('/')
            return parts[-1] if parts else url
        except:
            return url
    
    def run_deduplication(
        self,
        keep_strategy: str = "oldest",
        dry_run: bool = False
    ) -> Dict[str, int]:
        """Run full deduplication workflow.
        
        Args:
            keep_strategy: Which entry to keep ('oldest' or 'newest')
            dry_run: If True, only report without making changes
        
        Returns:
            Statistics dictionary
        """
        # Find duplicates
        duplicates = self.find_duplicates()
        
        if not duplicates:
            self.logger.info("✅ No duplicates found!")
            return {
                'duplicate_groups': 0,
                'total_duplicates': 0,
                'archived': 0,
                'kept': 0,
                'errors': 0,
            }
        
        # Show summary
        total_dupes = sum(len(pages) - 1 for pages in duplicates.values())
        self.logger.info(f"\n📊 Found {len(duplicates)} accounts with duplicates")
        self.logger.info(f"   Total duplicate entries to merge: {total_dupes}\n")
        
        # Merge duplicates
        stats = self.merge_duplicates(duplicates, keep_strategy, dry_run)
        
        return stats


def run_notion_deduplication(
    token: str,
    database_id: str,
    data_source_id: str,
    keep_strategy: str = "oldest",
    dry_run: bool = False,
) -> Dict[str, int]:
    """Standalone function to run deduplication.
    
    Args:
        token: Notion integration token
        database_id: Database ID
        data_source_id: Data source ID
        keep_strategy: 'oldest' or 'newest'
        dry_run: If True, only report without changes
    
    Returns:
        Statistics dictionary
    """
    client = Client(auth=token)
    deduplicator = NotionDeduplicator(client, database_id, data_source_id)
    return deduplicator.run_deduplication(keep_strategy, dry_run)
