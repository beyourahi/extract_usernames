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
        # Clean database ID - remove dashes and any URL parts
        self.database_id = self._clean_database_id(database_id)
        self.logger = logging.getLogger(__name__)
        self._last_request_time = 0
        self._existing_usernames_cache: Optional[Set[str]] = None
        self._data_source_id: Optional[str] = None
        self._property_names: Optional[Dict[str, str]] = None
        self._verify_connection()
    
    def _clean_database_id(self, db_id: str) -> str:
        """Clean and extract database ID from various formats.
        
        Supports:
        - Raw ID: 300472d4ce5181aa83f2000b8ae958d2
        - Dashed ID: 300472d4-ce51-81aa-83f2-000b8ae958d2
        - Full URL: https://notion.so/300472d4ce5181aa83f2000b8ae958d2
        - URL with dashes: https://notion.so/300472d4-ce51-81aa-83f2-000b8ae958d2?v=...
        """
        # Remove any URL prefix
        if 'notion.so/' in db_id:
            db_id = db_id.split('notion.so/')[-1]
        
        # Remove query parameters
        if '?' in db_id:
            db_id = db_id.split('?')[0]
        
        # Remove dashes
        db_id = db_id.replace('-', '')
        
        return db_id
    
    def _enforce_rate_limit(self):
        if self._last_request_time > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.RATE_LIMIT_DELAY:
                time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()
    
    def _get_data_source_id(self) -> str:
        """Get the data source ID from the database.
        
        For databases with a single data source, returns that data source ID.
        For multi-source databases, returns the first data source ID.
        """
        if self._data_source_id:
            return self._data_source_id
        
        try:
            self._enforce_rate_limit()
            db = self.client.databases.retrieve(database_id=self.database_id)
            
            # Get data sources from database
            data_sources = db.get('data_sources', [])
            
            if not data_sources:
                # If no data sources, use database_id as fallback
                self._data_source_id = self.database_id
            else:
                # Use the first data source (most common case)
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
        """Auto-detect property names from database schema.
        
        Returns:
            Dictionary mapping logical names to actual property names:
            {'title': 'Brand Name', 'url': 'Social Media Account', 'status': 'Status'}
        """
        if self._property_names:
            return self._property_names
        
        try:
            self._enforce_rate_limit()
            db = self.client.databases.retrieve(database_id=self.database_id)
            properties = db.get('properties', {})
            
            prop_map = {}
            
            # Find title property (there's always exactly one)
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get('type')
                if prop_type == 'title':
                    prop_map['title'] = prop_name
                elif prop_type == 'url' and 'social' in prop_name.lower():
                    prop_map['url'] = prop_name
                elif prop_type == 'status':
                    prop_map['status'] = prop_name
            
            # Fallback: search by common names if not found
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
            self.logger.warning(f"Could not detect property names: {e}. Using defaults.")
            # Use default property names as fallback
            return {
                'title': 'Brand Name',
                'url': 'Social Media Account',
                'status': 'Status'
            }
    
    def _verify_connection(self):
        """Verify connection to Notion database with helpful error messages."""
        try:
            self._enforce_rate_limit()
            db = self.client.databases.retrieve(database_id=self.database_id)
            db_title = db.get("title", [{}])[0].get("plain_text", "Unknown")
            self.logger.info(f"✅ Connected to Notion database: {db_title}")
            
            # Pre-fetch data source ID and property names
            self._get_data_source_id()
            self._detect_property_names()
        except APIResponseError as e:
            error_code = getattr(e, 'code', 'unknown')
            error_msg = str(e)
            
            # Build helpful error message
            help_msg = self._build_connection_error_help(error_code, error_msg)
            raise Exception(help_msg)
    
    def _build_connection_error_help(self, error_code: str, error_msg: str) -> str:
        """Build a helpful error message with troubleshooting steps."""
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
        """Get all existing usernames from the database.
        
        Args:
            force_refresh: Force refresh the cache
            
        Returns:
            Set of lowercase usernames
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
            
            # Build query parameters for new API
            query_params = {"page_size": 100}
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            # Use data_sources.query() with data_source_id (new API)
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
        """Create a new page in the Notion database.
        
        Args:
            username: Instagram username
            instagram_url: Full Instagram profile URL
            status: Initial status (default: "Didn't Approach")
            
        Returns:
            Result dictionary with success status and details
        """
        result = {'success': False, 'page_id': None, 'url': None, 'error': None}
        
        try:
            self._enforce_rate_limit()
            
            # Get actual property names from schema
            prop_names = self._detect_property_names()
            title_prop = prop_names.get('title', 'Brand Name')
            url_prop = prop_names.get('url', 'Social Media Account')
            status_prop = prop_names.get('status', 'Status')
            
            # Build properties with actual names
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
            
            # Add status if property exists
            if status_prop:
                properties[status_prop] = {
                    "status": {
                        "name": status
                    }
                }
            
            # Use data_source_id as parent (new API requirement)
            data_source_id = self._get_data_source_id()
            
            page = self.client.pages.create(
                parent={"data_source_id": data_source_id},
                properties=properties
            )
            result['success'] = True
            result['page_id'] = page.get("id")
            result['url'] = page.get("url")
            
            self.logger.info(f"✅ Created page for @{username}")
            
            # Update cache
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
        """Batch create pages for multiple accounts.
        
        Args:
            validated_accounts: List of account dictionaries
            skip_duplicates: Skip accounts already in database
            
        Returns:
            Statistics dictionary
        """
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
        """Get database information.
        
        Returns:
            Dictionary with database metadata
        """
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
