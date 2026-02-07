#!/usr/bin/env python3
"""Command-line interface for Instagram Username Extractor."""

import sys
import click
from pathlib import Path
from typing import Optional

from .config import ConfigManager
from . import prompts


@click.command()
@click.argument('input_path', required=False, type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--no-vlm', is_flag=True, help='Disable VLM mode (EasyOCR-only)')
@click.option('--vlm-model', type=str, help='VLM model to use')
@click.option('--diagnostics', is_flag=True, help='Enable diagnostics mode')
@click.option('--reconfigure', is_flag=True, help='Reconfigure settings')
@click.option('--initial-setup', is_flag=True, hidden=True, help='Run initial setup wizard')
@click.option('--show-config', is_flag=True, help='Show current configuration and exit')
@click.option('--reset-config', is_flag=True, help='Reset configuration to defaults')
@click.option('--notion-sync', is_flag=True, help='Sync to Notion after extraction')
@click.option('--no-notion-sync', is_flag=True, help='Skip Notion sync')
@click.version_option(version='2.0.0', prog_name='Instagram Username Extractor')
def main(
    input_path: Optional[str],
    output: Optional[str],
    no_vlm: bool,
    vlm_model: Optional[str],
    diagnostics: bool,
    reconfigure: bool,
    initial_setup: bool,
    show_config: bool,
    reset_config: bool,
    notion_sync: bool,
    no_notion_sync: bool,
):
    """Extract Instagram usernames from screenshots with VLM+OCR dual-engine validation.
    
    \b
    Quick Start:
      extract-usernames                    # Use saved config, prompt for input
      extract-usernames my_screenshots     # Extract from specific folder
      extract-usernames --reconfigure      # Update settings
    
    \b
    Examples:
      extract-usernames ~/Desktop/screenshots
      extract-usernames --no-vlm --output ./results
      extract-usernames --vlm-model minicpm-v:8b-2.6-q8_0
      extract-usernames --diagnostics --notion-sync
    """
    config_manager = ConfigManager()
    
    # Handle configuration commands
    if reset_config:
        if click.confirm("\n⚠️  Reset all settings to defaults?", default=False):
            config_manager.reset()
            click.secho("✅ Configuration reset to defaults", fg="green")
        return
    
    if show_config:
        config = config_manager.load()
        config_manager.display(config)
        click.echo(f"Config file: {config_manager.get_config_path()}")
        return
    
    # Load or create configuration
    if not config_manager.exists() or initial_setup:
        click.echo("\n⚙️  No configuration found. Running initial setup...\n")
        config = prompts.run_initial_setup()
        config_manager.save(config)
        click.secho(f"\n✅ Configuration saved to: {config_manager.get_config_path()}", fg="green")
        
        # Ask to proceed with extraction
        if not click.confirm("\n🚀 Start extraction now?", default=True):
            click.echo("\nConfiguration saved! Run 'extract-usernames' anytime to start extracting.")
            return
    else:
        config = config_manager.load()
    
    # Handle reconfiguration
    if reconfigure:
        choice = prompts.prompt_reconfigure_option()
        
        if choice == 'cancel':
            click.echo("Reconfiguration cancelled.")
            return
        elif choice == 'all':
            config = prompts.run_initial_setup()
        elif choice == 'directories':
            config = prompts.reconfigure_directories(config)
        elif choice == 'extraction':
            config = prompts.reconfigure_extraction(config)
        elif choice == 'notion':
            config = prompts.reconfigure_notion(config)
        
        config_manager.save(config)
        click.secho("\n✅ Configuration updated!", fg="green")
        
        if not click.confirm("\n🚀 Start extraction now?", default=True):
            return
    
    # Show current config and confirm
    if not input_path and not any([output, no_vlm, vlm_model, diagnostics, notion_sync, no_notion_sync]):
        if not prompts.confirm_config(config):
            if click.confirm("Reconfigure settings?", default=True):
                click.echo("\nRun: extract-usernames --reconfigure")
            return
    
    # Apply CLI overrides
    extraction_config = {
        'input_dir': input_path if input_path else config['input_dir'],
        'output_dir': output if output else config['output_dir'],
        'vlm_enabled': not no_vlm if no_vlm else config['vlm_enabled'],
        'vlm_model': vlm_model if vlm_model else config.get('vlm_model', 'glm-ocr:bf16'),
        'diagnostics': diagnostics if diagnostics else config.get('diagnostics', False),
    }
    
    # Validate input directory
    input_dir = Path(extraction_config['input_dir'])
    if not input_dir.exists():
        click.secho(f"\n❌ Error: Input directory does not exist: {input_dir}", fg="red")
        click.echo(f"\nCreate it or run: extract-usernames --reconfigure")
        sys.exit(1)
    
    # Run extraction
    try:
        from .main import run_extraction
        
        click.echo("\n" + "=" * 70)
        click.secho("🚀 Starting Extraction", fg="cyan", bold=True)
        click.echo("=" * 70)
        click.echo(f"Input:  {extraction_config['input_dir']}")
        click.echo(f"Output: {extraction_config['output_dir']}")
        click.echo(f"Mode:   {'VLM+OCR' if extraction_config['vlm_enabled'] else 'EasyOCR-only'}")
        click.echo("=" * 70 + "\n")
        
        results = run_extraction(
            input_dir=extraction_config['input_dir'],
            output_dir=extraction_config['output_dir'],
            use_vlm=extraction_config['vlm_enabled'],
            vlm_model=extraction_config['vlm_model'],
            diagnostics=extraction_config['diagnostics'],
        )
        
        click.secho(f"\n✅ Extraction complete!", fg="green", bold=True)
        click.echo(f"Verified usernames: {results.get('verified_count', 0)}")
        click.echo(f"Needs review: {results.get('review_count', 0)}")
        click.echo(f"\nResults saved to: {extraction_config['output_dir']}")
        
        # Handle Notion sync
        should_sync = False
        if notion_sync:
            should_sync = True
        elif no_notion_sync:
            should_sync = False
        elif config['notion']['enabled'] and config['notion'].get('auto_sync', False):
            should_sync = prompts.prompt_notion_sync()
        
        if should_sync and config['notion']['enabled']:
            click.echo("\n" + "=" * 70)
            click.secho("📤 Syncing to Notion", fg="cyan", bold=True)
            click.echo("=" * 70 + "\n")
            
            from .notion_sync import run_notion_sync
            
            notion_results = run_notion_sync(
                input_file=Path(extraction_config['output_dir']) / "verified_usernames.md",
                token=config['notion']['token'],
                database_id=config['notion']['database_id'],
                skip_validation=config['notion']['skip_validation'],
                delay=config['notion']['validation_delay'],
            )
            
            click.secho(f"\n✅ Notion sync complete!", fg="green", bold=True)
            click.echo(f"Added to Notion: {notion_results.get('added_count', 0)}")
            click.echo(f"Duplicates skipped: {notion_results.get('duplicate_count', 0)}")
        
    except KeyboardInterrupt:
        click.echo("\n\n⚠️  Extraction cancelled by user.")
        sys.exit(130)
    except Exception as e:
        click.secho(f"\n❌ Error: {e}", fg="red")
        if diagnostics or config.get('diagnostics', False):
            import traceback
            click.echo("\n" + traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()
