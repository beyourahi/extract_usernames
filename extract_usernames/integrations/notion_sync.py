"""Instagram Leads to Notion Sync (formerly leads_to_notion.py).

Main orchestration script for validating Instagram usernames and syncing to Notion.
Handles duplicate detection, validation, batch operations, and smart deduplication.

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
    auto_deduplicate: bool = True,
    dry_run_dedup: bool = False,
) -> Dict[str, int]:
    """Run Notion sync workflow with optional deduplication.
    
    Args:
        input_file: Path to markdown file with usernames
        token: Notion integration token
        database_id: Notion database ID
        skip_validation: Skip Instagram validation
        delay: Delay between Instagram requests
        auto_deduplicate: Automatically deduplicate after sync
        dry_run_dedup: Preview deduplication without removing
    
    Returns:
        Statistics dictionary with counts
    """
    logger = logging.getLogger(__name__)
    
    stats = {
        'added_count': 0,
        'duplicate_count': 0,
        'invalid_count': 0,
        'dedup_stats': None,
    }
    
    # Load usernames
    usernames = load_usernames_from_markdown(input_file)
    if not usernames:
        logger.info("ℹ️  No usernames found in input file")
        return stats
    
    # Connect to Notion
    notion = NotionDatabaseManager(token, database_id)
    existing = notion.get_all_existing_usernames()
    
    # Filter duplicates
    unique_usernames = list(set(u.lower() for u in usernames))
    new_usernames = [u for u in usernames if u.lower() not in existing]
    stats['duplicate_count'] = len(usernames) - len(unique_usernames)
    
    if not new_usernames:
        logger.info("✅ No new usernames to sync (all already in Notion)")
    else:
        # Validate on Instagram
        valid_accounts = []
        
        if skip_validation:
            valid_accounts = [
                {'username': u, 'url': f"https://instagram.com/{u}", 'exists': True}
                for u in new_usernames
            ]
        else:
            with InstagramValidator(delay_between_requests=delay) as validator:
                validation_results = validator.validate_batch(new_usernames)
                valid_accounts = [r for r in validation_results if r['exists']]
                stats['invalid_count'] = len(new_usernames) - len(valid_accounts)
        
        # Sync to Notion
        if valid_accounts:
            sync_stats = notion.batch_create_pages(valid_accounts, skip_duplicates=False)
            stats['added_count'] = sync_stats['created']
    
    # Run deduplication if requested
    if auto_deduplicate:
        logger.info("\n" + "=" * 70)
        logger.info("🧹 Smart Deduplication")
        logger.info("=" * 70)
        
        # Get data_source_id and property names from notion manager
        data_source_id = notion._get_data_source_id()
        property_names = notion._detect_property_names()
        
        # Run deduplication
        deduplicator = NotionDeduplicator(
            notion.client,
            database_id,
            data_source_id
        )
        
        dedup_stats = deduplicator.deduplicate(
            property_names=property_names,
            dry_run=dry_run_dedup
        )
        
        stats['dedup_stats'] = dedup_stats
        
        # Log results
        if dry_run_dedup:
            logger.info(f"\n📊 Deduplication Preview (Dry Run):")
            logger.info(f"   Duplicate groups found: {dedup_stats['duplicate_groups']}")
            logger.info(f"   Total duplicates: {dedup_stats['duplicates_found']}")
            logger.info(f"   💡 Run without --dry-run to remove duplicates")
        else:
            logger.info(f"\n✅ Deduplication Complete:")
            logger.info(f"   Duplicate groups: {dedup_stats['duplicate_groups']}")
            logger.info(f"   Duplicates removed: {dedup_stats['duplicates_removed']}")
            if dedup_stats['errors'] > 0:
                logger.warning(f"   ⚠️  Errors: {dedup_stats['errors']}")
    
    return stats
