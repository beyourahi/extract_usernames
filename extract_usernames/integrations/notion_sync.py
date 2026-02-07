"""Instagram Leads to Notion Sync (formerly leads_to_notion.py).

Main orchestration script for validating Instagram usernames and syncing to Notion.
Handles duplicate detection, validation, batch operations, and deduplication.

Author: Rahi Khan (Dropout Studio)
License: MIT
"""

import os
import sys
import json
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Set, Optional

from .instagram_validator import InstagramValidator
from .notion_manager import NotionDatabaseManager
from .notion_deduplicator import NotionDeduplicator


def load_usernames_from_markdown(file_path: Path) -> List[str]:
    """Load Instagram usernames from a markdown file.
    
    Handles various formats:
    - Plain usernames: username1
    - Bullet lists: - username1, * username1, • username1
    - Numbered lists: 1. username1, 2. username1
    - With @ symbol: @username1
    
    Args:
        file_path: Path to markdown file
        
    Returns:
        List of usernames
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    
    usernames = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines and headers
            if not line or line.startswith('#'):
                continue
            
            # Remove common list prefixes: bullets, numbers, @ symbols
            # Patterns: "- ", "* ", "• ", "@", "1. ", "2. ", etc.
            line = re.sub(r'^[-*•@]\s*', '', line)  # Remove bullet/@ prefix
            line = re.sub(r'^\d+\.\s*', '', line)   # Remove numbered list prefix
            line = line.strip()
            
            if not line:
                continue
            
            # Extract first word as username (handles multiple words on same line)
            username = line.split()[0] if line else None
            
            # Additional cleanup: remove @ if it's still there
            if username:
                username = username.lstrip('@').strip()
                if username:
                    usernames.append(username)
    
    return usernames


def run_notion_sync(
    input_file: Path,
    token: str,
    database_id: str,
    skip_validation: bool = False,
    delay: float = 2.0,
    merge_duplicates: bool = False,
    keep_strategy: str = "oldest",
    dry_run_merge: bool = False,
) -> Dict[str, int]:
    """Run Notion sync workflow.
    
    Args:
        input_file: Path to markdown file with usernames
        token: Notion integration token
        database_id: Notion database ID
        skip_validation: Skip Instagram validation
        delay: Delay between Instagram requests
        merge_duplicates: Merge duplicate entries after sync
        keep_strategy: 'oldest' or 'newest' when merging
        dry_run_merge: Preview merge without making changes
    
    Returns:
        Statistics dictionary with counts
    """
    stats = {
        'added_count': 0,
        'duplicate_count': 0,
        'invalid_count': 0,
        'merge_stats': None,
    }
    
    # Load usernames
    usernames = load_usernames_from_markdown(input_file)
    if not usernames:
        return stats
    
    # Connect to Notion
    notion = NotionDatabaseManager(token, database_id)
    existing = notion.get_all_existing_usernames()
    
    # Filter duplicates
    usernames = [u for u in usernames if u.lower() not in existing]
    stats['duplicate_count'] = len(usernames) - len(set(u.lower() for u in usernames))
    
    if not usernames:
        logging.info("✅ No new usernames to sync")
    else:
        # Validate on Instagram
        valid_accounts = []
        
        if skip_validation:
            valid_accounts = [
                {'username': u, 'url': f"https://instagram.com/{u}", 'exists': True}
                for u in usernames
            ]
        else:
            with InstagramValidator(delay_between_requests=delay) as validator:
                validation_results = validator.validate_batch(usernames)
                valid_accounts = [r for r in validation_results if r['exists']]
                stats['invalid_count'] = len(usernames) - len(valid_accounts)
        
        # Sync to Notion
        if valid_accounts:
            sync_stats = notion.batch_create_pages(valid_accounts, skip_duplicates=False)
            stats['added_count'] = sync_stats['created']
    
    # Merge duplicates if requested
    if merge_duplicates:
        logging.info("\n" + "=" * 70)
        logging.info("🔄 Merging Duplicates")
        logging.info("=" * 70)
        
        # Get data_source_id from notion manager
        data_source_id = notion._get_data_source_id()
        
        # Run deduplication
        deduplicator = NotionDeduplicator(
            notion.client,
            database_id,
            data_source_id
        )
        
        merge_stats = deduplicator.run_deduplication(
            keep_strategy=keep_strategy,
            dry_run=dry_run_merge
        )
        
        stats['merge_stats'] = merge_stats
    
    return stats
