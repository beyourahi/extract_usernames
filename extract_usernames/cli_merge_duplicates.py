#!/usr/bin/env python3
"""Standalone CLI for merging Notion database duplicates.

Merges duplicate entries based on Instagram URL after Notion sync.
"""

import click
import logging
from pathlib import Path

from .config import ConfigManager
from .integrations.notion_manager import NotionDatabaseManager
from .integrations.notion_deduplicator import NotionDeduplicator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)


@click.command()
@click.option('--token', '-t', type=str, help='Notion integration token (overrides config)')
@click.option('--database-id', '-d', type=str, help='Database ID (overrides config)')
@click.option('--keep-strategy', type=click.Choice(['oldest', 'newest']), default='oldest', help='Which duplicate to keep')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying them')
@click.option('--use-config', is_flag=True, default=True, help='Use saved config (default: True)')
@click.version_option(version='1.0.0', prog_name='Notion Duplicate Merger')
def main(
    token: str,
    database_id: str,
    keep_strategy: str,
    dry_run: bool,
    use_config: bool,
):
    """Merge duplicate entries in Notion database by Instagram URL.
    
    Finds all duplicate entries based on Instagram URL and merges them,
    keeping the oldest/newest entry and archiving the rest.
    
    \b
    Examples:
      merge-duplicates                          # Use saved config
      merge-duplicates --keep-strategy newest   # Keep newest entries
      merge-duplicates --dry-run                # Preview without changes
      merge-duplicates -t TOKEN -d DB_ID        # Use custom credentials
    """
    config_manager = ConfigManager()
    
    # Load config if using it
    if use_config and config_manager.exists():
        config = config_manager.load()
        notion_token = token if token else config.get('notion', {}).get('token')
        db_id = database_id if database_id else config.get('notion', {}).get('database_id')
    else:
        notion_token = token
        db_id = database_id
    
    # Validate credentials
    if not notion_token:
        click.secho("\n❌ Error: Notion token not provided", fg="red")
        click.echo("\nProvide token via:")
        click.echo("  • --token flag")
        click.echo("  • Saved config (run: extract-usernames --reconfigure)")
        return
    
    if not db_id:
        click.secho("\n❌ Error: Database ID not provided", fg="red")
        click.echo("\nProvide database ID via:")
        click.echo("  • --database-id flag")
        click.echo("  • Saved config (run: extract-usernames --reconfigure)")
        return
    
    try:
        click.echo("\n" + "=" * 70)
        click.secho("🔄 Notion Duplicate Merger", fg="cyan", bold=True)
        click.echo("=" * 70)
        
        if dry_run:
            click.secho("🔍 DRY RUN MODE - No changes will be made\n", fg="yellow", bold=True)
        
        click.echo(f"Keep strategy: {keep_strategy}")
        click.echo("=" * 70 + "\n")
        
        # Connect to Notion
        notion_manager = NotionDatabaseManager(notion_token, db_id)
        data_source_id = notion_manager._get_data_source_id()
        
        # Run deduplication
        deduplicator = NotionDeduplicator(
            notion_manager.client,
            db_id,
            data_source_id
        )
        
        stats = deduplicator.run_deduplication(
            keep_strategy=keep_strategy,
            dry_run=dry_run
        )
        
        # Show results
        click.echo("\n" + "=" * 70)
        click.secho("✅ Merge Complete!", fg="green", bold=True)
        click.echo("=" * 70)
        click.echo(f"Duplicate groups found: {stats['duplicate_groups']}")
        click.echo(f"Entries kept: {stats['kept']}")
        click.echo(f"Entries archived: {stats['archived']}")
        
        if stats['errors'] > 0:
            click.secho(f"Errors encountered: {stats['errors']}", fg="yellow")
        
        if dry_run:
            click.echo("\n💡 Run without --dry-run to apply changes")
        
    except KeyboardInterrupt:
        click.echo("\n\n⚠️  Cancelled by user.")
        return
    except Exception as e:
        click.secho(f"\n❌ Error: {e}", fg="red")
        import traceback
        click.echo("\n" + traceback.format_exc())
        return


if __name__ == '__main__':
    main()
