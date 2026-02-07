"""Notion Database Manager.

Manages Notion database operations including duplicate detection and page creation.
Designed for the "Client Hunt" database integration.

Author: Rahi Khan (Dropout Studio)
License: MIT
"""

import time
import logging
from typing import Dict, List, Set, Optional

from notion_client import Client
from notion_client.errors import APIResponseError


class NotionDatabaseManager:
    """Manages Notion database operations for Instagram lead tracking."""
    
    RATE_LIMIT_DELAY = 0.35
    
    def __init__(self, token: str, database_id: str):
        self.client = Client(auth=token)
        self.database_id = database_id.replace("-", "")
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0
        self._existing_usernames_cache: Optional[Set[str]] = None
        self._verify_connection()
    
    def _enforce_rate_limit(self):
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.RATE_LIMIT_DELAY:
                time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()
    
    def _verify_connection(self):
        try:
            self._enforce_rate_limit()
            db = self.client.databases.retrieve(database_id=self.database_id)
            db_title = db.get("title", [{}])[0].get("plain_text", "Unknown")
            self.logger.info(f"Connected to database: {db_title}")
        except APIResponseError as e:
            raise Exception(f"Could not connect to Notion database: {e}")
    
    def get_all_existing_usernames(self, force_refresh: bool = False) -> Set[str]:
        if self._existing_usernames_cache is not None and not force_refresh:
            return self._existing_usernames_cache
        
        usernames = set()
        has_more = True
        start_cursor = None
        
        while has_more:
            self._enforce_rate_limit()
            query_params = {"database_id": self.database_id, "page_size": 100}
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            response = self.client.databases.query(**query_params)
            
            for page in response.get("results", []):
                props = page.get("properties", {})
                brand_name_prop = props.get("Brand Name", {})
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
        result = {'success': False, 'page_id': None, 'url': None, 'error': None}
        
        try:
            self._enforce_rate_limit()
            properties = {
                "Brand Name": {"title": [{"text": {"content": username}}]},
                "Social Media Account": {"url": instagram_url},
                "Status": {"status": {"name": status}}
            }
            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            result['success'] = True
            result['page_id'] = page.get("id")
            result['url'] = page.get("url")
            
            if self._existing_usernames_cache is not None:
                self._existing_usernames_cache.add(username.lower())
        
        except APIResponseError as e:
            result['error'] = f"Notion API error: {e}"
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
        
        return result
    
    def batch_create_pages(self, validated_accounts: List[Dict], skip_duplicates: bool = True) -> Dict[str, int]:
        stats = {'total': len(validated_accounts), 'created': 0, 'failed': 0, 'skipped': 0, 'errors': []}
        
        existing = set()
        if skip_duplicates:
            try:
                existing = self.get_all_existing_usernames()
            except Exception:
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
