#!/usr/bin/env python3
"""Out-of-band Notion deduplication CLI.

Standalone entry point — NOT registered in `pyproject.toml [project.scripts]`,
invoked via `python -m extract_usernames.cli_merge_duplicates`. Reuses saved
`ConfigManager` token/database_id unless overridden by `--token`/`--database-id`.

Diverges from the in-sync deduplicator (notion_sync.py):
- Supports `keep_strategy` (oldest/newest) instead of quality-score selection.
- Calls `NotionDeduplicator.run_deduplication`, not `.deduplicate` — see notion_deduplicator.py.
"""

import click
import logging
from pathlib import Path

from .config import ConfigManager
from .integrations.notion_manager import NotionDatabaseManager
from .integrations.notion_deduplicator import NotionDeduplicator

# Plain message format — deduplicator emits human-readable progress lines
# with emoji that get mangled by default `%(levelname)s:%(name)s:%(message)s`.
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
    """Merge duplicate Notion entries by Instagram URL, archiving losers.

    \b
    Examples:
      merge-duplicates                          # Use saved config
      merge-duplicates --keep-strategy newest   # Keep newest entries
      merge-duplicates --dry-run                # Preview without changes
      merge-duplicates -t TOKEN -d DB_ID        # Use custom credentials

    KNOWN ISSUE: invokes `deduplicator.run_deduplication(...)` with kwargs
    `keep_strategy` and `dry_run`, but `NotionDeduplicator` (see
    notion_deduplicator.py) only exposes `.deduplicate(property_names, dry_run)`
    and a module-level `run_deduplication(...)`. This command currently raises
    AttributeError at runtime unless that method is added on the class.
    """
    config_manager = ConfigManager()

    # CLI flags take precedence over saved config; missing credentials fail loudly.
    if use_config and config_manager.exists():
        config = config_manager.load()
        notion_token = token if token else config.get('notion', {}).get('token')
        db_id = database_id if database_id else config.get('notion', {}).get('database_id')
    else:
        notion_token = token
        db_id = database_id

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

        # NotionDatabaseManager.__init__ triggers `_verify_connection` (network I/O)
        # which can raise. `_get_data_source_id` is required by the new Notion
        # data_sources API — `data_source_id` ≠ `database_id` for multi-source DBs.
        notion_manager = NotionDatabaseManager(notion_token, db_id)
        data_source_id = notion_manager._get_data_source_id()

        deduplicator = NotionDeduplicator(
            notion_manager.client,
            db_id,
            data_source_id
        )

        stats = deduplicator.run_deduplication(
            keep_strategy=keep_strategy,
            dry_run=dry_run
        )

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
